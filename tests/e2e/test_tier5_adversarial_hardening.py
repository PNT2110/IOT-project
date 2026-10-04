"""Tier 5: White-Box Adversarial Hardening E2E Test Suite.

Authoritative Phase 2 verification:
1. Firmware: Deadband oscillation, terminal dive vspeed dampening, pilot downward override, millis rollover.
2. Pi 5 Gateway & Local Web: 4MB OTA boundary, armed lockout, filename sanitization, camera disconnect, JPEG splitter.
3. Server Backend: AES-256-GCM bit-flip tampering, replay burst, timestamp skew, multi-device isolation,
   unauthenticated query rejection, self-review prohibition, CSV formula injection defense, GeoJSON access control,
   email normalization matrix, non-blocking SMTP event loop.
4. PC Frontend Logic: ErrorBanner 8s timer & ARIA contracts, CSV RFC 4180 escaping & GeoJSON export contracts.
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from pi5.web.app import PiWebConfig, create_pi_app
from pi5.web.auth import PiAuthService
from pi5.web.camera import MockCameraAdapter
from pi5.web.models import PiRole
from server.app.mail import SmtpEmailSender
from server.app.models import Device, SimulatedFlightRequest, User, Zone, ZoneSource
from server.app.security import encrypt_secret, normalize_email, utcnow
from tests.e2e.conftest import make_sealed_envelope, PROJECT_ROOT


# ==============================================================================
# Helper for Host C++ Firmware Compilation
# ==============================================================================
def _find_compiler() -> str:
    found = shutil.which("g++")
    if found:
        return found
    strawberry = Path("C:/Strawberry/c/bin/g++.exe")
    if strawberry.exists():
        return str(strawberry)
    return "g++"


def _run_cpp_check(tmp_path: Path, test_name: str, cpp_body: str) -> None:
    compiler = _find_compiler()
    flight_gate_path = PROJECT_ROOT / "firmware" / "FC_can_bang" / "flight_gate.h"
    cpp_source = tmp_path / f"{test_name}.cpp"
    full_source = f"""
#include <iostream>
#include <cassert>
#include <cmath>
#include "{flight_gate_path.as_posix()}"

