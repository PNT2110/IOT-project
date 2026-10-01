from __future__ import annotations

from datetime import datetime, timezone
import json

from fastapi.testclient import TestClient
import pyotp

from pi5.cli import seed_default_admin
from pi5.telemetry.esp_link import EspLink
from pi5.web.app import PiWebConfig, create_pi_app
from pi5.web.auth import PiAuthService
from pi5.web.camera import MockCameraAdapter, split_jpeg_frames
from pi5.web.models import PiRole
from pi5.web.persistence import PiUserStore

PASSWORD = "correct horse battery staple"


def frame(seq: int, *, arm_state: str = "DISARMED", fix: str = "VALID_FIX") -> bytes:
    return (json.dumps({
        "schema_version": "scope05.esp32.usb.v1", "seq": seq, "uptime_ms": seq * 200,
        "imu": {"roll_deg": 1.5, "pitch_deg": -2.0, "yaw_deg": 90.0},
        "baro": {"altitude_m": 12.3, "vertical_speed_mps": 0.1, "temperature_c": 31.0, "available": True},
        "temperature_c": 40.5,
        "power": {"battery_pct": 87.0, "voltage_v": 15.9},
        "sbus": {"signal_ok": True, "channels": [1000, 1500, 1000, 1500, 1000, 1000, 1500, 1500]},
        "gnss": {"fix_state": fix, "latitude": 10.7769, "longitude": 106.7009, "altitude_m": 5.0, "satellites": 9},
        "flight": {"arm_state": arm_state, "mode": "ANGLE"},
        "pid": {"roll": {"kp": 1.0, "ki": 0.1, "kd": 0.01}},
    }) + "\n").encode()


class FakeReader:
    def __init__(self):
        self.next: bytes = b""
        self.written: list[bytes] = []
        self.closed = 0
        self.fail_write = False

    def read_latest(self, timeout: float) -> bytes:
        data, self.next = self.next, b""
        return data

    def write_line(self, data: bytes) -> None:
        if self.fail_write:
            raise OSError("unplugged")
        self.written.append(data)

    def close(self) -> None:
        self.closed += 1


def make_client(role: PiRole = PiRole.ADMIN, **kwargs):
    auth = PiAuthService(allow_inmemory_email=True)
    auth.add_user("alice", PASSWORD, role=role, email="alice@example.test")
    app = create_pi_app(PiWebConfig(secure_cookies=False), auth=auth, camera=kwargs.pop("camera", MockCameraAdapter()), **kwargs)
    client = TestClient(app)
    challenge_id = client.post("/api/pi/v1/auth/challenge", json={"username": "alice", "password": PASSWORD, "terms_accepted": True}).json()["data"]["challenge_id"]
    mfa = client.post("/api/pi/v1/auth/login", json={"challenge_id": challenge_id, "otp": auth.challenge_code_for_test(challenge_id)}).json()["data"]["mfa_challenge_id"]
    assert client.post("/api/pi/v1/auth/login", json={"mfa_challenge_id": mfa, "totp": auth.challenge_totp_for_test(mfa)}).status_code == 200
    return client, auth, {"X-CSRF-Token": client.cookies.get("pi_csrf")}


# ---- camera

def test_mjpeg_splitter_yields_complete_frames():
    one = b"\xff\xd8AAAA\xff\xd9"
    two = b"\xff\xd8BB\xff\xd9"
    buffer = bytearray(b"junk" + one + two[:3])
    assert split_jpeg_frames(buffer) == [one]
    assert bytes(buffer) == two[:3]
    buffer.extend(two[3:])
    assert split_jpeg_frames(buffer) == [two]
    assert bytes(buffer) == b""


def test_mjpeg_splitter_bounds_garbage():
    buffer = bytearray(b"x" * 5000)
    assert split_jpeg_frames(buffer) == []
    assert len(buffer) <= 1


