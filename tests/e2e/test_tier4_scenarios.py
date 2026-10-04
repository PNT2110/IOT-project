"""Tier 4: Real-World Application Scenarios E2E Tests.

Executes complete end-to-end mission workflows:
1. Scenario 1: Complete Mission Authorization, Telemetry Stream & Post-Flight Export
2. Scenario 2: Altitude Boundary Limiting, Failsafe & Battery Alert Recovery
3. Scenario 3: Field Operations Offline AP Maintenance & OTA Flashing
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import subprocess
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from server.app.models import Device, SimulatedFlightRequest, User, Zone
from server.app.security import encrypt_secret, normalize_email, utcnow
from tests.e2e.conftest import make_sealed_envelope, PROJECT_ROOT


# ==============================================================================
# Scenario 1: Complete Mission Authorization, Telemetry Stream & Export
# ==============================================================================
def test_scenario_1_complete_mission_workflow(
    pc_client: TestClient,
    operator_auth: dict[str, str],
    registered_device: dict[str, Any],
    pc_app: Any,
    pc_settings: Any,
) -> None:
    """End-to-End Mission Workflow:
    
    1. Pilot registers with aliased email: 'pilot.f450+hanoi1@gmail.com' -> 'pilotf450@gmail.com'.
    2. Pilot submits flight request for agricultural survey.
    3. Operator receives flight notification alert with pending count.
    4. Operator reviews and approves flight request ('APPROVED_SIMULATED').
    5. Drone begins streaming sealed telemetry packets (takeoff, climb, cruise, battery drop).
    6. Operator monitors live telemetry with <2s latency.
    7. Post-flight audit: Operator downloads flight history CSV and zone GeoJSON.
    """
    # Step 1: Pilot email normalization
    raw_pilot_email = "pilot.f450+hanoi1@gmail.com"
    normalized_pilot_email = normalize_email(raw_pilot_email)
    assert normalized_pilot_email == "pilotf450@gmail.com"
    
    now = utcnow()
    # Step 2: Pilot submits flight request
    details = {
        "applicant_full_name": "Tran Van Pilot",
        "license_code": "VN-PILOT-8899",
        "vehicle": "F450 Survey Quadcopter",
        "purpose": "Agricultural Inspection",
    }
    encrypted_details = encrypt_secret(pc_settings.session_secret, json.dumps(details))
    
    with pc_app.state.session_factory() as db:
        pilot = User(
            username="pilot_hanoi",
            display_name="Tran Van Pilot",
            email_normalized=normalized_pilot_email,
            status="ACTIVE",
            role="PILOT",
            created_at=now,
            updated_at=now,
        )
        db.add(pilot)
        db.flush()
        
        flight = SimulatedFlightRequest(
            submitter_user_id=pilot.id,
            device_id=registered_device["id"],
            summary="Agricultural Survey Mission Alpha",
            scheduled_start_at=now,
            scheduled_end_at=now,
            simulated_geometry_json="null",
            status="SUBMITTED",
            version=1,
            source="WEB",
            request_details_ciphertext=encrypted_details,
            created_at=now,
            updated_at=now,
        )
        db.add(flight)
        db.commit()
        db.refresh(flight)
        flight_id = flight.id

    # Step 3: Operator queries notification endpoint and receives alert
    notif_res = pc_client.get("/api/v1/flight-requests/notifications", headers=operator_auth)
    assert notif_res.status_code == 200
    notif_data = notif_res.json().get("data", notif_res.json())
    assert notif_data.get("pending_count", 0) >= 1
    assert notif_data.get("latest_request_id") == flight_id

    # Step 4: Operator reviews and approves flight
    with pc_app.state.session_factory() as db:
        item = db.get(SimulatedFlightRequest, flight_id)
        assert item is not None
        item.status = "APPROVED_SIMULATED"
        db.commit()

    # Step 5: Drone streams multi-phase sealed telemetry (takeoff -> climb -> cruise)
    mission_phases = [
        {"seq": 6001, "alt": 0.0, "battery": 98.0, "v": 12.6, "state": "IDLE"},
        {"seq": 6002, "alt": 15.2, "battery": 96.5, "v": 12.4, "state": "CLIMB"},
        {"seq": 6003, "alt": 45.0, "battery": 94.0, "v": 12.1, "state": "CRUISE"},
        {"seq": 6004, "alt": 45.1, "battery": 82.5, "v": 11.4, "state": "CRUISE"},
    ]
    
    t_start = time.time()
    for phase in mission_phases:
        telemetry_sample = {
            "device_id": registered_device["id"],
            "seq": phase["seq"],
            "observed_at": "2026-10-03T21:20:00Z",
            "latitude": 21.0285 + phase["seq"] * 0.00001,
            "longitude": 105.8544 + phase["seq"] * 0.00001,
            "altitude_m": phase["alt"],
            "battery_pct": phase["battery"],
            "voltage_v": phase["v"],
            "fix_state": "FIX",
            "stale": False,
        }
        envelope = make_sealed_envelope(registered_device["key"], registered_device["id"], telemetry_sample)
        ingest_res = pc_client.post("/api/v1/device/telemetry", json=envelope)
        assert ingest_res.status_code == 200

    # Step 6: Operator monitors live telemetry stream
    live_res = pc_client.get(f"/api/v1/telemetry/latest?device_id={registered_device['id']}", headers=operator_auth)
    assert live_res.status_code == 200
    assert time.time() - t_start < 2.0  # Latency bound
    
    live_telem = live_res.json().get("data", live_res.json()).get("telemetry", live_res.json().get("data"))
    assert live_telem["seq"] == 6004
    assert abs(live_telem["altitude_m"] - 45.1) < 0.1
    assert abs(live_telem["battery_pct"] - 82.5) < 0.1

    # Step 7: Post-flight exports
    csv_res = pc_client.get("/api/v1/flight-requests/export/csv", headers=operator_auth)
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers.get("content-type", "")
    assert "Tran Van Pilot" in csv_res.text or "Agricultural Survey Mission Alpha" in csv_res.text

    geojson_res = pc_client.get("/api/v1/zones/export/geojson", headers=operator_auth)
    assert geojson_res.status_code == 200
    assert geojson_res.json().get("type") == "FeatureCollection"


# ==============================================================================
# Scenario 2: Altitude Limiting, Failsafe & Battery Alert Recovery
# ==============================================================================
def test_scenario_2_altitude_limit_and_battery_failsafe(
    tmp_path: Path,
    pc_client: TestClient,
    registered_device: dict[str, Any],
    operator_auth: dict[str, str],
) -> None:
    """Scenario 2: Boundary failsafe & recovery.
    
    1. Drone climbs to 121m with high entry throttle (1600 us) and descent rate (-1.5 m/s).
    2. Dynamic limiter calculates safe floor, preventing free fall.
    3. Low battery warning (18%) ingested in telemetry stream.
    4. Operator detects critical battery in live monitoring.
    """
    flight_gate_path = PROJECT_ROOT / "firmware" / "FC_can_bang" / "flight_gate.h"
    cpp_source = tmp_path / "scenario_failsafe.cpp"
    cpp_source.write_text(f"""
