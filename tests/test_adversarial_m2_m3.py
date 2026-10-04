"""Adversarial stress-testing suite for Milestone 2 and Milestone 3.

Adversarial probes:
1. RBAC on GET /api/v1/flight-requests/notifications and GET /api/v1/flight-requests/export/csv
   - Unauthenticated sessions (missing, malformed, expired, revoked tokens)
   - Regular user accounts (role="PILOT", role="USER")
   - Incomplete MFA / staged sessions
   - Privilege escalation and header spoofing
2. GeoJSON export filter parameter tampering and SQL/NoSQL injection
   - Parameter injection payloads on ?visibility=
   - Data exfiltration attempts by unauthenticated/regular users
   - Soft-deleted zone leakage attempts
   - Corrupted geometry resilience and RFC 7946 compliance
3. Pi camera stream pause, disconnect_consumer lifecycle, and capture loop termination
   - Generator exit triggering disconnect_consumer()
   - Multi-consumer concurrency and reference counting
   - Idle / zero-consumer capture loop shutdown
4. Pi UI module resolution and node --check syntax verification on all 11 modules
"""
from __future__ import annotations

import csv
import io
import json
import secrets
import subprocess
import time
from datetime import timedelta
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

PI_ROOT = Path(__file__).resolve().parents[1] / "edge" / "pi5"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from pi5.web.app import PiWebConfig, create_pi_app
from pi5.web.auth import PiAuthService
from pi5.web.camera import MockCameraAdapter, V4L2CameraAdapter
from server.app.config import Settings
from server.app.main import create_app
from server.app.models import (
    Credential,
    Device,
    SessionRecord,
    SimulatedFlightRequest,
    User,
    Zone,
    ZoneSource,
)
from server.app.security import (
    digest_token,
    encrypt_secret,
    hash_password,
    new_token,
    utcnow,
)


@pytest.fixture()
def app_env(tmp_path: Path):
    db_path = tmp_path / "adv_m2_server.sqlite3"
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{db_path}",
        session_secret=secrets.token_urlsafe(32),
        cookie_secure=False,
        allowed_origins=("http://testserver", "http://localhost:5173"),
        host="127.0.0.1",
        port=8765,
        enable_test_adapters=True,
    )
    application = create_app(settings, initialize_schema=True)
    with TestClient(application) as client:
        yield application, client, settings