def test_stream_requires_login_and_streams_frames():
    class StreamCamera(MockCameraAdapter):
        def mjpeg_frames(self):
            yield b"\xff\xd8one\xff\xd9"
            yield b"\xff\xd8two\xff\xd9"

    anonymous = TestClient(create_pi_app(PiWebConfig(secure_cookies=False), auth=PiAuthService(allow_inmemory_email=True), camera=StreamCamera()))
    assert anonymous.get("/api/pi/v1/camera/mjpeg").status_code == 401
    client, _, _ = make_client(PiRole.USER, camera=StreamCamera())
    response = client.get("/api/pi/v1/camera/mjpeg")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/x-mixed-replace")
    assert response.content.count(b"Content-Type: image/jpeg") == 2
    assert b"\xff\xd8two\xff\xd9" in response.content


# ---- ESP link

def test_esp_link_reads_latest_and_pings():
    clock = {"t": 0.0}
    reader = FakeReader()
    link = EspLink(reader, clock=lambda: clock["t"])
    reader.next = frame(1)
    link.tick()
    sample = link.read()
    assert sample["fix_state"] == "FIX" and sample["latitude"] == 10.7769
    assert sample["device"]["power"]["battery_pct"] == 87.0
    assert reader.written == [b"$PING*" + reader.written[0][6:]] and reader.written[0].startswith(b"$PING*")
    clock["t"] = 1.0
    link.tick()
    assert len(reader.written) == 1
    clock["t"] = 2.1
    link.tick()
    assert len(reader.written) == 2
    clock["t"] = 10.0
    assert link.read()["device"]["error"] == "ESP_USB_TIMEOUT"


def test_esp_link_pause_blocks_io_and_resume_restores():
    reader = FakeReader()
    link = EspLink(reader, clock=lambda: 0.0)
    link.pause()
    assert reader.closed == 1
    link.tick()
    assert reader.written == []
    try:
        link.send(b"$PING*00\n")
        raise AssertionError("send must fail while paused")
    except Exception as exc:
        assert "ESP_LINK_PAUSED" in str(exc)
    link.resume()
    link.send(b"$PING*00\n")
    assert reader.written == [b"$PING*00\n"]
    assert link.sent[-1][1] == "$PING*00"


def test_esp_link_without_device_reports_not_configured():
    link = EspLink(None)
    link.tick()
    assert link.read()["device"]["error"] == "ESP_USB_NOT_CONFIGURED"
    try:
        link.send(b"$PING*00\n")
        raise AssertionError("send must fail without a device")
    except Exception as exc:
        assert "ESP_NOT_CONNECTED" in str(exc)


# ---- tuning

def linked_client(role: PiRole = PiRole.ADMIN, *, arm_state: str = "DISARMED"):
    reader = FakeReader()
    link = EspLink(reader, clock=lambda: 0.0)
    reader.next = frame(1, arm_state=arm_state)
    link.tick()
    reader.written.clear()
    client, auth, csrf = make_client(role, esp_link=link)
    return client, csrf, reader


def test_tuning_pid_sends_checked_line():
    client, csrf, reader = linked_client()
    assert client.post("/api/pi/v1/tuning/pid", json={"axis": "roll", "kp": 1.25, "ki": 0.5, "kd": 0.02}).status_code == 403
    response = client.post("/api/pi/v1/tuning/pid", json={"axis": "roll", "kp": 1.25, "ki": 0.5, "kd": 0.02}, headers=csrf)
    assert response.status_code == 200
    assert reader.written == [b"$PID,roll,1.25,0.5,0.02*" + reader.written[0].split(b"*")[1]]
    assert client.post("/api/pi/v1/tuning/pid", json={"axis": "roll", "kp": 99, "ki": 0, "kd": 0}, headers=csrf).status_code == 422
    assert client.post("/api/pi/v1/tuning/pid", json={"axis": "throttle", "kp": 1, "ki": 0, "kd": 0}, headers=csrf).status_code == 422
    altitude = client.post("/api/pi/v1/tuning/max-altitude", json={"meters": 50}, headers=csrf)
    assert altitude.status_code == 200
    assert reader.written[-1].startswith(b"$MAXALT,50*")
    assert client.post("/api/pi/v1/tuning/max-altitude", json={"meters": 1}, headers=csrf).status_code == 422


