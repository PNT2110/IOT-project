"""Unit and integration tests for Milestone 2 Server Backend APIs.

Features tested:
- Feature 4: Telemetry Ingestion (POST /api/v1/device/telemetry)
- Feature 5: Telemetry Query / Stream (GET /api/v1/telemetry/latest & GET /api/v1/telemetry/stream)
- Feature 6: Flight Request Notifications (GET /api/v1/flight-requests/notifications)
- Feature 7: Zone GeoJSON Export (GET /api/v1/zones/export/geojson)
- Feature 8: Flight History CSV Export (GET /api/v1/flight-requests/export/csv)
"""
from __future__ import annotations

import csv
import io
import json
import time
from typing import Any

import base64
from datetime import timedelta
from pathlib import Path
import secrets

import pytest
from fastapi.testclient import TestClient

from server.app.config import Settings
from server.app.device_crypto import seal
from server.app.main import create_app
from server.app.models import Credential, Device, SessionRecord, SimulatedFlightRequest, User, Zone, ZoneSource
from server.app.security import digest_token, encrypt_secret, hash_password, new_token, utcnow


@pytest.fixture()
def app_env(tmp_path: Path):
    db_path = tmp_path / "m2_pc_server.sqlite3"
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


@pytest.fixture()
def pc_client(app_env) -> TestClient:
    return app_env[1]


@pytest.fixture()
def pc_app(app_env) -> Any:
    return app_env[0]


@pytest.fixture()
def pc_settings(app_env) -> Settings:
    return app_env[2]


