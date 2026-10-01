from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from pi5.web.app import PiWebConfig, create_pi_app
from pi5.web.auth import PiAuthService
from pi5.web.cache import MapCache
from pi5.web.camera import MockCameraAdapter, V4L2CameraAdapter
import pi5.web.camera as camera_module
from pi5.web.models import CameraErrorCode, CameraState, CacheProvenance, FixState, PiRole, TelemetrySample
from pi5.web.telemetry import MockTelemetrySource


@pytest.fixture()
def fixture_app():
    auth = PiAuthService()
    auth.add_user("local-user", "fixture-password", role=PiRole.USER)
    auth.add_user("local-admin", "fixture-password", role=PiRole.ADMIN)
    camera = MockCameraAdapter(queue_size=2)
    cache = MapCache()
    cache.load_fixture(
        {"tiles": ["fixture-only"]},
        CacheProvenance("local-fixture", "FIXTURE", None, datetime.now(timezone.utc), "v1", datetime.now(timezone.utc) + timedelta(days=1), "fixture-license"),
    )
    telemetry = MockTelemetrySource()
    app = create_pi_app(PiWebConfig(secure_cookies=True), auth=auth, camera=camera, map_cache=cache, telemetry=telemetry)
    return app, auth, camera, cache, telemetry


def login(client: TestClient, auth: PiAuthService, username: str = "local-user") -> None:
    challenge = client.post("/api/pi/v1/auth/challenge", json={"username": username, "password": "fixture-password"})
    assert challenge.status_code == 200
    challenge_id = challenge.json()["data"]["challenge_id"]
    otp = auth.challenge_code_for_test(challenge_id)
    response = client.post("/api/pi/v1/auth/login", json={"challenge_id": challenge_id, "otp": otp})
    assert response.status_code == 200


def test_local_auth_separate_domain_and_cookie_csrf(fixture_app):
    app, auth, *_ = fixture_app
    with TestClient(app, base_url="https://testserver") as client:
        assert client.get("/api/pi/v1/auth/me").status_code == 401
        login(client, auth)
        me = client.get("/api/pi/v1/auth/me")
        assert me.json()["data"]["role"] == "USER"
        assert "pi_session" in client.cookies and "pi_csrf" in client.cookies
        logout = client.post("/api/pi/v1/auth/logout")
        assert logout.status_code == 200
        assert client.get("/api/pi/v1/auth/me").status_code == 401
        assert all("password" not in event and "otp" not in event for event in auth.audit_events)


def test_camera_normal_frame_and_authenticated_stream(fixture_app):
    app, auth, camera, *_ = fixture_app
    camera.start()
    camera.produce(b"frame-1")
    with TestClient(app, base_url="https://testserver") as client:
        assert client.get("/api/pi/v1/camera/status").status_code == 401
        login(client, auth)
        response = client.get("/api/pi/v1/camera/stream")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert response.headers["x-camera-sequence"] == "1"
        assert response.content == b"frame-1"


@pytest.mark.parametrize(
    ("state", "error"),
    [
        (CameraState.UNAVAILABLE, CameraErrorCode.DEVICE_UNAVAILABLE),
        (CameraState.PERMISSION_DENIED, CameraErrorCode.PERMISSION_DENIED),
        (CameraState.BUSY, CameraErrorCode.DEVICE_BUSY),
        (CameraState.UNSUPPORTED_FORMAT, CameraErrorCode.UNSUPPORTED_FORMAT),
        (CameraState.OPEN_FAILED, CameraErrorCode.OPEN_FAILED),
        (CameraState.FRAME_READ_FAILED, CameraErrorCode.FRAME_READ_FAILED),
    ],
)
def test_camera_typed_failures(state, error):
    camera = MockCameraAdapter()
    camera.set_state(state, error)
    assert camera.status().state == state
    assert camera.status().error_code == error


def test_camera_empty_frame_disappears_and_disconnect_is_safe():
    camera = MockCameraAdapter(queue_size=1)
    camera.start()
    camera.produce(b"")
    assert camera.status().state == CameraState.FRAME_READ_FAILED
    camera.set_state(CameraState.AVAILABLE)
    camera.produce(b"one")
    camera.produce(b"two")
    assert camera.status().queue_depth == 1
    camera.disconnect_consumer()
    assert camera.status().queue_depth == 0
    assert camera.read_frame() is None


def test_video1_is_not_guessed_as_camera():
    with pytest.raises(ValueError, match="metadata node"):
        V4L2CameraAdapter("/dev/video1")


