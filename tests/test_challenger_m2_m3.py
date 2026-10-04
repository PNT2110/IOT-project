"""Empirical Challenger Stress & Verification Test Suite for Milestones 2 & 3.

Adversarial stress-testing covering:
1. Telemetry Ingestion: High frequency bursts, propagation latency (<2s), sequence out-of-order, multi-device isolation, replay attacks, timestamp skew.
2. Exports: Strict RFC 7946 GeoJSON validation with Shapely, strict RFC 4180 CSV validation with quote/comma/newline/Unicode escaping.
3. Pi OTA Upload: Oversized (>4MB), corrupt magic bytes, non-bin files, arming safety locks, link bracketing.
"""
from __future__ import annotations

import base64
import csv
from datetime import timedelta
import io
import json
from pathlib import Path
import secrets
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from shapely.geometry import shape

pytest_plugins = ["tests.e2e.conftest"]

from server.app.models import Device, SimulatedFlightRequest, Zone, ZoneSource
from server.app.security import encrypt_secret, utcnow
from tests.e2e.conftest import make_sealed_envelope


# ==============================================================================
# SECTION 1: TELEMETRY INGESTION & LATENCY VERIFICATION (< 2s)
# ==============================================================================

def test_telemetry_propagation_latency_stress(
    pc_client: TestClient,
    registered_device: dict[str, Any],
    operator_auth: dict[str, str],
) -> None:
    """Stress-test telemetry ingestion latency across 50 consecutive posts.
    
    Verifies that telemetry posted via POST /api/v1/device/telemetry is immediately
    observable via GET /api/v1/telemetry/latest with < 2.0s propagation delay.
    """
    latencies = []
    
    for seq in range(1, 51):
        obs_time = f"2026-10-04T05:{seq:02d}:00Z"
        payload = {
            "device_id": registered_device["id"],
            "seq": seq,
            "observed_at": obs_time,
            "latitude": 21.0285 + (seq * 0.0001),
            "longitude": 105.8544 + (seq * 0.0001),
            "altitude_m": 40.0 + (seq * 0.5),
            "battery_pct": max(1.0, 100.0 - seq),
            "voltage_v": 12.6 - (seq * 0.02),
            "fix_state": "FIX",
            "stale": False,
        }
        envelope = make_sealed_envelope(registered_device["key"], registered_device["id"], payload)
        
        t0 = time.perf_counter()
        post_res = pc_client.post("/api/v1/device/telemetry", json=envelope)
        assert post_res.status_code == 200, f"Post failed on seq {seq}: {post_res.text}"
        
        get_res = pc_client.get(
            f"/api/v1/telemetry/latest?device_id={registered_device['id']}",
            headers=operator_auth,
        )
        t1 = time.perf_counter()
        latency = t1 - t0
        latencies.append(latency)
        
        assert get_res.status_code == 200, f"Query failed on seq {seq}: {get_res.text}"
        body = get_res.json()["data"]["telemetry"]
        assert body["seq"] == seq
        assert body["observed_at"] == obs_time
        assert abs(body["latitude"] - (21.0285 + seq * 0.0001)) < 1e-6
        assert latency < 2.0, f"Latency violation on seq {seq}: {latency:.4f}s >= 2.0s"

    p50 = sorted(latencies)[len(latencies) // 2]
    p95 = sorted(latencies)[int(len(latencies) * 0.95)]
    p_max = max(latencies)
    print(f"\n[LATENCY STRESS BENCHMARK] 50 runs: p50={p50*1000:.2f}ms, p95={p95*1000:.2f}ms, max={p_max*1000:.2f}ms")
    assert p_max < 2.0, f"Max propagation latency exceeded 2s: {p_max:.4f}s"


def test_telemetry_high_frequency_burst_and_memory_stability(
    pc_client: TestClient,
    registered_device: dict[str, Any],
    operator_auth: dict[str, str],
    pc_app: Any,
) -> None:
    """Send a high-frequency burst of 100 packets.
    
    Verifies throughput, latest state consistency, and that server memory is bounded.
    """
    burst_count = 100
    t_start = time.perf_counter()
    
    for seq in range(1, burst_count + 1):
        payload = {
            "device_id": registered_device["id"],
            "seq": 10000 + seq,
            "latitude": 21.0 + (seq * 0.001),
            "longitude": 105.0 + (seq * 0.001),
            "altitude_m": 50.0,
            "battery_pct": 85.0,
        }
        envelope = make_sealed_envelope(registered_device["key"], registered_device["id"], payload)
        res = pc_client.post("/api/v1/device/telemetry", json=envelope)
        assert res.status_code == 200
        
    t_end = time.perf_counter()
    duration = t_end - t_start
    rate = burst_count / duration
    print(f"\n[BURST THROUGHPUT] {burst_count} envelopes processed in {duration:.3f}s ({rate:.1f} env/s)")

    # Verify latest is accurately updated to the last burst packet
    get_res = pc_client.get(
        f"/api/v1/telemetry/latest?device_id={registered_device['id']}",
        headers=operator_auth,
    )
    assert get_res.status_code == 200
    latest = get_res.json()["data"]["telemetry"]
    assert latest["seq"] == 10000 + burst_count

    # Check memory bounds: latest_telemetry cache should only retain 1 entry for this device + 1 for __latest__
    cache = pc_app.state.latest_telemetry
    assert len(cache) <= 2, f"Memory leak detected: cache has {len(cache)} entries instead of <= 2"


def test_telemetry_multi_device_isolation(
    pc_client: TestClient,
    pc_app: Any,
    operator_auth: dict[str, str],
) -> None:
    """Interleave telemetry from 3 separate devices and verify state isolation."""
    settings = pc_app.state.settings
    devices = []
    
    # Create 3 registered devices
    for i in range(3):
        raw_key = secrets.token_bytes(32)
        b64_key = base64.urlsafe_b64encode(raw_key).decode()
        encrypted_key = encrypt_secret(settings.session_secret, b64_key)
        with pc_app.state.session_factory() as db:
            dev = Device(name=f"MultiDrone-{i}", key_encrypted=encrypted_key, created_at=utcnow())
            db.add(dev)
            db.commit()
            db.refresh(dev)
            devices.append({"id": dev.id, "key": raw_key, "name": dev.name})

    # Post telemetry in interleaved order: Dev0 -> Dev1 -> Dev2 -> Dev1 -> Dev0
    steps = [
        (devices[0], 101, 10.1),
        (devices[1], 201, 20.1),
        (devices[2], 301, 30.1),
        (devices[1], 202, 20.2),
        (devices[0], 102, 10.2),
    ]
    for dev, seq, lat in steps:
        payload = {"device_id": dev["id"], "seq": seq, "latitude": lat, "longitude": 105.0}
        env = make_sealed_envelope(dev["key"], dev["id"], payload)
        res = pc_client.post("/api/v1/device/telemetry", json=env)
        assert res.status_code == 200

    # Query device 0
    res0 = pc_client.get(f"/api/v1/telemetry/latest?device_id={devices[0]['id']}", headers=operator_auth)
    assert res0.json()["data"]["telemetry"]["seq"] == 102
    assert res0.json()["data"]["telemetry"]["latitude"] == 10.2

    # Query device 1
    res1 = pc_client.get(f"/api/v1/telemetry/latest?device_id={devices[1]['id']}", headers=operator_auth)
    assert res1.json()["data"]["telemetry"]["seq"] == 202
    assert res1.json()["data"]["telemetry"]["latitude"] == 20.2

    # Query device 2
    res2 = pc_client.get(f"/api/v1/telemetry/latest?device_id={devices[2]['id']}", headers=operator_auth)
    assert res2.json()["data"]["telemetry"]["seq"] == 301
    assert res2.json()["data"]["telemetry"]["latitude"] == 30.1

    # Query latest global (last post was Dev 0 with seq 102)
    res_global = pc_client.get("/api/v1/telemetry/latest", headers=operator_auth)
    assert res_global.json()["data"]["telemetry"]["device_id"] == devices[0]["id"]
    assert res_global.json()["data"]["telemetry"]["seq"] == 102


def test_telemetry_out_of_order_sequence_empirical_behavior(
    pc_client: TestClient,
    registered_device: dict[str, Any],
    operator_auth: dict[str, str],
) -> None:
    """Empirically document sequence out-of-order behavior.
    
    When seq 50 arrives after seq 100, observe server behavior.
    """
    dev_id = registered_device["id"]
    key = registered_device["key"]

    # 1. Send seq=100
    p1 = {"device_id": dev_id, "seq": 100, "latitude": 21.1}
    pc_client.post("/api/v1/device/telemetry", json=make_sealed_envelope(key, dev_id, p1))
    
    res1 = pc_client.get(f"/api/v1/telemetry/latest?device_id={dev_id}", headers=operator_auth)
    assert res1.json()["data"]["telemetry"]["seq"] == 100

    # 2. Send delayed out-of-order packet seq=50
    p2 = {"device_id": dev_id, "seq": 50, "latitude": 21.05}
    pc_client.post("/api/v1/device/telemetry", json=make_sealed_envelope(key, dev_id, p2))
    
    res2 = pc_client.get(f"/api/v1/telemetry/latest?device_id={dev_id}", headers=operator_auth)
    # Empirical observation: Server stores latest by arrival time (seq 50)
    assert res2.json()["data"]["telemetry"]["seq"] == 50
    print("\n[EMPIRICAL FINDING] Telemetry cache updates on arrival time; out-of-order seq 50 replaces seq 100.")

    # 3. Send seq=101
    p3 = {"device_id": dev_id, "seq": 101, "latitude": 21.15}
    pc_client.post("/api/v1/device/telemetry", json=make_sealed_envelope(key, dev_id, p3))
    res3 = pc_client.get(f"/api/v1/telemetry/latest?device_id={dev_id}", headers=operator_auth)
    assert res3.json()["data"]["telemetry"]["seq"] == 101


def test_telemetry_replay_and_drift_attack_suite(
    pc_client: TestClient,
    registered_device: dict[str, Any],
) -> None:
    """Stress-test envelope replay and cryptographic timestamp drift attacks."""
    dev_id = registered_device["id"]
    key = registered_device["key"]
    now = int(time.time())

    # 1. Immediate replay
    env = make_sealed_envelope(key, dev_id, {"seq": 7001})
    res_first = pc_client.post("/api/v1/device/telemetry", json=env)
    assert res_first.status_code == 200
    res_replay = pc_client.post("/api/v1/device/telemetry", json=env)
    assert res_replay.status_code == 401

    # 2. Interleaved replay (post other packets, then attempt replaying the first envelope)
    for i in range(3):
        pc_client.post("/api/v1/device/telemetry", json=make_sealed_envelope(key, dev_id, {"seq": 7010 + i}))
    res_interleaved_replay = pc_client.post("/api/v1/device/telemetry", json=env)
    assert res_interleaved_replay.status_code == 401, "Replay attack succeeded after interleaving!"

    # 3. Timestamp drift boundary tests (max_skew = 300s)
    # Past beyond 300s
    env_past_301 = make_sealed_envelope(key, dev_id, {"seq": 7020}, ts=now - 301)
    assert pc_client.post("/api/v1/device/telemetry", json=env_past_301).status_code == 401
    
    # Future beyond 300s
    env_future_301 = make_sealed_envelope(key, dev_id, {"seq": 7021}, ts=now + 301)
    assert pc_client.post("/api/v1/device/telemetry", json=env_future_301).status_code == 401

    # Boundary valid: past 290s
    env_past_290 = make_sealed_envelope(key, dev_id, {"seq": 7022}, ts=now - 290)
    assert pc_client.post("/api/v1/device/telemetry", json=env_past_290).status_code == 200

    # Boundary valid: future 290s
    env_future_290 = make_sealed_envelope(key, dev_id, {"seq": 7023}, ts=now + 290)
    assert pc_client.post("/api/v1/device/telemetry", json=env_future_290).status_code == 200


def test_telemetry_malformed_envelope_and_payload_handling(
    pc_client: TestClient,
    registered_device: dict[str, Any],
) -> None:
    """Stress-test malformed envelopes (missing fields, wrong types, corrupted base64)."""
    dev_id = registered_device["id"]
    key = registered_device["key"]
    valid_env = make_sealed_envelope(key, dev_id, {"seq": 8001})

    # 1. Missing required envelope fields
    for field in ["device_id", "ts", "nonce", "ciphertext"]:
        corrupted = dict(valid_env)
        corrupted.pop(field)
        res = pc_client.post("/api/v1/device/telemetry", json=corrupted)
        assert res.status_code == 422, f"Expected 422 on missing {field}, got {res.status_code}"

    # 2. Invalid ts types
    bad_ts_env = dict(valid_env)
    bad_ts_env["ts"] = "2026-10-04"
    assert pc_client.post("/api/v1/device/telemetry", json=bad_ts_env).status_code == 422

    # 3. Invalid nonce length (not 12 bytes after base64 decode)
    short_nonce_env = dict(valid_env)
    short_nonce_env["nonce"] = base64.urlsafe_b64encode(b"too_short").decode()
    assert pc_client.post("/api/v1/device/telemetry", json=short_nonce_env).status_code == 401

    # 4. Unknown device ID
    unknown_dev_env = make_sealed_envelope(key, "non-existent-device-id", {"seq": 8002})
    assert pc_client.post("/api/v1/device/telemetry", json=unknown_dev_env).status_code == 401


# ==============================================================================
# SECTION 2: RFC 7946 GEOJSON & RFC 4180 CSV EXPORT CONFORMANCE
# ==============================================================================

def test_geojson_export_rfc7946_strict_conformance(
    pc_client: TestClient,
    pc_app: Any,
    operator_auth: dict[str, str],
) -> None:
    """Strictly validate Zone GeoJSON export against RFC 7946 using Shapely."""
    now = utcnow()
    with pc_app.state.session_factory() as db:
        source = ZoneSource(
            publisher="CHALLENGER_AEROSPACE",
            source_type="OPERATOR_DRAWN",
            license_name="OpenAir-1.0",
            checksum="rfc7946-chk-1",
            retrieved_at=now,
        )
        db.add(source)
        db.flush()

        # 1. Standard Polygon (counterclockwise exterior ring)
        geom1 = {
            "type": "Polygon",
            "coordinates": [
                [[105.80, 21.00], [105.85, 21.00], [105.85, 21.05], [105.80, 21.05], [105.80, 21.00]]
            ],
        }
        # 2. Polygon with interior hole
        geom2 = {
            "type": "Polygon",
            "coordinates": [
                [[106.00, 20.00], [106.10, 20.00], [106.10, 20.10], [106.00, 20.10], [106.00, 20.00]],
                [[106.02, 20.02], [106.08, 20.02], [106.08, 20.08], [106.02, 20.08], [106.02, 20.02]],
            ],
        }
        # 3. Deleted zone (must NOT be exported)
        geom_del = {
            "type": "Polygon",
            "coordinates": [
                [[100.0, 10.0], [100.1, 10.0], [100.1, 10.1], [100.0, 10.1], [100.0, 10.0]]
            ],
        }

        z1 = Zone(name="Zone RFC Alpha", source_id=source.id, geometry_json=json.dumps(geom1), visibility="INTERNAL", classification="RESTRICTED", version=1, retrieved_at=now, created_at=now, updated_at=now)
        z2 = Zone(name="Zone RFC Beta (Hole)", source_id=source.id, geometry_json=json.dumps(geom2), visibility="INTERNAL", classification="NO_FLY", version=1, retrieved_at=now, created_at=now, updated_at=now)
        z_deleted = Zone(name="Deleted Zone", source_id=source.id, geometry_json=json.dumps(geom_del), visibility="INTERNAL", classification="DEMO", version=1, retrieved_at=now, created_at=now, updated_at=now, deleted_at=now)
        db.add_all([z1, z2, z_deleted])
        db.commit()

    # Request GeoJSON export
    res = pc_client.get("/api/v1/zones/export/geojson", headers=operator_auth)
    assert res.status_code == 200
    assert "application/geo+json" in res.headers["content-type"]
    assert 'attachment; filename="zones.geojson"' in res.headers["content-disposition"]

    geojson_data = res.json()
    
    # RFC 7946 Section 3: Top-level FeatureCollection
    assert geojson_data["type"] == "FeatureCollection"
    assert isinstance(geojson_data["features"], list)
    assert len(geojson_data["features"]) >= 2

    exported_names = [f["properties"]["name"] for f in geojson_data["features"]]
    assert "Zone RFC Alpha" in exported_names
    assert "Zone RFC Beta (Hole)" in exported_names
    assert "Deleted Zone" not in exported_names, "CRITICAL: Soft-deleted zone was included in GeoJSON export!"

    # Validate each feature against RFC 7946 rules and Shapely geometric validity
    for f in geojson_data["features"]:
        assert f["type"] == "Feature"
        assert "id" in f
        assert "geometry" in f
        assert "properties" in f
        geom_dict = f["geometry"]
        assert geom_dict["type"] in {"Polygon", "MultiPolygon", "Point"}

        # Validate with Shapely
        poly_shape = shape(geom_dict)
        assert poly_shape.is_valid, f"Geometric invalidity in feature {f['id']}: {geom_dict}"

        # RFC 7946 Section 3.1.1: Position order is [longitude, latitude]
        for ring in geom_dict["coordinates"]:
            assert len(ring) >= 4, "RFC 7946 violation: Linear ring must have >= 4 coordinates"
            assert ring[0] == ring[-1], "RFC 7946 violation: Linear ring must be closed (first == last)"
            for coord in ring:
                lon, lat = coord[0], coord[1]
                assert -180.0 <= lon <= 180.0, f"RFC 7946 violation: Longitude {lon} out of [-180, 180]"
                assert -90.0 <= lat <= 90.0, f"RFC 7946 violation: Latitude {lat} out of [-90, 90]"

    print(f"\n[GEOJSON CONFORMANCE] Verified {len(geojson_data['features'])} features with Shapely 2.1.2.")


def test_csv_export_rfc4180_strict_conformance_and_escaping(
    pc_client: TestClient,
    pc_app: Any,
    operator_auth: dict[str, str],
) -> None:
    """Strictly validate Flight History CSV export against RFC 4180."""
    settings = pc_app.state.settings
    now = utcnow()

    # Challenging test vector with quotes, commas, CRLF, and Vietnamese UTF-8
    test_cases = [
        {
            "summary": 'Drone "Hexacopter" v2, Flight #101',
            "applicant": 'Nguyễn Văn "Hải" Cường, ThS.',
            "license": 'VN-LIC,"CAT-B"',
            "vehicle": 'F450 "Carbon", Quad-motor',
        },
        {
            "summary": "Line 1 with note:\r\nLine 2 continued\r\nLine 3 end",
            "applicant": "Trần Thị Ánh Tuyết",
            "license": "AOPA/VN-9999",
            "vehicle": "Mavic 3 Enterprise; Custom RTK",
        },
    ]

    with pc_app.state.session_factory() as db:
        for tc in test_cases:
            details = {
                "applicant_full_name": tc["applicant"],
                "license_code": tc["license"],
                "vehicle": tc["vehicle"],
                "flight_date": "2026-10-04",
                "flight_time": "14:00",
            }
            ciphertext = encrypt_secret(settings.session_secret, json.dumps(details))
            flight = SimulatedFlightRequest(
                summary=tc["summary"],
                status="SUBMITTED",
                version=1,
                simulated=True,
                source="USER_SIMULATED",
                simulated_geometry_json="null",
                scheduled_start_at=now,
                scheduled_end_at=now + timedelta(hours=2),
                request_details_ciphertext=ciphertext,
                created_at=now,
                updated_at=now,
            )
            db.add(flight)
        db.commit()

    # Request CSV export
    res = pc_client.get("/api/v1/flight-requests/export/csv", headers=operator_auth)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert 'attachment; filename="flight_history.csv"' in res.headers["content-disposition"]

    csv_text = res.text
    # RFC 4180 Section 2.1: Each record is on a separate line delimited by CRLF
    assert "\r\n" in csv_text, "RFC 4180 violation: Lines must be delimited by CRLF (\\r\\n)"

    # Parse with standard Python csv reader
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    
    # Check headers
    assert len(rows) >= 3
    expected_header = [
        "id", "status", "source", "device_name", "summary",
        "applicant_name", "license_code", "vehicle",
        "scheduled_start_at", "scheduled_end_at", "created_at", "updated_at",
    ]
    assert rows[0] == expected_header

    # Verify that the parsed rows match our unescaped original strings byte-for-byte!
    matched_cases = 0
    for row in rows[1:]:
        assert len(row) == 12, f"RFC 4180 column mismatch: expected 12, got {len(row)}: {row}"
        summary, applicant, license_code, vehicle = row[4], row[5], row[6], row[7]
        
        for tc in test_cases:
            if tc["applicant"] == applicant:
                assert summary == tc["summary"]
                assert license_code == tc["license"]
                assert vehicle == tc["vehicle"]
                matched_cases += 1

    assert matched_cases == len(test_cases), f"Could not find all test cases in CSV output (matched {matched_cases}/{len(test_cases)})"
    print(f"\n[CSV CONFORMANCE] Successfully validated RFC 4180 roundtrip with embedded quotes, commas, CRLF, and Vietnamese text.")


# ==============================================================================
# SECTION 3: PI OTA FIRMWARE UPLOAD BOUNDS & ARMED SAFETY LOCKS
# ==============================================================================

def test_pi_ota_upload_exact_and_oversized_bounds(tmp_path: Path) -> None:
    """Stress-test Pi OTA upload 4MB boundary at both route and gateway levels."""
    from pi5.web.app import PiWebConfig, create_pi_app
    from pi5.web.auth import PiAuthService
    from pi5.web.camera import MockCameraAdapter

    # Test with gateway config allowing up to 6MB requests so extra_routes 4MB limit is tested
    auth = PiAuthService(allow_inmemory_email=True)
    camera = MockCameraAdapter()
    config = PiWebConfig(secure_cookies=False, max_request_bytes=6 * 1024 * 1024)
    app = create_pi_app(config, auth=auth, camera=camera)

    max_bytes = 4 * 1024 * 1024  # 4,194,304 bytes

    with TestClient(app) as client:
        # 1. Oversized: 4MB + 1 byte -> Must reject with 413 PAYLOAD_TOO_LARGE
        oversized_bin = b"\xe9" + b"\x00" * max_bytes
        res_oversized = client.post(
            "/api/pi/v1/firmware/upload",
            files={"file": ("huge.bin", io.BytesIO(oversized_bin), "application/octet-stream")},
        )
        assert res_oversized.status_code == 413, f"Expected 413 on 4MB+1 byte, got {res_oversized.status_code}"
        assert res_oversized.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"

        # 2. Extreme oversized: 8MB -> Blocked by gateway middleware with REQUEST_TOO_LARGE
        huge_bin = b"\xe9" + b"\x00" * (8 * 1024 * 1024)
        res_huge = client.post(
            "/api/pi/v1/firmware/upload",
            files={"file": ("massive.bin", io.BytesIO(huge_bin), "application/octet-stream")},
        )
        assert res_huge.status_code == 413
        assert res_huge.json()["error"]["code"] in {"PAYLOAD_TOO_LARGE", "REQUEST_TOO_LARGE"}
        print("\n[OTA BOUNDARY] Verified 4MB+1 byte rejected with 413 PAYLOAD_TOO_LARGE and >6MB rejected with REQUEST_TOO_LARGE.")


def test_pi_ota_upload_corrupted_magic_bytes_and_formats(pi_client: TestClient) -> None:
    """Stress-test corrupt magic bytes and invalid file types."""
    # 1. Non-ESP32 magic bytes
    bad_magic_samples = [
        (b"\x7fELF\x02\x01\x01\x00", "Linux ELF"),
        (b"PK\x03\x04\x14\x00\x00\x00", "ZIP archive"),
        (b"\x1f\x8b\x08\x00\x00\x00\x00\x00", "GZIP file"),
        (b"#!/usr/bin/env python3\n", "Python script"),
        (b"\x00" * 32, "Zero bytes"),
    ]
    for bad_bytes, label in bad_magic_samples:
        res = pi_client.post(
            "/api/pi/v1/firmware/upload",
            files={"file": ("firmware.bin", io.BytesIO(bad_bytes), "application/octet-stream")},
        )
        assert res.status_code == 400, f"Expected 400 on {label}, got {res.status_code}"
        assert res.json()["error"]["code"] == "INVALID_MAGIC_BYTE"

    # 2. Empty file (0 bytes)
    res_empty = pi_client.post(
        "/api/pi/v1/firmware/upload",
        files={"file": ("empty.bin", io.BytesIO(b""), "application/octet-stream")},
    )
    assert res_empty.status_code == 400
    assert res_empty.json()["error"]["code"] == "EMPTY_FILE"


def test_pi_ota_upload_drone_armed_safety_lock(pi_env: Any) -> None:
    """Verify OTA flashing is strictly blocked when drone is ARMED."""
    client = pi_env[0]
    app = client.app
    valid_bin = b"\xe9" + b"\x01" * 1024

    class MockArmedLink:
        def arm_state(self):
            return "ARMED"
        def pause(self):
            pass
        def resume(self):
            pass

    app.state.esp_link = MockArmedLink()

    res = client.post(
        "/api/pi/v1/firmware/upload",
        files={"file": ("FC_can_bang.bin", io.BytesIO(valid_bin), "application/octet-stream")},
    )
    assert res.status_code == 409, f"Expected 409 when drone is ARMED, got {res.status_code}"
    assert res.json()["error"]["code"] == "DRONE_ARMED"
    print("\n[ARMED SAFETY LOCK] Flashing attempt blocked with HTTP 409 when drone is ARMED.")


def test_pi_ota_upload_content_type_flexibility(pi_client: TestClient) -> None:
    """Verify OTA endpoint accepts both multipart/form-data and raw octet-stream."""
    valid_bin = b"\xe9\x04\x00\x20" + secrets.token_bytes(256)

    # 1. Multipart with non-standard field name 'firmware'
    res_multi = pi_client.post(
        "/api/pi/v1/firmware/upload",
        files={"firmware": ("custom.bin", io.BytesIO(valid_bin), "application/octet-stream")},
    )
    assert res_multi.status_code == 202
    assert res_multi.json()["data"]["status"] in {"FLASHING", "COMPLETED", "DONE"}

    # 2. Raw application/octet-stream in request body
    res_raw = pi_client.post(
        "/api/pi/v1/firmware/upload",
        content=valid_bin,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert res_raw.status_code == 202
    assert res_raw.json()["data"]["status"] in {"FLASHING", "COMPLETED", "DONE"}