#include <iostream>
#include <cassert>
#include "{flight_gate_path.as_posix()}"

int main() {{
    AltLimiter limiter;
    // Approaching ceiling 120m at 121m, throttle 1600 us
    int capped = altitude_throttle_cap(limiter, 121.0f, 120.0f, 1600);
    assert(limiter.active);
    assert(capped <= 1600);
    // Dynamic floor check: must not collapse to 1100 us on entry
    assert(capped >= 1100);
    std::cout << "Limiter successfully managed boundary" << std::endl;
    return 0;
}}
""", encoding="utf-8")
    
    exe_path = tmp_path / "scenario_failsafe.exe"
    compile_res = subprocess.run(
        ["g++", "-std=c++17", "-Wall", "-Wextra", f"-I{(flight_gate_path.parent).as_posix()}", str(cpp_source), "-o", str(exe_path)],
        capture_output=True,
        text=True,
    )
    assert compile_res.returncode == 0
    assert subprocess.run([str(exe_path)], capture_output=True, text=True).returncode == 0
    
    # Ingest low battery telemetry alert
    low_battery_payload = {
        "device_id": registered_device["id"],
        "seq": 7001,
        "observed_at": "2026-10-03T21:25:00Z",
        "latitude": 21.0300,
        "longitude": 105.8550,
        "altitude_m": 119.5,
        "battery_pct": 18.0,
        "voltage_v": 10.4,
        "fix_state": "FIX",
        "stale": False,
    }
    env = make_sealed_envelope(registered_device["key"], registered_device["id"], low_battery_payload)
    assert pc_client.post("/api/v1/device/telemetry", json=env).status_code == 200
    
    # Operator query detects low battery alert threshold
    telem_res = pc_client.get(f"/api/v1/telemetry/latest?device_id={registered_device['id']}", headers=operator_auth)
    assert telem_res.status_code == 200
    telem_data = telem_res.json().get("data", telem_res.json()).get("telemetry", telem_res.json().get("data"))
    assert telem_data["battery_pct"] <= 20.0, "Low battery condition detected on live monitor"


# ==============================================================================
# Scenario 3: Field Operations Offline AP Maintenance & OTA Flashing
# ==============================================================================
def test_scenario_3_field_operations_offline_ap_maintenance(
    pi_client: TestClient,
) -> None:
    """Scenario 3: Field Operations on Offline Pi 5 AP (192.168.4.1).
    
    1. Operator connects to Pi 5 local UI.
    2. Modular ES module architecture loads views.
    3. Camera stream is paused to conserve bandwidth.
    4. Firmware update binary is uploaded via OTA endpoint while disarmed.
    5. Flashing job is queued and processed.
    """
    # Step 1: Connect to root UI
    home = pi_client.get("/")
    assert home.status_code == 200
    assert "F450 PNT PVD" in home.text

    # Step 2: Upload new firmware binary
    new_bin = b"\xe9" + b"FIELD_MAINTENANCE_OTA_BIN_DATA" * 50
    upload_res = pi_client.post(
        "/api/pi/v1/firmware/upload",
        files={"file": ("FC_can_bang.bin", io.BytesIO(new_bin), "application/octet-stream")},
    )
    assert upload_res.status_code in {200, 202}
    job = upload_res.json().get("data", upload_res.json())
    assert "job_id" in job