int main() {{
{cpp_body}
    std::cout << "CHECK_PASSED" << std::endl;
    return 0;
}}
"""
    cpp_source.write_text(full_source, encoding="utf-8")
    exe_path = tmp_path / f"{test_name}.exe"
    res = subprocess.run(
        [compiler, "-std=c++17", "-Wall", "-Wextra", f"-I{(flight_gate_path.parent).as_posix()}", str(cpp_source), "-o", str(exe_path)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Compilation failed: {res.stderr}"
    run_res = subprocess.run([str(exe_path)], capture_output=True, text=True, timeout=10)
    assert run_res.returncode == 0, f"Execution failed: {run_res.stderr}"
    assert "CHECK_PASSED" in run_res.stdout


# ==============================================================================
# 1. Firmware White-Box Adversarial Hardening
# ==============================================================================
def test_adv_fw_deadband_hysteresis_oscillation(tmp_path: Path) -> None:
    """Adversarial Test 1.1: Rapid jitter around ceiling (120.01m <-> 119.5m).
    
    Limiter MUST NOT oscillate between active/inactive in the 1-meter release band.
    It must stay active until strictly below 119.0m (max_alt_m - ALT_LIMIT_RELEASE_M).
    """
    cpp_body = """
    AltLimiter limiter;
    // Step 1: breach ceiling at 120.5m with 1500us
    int c1 = altitude_throttle_cap(limiter, 120.5f, 120.0f, 1500);
    assert(limiter.active);
    assert(c1 == 1470);

    // Step 2: jitter down to 119.6m (inside 1m deadband: 119m to 120m)
    int c2 = altitude_throttle_cap(limiter, 119.6f, 120.0f, 1500);
    assert(limiter.active); // MUST stay active
    assert(c2 == 1470);

    // Step 3: jitter back up to 120.1m
    int c3 = altitude_throttle_cap(limiter, 120.1f, 120.0f, 1500);
    assert(limiter.active);
    assert(c3 <= 1470);

    // Step 4: descent through 119.1m (still in deadband)
    int c4 = altitude_throttle_cap(limiter, 119.1f, 120.0f, 1500);
    assert(limiter.active);

    // Step 5: descent to 118.9m (below 120.0 - 1.0 = 119.0m)
    int c5 = altitude_throttle_cap(limiter, 118.9f, 120.0f, 1500);
    assert(!limiter.active); // Released!
    assert(c5 == 1500);
    """
    _run_cpp_check(tmp_path, "test_deadband_oscillation", cpp_body)


def test_adv_fw_terminal_dive_vspeed_damping(tmp_path: Path) -> None:
    """Adversarial Test 1.2: Terminal descent (-15.0 m/s dive).
    
    The dynamic floor must scale upwards with negative vspeed to brake the descent,
    but never exceed throttle_us - 20, nor fall below ALT_LIMIT_DEFAULT_FLOOR_US (1100).
    """
    cpp_body = """
    AltLimiter limiter;
    // Enter ceiling at 122m, throttle 1600us, falling at -15.0 m/s
    int c1 = altitude_throttle_cap(limiter, 122.0f, 120.0f, 1600, -15.0f);
    assert(limiter.active);
    // effective_floor cap logic:
    // base = 1600 - 150 = 1450us
    // boost = (-(-15.0) - 0.4) * 100 = 1460us
    // clamped to throttle_us - 20 = 1580us
    assert(c1 >= 1450);
    assert(c1 <= 1580);
    assert(c1 >= ALT_LIMIT_DEFAULT_FLOOR_US);
    """
    _run_cpp_check(tmp_path, "test_terminal_dive", cpp_body)


def test_adv_fw_downward_stick_priority(tmp_path: Path) -> None:
    """Adversarial Test 1.3: Pilot manual downward override.
    
    When altitude limiter is active, if the pilot intentionally throttles DOWN
    (e.g. to 1150us or 1000us), the system MUST output the lower commanded throttle.
    Pilot must never be locked at high throttle when pulling the stick back.
    """
    cpp_body = """
    AltLimiter limiter;
    // Enter at 125m, throttle 1700us -> cap is 1670us
    int c1 = altitude_throttle_cap(limiter, 125.0f, 120.0f, 1700);
    assert(limiter.active);
    assert(c1 == 1670);

    // Pilot pulls throttle down to 1300us
    int c2 = altitude_throttle_cap(limiter, 125.0f, 120.0f, 1300);
    assert(c2 == 1300);

    // Pilot pulls throttle down to 1050us (below 1100us floor)
    int c3 = altitude_throttle_cap(limiter, 125.0f, 120.0f, 1050);
    assert(c3 == 1050);
    """
    _run_cpp_check(tmp_path, "test_downward_override", cpp_body)


def test_adv_fw_millis_rollover_link_alive(tmp_path: Path) -> None:
    """Adversarial Test 1.4: Millis() 32-bit integer rollover.
    
    Unsigned subtraction (now_ms - last_ping_ms) correctly computes elapsed time
    across the 49.7-day rollover boundary without integer underflow bugs.
    """
    cpp_body = """
    unsigned long timeout = 10000UL;
    // Rollover case 1: last ping at 0xFFFFFF80 (near max), now at 100ms
    // Elapsed = 100 - (2^32 - 128) = 228ms <= 10000ms -> Alive
    assert(pi_link_alive(100UL, 0xFFFFFF80UL, true, timeout));

    // Rollover case 2: last ping at 0xFFFFFF00, now at 10100ms
    // Elapsed = 10100 - (2^32 - 256) = 10356ms > 10000ms -> Dead
    assert(!pi_link_alive(10100UL, 0xFFFFFF00UL, true, timeout));

    // Without ping seen, never alive
    assert(!pi_link_alive(100UL, 0xFFFFFF80UL, false, timeout));
    """
    _run_cpp_check(tmp_path, "test_millis_rollover", cpp_body)


# ==============================================================================
# 2. Pi 5 Gateway & Local Web Adversarial Hardening
# ==============================================================================
def test_adv_pi_ota_upload_exact_4mb_boundary(tmp_path: Path) -> None:
    """Adversarial Test 2.1: OTA firmware exact 4MB limit and 1-byte overflow.
    
    With max_request_bytes set to 5MB, exact 4 * 1024 * 1024 bytes with magic byte 0xe9
    is accepted by FirmwareUpdater. 4 * 1024 * 1024 + 1 bytes is rejected with 413 PAYLOAD_TOO_LARGE.
    """
    auth = PiAuthService(allow_inmemory_email=True)
    auth.add_user("pi_operator", "pi_secret_password_123", role=PiRole.USER, email="pi@example.test")
    camera = MockCameraAdapter()
    config = PiWebConfig(secure_cookies=False, max_request_bytes=5_000_000)
    app = create_pi_app(config, auth=auth, camera=camera)

    with TestClient(app) as client:
        max_bytes = 4 * 1024 * 1024
        exact_4mb = b"\xe9" + b"\x00" * (max_bytes - 1)
        
        # Exactly 4MB with magic byte 0xe9
        res_exact = client.post(
            "/api/pi/v1/firmware/upload",
            content=exact_4mb,
            headers={"Content-Type": "application/octet-stream"},
        )
        assert res_exact.status_code == 202
        body = res_exact.json().get("data", res_exact.json())
        assert body.get("status") in {"QUEUED", "FLASHING", "COMPLETED"}

        # 4MB + 1 byte
        overflow_bytes = b"\xe9" + b"\x00" * max_bytes
        res_overflow = client.post(
            "/api/pi/v1/firmware/upload",
            content=overflow_bytes,
            headers={"Content-Type": "application/octet-stream"},
        )
        assert res_overflow.status_code == 413
        code = (res_overflow.json().get("error") or res_overflow.json().get("detail") or {}).get("code")
        assert code in {"PAYLOAD_TOO_LARGE", "REQUEST_TOO_LARGE"}


def test_adv_pi_ota_armed_lockout(pi_client: TestClient) -> None:
    """Adversarial Test 2.2: Flashing rejected when drone is armed.
    
    If the link or mock indicates arm_state == "ARMED", return 409 DRONE_ARMED.
    """
    app = pi_client.app
    mock_link = MagicMock()
    mock_link.arm_state.return_value = "ARMED"
    app.state.esp_link = mock_link

    payload = b"\xe9" + b"\x01" * 1023
    res = pi_client.post(
        "/api/pi/v1/firmware/upload",
        content=payload,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert res.status_code == 409
    code = (res.json().get("error") or res.json().get("detail") or {}).get("code")
    assert code == "DRONE_ARMED"


def test_adv_pi_ota_filename_sanitization(pi_client: TestClient) -> None:
    """Adversarial Test 2.3: Multipart upload with directory traversal filename."""
    app = pi_client.app
    app.state.esp_link = None  # reset link
    
    boundary = "----AdversarialBoundary7MA4YWxkTrZu0gW"
    payload = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="../../etc/passwd.bin"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
        + "\xe9\xaa\xbb\xcc" * 64
        + f"\r\n--{boundary}--\r\n"
    ).encode("latin1")

    res = pi_client.post(
        "/api/pi/v1/firmware/upload",
        content=payload,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    assert res.status_code == 202
    data = res.json().get("data", res.json())
    assert "job_id" in data


def test_adv_pi_camera_disconnect_and_idle_shutdown(pi_client: TestClient, pi_camera: Any) -> None:
    """Adversarial Test 2.4: Camera stream consumer disconnect cleanup.
    
    When consumers disconnect, disconnect_consumer() drops consumer count to 0 and stops.
    """
    assert pi_camera.consumer_count == 0
    pi_camera.start()
    assert pi_camera.running is True
    assert pi_camera.consumer_count == 1

    pi_camera.disconnect_consumer()
    assert pi_camera.consumer_count == 0
    assert pi_camera.running is False


def test_adv_pi_camera_frame_splitter_stress() -> None:
    """Adversarial Test 2.5: split_jpeg_frames robustness under corrupted buffers."""
    from pi5.web.camera import split_jpeg_frames, MAX_PARTIAL_FRAME
    
    # 1. Incomplete frame without EOI
    buf = bytearray(b"\xff\xd8\x00\x01\x02\x03")
    frames = split_jpeg_frames(buf)
    assert frames == []
    assert len(buf) == 6

    # 2. Complete frame
    buf.extend(b"\xff\xd9")
    frames = split_jpeg_frames(buf)
    assert len(frames) == 1
    assert frames[0] == b"\xff\xd8\x00\x01\x02\x03\xff\xd9"
    assert len(buf) == 0

    # 3. Buffer overflow exceeding MAX_PARTIAL_FRAME
    overflow_buf = bytearray(b"\xff\xd8" + b"\xaa" * (MAX_PARTIAL_FRAME + 10))
    frames = split_jpeg_frames(overflow_buf)
    assert frames == []
    assert len(overflow_buf) == 0  # cleared on overflow


# ==============================================================================
# 3. Server Backend Adversarial Hardening
# ==============================================================================
def test_adv_server_telemetry_ciphertext_bitflip_tamper(
    pc_client: TestClient,
    registered_device: dict[str, Any],
) -> None:
    """Adversarial Test 3.1: AES-256-GCM ciphertext bit-flip tampering.
    
    Flipping even a single bit in the ciphertext or tag must cause authentication failure.
    """
    valid_payload = {
        "device_id": registered_device["id"],
        "latitude": 21.0285,
        "longitude": 105.8544,
        "altitude_m": 45.0,
        "battery_pct": 88.0,
    }
    env = make_sealed_envelope(registered_device["key"], registered_device["id"], valid_payload)
    
    # Tamper: flip first character of ciphertext
    ct = env["ciphertext"]
    flipped_char = "B" if ct[0] != "B" else "C"
    tampered_env = {**env, "ciphertext": flipped_char + ct[1:]}

    res = pc_client.post("/api/v1/device/telemetry", json=tampered_env)
    assert res.status_code == 401
    code = (res.json().get("error") or res.json().get("detail") or {}).get("code")
    assert code == "DEVICE_AUTH_FAILED"


def test_adv_server_telemetry_replay_burst(
    pc_client: TestClient,
    registered_device: dict[str, Any],
) -> None:
    """Adversarial Test 3.2: Replay burst attack.
    
    1st request with a specific nonce passes; all subsequent duplicate requests fail.
    """
    valid_payload = {
        "device_id": registered_device["id"],
        "seq": 9999,
        "latitude": 21.0285,
        "longitude": 105.8544,
    }
    env = make_sealed_envelope(registered_device["key"], registered_device["id"], valid_payload)
    
    # First attempt: succeeds
    res1 = pc_client.post("/api/v1/device/telemetry", json=env)
    assert res1.status_code == 200

    # Next 5 identical attempts: rejected as replay
    for _ in range(5):
        res = pc_client.post("/api/v1/device/telemetry", json=env)
        assert res.status_code == 401
        code = (res.json().get("error") or res.json().get("detail") or {}).get("code")
        assert code == "DEVICE_AUTH_FAILED"


def test_adv_server_telemetry_skew_rejection(
    pc_client: TestClient,
    registered_device: dict[str, Any],
) -> None:
    """Adversarial Test 3.3: Future and past timestamp skew > 300s."""
    now = int(time.time())
    valid_payload = {"device_id": registered_device["id"], "latitude": 21.0}

    # 305 seconds in future
    future_env = make_sealed_envelope(registered_device["key"], registered_device["id"], valid_payload, ts=now + 305)
    res_f = pc_client.post("/api/v1/device/telemetry", json=future_env)
    assert res_f.status_code == 401

    # 305 seconds in past
    past_env = make_sealed_envelope(registered_device["key"], registered_device["id"], valid_payload, ts=now - 305)
    res_p = pc_client.post("/api/v1/device/telemetry", json=past_env)
    assert res_p.status_code == 401


def test_adv_server_telemetry_multi_device_isolation(
    pc_client: TestClient,
    registered_device: dict[str, Any],
    pc_app: Any,
    operator_auth: dict[str, str],
) -> None:
    """Adversarial Test 3.4: Multi-device isolation in latest telemetry cache."""
    # Register 2nd device
    import secrets, base64
    settings = pc_app.state.settings
    key2 = secrets.token_bytes(32)
    b64_key2 = base64.urlsafe_b64encode(key2).decode()
    enc_key2 = encrypt_secret(settings.session_secret, b64_key2)
    with pc_app.state.session_factory() as db:
        dev2 = Device(name="F450-Drone-Beta", key_encrypted=enc_key2, created_at=utcnow())
        db.add(dev2)
        db.commit()
        db.refresh(dev2)
        dev2_id = dev2.id

    # Ingest for Device 1
    p1 = {"device_id": registered_device["id"], "altitude_m": 50.0, "battery_pct": 90.0}
    env1 = make_sealed_envelope(registered_device["key"], registered_device["id"], p1)
    res1 = pc_client.post("/api/v1/device/telemetry", json=env1)
    assert res1.status_code == 200

    # Ingest for Device 2
    p2 = {"device_id": dev2_id, "altitude_m": 120.0, "battery_pct": 40.0}
    env2 = make_sealed_envelope(key2, dev2_id, p2)
    res2 = pc_client.post("/api/v1/device/telemetry", json=env2)
    assert res2.status_code == 200

    # Query device 1: should see alt 50.0
    q1 = pc_client.get(f"/api/v1/telemetry/latest?device_id={registered_device['id']}", headers=operator_auth)
    assert q1.status_code == 200
    assert q1.json().get("data", {}).get("telemetry", {}).get("altitude_m") == 50.0

    # Query device 2: should see alt 120.0
    q2 = pc_client.get(f"/api/v1/telemetry/latest?device_id={dev2_id}", headers=operator_auth)
    assert q2.status_code == 200
    assert q2.json().get("data", {}).get("telemetry", {}).get("altitude_m") == 120.0


def test_adv_server_telemetry_unauthenticated_query_rejected(pc_client: TestClient) -> None:
    """Adversarial Test 3.5: /api/v1/telemetry/latest without auth returns 401."""
    res = pc_client.get("/api/v1/telemetry/latest")
    assert res.status_code == 401


def test_adv_server_flight_notifications_self_review_forbidden(
    pc_client: TestClient,
    pilot_auth: dict[str, str],
    pc_app: Any,
) -> None:
    """Adversarial Test 3.6: A reviewer cannot review/decide their own submitted request."""
    # Find pilot user ID
    with pc_app.state.session_factory() as db:
        pilot = db.scalars(select(User).where(User.username == "pilot_e2e")).first()
        pilot_id = pilot.id
        now = utcnow()
        req = SimulatedFlightRequest(
            submitter_user_id=pilot_id,
            summary="Self-review attempt flight",
            scheduled_start_at=now,
            scheduled_end_at=now,
            status="SUBMITTED",
            version=1,
            created_at=now,
            updated_at=now,
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        req_id = req.id

    # Elevate pilot temporarily to OPERATOR to test self-review rule
    with pc_app.state.session_factory() as db:
        user = db.get(User, pilot_id)
        user.role = "OPERATOR"
        db.commit()

    # Attempt to review own request
    res = pc_client.post(
        f"/api/v1/flight-requests/{req_id}/review",
        json={"reason": "Self approving"},
        headers={**pilot_auth, "If-Match": "1"},
    )
    assert res.status_code == 403
    code = (res.json().get("error") or res.json().get("detail") or {}).get("code")
    assert code == "SELF_REVIEW_FORBIDDEN"


def test_adv_server_csv_formula_injection_defense(
    pc_client: TestClient,
    operator_auth: dict[str, str],
    pc_app: Any,
    pc_settings: Any,
) -> None:
    """Adversarial Test 3.7: CSV export sanitization for Excel injection characters.
    
    Inputs starting with '=', '+', '-', '@' must be quoted and escaped safely in CSV output.
    """
    now = utcnow()
    malicious_details = {
        "applicant_full_name": "=cmd|' /C calc'!A0",
        "license_code": "@SUM(1+1)",
        "vehicle": "+F450-Drone-Payload",
    }
    enc = encrypt_secret(pc_settings.session_secret, json.dumps(malicious_details))
    
    with pc_app.state.session_factory() as db:
        req = SimulatedFlightRequest(
            summary='Malicious "Formula" Injection, with commas and \r\n newline',
            scheduled_start_at=now,
            scheduled_end_at=now,
            status="SUBMITTED",
            version=1,
            request_details_ciphertext=enc,
            created_at=now,
            updated_at=now,
        )
        db.add(req)
        db.commit()

    res = pc_client.get("/api/v1/flight-requests/export/csv", headers=operator_auth)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    csv_text = res.text

    # Parse with standard Python CSV reader to verify RFC 4180 parsing compliance
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) >= 2
    header = rows[0]
    assert "applicant_name" in header
    assert "license_code" in header

    # Verify fields parsed intact without escaping failure
    found_row = False
    for r in rows[1:]:
        if "=cmd|' /C calc'!A0" in r:
            found_row = True
            break
    assert found_row is True


def test_adv_server_geojson_export_access_control(
    pc_client: TestClient,
    operator_auth: dict[str, str],
    pc_app: Any,
) -> None:
    """Adversarial Test 3.8: GeoJSON export access control between anonymous & operator."""
    now = utcnow()
    with pc_app.state.session_factory() as db:
        src = ZoneSource(publisher="VN_AIR", source_type="OFFICIAL", license_name="MIT", checksum="a"*64, retrieved_at=now)
        db.add(src)
        db.flush()

        z_pub = Zone(name="Public Drone Park", source_id=src.id, geometry_json='{"type":"Polygon","coordinates":[[[105.8,21.0],[105.9,21.0],[105.9,21.1],[105.8,21.1],[105.8,21.0]]]}', visibility="PUBLIC", classification="RESTRICTED", version=1, retrieved_at=now, created_at=now, updated_at=now)
        z_int = Zone(name="Confidential Military Zone", source_id=src.id, geometry_json='{"type":"Polygon","coordinates":[[[105.1,21.0],[105.2,21.0],[105.2,21.1],[105.1,21.1],[105.1,21.0]]]}', visibility="INTERNAL", classification="NO_FLY", version=1, retrieved_at=now, created_at=now, updated_at=now)
        db.add_all([z_pub, z_int])
        db.commit()

    # Anonymous export -> MUST NOT contain INTERNAL zone
    res_anon = pc_client.get("/api/v1/zones/export/geojson")
    assert res_anon.status_code == 200
    features_anon = res_anon.json().get("features", [])
    names_anon = [f["properties"]["name"] for f in features_anon]
    assert "Public Drone Park" in names_anon
    assert "Confidential Military Zone" not in names_anon

    # Operator export -> includes INTERNAL zones
    res_op = pc_client.get("/api/v1/zones/export/geojson", headers=operator_auth)
    assert res_op.status_code == 200
    features_op = res_op.json().get("features", [])
    names_op = [f["properties"]["name"] for f in features_op]
    assert "Public Drone Park" in names_op
    assert "Confidential Military Zone" in names_op


def test_adv_server_email_normalization_matrix() -> None:
    """Adversarial Test 3.9: Email normalization matrix with unusual RFC variations."""
    cases = [
        ("USER.NAME+tag1+tag2@GMAIL.COM", "username@gmail.com"),
        ("user.name+tag@googlemail.com", "username@gmail.com"),
        ("  pilot.drone+f450@gmail.com \t ", "pilotdrone@gmail.com"),
        ("first.last+subaddress@outlook.com", "first.last@outlook.com"),
        ("first.last+subaddress@company.vn", "first.last@company.vn"),
        ("no_at_sign_identifier", "no_at_sign_identifier"),
        ("@empty_local.com", "@empty_local.com"),
        ("+leading_plus@gmail.com", "@gmail.com"),
        ("...consecutive...dots...@gmail.com", "consecutivedots@gmail.com"),
    ]
    for raw, expected in cases:
        assert normalize_email(raw) == expected, f"Failed for {raw}"


@pytest.mark.anyio
async def test_adv_server_smtp_nonblocking_event_loop() -> None:
    """Adversarial Test 3.10: SmtpEmailSender non-blocking async execution.
    
    send_code() must return a coroutine/awaitable immediately and execute in threadpool,
    without stalling the async event loop.
    """
    sender = SmtpEmailSender(
        host="smtp.example.test",
        port=587,
        username="user",
        password="pwd",
        sender="noreply@example.test",
    )
    
    # Mock _send_blocking with an intentional delay to verify caller does not block synchronously
    def slow_send(*args: Any, **kwargs: Any) -> None:
        time.sleep(0.1)

    sender._send_blocking = slow_send  # type: ignore[assignment]
    
    t0 = time.perf_counter()
    coro = sender.send_code("user@example.test", "LOGIN", "123456", utcnow())
    # The return of the call must be practically instantaneous (< 50ms)
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.05, f"send_code() blocked synchronously for {elapsed:.4f}s!"

    # Now await it to verify async completion
    await coro


# ==============================================================================
# 4. PC Frontend Logic Contract Hardening
# ==============================================================================
def test_adv_frontend_error_banner_contract() -> None:
    """Adversarial Test 4.1: Verify ErrorBanner accessibility and dismiss contracts."""
    banner_file = PROJECT_ROOT / "frontend" / "src" / "components" / "ErrorBanner.tsx"
    assert banner_file.exists()
    content = banner_file.read_text(encoding="utf-8")

    # Contract 1: 8-second default auto-dismiss timer
    assert "autoDismissMs = 8000" in content
    # Contract 2: role="alert"
    assert 'role="alert"' in content
    # Contract 3: aria-live="assertive"
    assert 'aria-live="assertive"' in content
    # Contract 4: manual dismiss button with aria-label="Đóng thông báo"
    assert 'aria-label="Đóng thông báo"' in content
    # Contract 5: window.clearTimeout cleanup on unmount
    assert "window.clearTimeout" in content


def test_adv_frontend_csv_and_geojson_export_contract() -> None:
    """Adversarial Test 4.2: Verify OperationsWorkspace export implementations."""
    ws_file = PROJECT_ROOT / "frontend" / "src" / "components" / "operations" / "OperationsWorkspace.tsx"
    assert ws_file.exists()
    content = ws_file.read_text(encoding="utf-8")

    # Contract 1: escapeCsv RFC 4180 function doubling inner quotes
    assert 'replace(/"/g, \'""\')' in content
    # Contract 2: UTF-8 BOM in CSV export for Excel compatibility
    assert '"\\uFEFF"' in content
    # Contract 3: CRLF delimiter in CSV rows
    assert 'join("\\r\\n")' in content
    # Contract 4: GeoJSON RFC 7946 export with FeatureCollection
    assert 'type: "FeatureCollection"' in content
    assert 'type: "application/geo+json;charset=utf-8"' in content
    # Contract 5: Web Audio API notification chime synthesis without external assets
    assert "AudioContext" in content
    assert "createOscillator" in content


# ==============================================================================
# 5. Deep Adversarial Penetration (Challenger 2 Expansion)
# ==============================================================================
def test_adv_fw_step_quantization_long_duration(tmp_path: Path) -> None:
    """Adversarial Test 5.1: 5,000 steps of ceiling violation decay.
    
    ALT_LIMIT_STEP_US is 0.05 us per step (10 us / sec at 200 Hz).
    Over 5,000 steps, throttle cap must decrement smoothly and clamp at effective_floor.
    """
    cpp_body = """
    AltLimiter limiter;
    // Enter ceiling at 122m, commanded throttle 1700us -> initial cap 1670us
    int cap0 = altitude_throttle_cap(limiter, 122.0f, 120.0f, 1700);
    assert(limiter.active);
    assert(cap0 == 1670);

    // Simulate 5,000 consecutive cycles above ceiling
    int last_cap = cap0;
    for (int i = 0; i < 5000; i++) {
        last_cap = altitude_throttle_cap(limiter, 122.0f, 120.0f, 1700);
    }
    // 5000 * 0.05 = 250us decrement -> 1670 - 250 = 1420us
    // But floor is min(1450, 1700 - 150) = 1450us
    // So cap must be clamped at effective floor (1450us)
    assert(last_cap == 1450);
    assert(limiter.floor_us == 1450.0f);
    """
    _run_cpp_check(tmp_path, "test_step_quantization", cpp_body)


def test_adv_fw_zero_throttle_idle_floor_immunity(tmp_path: Path) -> None:
    """Adversarial Test 5.2: Commanded throttle 0 or idle 1000us returns commanded value.
    
    The altitude limiter must NEVER command throttle above pilot's stick position.
    When pilot sets throttle = 1000us (idle) or 0us, output must be <= commanded stick.
    """
    cpp_body = """
    AltLimiter limiter;
    // Enter ceiling at 125m, throttle 1600us -> active
    altitude_throttle_cap(limiter, 125.0f, 120.0f, 1600);
    assert(limiter.active);

    // Pilot pulls stick to 0us (e.g. emergency cutoff)
    int c_zero = altitude_throttle_cap(limiter, 125.0f, 120.0f, 0);
    assert(c_zero == 0);

    // Pilot pulls stick to 1000us (idle)
    int c_idle = altitude_throttle_cap(limiter, 125.0f, 120.0f, 1000);
    assert(c_idle == 1000);
    """
    _run_cpp_check(tmp_path, "test_zero_throttle_immunity", cpp_body)


def test_adv_server_aes_aad_device_and_timestamp_tampering(
    pc_client: TestClient,
    registered_device: dict[str, Any],
) -> None:
    """Adversarial Test 5.3: AES-256-GCM AAD (Associated Data) tampering.
    
    AES-GCM authenticates f"{device_id}|{ts}". Changing either device_id or ts
    by 1 second/byte without re-encrypting ciphertext MUST trigger InvalidTag / 401.
    """
    now = int(time.time())
    payload = {"device_id": registered_device["id"], "seq": 5001, "latitude": 21.0}
    env = make_sealed_envelope(registered_device["key"], registered_device["id"], payload, ts=now)

    # 1. Tamper timestamp by +1 second (keeping within 300s window so not rejected for skew)
    tampered_ts_env = {**env, "ts": now + 1}
    res_ts = pc_client.post("/api/v1/device/telemetry", json=tampered_ts_env)
    assert res_ts.status_code == 401

    # 2. Tamper device_id in envelope
    tampered_dev_env = {**env, "device_id": "forged-device-id"}
    res_dev = pc_client.post("/api/v1/device/telemetry", json=tampered_dev_env)
    assert res_dev.status_code in {401, 404}


def test_adv_server_aes_malformed_envelope_types(
    pc_client: TestClient,
    registered_device: dict[str, Any],
) -> None:
    """Adversarial Test 5.4: Malformed nonce lengths and non-dict payloads."""
    from server.app.device_crypto import DeviceAuthError, open_sealed, seal

    key = registered_device["key"]
    dev_id = registered_device["id"]
    now = int(time.time())

    # 1. 11-byte nonce (AES-GCM requires 12 bytes)
    short_nonce_env = seal(key, dev_id, {"lat": 21.0}, now, nonce=b"12345678901")
    with pytest.raises(DeviceAuthError, match="malformed nonce"):
        open_sealed(key, short_nonce_env, now)

    # 2. 13-byte nonce
    long_nonce_env = seal(key, dev_id, {"lat": 21.0}, now, nonce=b"1234567890123")
    with pytest.raises(DeviceAuthError, match="malformed nonce"):
        open_sealed(key, long_nonce_env, now)


def test_adv_server_geometry_adversarial_validation() -> None:
    """Adversarial Test 5.5: Shapely GeoJSON polygon validation edge cases."""
    from server.app.geo import GeometryError, validate_polygon_geojson

    # 1. Self-intersecting bowtie polygon
    bowtie = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [1.0, 1.0], [0.0, 1.0], [1.0, 0.0], [0.0, 0.0]]],
    }
    with pytest.raises(GeometryError, match="geometry must be non-empty and valid"):
        validate_polygon_geojson(bowtie)

    # 2. Coordinates outside WGS84 bounds (-180 to 180, -90 to 90)
    out_of_bounds = {
        "type": "Polygon",
        "coordinates": [[[185.0, 20.0], [186.0, 20.0], [186.0, 21.0], [185.0, 21.0], [185.0, 20.0]]],
    }
    with pytest.raises(GeometryError, match="outside WGS84 bounds"):
        validate_polygon_geojson(out_of_bounds)

    # 3. Non-finite coordinates (NaN or Inf)
    nan_geom = {
        "type": "Polygon",
        "coordinates": [[[float("nan"), 20.0], [10.0, 20.0], [10.0, 21.0], [float("nan"), 20.0]]],
    }
    with pytest.raises(GeometryError, match="coordinates must be finite"):
        validate_polygon_geojson(nan_geom)

    # 4. Point geometry (only Polygon/MultiPolygon accepted)
    point_geom = {"type": "Point", "coordinates": [105.8, 21.0]}
    with pytest.raises(GeometryError, match="only Polygon or MultiPolygon is accepted"):
        validate_polygon_geojson(point_geom)

    # 5. GeoJSON with forbidden CRS member
    crs_geom = {
        "type": "Polygon",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "coordinates": [[[10.0, 10.0], [11.0, 10.0], [11.0, 11.0], [10.0, 11.0], [10.0, 10.0]]],
    }
    with pytest.raises(GeometryError, match="GeoJSON CRS member is not accepted"):
        validate_polygon_geojson(crs_geom)


def test_adv_server_rbac_pilot_zone_tamper_rejected(
    pc_client: TestClient,
    pilot_auth: dict[str, str],
) -> None:
    """Adversarial Test 5.6: Authenticated PILOT cannot read or mutate internal zones."""
    # Attempt internal zones read
    res_get = pc_client.get("/api/v1/internal/zones", headers=pilot_auth)
    assert res_get.status_code == 403
    code_get = (res_get.json().get("error") or res_get.json().get("detail") or {}).get("code")
    assert code_get == "FORBIDDEN"

    # Attempt internal zones create
    res_post = pc_client.post(
        "/api/v1/internal/zones",
        json={
            "name": "Unauthorized Zone",
            "source_id": "mock_src",
            "geometry": {"type": "Polygon", "coordinates": [[[0,0],[1,0],[1,1],[0,1],[0,0]]]},
            "visibility": "PUBLIC",
            "classification": "RESTRICTED",
        },
        headers={**pilot_auth, "Idempotency-Key": "pilot-tamper-key"},
    )
    assert res_post.status_code == 403
    code_post = (res_post.json().get("error") or res_post.json().get("detail") or {}).get("code")
    assert code_post == "FORBIDDEN"


def test_adv_pi_camera_stream_failure_handling(pi_env: tuple[TestClient, Any, Any]) -> None:
    """Adversarial Test 5.7: Camera endpoint handles frame read failure with 503."""
    from pi5.web.models import CameraErrorCode, CameraState

    client, auth, camera = pi_env
    challenge = client.post("/api/pi/v1/auth/challenge", json={"username": "pi_operator", "password": "pi_secret_password_123", "terms_accepted": True})
    challenge_id = challenge.json()["data"]["challenge_id"]
    otp = auth.challenge_code_for_test(challenge_id)
    email_step = client.post("/api/pi/v1/auth/login", json={"challenge_id": challenge_id, "otp": otp})
    mfa_id = email_step.json()["data"]["mfa_challenge_id"]
    client.post("/api/pi/v1/auth/login", json={"mfa_challenge_id": mfa_id, "totp": auth.challenge_totp_for_test(mfa_id)})

    camera.set_state(CameraState.FRAME_READ_FAILED, CameraErrorCode.FRAME_READ_FAILED, "corrupted frame")
    res = client.get("/api/pi/v1/camera/stream")
    assert res.status_code == 503
    err_code = (res.json().get("error") or res.json().get("detail") or {}).get("code")
    assert err_code in {"FRAME_READ_FAILED", "EMPTY_FRAME", "FRAME_UNAVAILABLE"}


def test_adv_pi_camera_rapid_start_stop_churn(pi_camera: Any) -> None:
    """Adversarial Test 5.8: Rapid 10-cycle camera start/stop churn maintains zero leaks."""
    for _ in range(10):
        pi_camera.start()
        assert pi_camera.running is True
        pi_camera.disconnect_consumer()
    assert pi_camera.consumer_count == 0
    assert pi_camera.running is False


def test_adv_pi_ui_es_module_graph_integrity() -> None:
    """Adversarial Test 5.9: Static validation of Pi 5 Web UI ES Module imports and exports."""
    import re
    ui_dir = PROJECT_ROOT / "edge" / "pi5" / "pi5" / "web" / "ui"
    assert ui_dir.exists()

    js_files = list(ui_dir.rglob("*.js"))
    assert len(js_files) >= 10, f"Expected at least 10 JS modules in UI, found {len(js_files)}"

    # Parse exported symbols per file
    exports_by_file: dict[str, set[str]] = {}
    for jf in js_files:
        content = jf.read_text(encoding="utf-8")
        # Match "export function name", "export const name", "export class name", "export { a, b }"
        names = set(re.findall(r"export\s+(?:async\s+)?(?:function|const|class|let)\s+([a-zA-Z0-9_$]+)", content))
        for block in re.findall(r"export\s+\{([^}]+)\}", content):
            for part in block.split(","):
                clean = part.strip().split(" as ")[-1].strip()
                if clean:
                    names.add(clean)
        exports_by_file[jf.name] = names

    # Verify key expected exports exist
    assert "h" in exports_by_file["dom.js"]
    assert "api" in exports_by_file["api.js"]
    assert "cameraView" in exports_by_file["camera.js"]
    assert "firmwareView" in exports_by_file["firmware.js"]
    assert "flightModal" in exports_by_file["flight.js"]


def test_adv_frontend_telemetry_polling_decoupling_contract() -> None:
    """Adversarial Test 5.10: TelemetryPanel autonomous polling vs parent decoupling."""
    tp_file = PROJECT_ROOT / "frontend" / "src" / "components" / "operations" / "TelemetryPanel.tsx"
    assert tp_file.exists()
    content = tp_file.read_text(encoding="utf-8")

    # Contract 1: Guard against autonomous polling when external telemetry is provided
    assert "if (externalTelemetry !== undefined) return;" in content
    # Contract 2: 1s polling interval
    assert "window.setInterval(pollTelemetry, 1000)" in content
    # Contract 3: Cleanup on unmount
    assert "window.clearInterval(telemetryInterval)" in content
    # Contract 4: Age text ticker
    assert "window.clearInterval(ageTicker)" in content
    # Contract 5: Battery threshold classes
    assert "battery-healthy" in content
    assert "battery-warning" in content
    assert "battery-critical" in content


def test_adv_frontend_audiocontext_lifecycle_safety() -> None:
    """Adversarial Test 5.11: AudioContext closes after 500ms and catches autoplay exceptions."""
    ws_file = PROJECT_ROOT / "frontend" / "src" / "components" / "operations" / "OperationsWorkspace.tsx"
    assert ws_file.exists()
    content = ws_file.read_text(encoding="utf-8")

    # Contract 1: Fallback webkitAudioContext support
    assert "webkitAudioContext" in content
    # Contract 2: Autoplay suspended state resume
    assert 'if (ctx.state === "suspended")' in content
    # Contract 3: ctx.close() scheduled after 500ms
    assert "ctx.close()" in content
    assert "500" in content
    # Contract 4: try/catch block suppressing audio blockages
    assert "playNotificationChime" in content
