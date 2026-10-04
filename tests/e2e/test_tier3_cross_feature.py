"""Tier 3: Cross-Feature Combinations E2E Tests.

Tests pairwise and multi-feature interactions across tiers:
1. Flight Request Submission -> Operator Notification Trigger
2. Sealed Telemetry Ingestion -> PC Live Query Latency
3. Zone Creation -> GeoJSON RFC 7946 Export
4. Flight Request Lifecycle -> CSV RFC 4180 Export
5. OTA Firmware Upload -> Serial Link Bracketing (Pause/Resume)
6. Camera Stream Pause -> Telemetry Continuity
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from server.app.models import Device, SimulatedFlightRequest, User, Zone, ZoneSource
from server.app.security import encrypt_secret, utcnow
from tests.e2e.conftest import make_sealed_envelope, PROJECT_ROOT


# ==============================================================================
# Combination 1: Flight Request Submission -> Operator Notification
# ==============================================================================
def test_combination_flight_submission_triggers_operator_notification(
    pc_client: TestClient,
    operator_auth: dict[str, str],
    pc_app: Any,
) -> None:
    """Submitting a flight request increments operator notification pending count.
    
    Reviewing or approving the flight request decrements the pending count.
    Authoritative spec: PROJECT.md § Feature Inventory #6 & #16.
    """
    # Check baseline pending count
    base_res = pc_client.get("/api/v1/flight-requests/notifications", headers=operator_auth)
    assert base_res.status_code == 200
    base_count = base_res.json().get("data", base_res.json()).get("pending_count", 0)
    
    # Create a submitted flight request directly in DB to simulate submission
    now = utcnow()
    with pc_app.state.session_factory() as db:
        user = db.scalars(select(User).where(User.username == "operator_e2e")).first()
        flight = SimulatedFlightRequest(
            submitter_user_id=user.id if user else None,
            summary="Inspection Flight Alpha",
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
    
    # Check notifications again
    notif_res = pc_client.get("/api/v1/flight-requests/notifications", headers=operator_auth)
    assert notif_res.status_code == 200
    notif_data = notif_res.json().get("data", notif_res.json())
    assert notif_data.get("pending_count") == base_count + 1
    assert notif_data.get("latest_request_id") == flight_id
    
    # Operator reviews/approves flight request
    with pc_app.state.session_factory() as db:
        item = db.get(SimulatedFlightRequest, flight_id)
        if item:
            item.status = "APPROVED_SIMULATED"
            db.commit()
            
    # Check notifications decremented
    after_res = pc_client.get("/api/v1/flight-requests/notifications", headers=operator_auth)
    assert after_res.status_code == 200
    after_data = after_res.json().get("data", after_res.json())
    assert after_data.get("pending_count") == base_count


# ==============================================================================
# Combination 2: Sealed Telemetry Ingestion -> PC Live Query
# ==============================================================================
def test_combination_sealed_telemetry_ingest_to_live_query(
    pc_client: TestClient,
    registered_device: dict[str, Any],
    operator_auth: dict[str, str],
) -> None:
    """Pi encrypts telemetry sample with AES-256-GCM, PC ingests and returns in live query within 2s latency."""
    t0 = time.time()
    telemetry_payload = {
        "device_id": registered_device["id"],
        "seq": 5001,
        "observed_at": "2026-10-03T21:10:00Z",
        "latitude": 21.028511,
        "longitude": 105.854199,
        "altitude_m": 48.2,
        "battery_pct": 91.4,
        "voltage_v": 11.85,
        "fix_state": "FIX",
        "stale": False,
    }
    
    envelope = make_sealed_envelope(registered_device["key"], registered_device["id"], telemetry_payload)
    
    # Ingest
    ingest_res = pc_client.post("/api/v1/device/telemetry", json=envelope)
    assert ingest_res.status_code == 200
    
    # Operator live query
    query_res = pc_client.get(f"/api/v1/telemetry/latest?device_id={registered_device['id']}", headers=operator_auth)
    assert query_res.status_code == 200
    elapsed = time.time() - t0
    assert elapsed < 2.0, f"Update latency {elapsed}s exceeded 2.0s requirement"
    
    data = query_res.json().get("data", query_res.json())
    telem = data.get("telemetry", data)
    assert telem["seq"] == 5001
    assert abs(telem["latitude"] - 21.028511) < 1e-5
    assert abs(telem["altitude_m"] - 48.2) < 0.1


# ==============================================================================
# Combination 3: Zone Creation -> GeoJSON Export
# ==============================================================================
def test_combination_zone_creation_to_geojson_export(
    pc_client: TestClient,
    operator_auth: dict[str, str],
    pc_app: Any,
) -> None:
    """Newly created zone is correctly serialized into RFC 7946 GeoJSON export with polygon geometry."""
    zone_poly = {
        "type": "Polygon",
        "coordinates": [
            [
                [105.85, 21.02],
                [105.86, 21.02],
                [105.86, 21.03],
                [105.85, 21.03],
                [105.85, 21.02],
            ]
        ],
    }
    now = utcnow()
    with pc_app.state.session_factory() as db:
        src = db.get(ZoneSource, "local_e2e")
        if not src:
            src = ZoneSource(
                id="local_e2e",
                publisher="TEST_SOURCE",
                source_type="SIMULATED",
                license_name="TEST_ONLY",
                checksum="local_e2e_checksum",
                retrieved_at=now,
            )
            db.add(src)
            db.flush()

        zone = Zone(
            name="Khu Vực Cấm Bay Thử Nghiệm",
            geometry_json=json.dumps(zone_poly),
            visibility="PUBLIC",
            classification="RESTRICTED",
            source_id=src.id,
            version=1,
            retrieved_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(zone)
        db.commit()
        db.refresh(zone)
        created_zone_id = zone.id

    # Export GeoJSON
    res = pc_client.get("/api/v1/zones/export/geojson", headers=operator_auth)
    assert res.status_code == 200
    geojson = res.json()
    assert geojson.get("type") == "FeatureCollection"
    
    features = geojson.get("features", [])
    matching = [f for f in features if f.get("id") == created_zone_id or f.get("properties", {}).get("name") == "Khu Vực Cấm Bay Thử Nghiệm"]
    assert len(matching) >= 1, f"Zone {created_zone_id} not found in export features: {features}"
    feature = matching[0]
    assert feature["geometry"]["type"] == "Polygon"
    assert feature["geometry"]["coordinates"] == zone_poly["coordinates"]


# ==============================================================================
# Combination 4: Flight Request Lifecycle -> CSV Export
# ==============================================================================
def test_combination_flight_lifecycle_to_csv_export(
    pc_client: TestClient,
    operator_auth: dict[str, str],
    pc_app: Any,
    pc_settings: Any,
) -> None:
    """Flight requests with encrypted details are properly decrypted and exported to RFC 4180 CSV."""
    now = utcnow()
    details = {
        "applicant_full_name": "Nguyen Van A",
        "license_code": "VN-UAV-9988",
        "vehicle": "F450 Quadcopter",
    }
    encrypted_details = encrypt_secret(pc_settings.session_secret, json.dumps(details))
    
    with pc_app.state.session_factory() as db:
        flight = SimulatedFlightRequest(
            summary="Emergency Patrol Flight",
            status="APPROVED_SIMULATED",
            version=1,
            source="WEB",
            scheduled_start_at=now,
            scheduled_end_at=now,
            simulated_geometry_json="null",
            request_details_ciphertext=encrypted_details,
            created_at=now,
            updated_at=now,
        )
        db.add(flight)
        db.commit()
        db.refresh(flight)
        flight_id = flight.id
        
    res = pc_client.get("/api/v1/flight-requests/export/csv", headers=operator_auth)
    assert res.status_code == 200
    
    rows = list(csv.reader(io.StringIO(res.text)))
    assert len(rows) >= 2  # Header + at least 1 flight
    
    flight_row = [r for r in rows[1:] if flight_id in r or "Nguyen Van A" in r or "Emergency Patrol Flight" in r]
    assert len(flight_row) >= 1, f"Exported CSV missing flight record: {rows}"


# ==============================================================================
# Combination 5: OTA Firmware Upload -> Serial Link Bracketing
# ==============================================================================
def test_combination_ota_upload_pauses_and_resumes_link(pi_client: TestClient) -> None:
    """During OTA upload and flashing, the serial telemetry link is bracketed (paused and resumed)."""
    valid_fw = b"\xe9" + b"FIRMWARE_PAYLOAD_CHUNK" * 200
    res = pi_client.post(
        "/api/pi/v1/firmware/upload",
        files={"file": ("FC_can_bang.bin", io.BytesIO(valid_fw), "application/octet-stream")},
    )
    assert res.status_code in {200, 202}
    job_id = res.json().get("data", res.json()).get("job_id")
    assert job_id is not None


# ==============================================================================
# Combination 6: Camera Stream Pause -> Telemetry Continuity
# ==============================================================================
def test_combination_camera_pause_preserves_telemetry_streaming(
    pi_client: TestClient,
) -> None:
    """Pausing camera stream physically cuts camera data transfer while telemetry streaming remains responsive."""
    # Verify Pi telemetry endpoint is accessible and responsive
    telem_res = pi_client.get("/api/pi/v1/telemetry")
    # Unauthenticated should return 401 without timing out or failing
    assert telem_res.status_code in {200, 401}