def test_v4l2_single_frame_is_bounded_and_transient(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return camera_module.subprocess.CompletedProcess(args, 0, stdout=b"jpeg-frame", stderr=b"")

    monkeypatch.setattr(camera_module.subprocess, "run", fake_run)
    camera = V4L2CameraAdapter("/dev/video0", max_frame_bytes=64)
    assert camera.start().state == CameraState.AVAILABLE or camera.start().state == CameraState.UNAVAILABLE
    # Avoid host device availability deciding the adapter unit test.
    monkeypatch.setattr(camera, "status", lambda: camera_module.CameraStatus(CameraState.AVAILABLE, "/dev/video0", "V4L2"))
    camera.start()
    frame = camera.read_frame()
    assert frame is not None and frame.payload == b"jpeg-frame"
    assert calls[0][0][-1] == "--stream-to=-"
    assert calls[0][1]["capture_output"] is True
    camera.disconnect_consumer()


def test_cache_provenance_stale_and_unavailable():
    cache = MapCache()
    assert cache.read()["state"] == "UNAVAILABLE"
    cache.load_fixture(
        {"tiles": []},
        CacheProvenance("generated-fixture", "SYNTHETIC", None, datetime.now(timezone.utc), "v1", datetime.now(timezone.utc) - timedelta(seconds=1), "local-test"),
    )
    result = cache.read()
    assert result["state"] == "STALE"
    assert result["provenance"]["source_type"] == "SYNTHETIC"


def test_telemetry_contract_and_3d_does_not_invent_orientation(fixture_app):
    app, auth, _, _, telemetry = fixture_app
    with TestClient(app, base_url="https://testserver") as client:
        login(client, auth)
        telemetry_response = client.get("/api/pi/v1/telemetry")
        assert telemetry_response.json()["data"]["source"] == "MOCK"
        assert telemetry_response.json()["data"]["fix_state"] == FixState.UNAVAILABLE.value
        view = client.get("/api/pi/v1/3d").json()["data"]
        assert view["enabled"] is False
        assert view["animation"] is False
        assert view["orientation"]["heading_deg"] is None


def test_3d_only_uses_existing_orientation_fields(fixture_app):
    app, auth, _, _, telemetry = fixture_app
    telemetry.set_sample(TelemetrySample("scope04.telemetry.v1", "MOCK", datetime.now(timezone.utc), 1, False, FixState.FIX, heading_deg=90.0, pitch_deg=1.0, roll_deg=2.0))
    with TestClient(app, base_url="https://testserver") as client:
        login(client, auth)
        view = client.get("/api/pi/v1/3d").json()["data"]
        assert view["enabled"] is True
        assert view["orientation"] == {"heading_deg": 90.0, "pitch_deg": 1.0, "roll_deg": 2.0}


def test_no_fix_and_stale_telemetry_remain_typed(fixture_app):
    app, auth, _, _, telemetry = fixture_app
    telemetry.set_sample(TelemetrySample("scope04.telemetry.v1", "MOCK", datetime.now(timezone.utc), 2, True, FixState.NO_FIX))
    with TestClient(app, base_url="https://testserver") as client:
        login(client, auth)
        sample = client.get("/api/pi/v1/telemetry").json()["data"]
        assert sample["source"] == "MOCK"
        assert sample["fix_state"] == FixState.NO_FIX.value
        assert sample["stale"] is True
        assert sample["latitude"] is None


def test_bind_policy_rejects_public_listener_and_command_routes_do_not_exist():
    with pytest.raises(ValueError, match="wildcard"):
        create_pi_app(PiWebConfig(bind_host="0.0.0.0"))
    app = create_pi_app()
    with TestClient(app) as client:
        assert client.post("/api/pi/v1/arm").status_code == 404
        assert client.post("/api/pi/v1/disarm").status_code == 404
        assert client.post("/api/pi/v1/firmware/update").status_code == 404


def test_wrong_mfa_is_rate_limited_without_secret_disclosure(fixture_app):
    app, auth, *_ = fixture_app
    with TestClient(app, base_url="https://testserver") as client:
        challenge = client.post("/api/pi/v1/auth/challenge", json={"username": "local-user", "password": "fixture-password"}).json()["data"]["challenge_id"]
        for _ in range(5):
            response = client.post("/api/pi/v1/auth/login", json={"challenge_id": challenge, "otp": "000000"})
        assert response.status_code == 429
        assert all("fixture-password" not in event.values() for event in auth.audit_events)
