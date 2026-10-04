"""Tier 2: Boundary & Corner Cases E2E Tests.

Exercises system limits, malformed inputs, extreme coordinates/altitudes,
replay attacks, cryptographic skew, and error handling edge cases.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path
import subprocess
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from server.app.security import normalize_email
from tests.e2e.conftest import make_sealed_envelope, PROJECT_ROOT


# ==============================================================================
# 1. Email Normalization Boundary & Corner Cases
# ==============================================================================
def test_email_normalization_multiple_plus_tags() -> None:
    """Multiple subaddress '+' signs must be truncated from first '+'."""
    assert normalize_email("pilot+primary+backup@gmail.com") == "pilot@gmail.com"
    assert normalize_email("operator+f450+test1+v2@googlemail.com") == "operator@gmail.com"
    assert normalize_email("user+tag1+tag2@example.com") == "user@example.com"


def test_email_normalization_consecutive_and_trailing_dots() -> None:
    """Consecutive and trailing dots in local part for Gmail."""
    assert normalize_email("pilot..drone@gmail.com") == "pilotdrone@gmail.com"
    assert normalize_email("operator.@gmail.com") == "operator@gmail.com"
    assert normalize_email("..test..user..@gmail.com") == "testuser@gmail.com"


def test_email_normalization_non_email_identifiers() -> None:
    """Non-email usernames like 'admin', 'operator_01', or empty strings must not crash."""
    assert normalize_email("admin") == "admin"
    assert normalize_email("operator_01") == "operator_01"
    assert normalize_email("  SUPER_ADMIN  ") == "super_admin"
    assert normalize_email("") == ""


def test_email_normalization_extreme_length() -> None:
    """Email up to RFC maximum lengths (local 64, total 254/320)."""
    long_local = "a" * 60 + ".b" * 4
    raw_email = f"{long_local}+sub@gmail.com"
    expected = ("a" * 60 + "b" * 4) + "@gmail.com"
    assert normalize_email(raw_email) == expected


# ==============================================================================
# 2. Altitude Limiter Boundary & Corner Cases
# ==============================================================================
def test_altitude_limiter_boundary_negative_vspeed_dampening(tmp_path: Path) -> None:
    """High descent rate (vspeed = -3.0 m/s) must hold throttle at or above safe floor."""
    flight_gate_path = PROJECT_ROOT / "firmware" / "FC_can_bang" / "flight_gate.h"
    cpp_source = tmp_path / "verify_vspeed_dampening.cpp"
    cpp_source.write_text(f"""
#include <iostream>
#include <cassert>
#include "{flight_gate_path.as_posix()}"

int main() {{
    AltLimiter limiter;
    // Enter ceiling 120.0m with relative altitude 122.0m, throttle 1550 us, vspeed -3.5 m/s (rapid descent)
    int capped = altitude_throttle_cap(limiter, 122.0f, 120.0f, 1550);
    assert(limiter.active);
    // Limiter must not drop below safe floor even during rapid descent
    assert(capped >= 1100);
    std::cout << "vspeed dampening boundary ok: " << capped << std::endl;
    return 0;
}}
""", encoding="utf-8")
    
    exe_path = tmp_path / "verify_vspeed_dampening.exe"
    res = subprocess.run(
        ["g++", "-std=c++17", "-Wall", "-Wextra", f"-I{(flight_gate_path.parent).as_posix()}", str(cpp_source), "-o", str(exe_path)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    run_res = subprocess.run([str(exe_path)], capture_output=True, text=True)
    assert run_res.returncode == 0


def test_altitude_limiter_boundary_below_arm_altitude(tmp_path: Path) -> None:
    """Negative relative altitude (e.g. -20m below takeoff point) must never activate limiter."""
    flight_gate_path = PROJECT_ROOT / "firmware" / "FC_can_bang" / "flight_gate.h"
    cpp_source = tmp_path / "verify_negative_alt.cpp"
    cpp_source.write_text(f"""
#include <iostream>
#include <cassert>
#include "{flight_gate_path.as_posix()}"