def test_tuning_rejected_when_armed_409():
    client, csrf, reader = linked_client(arm_state="ARMED")
    response = client.post("/api/pi/v1/tuning/pid", json={"axis": "roll", "kp": 1, "ki": 0, "kd": 0}, headers=csrf)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DRONE_ARMED"
    assert reader.written == []


def test_tuning_forbidden_for_user_403():
    client, csrf, reader = linked_client(PiRole.USER)
    assert client.post("/api/pi/v1/tuning/pid", json={"axis": "roll", "kp": 1, "ki": 0, "kd": 0}, headers=csrf).status_code == 403
    assert client.post("/api/pi/v1/tuning/max-altitude", json={"meters": 50}, headers=csrf).status_code == 403
    assert reader.written == []


def test_tuning_without_esp_503():
    client, _, csrf = make_client()
    response = client.post("/api/pi/v1/tuning/max-altitude", json={"meters": 50}, headers=csrf)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ESP_NOT_CONNECTED"


# ---- roles and screens

def test_user_gets_403_on_map_telemetry_firmware_flight():
    client, _, csrf = make_client(PiRole.USER)
    assert client.get("/api/pi/v1/camera/status").status_code == 200
    for path in ("/api/pi/v1/map/cache", "/api/pi/v1/telemetry", "/api/pi/v1/firmware/latest", "/api/pi/v1/admin/active", "/api/pi/v1/flight-requests", "/api/pi/v1/flight-options"):
        assert client.get(path).status_code == 403, path
    body = {"full_name": "Alice", "license_code": "VN-1", "flight_date": "2026-10-02", "flight_time": "09:30", "vehicle": "F450 PNT PVD"}
    assert client.post("/api/pi/v1/flight-requests", json=body, headers=csrf).status_code == 403
    assert client.post("/api/pi/v1/firmware/flash", json={"version": "v1"}, headers=csrf).status_code == 403


def test_admin_flight_request_requires_csrf_and_has_no_arm_route():
    client, _, csrf = make_client()
    body = {"full_name": "Alice Operator", "license_code": "VN-123", "flight_date": "2026-10-02", "flight_time": "09:30", "vehicle": "F450 PNT PVD"}
    assert client.get("/api/pi/v1/flight-options").json()["data"]["vehicles"] == ["F450 PNT PVD"]
    assert client.post("/api/pi/v1/flight-requests", json=body).status_code == 403
    created = client.post("/api/pi/v1/flight-requests", json=body, headers=csrf)
    assert created.status_code == 201
    item = created.json()["data"]
    # No PC authority is configured in this app instance: the request waits to be sent.
    assert item["status"] == "PENDING_SEND" and item["arm_permission"] == "BLOCKED" and item["gps"] is None
    assert client.get("/api/pi/v1/flight-requests").json()["data"][0]["request_id"] == item["request_id"]
    assert client.post("/api/pi/v1/flight-requests", json={**body, "flight_time": "9h"}, headers=csrf).status_code == 422
    assert client.post("/api/pi/v1/arm").status_code in {404, 405}
    assert client.post("/api/pi/v1/disarm").status_code in {404, 405}


def test_active_users_excludes_idle():
    client, auth, _ = make_client()
    auth.add_user("bob", PASSWORD, role=PiRole.USER, email="bob@example.test")
    active = client.get("/api/pi/v1/admin/active").json()["data"]
    assert [item["username"] for item in active] == ["alice"]
    client.app.state.last_seen.clear()
    assert client.app.state.last_seen == {}


def test_admin_rejects_role_request():
    auth = PiAuthService(allow_inmemory_email=True)
    bob = auth.add_user("bob", PASSWORD, role=PiRole.USER, email="bob@example.test")
    request = auth.request_admin(bob, "cần quyền quản trị")
    admin = auth.add_user("alice2", PASSWORD, role=PiRole.ADMIN, email="alice2@example.test")
    decided = auth.decide_role_request(admin, request["request_id"], "REJECTED")
    assert decided["status"] == "REJECTED"
    assert auth.users[auth._key("bob")].role is PiRole.USER


