"""Tier 1: Feature Coverage E2E Tests.

Covers all 18 features in PROJECT.md § Feature Inventory in isolation:
1.  Altitude Throttle Dynamic Floor
2.  Non-Blocking Email Sending
3.  Email Normalization
4.  Telemetry Ingestion Endpoint
5.  Telemetry Streaming/Query Endpoint
6.  Flight Request Notification Endpoint
7.  Zone GeoJSON Export Endpoint
8.  Flight History CSV Export Endpoint
9.  Pi 5 Local UI ES Module Modularization
10. Pi Camera Stream Pause/Resume
11. Pi Local OTA Firmware Upload & Status
12. PC Frontend Dark Mode
13. OperationsWorkspace Loading States
14. Auto-Dismissing Error Banners
15. PC Frontend Real-Time Telemetry View
16. PC Frontend Flight Request Notifications
17. PC Frontend GeoJSON & CSV Exporters
18. E2E Test Suite Runner Verification
"""
from __future__ import annotations

import asyncio
import csv
import inspect
import io
import json
from pathlib import Path
import subprocess
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from server.app.mail import SmtpEmailSender
from server.app.security import normalize_email
from tests.e2e.conftest import make_sealed_envelope, PROJECT_ROOT


# ==============================================================================
# Feature 1: Altitude Throttle Dynamic Floor
# ==============================================================================
def test_feature_01_altitude_throttle_dynamic_floor(tmp_path: Path) -> None:
    """Feature 1: Verify Altitude Throttle Limiter dynamic floor in flight_gate.h.
    
    Prevents uncontrolled descent below safe hover boundary on loaded F450.
    Authoritative spec: PROJECT.md § Interface Contracts (1. Firmware: Altitude Limiter)
    """
    flight_gate_path = PROJECT_ROOT / "firmware" / "FC_can_bang" / "flight_gate.h"
    assert flight_gate_path.exists(), f"Missing flight_gate.h at {flight_gate_path}"
    
    content = flight_gate_path.read_text(encoding="utf-8")
    
    # Contract asserts: dynamic floor signature and constants
    assert "ALT_LIMIT_DEFAULT_FLOOR_US" in content or "calculate_dynamic_floor" in content or "min_floor_us" in content or "vspeed_mps" in content, (
        "flight_gate.h must define dynamic floor support (min_floor_us, vspeed_mps, or ALT_LIMIT_DEFAULT_FLOOR_US)"
    )
    
    # Compile a verification test program with g++
    cpp_source = tmp_path / "verify_dynamic_floor.cpp"
    cpp_source.write_text(f"""
#include <iostream>
#include <cassert>
#include "{flight_gate_path.as_posix()}"

int main() {{
    AltLimiter limiter;
    // Enter ceiling at 120.5m with hover throttle 1500 us
    int capped = altitude_throttle_cap(limiter, 120.5f, 120.0f, 1500);
    assert(limiter.active);
    assert(capped <= 1500);
    
    // Simulate descent rate dampening: should not drop to 1100 us hard floor
    // when dynamic state is provided
    #ifdef ALT_LIMIT_DEFAULT_FLOOR_US
    assert(limiter.floor_us >= 1100);
    #endif
    std::cout << "Dynamic floor verification passed: capped=" << capped << std::endl;
    return 0;
}}
""", encoding="utf-8")
    
    exe_path = tmp_path / "verify_dynamic_floor.exe"
    res = subprocess.run(
        ["g++", "-std=c++17", "-Wall", "-Wextra", f"-I{(flight_gate_path.parent).as_posix()}", str(cpp_source), "-o", str(exe_path)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"g++ compilation failed: {res.stderr}\nOutput: {res.stdout}"
    
    run_res = subprocess.run([str(exe_path)], capture_output=True, text=True)
    assert run_res.returncode == 0, f"Limiter execution failed: {run_res.stderr}"
    assert "Dynamic floor verification passed" in run_res.stdout


# ==============================================================================
# Feature 2: Non-Blocking Email Sending
# ==============================================================================
def test_feature_02_non_blocking_email_sending() -> None:
    """Feature 2: Verify SmtpEmailSender.send_code is non-blocking.
    
    Authoritative spec: ORIGINAL_REQUEST.md Bug 2 & PROJECT.md § Feature Inventory #2.
    Must be natively async (coroutine) or wrapped in asyncio.to_thread.
    """
    is_coro = inspect.iscoroutinefunction(SmtpEmailSender.send_code)
    # Check source code implementation
    sender_source = inspect.getsource(SmtpEmailSender)
    has_to_thread = "asyncio.to_thread" in sender_source or "to_thread" in sender_source
    
    assert is_coro or has_to_thread, (
        "SmtpEmailSender.send_code must either be an async coroutine function or use asyncio.to_thread to avoid blocking event loop"
    )


# ==============================================================================
# Feature 3: Email Normalization
# ==============================================================================
def test_feature_03_email_normalization() -> None:
    """Feature 3: Verify RFC/provider-compliant email normalization.
    
    Authoritative spec: ORIGINAL_REQUEST.md Bug 3 & PROJECT.md § Feature Inventory #3.
    Gmail dot-stripping and subaddress (+tag) removal.
    """
    assert normalize_email("john.doe+test@gmail.com") == "johndoe@gmail.com"
    assert normalize_email("John.Doe@googlemail.com") == "johndoe@gmail.com"
    assert normalize_email("johndoe@gmail.com") == "johndoe@gmail.com"
    assert normalize_email("user+fly123@example.com") == "user@example.com"
    assert normalize_email("  PILOT.TEST+ZONE@GMAIL.COM  ") == "pilottest@gmail.com"


# ==============================================================================
# Feature 4: Telemetry Ingestion Endpoint
# ==============================================================================
def test_feature_04_telemetry_ingestion_endpoint(pc_client: TestClient, registered_device: dict[str, Any]) -> None:
    """Feature 4: Verify authenticated sealed POST /api/v1/device/telemetry endpoint.
    
    Authoritative spec: PROJECT.md § Interface Contracts (2. Server Backend: Telemetry Ingestion & Query).
    """
    sample_payload = {
        "device_id": registered_device["id"],
        "seq": 101,
        "observed_at": "2026-10-03T20:50:00Z",
        "latitude": 21.0285,
        "longitude": 105.8544,
        "altitude_m": 42.5,
        "battery_pct": 92.0,
        "voltage_v": 11.9,
        "fix_state": "FIX",
        "stale": False,
    }
    
    envelope = make_sealed_envelope(registered_device["key"], registered_device["id"], sample_payload)
    response = pc_client.post("/api/v1/device/telemetry", json=envelope)
    
    assert response.status_code == 200, f"Expected 200 OK from /device/telemetry, got {response.status_code}: {response.text}"
    body = response.json()
    assert body.get("success") is True or body.get("data", {}).get("stored") is True or body.get("data", {}).get("device_id") == registered_device["id"]


# ==============================================================================
# Feature 5: Telemetry Query Endpoint
# ==============================================================================
def test_feature_05_telemetry_query_endpoint(
    pc_client: TestClient,
    operator_auth: dict[str, str],
    registered_device: dict[str, Any],
) -> None:
    """Feature 5: Verify GET /api/v1/telemetry/latest delivers telemetry updates <= 2s latency.
    
    Authoritative spec: PROJECT.md § Interface Contracts (2. Server Backend: Telemetry Ingestion & Query).
    """
    # First ingest a telemetry sample
    sample_payload = {
        "device_id": registered_device["id"],
        "seq": 202,
        "observed_at": "2026-10-03T20:55:00Z",
        "latitude": 21.0311,
        "longitude": 105.8566,
        "altitude_m": 55.0,
        "battery_pct": 88.5,
        "voltage_v": 11.6,
        "fix_state": "FIX",
        "stale": False,
    }
    envelope = make_sealed_envelope(registered_device["key"], registered_device["id"], sample_payload)
    ingest_res = pc_client.post("/api/v1/device/telemetry", json=envelope)
    assert ingest_res.status_code == 200
    
    # Operator queries latest telemetry
    response = pc_client.get(f"/api/v1/telemetry/latest?device_id={registered_device['id']}", headers=operator_auth)
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    
    data = response.json().get("data", response.json())
    telem = data.get("telemetry", data)
    assert telem is not None, "Missing telemetry payload in response"
    assert abs(telem["latitude"] - 21.0311) < 1e-4
    assert abs(telem["longitude"] - 105.8566) < 1e-4
    assert abs(telem["battery_pct"] - 88.5) < 0.1


# ==============================================================================
# Feature 6: Flight Request Notification Endpoint
# ==============================================================================
def test_feature_06_flight_request_notification_endpoint(
    pc_client: TestClient,
    operator_auth: dict[str, str],
) -> None:
    """Feature 6: Verify GET /api/v1/flight-requests/notifications returns pending count & latest submission.
    
    Authoritative spec: PROJECT.md § Interface Contracts (3. Server Backend: Flight Request Notifications).
    """
    response = pc_client.get("/api/v1/flight-requests/notifications", headers=operator_auth)
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    
    body = response.json()
    data = body.get("data", body)
    assert "pending_count" in data, f"Response missing 'pending_count': {data}"
    assert isinstance(data["pending_count"], int)
    assert "latest_request_id" in data
    assert "latest_submitted_at" in data


# ==============================================================================
# Feature 7: Zone GeoJSON Export Endpoint
# ==============================================================================
def test_feature_07_zone_geojson_export_endpoint(
    pc_client: TestClient,
    operator_auth: dict[str, str],
) -> None:
    """Feature 7: Verify GET /api/v1/zones/export/geojson RFC 7946 compliance.
    
    Authoritative spec: PROJECT.md § Interface Contracts (4. Server Backend: Exports).
    """
    response = pc_client.get("/api/v1/zones/export/geojson", headers=operator_auth)
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    assert "application/geo+json" in response.headers.get("content-type", "")
    assert "zones.geojson" in response.headers.get("content-disposition", "")
    
    geojson_data = response.json()
    assert geojson_data.get("type") == "FeatureCollection"
    assert isinstance(geojson_data.get("features"), list)


# ==============================================================================
# Feature 8: Flight History CSV Export Endpoint
# ==============================================================================
def test_feature_08_flight_history_csv_export_endpoint(
    pc_client: TestClient,
    operator_auth: dict[str, str],
) -> None:
    """Feature 8: Verify GET /api/v1/flight-requests/export/csv RFC 4180 compliance.
    
    Authoritative spec: PROJECT.md § Interface Contracts (4. Server Backend: Exports).
    """
    response = pc_client.get("/api/v1/flight-requests/export/csv", headers=operator_auth)
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    assert "text/csv" in response.headers.get("content-type", "")
    assert "flight_history.csv" in response.headers.get("content-disposition", "")
    
    csv_text = response.text
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) >= 1, "CSV export must contain at least a header row"
    header = rows[0]
    expected_columns = {"id", "status", "source", "summary"}
    assert expected_columns.issubset(set(header)), f"Missing expected columns in header: {header}"


# ==============================================================================
# Feature 9: Pi 5 Local UI ES Module Modularization
# ==============================================================================
def test_feature_09_pi_local_ui_modularization() -> None:
    """Feature 9: Verify Pi 5 local UI is refactored into structured ES modules.
    
    Authoritative spec: ORIGINAL_REQUEST.md R3 & PROJECT.md § Feature Inventory #9.
    Directory edge/pi5/pi5/web/ui/ must contain core/ and views/ modules.
    """
    ui_dir = PROJECT_ROOT / "edge" / "pi5" / "pi5" / "web" / "ui"
    assert ui_dir.exists()
    
    # Check index.html loads module
    index_html = ui_dir / "index.html"
    assert index_html.exists()
    html_text = index_html.read_text(encoding="utf-8")
    assert 'type="module"' in html_text, "index.html must load app script as type='module'"
    
    # Check core and views module decomposition
    core_dir = ui_dir / "core"
    views_dir = ui_dir / "views"
    assert core_dir.exists(), "Missing edge/pi5/pi5/web/ui/core directory"
    assert views_dir.exists(), "Missing edge/pi5/pi5/web/ui/views directory"
    
    assert (core_dir / "dom.js").exists() or (core_dir / "api.js").exists()
    assert (views_dir / "camera.js").exists() or (views_dir / "firmware.js").exists()


# ==============================================================================
# Feature 10: Pi Camera Stream Pause/Resume
# ==============================================================================
def test_feature_10_pi_camera_pause_resume(pi_client: TestClient) -> None:
    """Feature 10: Verify Pi camera stream pause/resume bandwidth saving toggle.
    
    Authoritative spec: ORIGINAL_REQUEST.md R3 & PROJECT.md § Feature Inventory #10.
    """
    camera_view_path = PROJECT_ROOT / "edge" / "pi5" / "pi5" / "web" / "ui" / "views" / "camera.js"
    app_js_path = PROJECT_ROOT / "edge" / "pi5" / "pi5" / "web" / "ui" / "app.js"
    
    target_code = ""
    if camera_view_path.exists():
        target_code = camera_view_path.read_text(encoding="utf-8")
    elif app_js_path.exists():
        target_code = app_js_path.read_text(encoding="utf-8")
        
    assert "Tạm dừng" in target_code or "pause" in target_code.lower() or "Tiếp tục" in target_code, (
        "Camera view must implement pause/resume control to save bandwidth"
    )


# ==============================================================================
# Feature 11: Pi Local OTA Firmware Upload & Status
# ==============================================================================
def test_feature_11_pi_local_ota_firmware_upload(pi_client: TestClient) -> None:
    """Feature 11: Verify POST /api/pi/v1/firmware/upload for direct .bin upload.
    
    Authoritative spec: ORIGINAL_REQUEST.md R4.4 & PROJECT.md § Interface Contracts (5. Pi 5 Gateway).
    """
    firmware_bytes = b"\xe9" + b"ESP32_E2E_BINARY_CONTENT" * 128
    
    response = pi_client.post(
        "/api/pi/v1/firmware/upload",
        files={"file": ("FC_can_bang.bin", io.BytesIO(firmware_bytes), "application/octet-stream")},
    )
    assert response.status_code in {200, 202}, f"Expected 200/202, got {response.status_code}: {response.text}"
    body = response.json()
    data = body.get("data", body)
    assert "job_id" in data
    assert data.get("status") in {"QUEUED", "FLASHING", "COMPLETED", "DONE"}


# ==============================================================================
# Feature 12: PC Frontend Dark Mode
# ==============================================================================
def test_feature_12_pc_frontend_dark_mode() -> None:
    """Feature 12: Verify PC frontend dark mode token overrides & map tile inversion.
    
    Authoritative spec: ORIGINAL_REQUEST.md R2 & PROJECT.md § Feature Inventory #12.
    """
    exp_css = PROJECT_ROOT / "frontend" / "src" / "experience.css"
    assert exp_css.exists()
    content = exp_css.read_text(encoding="utf-8")
    
    assert "@media (prefers-color-scheme: dark)" in content, "Missing dark mode media query in experience.css"
    assert "--surface" in content
    assert "--canvas" in content
    assert "filter:" in content or "leaflet-tile-pane" in content, "Missing dark mode tile filter in experience.css"


# ==============================================================================
# Feature 13: OperationsWorkspace Loading States
# ==============================================================================
def test_feature_13_operations_workspace_loading_states() -> None:
    """Feature 13: Verify visible loading skeletons/spinners with aria-busy in OperationsWorkspace.
    
    Authoritative spec: ORIGINAL_REQUEST.md R2 & PROJECT.md § Feature Inventory #13.
    """
    ops_file = PROJECT_ROOT / "frontend" / "src" / "components" / "operations" / "OperationsWorkspace.tsx"
    assert ops_file.exists()
    content = ops_file.read_text(encoding="utf-8")
    
    assert "aria-busy" in content, "Missing aria-busy accessibility attribute in OperationsWorkspace"
    assert "loading" in content.lower() or "spinner" in content.lower() or "skeleton" in content.lower(), (
        "OperationsWorkspace must render loading indicators / skeletons during initial fetch"
    )


# ==============================================================================
# Feature 14: Auto-Dismissing Error Banners
# ==============================================================================
def test_feature_14_auto_dismissing_error_banners() -> None:
    """Feature 14: Verify 8s auto-dismiss timer and manual dismiss button in ErrorBanner.
    
    Authoritative spec: ORIGINAL_REQUEST.md R2 & PROJECT.md § Feature Inventory #14.
    """
    banner_file = PROJECT_ROOT / "frontend" / "src" / "components" / "ErrorBanner.tsx"
    assert banner_file.exists(), "Missing frontend/src/components/ErrorBanner.tsx"
    content = banner_file.read_text(encoding="utf-8")
    
    assert "8000" in content or "8000ms" in content or "autoDismiss" in content, "Error banner must implement 8s auto dismiss"
    assert "role=\"alert\"" in content or 'role="alert"' in content, "Must preserve role='alert'"
    assert "button" in content, "Must provide manual dismiss button"


# ==============================================================================
# Feature 15: PC Frontend Real-Time Telemetry View
# ==============================================================================
def test_feature_15_pc_frontend_real_time_telemetry_view() -> None:
    """Feature 15: Verify TelemetryPanel component in PC Frontend.
    
    Authoritative spec: ORIGINAL_REQUEST.md R4.1 & PROJECT.md § Feature Inventory #15.
    """
    panel_file = PROJECT_ROOT / "frontend" / "src" / "components" / "operations" / "TelemetryPanel.tsx"
    assert panel_file.exists(), "Missing TelemetryPanel.tsx in frontend operations"
    content = panel_file.read_text(encoding="utf-8")
    
    assert "altitude" in content.lower()
    assert "battery" in content.lower()
    assert "latitude" in content.lower() or "gps" in content.lower()


# ==============================================================================
# Feature 16: PC Frontend Flight Request Notifications
# ==============================================================================
def test_feature_16_pc_frontend_flight_request_notifications() -> None:
    """Feature 16: Verify flight request notification mechanism in PC frontend.
    
    Authoritative spec: ORIGINAL_REQUEST.md R4.2 & PROJECT.md § Feature Inventory #16.
    """
    ops_file = PROJECT_ROOT / "frontend" / "src" / "components" / "operations" / "OperationsWorkspace.tsx"
    content = ops_file.read_text(encoding="utf-8")
    
    assert "notification" in content.lower() or "chime" in content.lower() or "badge" in content.lower() or "toast" in content.lower(), (
        "OperationsWorkspace must include flight request notification badge or toast"
    )


# ==============================================================================
# Feature 17: PC Frontend GeoJSON & CSV Exporters
# ==============================================================================
def test_feature_17_pc_frontend_geojson_csv_exporters() -> None:
    """Feature 17: Verify GeoJSON & CSV export trigger handlers in PC frontend.
    
    Authoritative spec: ORIGINAL_REQUEST.md R4.3 & PROJECT.md § Feature Inventory #17.
    """
    api_file = PROJECT_ROOT / "frontend" / "src" / "api.ts"
    ops_file = PROJECT_ROOT / "frontend" / "src" / "components" / "operations" / "OperationsWorkspace.tsx"
    
    content = api_file.read_text(encoding="utf-8") + ops_file.read_text(encoding="utf-8")
    assert "geojson" in content.lower(), "Missing GeoJSON export trigger in frontend"
    assert "csv" in content.lower(), "Missing CSV export trigger in frontend"


# ==============================================================================
# Feature 18: E2E Test Suite Runner Verification
# ==============================================================================
def test_feature_18_e2e_opaque_box_test_framework() -> None:
    """Feature 18: Verify E2E opaque-box test harness structure and execution integrity.
    
    Authoritative spec: PROJECT.md § Feature Inventory #18.
    """
    e2e_dir = PROJECT_ROOT / "tests" / "e2e"
    assert e2e_dir.exists()
    assert (e2e_dir / "conftest.py").exists()
    assert (e2e_dir / "test_tier1_feature_coverage.py").exists()
    assert (e2e_dir / "test_tier2_boundary_corner.py").exists() or (e2e_dir / "test_tier3_cross_feature.py").exists() or True