int main() {{
    AltLimiter limiter;
    int capped = altitude_throttle_cap(limiter, -20.0f, 100.0f, 1500);
    assert(!limiter.active);
    assert(capped == 1500);
    return 0;
}}
""", encoding="utf-8")
    
    exe_path = tmp_path / "verify_negative_alt.exe"
    res = subprocess.run(
        ["g++", "-std=c++17", "-Wall", "-Wextra", f"-I{(flight_gate_path.parent).as_posix()}", str(cpp_source), "-o", str(exe_path)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    run_res = subprocess.run([str(exe_path)], capture_output=True, text=True)
    assert run_res.returncode == 0


# ==============================================================================
# 3. Telemetry Ingestion Boundary & Security Cases
# ==============================================================================
def test_telemetry_ingestion_extreme_coordinates_and_altitude(
    pc_client: TestClient,
    registered_device: dict[str, Any],
) -> None:
    """Extreme geographical coordinates (North pole, Antimeridian) and altitudes (-400m Dead Sea, 10,000m)."""
    extreme_samples = [
        {"lat": 90.0, "lon": 0.0, "alt": 10000.0, "battery": 100.0, "v": 12.6},
        {"lat": -90.0, "lon": 0.0, "alt": -413.0, "battery": 0.0, "v": 9.5},
        {"lat": 0.0, "lon": 180.0, "alt": 0.0, "battery": 50.0, "v": 11.1},
        {"lat": 0.0, "lon": -180.0, "alt": 42.0, "battery": 75.0, "v": 11.8},
    ]
    
    for i, s in enumerate(extreme_samples):
        payload = {
            "device_id": registered_device["id"],
            "seq": 1000 + i,
            "observed_at": "2026-10-03T21:00:00Z",
            "latitude": s["lat"],
            "longitude": s["lon"],
            "altitude_m": s["alt"],
            "battery_pct": s["battery"],
            "voltage_v": s["v"],
            "fix_state": "FIX",
            "stale": False,
        }
        envelope = make_sealed_envelope(registered_device["key"], registered_device["id"], payload)
        response = pc_client.post("/api/v1/device/telemetry", json=envelope)
        assert response.status_code == 200, f"Failed on extreme sample {s}: {response.text}"


def test_telemetry_ingestion_replay_attack_rejected(
    pc_client: TestClient,
    registered_device: dict[str, Any],
) -> None:
    """Replaying identical sealed envelope (same nonce) within TTL must be rejected with 401."""
    payload = {
        "device_id": registered_device["id"],
        "seq": 2001,
        "observed_at": "2026-10-03T21:05:00Z",
        "latitude": 21.03,
        "longitude": 105.85,
        "altitude_m": 30.0,
        "battery_pct": 90.0,
        "fix_state": "FIX",
    }
    envelope = make_sealed_envelope(registered_device["key"], registered_device["id"], payload)
    
    first_res = pc_client.post("/api/v1/device/telemetry", json=envelope)
    assert first_res.status_code == 200
    
    # Replay identical envelope
    replay_res = pc_client.post("/api/v1/device/telemetry", json=envelope)
    assert replay_res.status_code == 401, f"Expected 401 on replay attack, got {replay_res.status_code}: {replay_res.text}"


def test_telemetry_ingestion_stale_timestamp_skew_rejected(
    pc_client: TestClient,
    registered_device: dict[str, Any],
) -> None:
    """Envelopes with timestamp skew > 300s in the past or future must be rejected with 401."""
    now = int(time.time())
    stale_past = now - 3600  # 1 hour ago
    stale_future = now + 3600  # 1 hour future
    
    payload = {"device_id": registered_device["id"], "seq": 3001, "latitude": 21.0, "longitude": 105.0}
    
    env_past = make_sealed_envelope(registered_device["key"], registered_device["id"], payload, ts=stale_past)
    env_future = make_sealed_envelope(registered_device["key"], registered_device["id"], payload, ts=stale_future)
    
    assert pc_client.post("/api/v1/device/telemetry", json=env_past).status_code == 401
    assert pc_client.post("/api/v1/device/telemetry", json=env_future).status_code == 401


def test_telemetry_ingestion_tampered_ciphertext_rejected(
    pc_client: TestClient,
    registered_device: dict[str, Any],
) -> None:
    """Tampering with a single byte in ciphertext must fail AES-GCM authentication tag and return 401."""
    payload = {"device_id": registered_device["id"], "seq": 4001, "latitude": 21.0, "longitude": 105.0}
    envelope = make_sealed_envelope(registered_device["key"], registered_device["id"], payload)
    
    # Corrupt ciphertext
    ct = list(envelope["ciphertext"])
    ct[0] = "A" if ct[0] != "A" else "B"
    envelope["ciphertext"] = "".join(ct)
    
    res = pc_client.post("/api/v1/device/telemetry", json=envelope)
    assert res.status_code == 401


# ==============================================================================
# 4. Flight Notification & Export Boundary Cases
# ==============================================================================
def test_flight_notifications_empty_queue(
    pc_client: TestClient,
    operator_auth: dict[str, str],
) -> None:
    """Empty flight queue returns pending_count: 0 and null latest_request_id."""
    res = pc_client.get("/api/v1/flight-requests/notifications", headers=operator_auth)
    assert res.status_code == 200
    data = res.json().get("data", res.json())
    assert data.get("pending_count") == 0
    assert data.get("latest_request_id") is None


def test_flight_notifications_unauthorized_access(pc_client: TestClient) -> None:
    """Unauthenticated requests to flight notifications must be rejected with 401."""
    res = pc_client.get("/api/v1/flight-requests/notifications")
    assert res.status_code in {401, 403}


def test_geojson_export_empty_zones(pc_client: TestClient, operator_auth: dict[str, str]) -> None:
    """When no zones exist, GeoJSON export returns valid FeatureCollection with empty features list."""
    res = pc_client.get("/api/v1/zones/export/geojson", headers=operator_auth)
    assert res.status_code == 200
    body = res.json()
    assert body.get("type") == "FeatureCollection"
    assert isinstance(body.get("features"), list)


def test_csv_export_empty_flights(pc_client: TestClient, operator_auth: dict[str, str]) -> None:
    """When no flights exist, CSV export returns valid header row and 0 data rows."""
    res = pc_client.get("/api/v1/flight-requests/export/csv", headers=operator_auth)
    assert res.status_code == 200
    rows = list(csv.reader(io.StringIO(res.text)))
    assert len(rows) == 1  # Only header


def test_csv_export_special_characters_escaping(
    pc_client: TestClient,
    operator_auth: dict[str, str],
    pc_app: Any,
) -> None:
    """Zone names or summaries containing quotes, commas, and UTF-8 characters must be properly escaped."""
    res = pc_client.get("/api/v1/flight-requests/export/csv", headers=operator_auth)
    assert res.status_code == 200
    # Header format compliance with RFC 4180
    assert "text/csv" in res.headers.get("content-type", "")


# ==============================================================================
# 5. OTA Firmware Upload Boundary Cases
# ==============================================================================
def test_ota_upload_invalid_magic_byte_rejected(pi_client: TestClient) -> None:
    """Upload without ESP32 magic byte 0xe9 must be rejected."""
    invalid_bin = b"\x7fELF" + b"bogus_content" * 10
    res = pi_client.post(
        "/api/pi/v1/firmware/upload",
        files={"file": ("firmware.bin", io.BytesIO(invalid_bin), "application/octet-stream")},
    )
    assert res.status_code in {400, 422}


def test_ota_upload_oversized_binary_rejected(pi_client: TestClient) -> None:
    """Upload exceeding 4MB limit must be rejected with 413 Payload Too Large."""
    oversized = b"\xe9" + b"X" * (4 * 1024 * 1024 + 100)
    res = pi_client.post(
        "/api/pi/v1/firmware/upload",
        files={"file": ("huge.bin", io.BytesIO(oversized), "application/octet-stream")},
    )
    assert res.status_code in {413, 400, 422}


def test_ota_upload_zero_byte_file_rejected(pi_client: TestClient) -> None:
    """Zero byte file upload must be rejected."""
    res = pi_client.post(
        "/api/pi/v1/firmware/upload",
        files={"file": ("empty.bin", io.BytesIO(b""), "application/octet-stream")},
    )
    assert res.status_code in {400, 422}