# ---- static UI, session cookie, default admin

def test_index_served_from_static_with_strict_csp():
    client = TestClient(create_pi_app(PiWebConfig(secure_cookies=False), auth=PiAuthService(allow_inmemory_email=True)))
    page = client.get("/")
    assert page.status_code == 200
    assert '<script type="module" src="/ui/app.js">' in page.text
    assert "F450 PNT PVD" in page.text
    assert "unsafe-inline" not in page.headers["content-security-policy"].split("script-src")[1].split(";")[0]
    assert client.get("/ui/app.js").status_code == 200
    assert client.get("/ui/vendor/leaflet/leaflet.js").status_code == 200
    assert client.get("/ui/vendor/three.module.min.js").status_code == 200
    script = client.get("/ui/app.js").text
    for label in ("Xin quyền admin", "Xin cấp phép bay", "Camera", "Bản đồ", "Thông số", "Người dùng", "Firmware"):
        assert label in script, label


def test_session_cookie_not_secure_when_configured():
    client, _, _ = make_client()
    challenge = client.post("/api/pi/v1/auth/challenge", json={"username": "alice", "password": PASSWORD, "terms_accepted": True})
    assert challenge.status_code == 200
    assert client.cookies.get("pi_session")
    assert client.get("/api/pi/v1/auth/me").json()["data"]["username"] == "alice"


def test_seed_default_admin_idempotent(tmp_path):
    store = PiUserStore(str(tmp_path / "users.sqlite3"), "k" * 40)
    secret = pyotp.random_base32()
    env = {"PI_DEFAULT_ADMIN_USERNAME": "Pitan", "PI_DEFAULT_ADMIN_PASSWORD": "pitan-test-pass", "PI_DEFAULT_ADMIN_TOTP_SECRET": secret}
    assert seed_default_admin(store, env) is True
    assert seed_default_admin(store, {**env, "PI_DEFAULT_ADMIN_PASSWORD": "a-different-one"}) is False
    auth = PiAuthService(store=store, allow_inmemory_email=True)
    user = auth.users[auth._key("pitan")]
    assert user.role is PiRole.ADMIN and user.email == "" and user.totp_secret == secret
    assert len(auth.users) == 1


def test_captive_probe_redirects_and_network_routes():
    class FakeNetwork:
        def __init__(self): self.connected = False; self.calls = []
        def status(self): return {"upstream_connected": self.connected, "iface": "wlan1", "ssid": "Home" if self.connected else None, "ip": None}
        def scan(self): return [{"ssid": "Home", "signal": 70, "secure": True}]
        def connect(self, ssid, psk):
            self.calls.append((ssid, psk)); self.connected = True
            return {"ok": True, "error": None}

    network = FakeNetwork()
    client, _, csrf = make_client(PiRole.USER, network=network)
    for path in ("/generate_204", "/hotspot-detect.html", "/connecttest.txt", "/ncsi.txt", "/redirect"):
        probe = client.get(path, follow_redirects=False)
        assert probe.status_code == 302 and probe.headers["location"] == "http://192.168.4.1/", path

    anonymous = TestClient(client.app)
    assert anonymous.get("/api/pi/v1/network/status").json()["data"]["upstream_connected"] is False
    # Offline: the Wi-Fi setup screen comes before login, so these are open.
    assert anonymous.get("/api/pi/v1/network/scan").json()["data"][0]["ssid"] == "Home"
    assert anonymous.post("/api/pi/v1/network/connect", json={"ssid": "Home", "password": "password123"}).json()["data"]["ok"] is True
    assert network.calls == [("Home", "password123")]
    # Online: changing the upstream network needs an admin.
    assert anonymous.get("/api/pi/v1/network/scan").status_code == 401
    assert anonymous.post("/api/pi/v1/network/connect", json={"ssid": "Other", "password": "password123"}).status_code == 401
    assert client.get("/api/pi/v1/network/scan").status_code == 403
    assert client.post("/api/pi/v1/network/connect", json={"ssid": "Other", "password": "password123"}, headers=csrf).status_code == 403
    assert network.calls == [("Home", "password123")]