def _create_user_with_session(app: Any, username: str, email: str, role: str) -> tuple[User, str]:
    now = utcnow()
    settings = app.state.settings
    with app.state.session_factory() as db:
        user = User(
            username=username,
            display_name=f"{username.capitalize()} User",
            email_normalized=email.lower().strip(),
            status="ACTIVE",
            role=role,
            version=1,
            email_verified_at=now,
            created_at=now,
            updated_at=now,
        )
        user.credential = Credential(
            password_hash=hash_password("M2_Secure_Password_123!"),
            totp_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        db.flush()

        raw_token = new_token()
        session = SessionRecord(
            token_digest=digest_token(settings.session_secret, raw_token),
            user_id=user.id,
            stage="AUTHENTICATED",
            csrf_digest=digest_token(settings.session_secret, "m2-csrf-token"),
            expires_at=now + timedelta(hours=8),
            last_seen_at=now,
            created_at=now,
        )
        db.add(session)
        db.commit()
        db.refresh(user)
        return user, raw_token


@pytest.fixture()
def operator_auth(pc_app: Any) -> dict[str, str]:
    _, token = _create_user_with_session(pc_app, "operator_m2", "operator_m2@example.test", "OPERATOR")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def pilot_auth(pc_app: Any) -> dict[str, str]:
    _, token = _create_user_with_session(pc_app, "pilot_m2", "pilot_m2@example.test", "PILOT")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def registered_device(pc_app: Any) -> dict[str, Any]:
    settings = pc_app.state.settings
    raw_key = secrets.token_bytes(32)
    b64_key = base64.urlsafe_b64encode(raw_key).decode()
    encrypted_key = encrypt_secret(settings.session_secret, b64_key)

    with pc_app.state.session_factory() as db:
        device = Device(
            name="F450-Drone-Alpha",
            key_encrypted=encrypted_key,
            created_at=utcnow(),
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        return {
            "id": device.id,
            "name": device.name,
            "key": raw_key,
            "key_b64": b64_key,
        }


def make_sealed_envelope(
    key: bytes,
    device_id: str,
    payload: dict[str, Any],
    ts: int | None = None,
    nonce: bytes | None = None,
) -> dict[str, Any]:
    now = int(time.time()) if ts is None else ts
    return seal(key, device_id, payload, now, nonce=nonce)


# ==============================================================================
# Feature 4: Telemetry Ingestion
# ==============================================================================

def test_telemetry_ingest_happy_path(
    pc_client: TestClient,
    registered_device: dict[str, Any],
    pc_app: Any,
) -> None:
    """Test successful sealed telemetry sample ingestion and in-memory persistence."""
    payload = {
        "device_id": registered_device["id"],
        "seq": 100,
        "observed_at": "2026-10-04T05:00:00Z",
        "latitude": 21.0285,
        "longitude": 105.8542,
        "altitude_m": 35.4,
        "battery_pct": 95.0,
        "voltage_v": 12.4,
        "fix_state": "FIX",
        "stale": False,
    }
    envelope = make_sealed_envelope(registered_device["key"], registered_device["id"], payload)
    response = pc_client.post("/api/v1/device/telemetry", json=envelope)

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["stored"] is True
    assert body["data"]["device_id"] == registered_device["id"]

    # Verify server in-memory state
    cached = pc_app.state.latest_telemetry.get(registered_device["id"])
    assert cached is not None
    assert cached["seq"] == 100
    assert cached["latitude"] == 21.0285
    assert cached["device_name"] == registered_device["name"]
    assert pc_app.state.latest_telemetry.get("__latest__") == cached


def test_telemetry_ingest_replay_attack_rejected(
    pc_client: TestClient,
    registered_device: dict[str, Any],
) -> None:
    """Submitting the same envelope twice within nonce TTL must result in 401."""
    payload = {"seq": 101, "latitude": 21.0, "longitude": 105.0}
    envelope = make_sealed_envelope(registered_device["key"], registered_device["id"], payload)

    res1 = pc_client.post("/api/v1/device/telemetry", json=envelope)
    assert res1.status_code == 200

    res2 = pc_client.post("/api/v1/device/telemetry", json=envelope)
    assert res2.status_code == 401
    assert res2.json()["error"]["code"] == "DEVICE_AUTH_FAILED"


def test_telemetry_ingest_invalid_key_rejected(
    pc_client: TestClient,
    registered_device: dict[str, Any],
) -> None:
    """Submitting envelope encrypted with wrong key must fail authentication."""
    wrong_key = b"wrong_key_32_bytes_long_12345678"
    payload = {"seq": 102}
    envelope = make_sealed_envelope(wrong_key, registered_device["id"], payload)

    res = pc_client.post("/api/v1/device/telemetry", json=envelope)
    assert res.status_code == 401


# ==============================================================================
# Feature 5: Telemetry Query & Streaming
# ==============================================================================

def test_telemetry_query_latest_found(
    pc_client: TestClient,
    operator_auth: dict[str, str],
    registered_device: dict[str, Any],
) -> None:
    """Querying latest telemetry returns the ingested sample."""
    sample = {
        "device_id": registered_device["id"],
        "seq": 500,
        "latitude": 21.0500,
        "longitude": 105.8000,
        "altitude_m": 80.0,
        "battery_pct": 77.0,
        "voltage_v": 11.2,
        "fix_state": "FIX",
    }
    envelope = make_sealed_envelope(registered_device["key"], registered_device["id"], sample)
    assert pc_client.post("/api/v1/device/telemetry", json=envelope).status_code == 200

    # Query with device_id
    res_dev = pc_client.get(f"/api/v1/telemetry/latest?device_id={registered_device['id']}", headers=operator_auth)
    assert res_dev.status_code == 200
    data_dev = res_dev.json()["data"]["telemetry"]
    assert data_dev["seq"] == 500
    assert data_dev["battery_pct"] == 77.0

    # Query without device_id (retrieves __latest__)
    res_latest = pc_client.get("/api/v1/telemetry/latest", headers=operator_auth)
    assert res_latest.status_code == 200
    data_latest = res_latest.json()["data"]["telemetry"]
    assert data_latest["seq"] == 500


def test_telemetry_query_latest_not_found(
    pc_client: TestClient,
    operator_auth: dict[str, str],
) -> None:
    """Querying when no telemetry has been ingested returns 404."""
    res = pc_client.get("/api/v1/telemetry/latest?device_id=nonexistent-id", headers=operator_auth)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "TELEMETRY_NOT_FOUND"


def test_telemetry_query_unauthenticated(pc_client: TestClient) -> None:
    """Unauthenticated query to telemetry returns 401."""
    res = pc_client.get("/api/v1/telemetry/latest")
    assert res.status_code == 401


# ==============================================================================
# Feature 6: Flight Request Notifications
# ==============================================================================

def test_flight_request_notifications_flow(
    pc_client: TestClient,
    operator_auth: dict[str, str],
    pc_app: Any,
) -> None:
    """Test notification queue counts pending requests and reports latest submission."""
    # Initially empty
    res0 = pc_client.get("/api/v1/flight-requests/notifications", headers=operator_auth)
    assert res0.status_code == 200
    assert res0.json()["data"]["pending_count"] == 0
    assert res0.json()["data"]["latest_request_id"] is None

    now = utcnow()
    # Add submitted request
    with pc_app.state.session_factory() as db:
        flight = SimulatedFlightRequest(
            summary="Notification Test Flight",
            scheduled_start_at=now,
            scheduled_end_at=now,
            simulated_geometry_json="null",
            status="SUBMITTED",
            version=1,
            source="WEB",
            created_at=now,
            updated_at=now,
        )
        db.add(flight)
        db.commit()
        db.refresh(flight)
        flight_id = flight.id

    # Notification now has pending_count 1
    res1 = pc_client.get("/api/v1/flight-requests/notifications", headers=operator_auth)
    assert res1.status_code == 200
    data1 = res1.json()["data"]
    assert data1["pending_count"] == 1
    assert data1["latest_request_id"] == flight_id
    assert len(data1["items"]) == 1

    # Transition to REJECTED
    with pc_app.state.session_factory() as db:
        f = db.get(SimulatedFlightRequest, flight_id)
        if f:
            f.status = "REJECTED"
            db.commit()

    # Notification count returns to 0
    res2 = pc_client.get("/api/v1/flight-requests/notifications", headers=operator_auth)
    assert res2.status_code == 200
    assert res2.json()["data"]["pending_count"] == 0


def test_flight_request_notifications_rbac(
    pc_client: TestClient,
    pilot_auth: dict[str, str],
) -> None:
    """Regular pilot user without reviewer privileges is forbidden (403)."""
    res = pc_client.get("/api/v1/flight-requests/notifications", headers=pilot_auth)
    assert res.status_code == 403


# ==============================================================================
# Feature 7: Zone GeoJSON Export
# ==============================================================================

def test_zone_geojson_export(
    pc_client: TestClient,
    operator_auth: dict[str, str],
    pc_app: Any,
) -> None:
    """Test RFC 7946 GeoJSON FeatureCollection export and soft-delete filtering."""
    now = utcnow()
    poly1 = {"type": "Polygon", "coordinates": [[[105.8, 21.0], [105.9, 21.0], [105.9, 21.1], [105.8, 21.1], [105.8, 21.0]]]}
    poly2 = {"type": "Polygon", "coordinates": [[[106.0, 20.5], [106.1, 20.5], [106.1, 20.6], [106.0, 20.6], [106.0, 20.5]]]}

    with pc_app.state.session_factory() as db:
        src = ZoneSource(
            id="src_1",
            publisher="TEST_SOURCE",
            source_type="OFFICIAL",
            license_name="OpenData",
            checksum="abc123",
            retrieved_at=now,
        )
        db.add(src)
        db.flush()

        z1 = Zone(
            name="Zone Alpha Active",
            geometry_json=json.dumps(poly1),
            visibility="PUBLIC",
            classification="NO_FLY",
            source_id="src_1",
            version=1,
            retrieved_at=now,
            created_at=now,
            updated_at=now,
        )
        z2 = Zone(
            name="Zone Beta Deleted",
            geometry_json=json.dumps(poly2),
            visibility="PUBLIC",
            classification="RESTRICTED",
            source_id="src_1",
            version=1,
            retrieved_at=now,
            created_at=now,
            updated_at=now,
            deleted_at=now,  # Deleted zone!
        )
        db.add_all([z1, z2])
        db.commit()
        db.refresh(z1)
        z1_id = z1.id

    res = pc_client.get("/api/v1/zones/export/geojson", headers=operator_auth)
    assert res.status_code == 200
    assert "application/geo+json" in res.headers["content-type"]
    assert "attachment; filename=\"zones.geojson\"" in res.headers["content-disposition"]

    collection = res.json()
    assert collection["type"] == "FeatureCollection"
    feature_names = [f["properties"]["name"] for f in collection["features"]]
    assert "Zone Alpha Active" in feature_names
    assert "Zone Beta Deleted" not in feature_names

    # Check geometry of matching feature
    alpha_feat = next(f for f in collection["features"] if f["id"] == z1_id)
    assert alpha_feat["geometry"]["type"] == "Polygon"
    assert alpha_feat["geometry"]["coordinates"] == poly1["coordinates"]
    assert alpha_feat["properties"]["classification"] == "NO_FLY"


# ==============================================================================
# Feature 8: Flight History CSV Export
# ==============================================================================

def test_flight_history_csv_export(
    pc_client: TestClient,
    operator_auth: dict[str, str],
    pc_app: Any,
    pc_settings: Any,
) -> None:
    """Test RFC 4180 CSV export with decrypted details and special character handling."""
    now = utcnow()
    details = {
        "applicant_full_name": "Lê Văn \"Phi Công\", Người Lái",
        "license_code": "VN-UAV-7788",
        "vehicle": "F450, Pro Quad",
    }
    encrypted = encrypt_secret(pc_settings.session_secret, json.dumps(details))

    with pc_app.state.session_factory() as db:
        flight = SimulatedFlightRequest(
            summary="Mission: Test \"Escaping\", and Commas",
            status="APPROVED_SIMULATED",
            version=1,
            source="WEB",
            scheduled_start_at=now,
            scheduled_end_at=now,
            simulated_geometry_json="null",
            request_details_ciphertext=encrypted,
            created_at=now,
            updated_at=now,
        )
        db.add(flight)
        db.commit()
        db.refresh(flight)
        flight_id = flight.id

    res = pc_client.get("/api/v1/flight-requests/export/csv", headers=operator_auth)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "attachment; filename=\"flight_history.csv\"" in res.headers["content-disposition"]

    reader = csv.reader(io.StringIO(res.text))
    rows = list(reader)
    header = rows[0]
    expected_headers = [
        "id", "status", "source", "device_name", "summary",
        "applicant_name", "license_code", "vehicle",
        "scheduled_start_at", "scheduled_end_at", "created_at", "updated_at",
    ]
    assert header == expected_headers

    # Find the row for flight_id
    matching_rows = [r for r in rows[1:] if r[0] == flight_id]
    assert len(matching_rows) == 1
    row = matching_rows[0]
    assert row[1] == "APPROVED_SIMULATED"
    assert row[2] == "WEB"
    assert row[4] == "Mission: Test \"Escaping\", and Commas"
    assert row[5] == "Lê Văn \"Phi Công\", Người Lái"
    assert row[6] == "VN-UAV-7788"
    assert row[7] == "F450, Pro Quad"


def test_flight_history_csv_export_empty(
    pc_client: TestClient,
    operator_auth: dict[str, str],
) -> None:
    """When no flights exist, export returns CSV with only the header row."""
    res = pc_client.get("/api/v1/flight-requests/export/csv", headers=operator_auth)
    assert res.status_code == 200
    rows = list(csv.reader(io.StringIO(res.text)))
    assert len(rows) == 1
    assert rows[0][0] == "id"


def test_zone_geojson_export_empty(
    pc_client: TestClient,
    operator_auth: dict[str, str],
    pc_app: Any,
) -> None:
    """When no active zones exist, GeoJSON export returns valid empty FeatureCollection."""
    from sqlalchemy import select
    with pc_app.state.session_factory() as db:
        for z in db.scalars(select(Zone)).all():
            z.deleted_at = utcnow()
        db.commit()

    res = pc_client.get("/api/v1/zones/export/geojson", headers=operator_auth)
    assert res.status_code == 200
    body = res.json()
    assert body["type"] == "FeatureCollection"
    assert body["features"] == []


def test_telemetry_sse_stream_endpoint(
    pc_client: TestClient,
    registered_device: dict[str, Any],
) -> None:
    """Verify GET /api/v1/telemetry/stream connects as text/event-stream."""
    sample = {
        "device_id": registered_device["id"],
        "seq": 999,
        "latitude": 21.0,
        "longitude": 105.0,
    }
    env = make_sealed_envelope(registered_device["key"], registered_device["id"], sample)
    assert pc_client.post("/api/v1/device/telemetry", json=env).status_code == 200

    res = pc_client.get("/api/v1/telemetry/stream?limit=1")
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]
    assert "data:" in res.text
    assert '"seq": 999' in res.text


def test_telemetry_ingest_extreme_coordinates(
    pc_client: TestClient,
    registered_device: dict[str, Any],
) -> None:
    """Coordinates at geographical extrema (-90/90, -180/180) must be accepted."""
    extreme_payload = {
        "device_id": registered_device["id"],
        "seq": 8888,
        "observed_at": "2026-10-04T05:30:00Z",
        "latitude": 90.0,
        "longitude": -180.0,
        "altitude_m": -400.0,
        "battery_pct": 100.0,
        "voltage_v": 12.6,
        "fix_state": "FIX",
        "stale": False,
    }
    envelope = make_sealed_envelope(registered_device["key"], registered_device["id"], extreme_payload)
    response = pc_client.post("/api/v1/device/telemetry", json=envelope)
    assert response.status_code == 200
    assert response.json()["data"]["stored"] is True