def _create_user(
    application,
    *,
    email: str,
    role: str = "PILOT",
    status: str = "ACTIVE",
    totp_active: bool = True,
) -> tuple[str, str]:
    """Helper creating user and returning (token, user_id)."""
    with application.state.session_factory() as db:
        username = email.split("@")[0].replace(".", "_") + f"_{secrets.token_hex(4)}"
        user = User(
            username=username,
            display_name=f"{username} Display",
            email_normalized=email.lower().strip(),
            role=role,
            status=status,
            version=1,
            email_verified_at=utcnow(),
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        user.credential = Credential(
            password_hash=hash_password("StrongP@ssw0rd!123"),
            totp_active=totp_active,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(user)
        db.flush()

        raw_token = new_token()
        token_digest = digest_token(application.state.settings.session_secret, raw_token)
        session = SessionRecord(
            user_id=user.id,
            token_digest=token_digest,
            csrf_digest=digest_token(application.state.settings.session_secret, "csrf_val"),
            stage="AUTHENTICATED",
            expires_at=utcnow() + timedelta(hours=8),
            created_at=utcnow(),
            last_seen_at=utcnow(),
        )
        db.add(session)
        db.commit()
        return raw_token, user.id


# ==============================================================================
# PROBE 1: RBAC on Notifications & CSV Export
# ==============================================================================

class TestRbacAdversarial:
    """Adversarial testing of RBAC authorization and authentication."""

    def test_notifications_unauthenticated_variations(self, app_env):
        application, client, settings = app_env

        # 1. No auth headers at all
        res = client.get("/api/v1/flight-requests/notifications")
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "AUTH_REQUIRED"

        # 2. Empty bearer token
        res = client.get("/api/v1/flight-requests/notifications", headers={"Authorization": "Bearer "})
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "AUTH_REQUIRED"

        # 3. Invalid / forged bearer token
        res = client.get("/api/v1/flight-requests/notifications", headers={"Authorization": "Bearer forged_token_abc"})
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "SESSION_INVALID"

        # 4. Expired session token
        with application.state.session_factory() as db:
            user = User(
                username="exp_user",
                display_name="Exp User",
                email_normalized="exp@drone.local",
                role="OPERATOR",
                status="ACTIVE",
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.add(user)
            db.flush()
            exp_token = new_token()
            db.add(SessionRecord(
                user_id=user.id,
                token_digest=digest_token(settings.session_secret, exp_token),
                csrf_digest=digest_token(settings.session_secret, "csrf"),
                stage="AUTHENTICATED",
                expires_at=utcnow() - timedelta(minutes=10),
                created_at=utcnow() - timedelta(hours=1),
                last_seen_at=utcnow() - timedelta(minutes=10),
            ))
            db.commit()

        res = client.get("/api/v1/flight-requests/notifications", headers={"Authorization": f"Bearer {exp_token}"})
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "SESSION_INVALID"

        # 5. Revoked session token
        with application.state.session_factory() as db:
            rev_token = new_token()
            db.add(SessionRecord(
                user_id=user.id,
                token_digest=digest_token(settings.session_secret, rev_token),
                csrf_digest=digest_token(settings.session_secret, "csrf"),
                stage="AUTHENTICATED",
                expires_at=utcnow() + timedelta(hours=1),
                revoked_at=utcnow() - timedelta(minutes=5),
                created_at=utcnow() - timedelta(hours=1),
                last_seen_at=utcnow() - timedelta(minutes=5),
            ))
            db.commit()

        res = client.get("/api/v1/flight-requests/notifications", headers={"Authorization": f"Bearer {rev_token}"})
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "SESSION_INVALID"

    def test_notifications_staged_2fa_rejected(self, app_env):
        application, client, settings = app_env
        with application.state.session_factory() as db:
            user = User(
                username="staged_user",
                display_name="Staged User",
                email_normalized="staged@drone.local",
                role="OPERATOR",
                status="ACTIVE",
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.add(user)
            db.flush()
            staged_token = new_token()
            db.add(SessionRecord(
                user_id=user.id,
                token_digest=digest_token(settings.session_secret, staged_token),
                csrf_digest=digest_token(settings.session_secret, "csrf"),
                stage="STAGED_2FA",  # Has not completed MFA
                expires_at=utcnow() + timedelta(hours=1),
                created_at=utcnow(),
                last_seen_at=utcnow(),
            ))
            db.commit()

        res = client.get("/api/v1/flight-requests/notifications", headers={"Authorization": f"Bearer {staged_token}"})
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "MFA_INCOMPLETE"

    def test_notifications_role_isolation_pilots_and_users_blocked(self, app_env):
        application, client, _ = app_env

        # 1. Pilot role
        pilot_token, _ = _create_user(application, email="pilot@drone.local", role="PILOT")
        res = client.get("/api/v1/flight-requests/notifications", headers={"Authorization": f"Bearer {pilot_token}"})
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"

        # 2. General user role
        user_token, _ = _create_user(application, email="regular@drone.local", role="USER")
        res = client.get("/api/v1/flight-requests/notifications", headers={"Authorization": f"Bearer {user_token}"})
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"

        # 3. Viewer role
        viewer_token, _ = _create_user(application, email="viewer@drone.local", role="VIEWER")
        res = client.get("/api/v1/flight-requests/notifications", headers={"Authorization": f"Bearer {viewer_token}"})
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"

    def test_notifications_header_spoofing_attempts(self, app_env):
        application, client, _ = app_env
        pilot_token, _ = _create_user(application, email="attacker@drone.local", role="PILOT")

        spoofed_headers = {
            "Authorization": f"Bearer {pilot_token}",
            "X-User-Role": "ADMIN",
            "X-Role": "OWNER",
            "X-Forwarded-Role": "OPERATOR",
            "X-Admin": "true",
            "X-Original-User": "admin@drone.local",
        }
        res = client.get("/api/v1/flight-requests/notifications", headers=spoofed_headers)
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"

    def test_notifications_reviewer_roles_succeed(self, app_env):
        application, client, _ = app_env

        for role in ["OPERATOR", "ADMIN", "OWNER"]:
            token, _ = _create_user(application, email=f"{role.lower()}@drone.local", role=role)
            res = client.get("/api/v1/flight-requests/notifications", headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 200
            data = res.json()["data"]
            assert "pending_count" in data
            assert "items" in data

    def test_csv_export_unauthenticated_and_regular_users_rejected(self, app_env):
        application, client, _ = app_env

        # 1. Unauthenticated
        res = client.get("/api/v1/flight-requests/export/csv")
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "AUTH_REQUIRED"

        # 2. Pilot user
        pilot_token, _ = _create_user(application, email="pilot2@drone.local", role="PILOT")
        res = client.get("/api/v1/flight-requests/export/csv", headers={"Authorization": f"Bearer {pilot_token}"})
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"

        # 3. Regular user
        user_token, _ = _create_user(application, email="user2@drone.local", role="USER")
        res = client.get("/api/v1/flight-requests/export/csv", headers={"Authorization": f"Bearer {user_token}"})
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"

    def test_csv_export_reviewers_allowed_and_decrypted(self, app_env):
        application, client, settings = app_env
        op_token, op_user_id = _create_user(application, email="op2@drone.local", role="OPERATOR")

        # Seed encrypted flight request
        with application.state.session_factory() as db:
            details = {"applicant_full_name": "Nguyen Van A", "license_code": "PNT-001", "vehicle": "F450"}
            enc = encrypt_secret(settings.session_secret, json.dumps(details))
            flight = SimulatedFlightRequest(
                submitter_user_id=op_user_id,
                summary="Patrol flight",
                status="SUBMITTED",
                scheduled_start_at=utcnow(),
                scheduled_end_at=utcnow() + timedelta(hours=1),
                simulated_geometry_json='{"type":"Polygon","coordinates":[[[105,21],[106,21],[106,22],[105,22],[105,21]]]}',
                request_details_ciphertext=enc,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.add(flight)
            db.commit()

        res = client.get("/api/v1/flight-requests/export/csv", headers={"Authorization": f"Bearer {op_token}"})
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]
        assert 'attachment; filename="flight_history.csv"' in res.headers["content-disposition"]

        reader = csv.DictReader(io.StringIO(res.text))
        rows = list(reader)
        assert len(rows) >= 1
        found = [r for r in rows if r["summary"] == "Patrol flight"]
        assert len(found) == 1
        assert found[0]["applicant_name"] == "Nguyen Van A"
        assert found[0]["license_code"] == "PNT-001"
        assert found[0]["vehicle"] == "F450"

    def test_simulated_endpoint_equivalency(self, app_env):
        application, client, _ = app_env
        # Unauthenticated on simulated routes
        assert client.get("/api/v1/simulated/flight-requests/notifications").status_code == 401
        assert client.get("/api/v1/simulated/flight-requests/export/csv").status_code == 401

        pilot_token, _ = _create_user(application, email="simpilot@drone.local", role="PILOT")
        assert client.get("/api/v1/simulated/flight-requests/notifications", headers={"Authorization": f"Bearer {pilot_token}"}).status_code == 403
        assert client.get("/api/v1/simulated/flight-requests/export/csv", headers={"Authorization": f"Bearer {pilot_token}"}).status_code == 403


# ==============================================================================
# PROBE 2: GeoJSON Export Query Injection & Parameter Tampering
# ==============================================================================

class TestGeoJsonExportAdversarial:
    """Adversarial testing of GeoJSON export endpoint."""

    @pytest.fixture(autouse=True)
    def seed_zones(self, app_env):
        application, _, _ = app_env
        with application.state.session_factory() as db:
            src = ZoneSource(publisher="CAAV", source_type="OFFICIAL", license_name="Public Domain", checksum="c1", retrieved_at=utcnow())
            db.add(src)
            db.flush()

            # Public zone
            db.add(Zone(
                name="Zone Public 1",
                source_id=src.id,
                geometry_json='{"type":"Polygon","coordinates":[[[105.8,21.0],[105.9,21.0],[105.9,21.1],[105.8,21.1],[105.8,21.0]]]}',
                visibility="PUBLIC",
                classification="NO_FLY",
                version=1,
                retrieved_at=utcnow(),
                created_at=utcnow(),
                updated_at=utcnow(),
            ))
            # Restricted internal zone
            db.add(Zone(
                name="Zone Restricted Internal",
                source_id=src.id,
                geometry_json='{"type":"Polygon","coordinates":[[[106.0,21.0],[106.1,21.0],[106.1,21.1],[106.0,21.1],[106.0,21.0]]]}',
                visibility="RESTRICTED",
                classification="RESTRICTED",
                version=1,
                retrieved_at=utcnow(),
                created_at=utcnow(),
                updated_at=utcnow(),
            ))
            # Soft-deleted zone
            db.add(Zone(
                name="Zone Soft Deleted",
                source_id=src.id,
                geometry_json='{"type":"Polygon","coordinates":[[[107.0,21.0],[107.1,21.0],[107.1,21.1],[107.0,21.1],[107.0,21.0]]]}',
                visibility="PUBLIC",
                classification="NO_FLY",
                version=1,
                deleted_at=utcnow(),
                retrieved_at=utcnow(),
                created_at=utcnow(),
                updated_at=utcnow(),
            ))
            db.commit()

    def test_unauthenticated_only_receives_public_zones(self, app_env):
        _, client, _ = app_env
        res = client.get("/api/v1/zones/export/geojson")
        assert res.status_code == 200
        data = res.json()
        assert data["type"] == "FeatureCollection"
        names = [f["properties"]["name"] for f in data["features"]]
        assert "Zone Public 1" in names
        assert "Zone Restricted Internal" not in names
        assert "Zone Soft Deleted" not in names

    def test_unauthenticated_visibility_parameter_tampering_cannot_leak(self, app_env):
        _, client, _ = app_env
        # Attacker tries to ask for RESTRICTED visibility
        res = client.get("/api/v1/zones/export/geojson?visibility=RESTRICTED")
        assert res.status_code == 200
        data = res.json()
        names = [f["properties"]["name"] for f in data["features"]]
        # Unauthenticated caller is forced to PUBLIC, so RESTRICTED zone is NOT leaked
        assert "Zone Restricted Internal" not in names
        assert "Zone Soft Deleted" not in names

    def test_regular_user_visibility_tampering_cannot_leak(self, app_env):
        application, client, _ = app_env
        pilot_token, _ = _create_user(application, email="pilot_probe@drone.local", role="PILOT")

        res = client.get(
            "/api/v1/zones/export/geojson?visibility=RESTRICTED",
            headers={"Authorization": f"Bearer {pilot_token}"},
        )
        assert res.status_code == 200
        data = res.json()
        names = [f["properties"]["name"] for f in data["features"]]
        assert "Zone Restricted Internal" not in names

    def test_sql_injection_payloads_on_visibility_filter(self, app_env):
        application, client, _ = app_env
        op_token, _ = _create_user(application, email="op_probe@drone.local", role="OPERATOR")

        injection_payloads = [
            "' OR '1'='1",
            "PUBLIC' OR '1'='1",
            "'; DROP TABLE zone; --",
            "UNION SELECT * FROM zone --",
            "RESTRICTED' OR 1=1 --",
            "\\x00",
            "A" * 5000,
            "' UNION SELECT 1,2,3,4,5,6,7,8,9,10,11 --",
            "1; SELECT pg_sleep(5); --",
        ]

        for payload in injection_payloads:
            # Test as operator
            res = client.get(
                "/api/v1/zones/export/geojson",
                params={"visibility": payload},
                headers={"Authorization": f"Bearer {op_token}"},
            )
            # Must safely execute without 500 internal server error
            assert res.status_code == 200
            data = res.json()
            assert data["type"] == "FeatureCollection"
            # Payload shouldn't match any legitimate visibility string, so features should be empty
            assert len(data["features"]) == 0

        # Verify DB integrity was not damaged
        with application.state.session_factory() as db:
            count = len(db.scalars(Zone.__table__.select()).all())
            assert count >= 3

    def test_soft_deleted_zones_never_leaked(self, app_env):
        application, client, _ = app_env
        admin_token, _ = _create_user(application, email="admin_probe@drone.local", role="ADMIN")

        for vis in [None, "PUBLIC", "RESTRICTED", ""]:
            params = {"visibility": vis} if vis else {}
            res = client.get(
                "/api/v1/zones/export/geojson",
                params=params,
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert res.status_code == 200
            names = [f["properties"]["name"] for f in res.json()["features"]]
            assert "Zone Soft Deleted" not in names

    def test_malformed_geometry_skips_without_crashing(self, app_env):
        from sqlalchemy import select
        application, client, _ = app_env
        with application.state.session_factory() as db:
            src = db.scalar(select(ZoneSource))
            db.add(Zone(
                name="Corrupt Geometry Zone",
                source_id=src.id,
                geometry_json="NOT_VALID_JSON_AT_ALL{{{",
                visibility="PUBLIC",
                classification="NO_FLY",
                version=1,
                retrieved_at=utcnow(),
                created_at=utcnow(),
                updated_at=utcnow(),
            ))
            db.commit()

        res = client.get("/api/v1/zones/export/geojson")
        assert res.status_code == 200
        names = [f["properties"]["name"] for f in res.json()["features"]]
        assert "Zone Public 1" in names
        assert "Corrupt Geometry Zone" not in names  # Gracefully skipped


# ==============================================================================
# PROBE 3: Camera Pause & Disconnect Consumer Lifecycle
# ==============================================================================

class TestCameraPauseAndTermination:
    """Adversarial testing of Pi camera stream pause and termination."""

    def test_mock_camera_stream_disconnect_lifecycle(self):
        mock = MockCameraAdapter()
        assert mock.consumer_count == 0
        assert mock.running is False

        # Produce a frame
        mock.produce(b"\xff\xd8\xff\xe0testjpeg\xff\xd9")

        # Generator starts adapter
        gen_factory = mock.mjpeg_frames()
        assert mock.consumer_count == 1
        assert mock.running is True

        gen = gen_factory()
        frame = next(gen)
        assert frame.startswith(b"\xff\xd8")

        # Client pauses / closes stream -> gen.close() triggers finally block
        gen.close()
        assert mock.consumer_count == 0
        assert mock.running is False
        assert len(mock.queue) == 0

    def test_mock_camera_multi_consumer_refcount(self):
        mock = MockCameraAdapter(queue_size=10)
        mock.produce(b"\xff\xd8\xff\xe0frame1\xff\xd9")
        mock.produce(b"\xff\xd8\xff\xe0frame2\xff\xd9")

        # Two consumers connect
        gen_factory1 = mock.mjpeg_frames()
        gen_factory2 = mock.mjpeg_frames()
        assert mock.consumer_count == 2
        assert mock.running is True

        gen1 = gen_factory1()
        gen2 = gen_factory2()

        # Advance both generators so their execution enters the try block
        next(gen1)
        next(gen2)

        # Consumer 1 pauses / disconnects
        gen1.close()
        # Adapter should still be running because Consumer 2 is still active
        assert mock.consumer_count == 1
        assert mock.running is True

        # Consumer 2 pauses / disconnects
        gen2.close()
        # All consumers disconnected -> capture halts
        assert mock.consumer_count == 0
        assert mock.running is False

    def test_v4l2_adapter_disconnect_consumer_stops_streamer(self):
        adapter = V4L2CameraAdapter("/dev/video0")
        adapter.running = True
        adapter.consumer_count = 1

        mock_streamer = MagicMock()
        adapter.streamer = mock_streamer

        # Disconnecting the last consumer must stop adapter and streamer
        adapter.disconnect_consumer()
        assert adapter.consumer_count == 0
        assert adapter.running is False
        mock_streamer.stop.assert_called_once()

    def test_extra_routes_streaming_response_generator_finally_disconnects(self):
        """Simulate extra_routes.py /api/pi/v1/camera/mjpeg body() lifecycle."""
        mock = MockCameraAdapter()
        mock.produce(b"\xff\xd8\xff\xe0frame1\xff\xd9")

        # Verify body() with generator yielding frames
        gen_func = mock.mjpeg_frames()
        def body():
            try:
                for frame in gen_func():
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            finally:
                mock.disconnect_consumer()

        gen = body()
        chunk = next(gen)
        assert b"frame1" in chunk
        # Close generator (simulates client disconnect when image.src = "")
        gen.close()

        # Verify capture stopped
        assert mock.consumer_count == 0
        assert mock.running is False

    def test_mock_camera_adapter_function_vs_generator_discrepancy(self):
        """Demonstrates contract discrepancy: MockCameraAdapter.mjpeg_frames() returns a function,
        whereas V4L2CameraAdapter.mjpeg_frames() returns an iterable generator."""
        mock = MockCameraAdapter()
        ret = mock.mjpeg_frames()
        # In MockCameraAdapter, mjpeg_frames() returns the 'gen' function itself (callable, not iterable)
        assert callable(ret)
        assert not hasattr(ret, "__next__")


# ==============================================================================
# PROBE 4: Pi UI Module Resolution & Syntax Checks
# ==============================================================================

class TestPiUiModuleResolution:
    """Verifies all 11 Pi UI JavaScript modules pass syntax and import checks."""

    UI_FILES = [
        "edge/pi5/pi5/web/ui/core/dom.js",
        "edge/pi5/pi5/web/ui/core/api.js",
        "edge/pi5/pi5/web/ui/views/wifi.js",
        "edge/pi5/pi5/web/ui/views/auth.js",
        "edge/pi5/pi5/web/ui/views/camera.js",
        "edge/pi5/pi5/web/ui/views/map.js",
        "edge/pi5/pi5/web/ui/views/telemetry.js",
        "edge/pi5/pi5/web/ui/views/users.js",
        "edge/pi5/pi5/web/ui/views/firmware.js",
        "edge/pi5/pi5/web/ui/views/flight.js",
        "edge/pi5/pi5/web/ui/app.js",
    ]

    def test_all_11_files_exist(self):
        assert len(self.UI_FILES) == 11
        for path in self.UI_FILES:
            assert Path(path).exists(), f"Missing UI file: {path}"

    def test_node_check_passes_on_all_modules(self):
        cmd = ["node", "--check"] + self.UI_FILES
        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode == 0, f"node --check failed:\n{proc.stderr}"

    def test_module_import_export_contracts(self):
        """Parse imports and exports statically to verify reference resolution."""
        import re

        exports_by_file: dict[str, set[str]] = {}
        for path in self.UI_FILES:
            content = Path(path).read_text(encoding="utf-8")
            exports = set(re.findall(r"export\s+(?:async\s+)?(?:function|const|let|var)\s+([a-zA-Z0-9_$]+)", content))
            exports_by_file[Path(path).as_posix()] = exports

        # Check dom.js exports
        dom_exports = exports_by_file["edge/pi5/pi5/web/ui/core/dom.js"]
        assert {"h", "banner", "form", "field", "modal", "closeModal"}.issubset(dom_exports)

        # Check api.js exports
        api_exports = exports_by_file["edge/pi5/pi5/web/ui/core/api.js"]
        assert {"API", "api", "app", "topActions", "clearScreen", "every", "addCleanup"}.issubset(api_exports)

        # Check view exports
        assert "cameraView" in exports_by_file["edge/pi5/pi5/web/ui/views/camera.js"]
        assert "mapView" in exports_by_file["edge/pi5/pi5/web/ui/views/map.js"]
        assert "wifiScreen" in exports_by_file["edge/pi5/pi5/web/ui/views/wifi.js"]
        assert "authScreen" in exports_by_file["edge/pi5/pi5/web/ui/views/auth.js"]
        assert "telemetryView" in exports_by_file["edge/pi5/pi5/web/ui/views/telemetry.js"]
        assert "usersView" in exports_by_file["edge/pi5/pi5/web/ui/views/users.js"]
        assert "firmwareView" in exports_by_file["edge/pi5/pi5/web/ui/views/firmware.js"]
        assert "flightModal" in exports_by_file["edge/pi5/pi5/web/ui/views/flight.js"]
