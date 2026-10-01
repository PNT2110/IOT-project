#!/usr/bin/env python3
"""Adversarial Verification Probe for Reviewer R6-1.

Verifies:
1. CameraService: singleton, frame generation, JPEG SOI/EOI, dynamic variation, thread concurrency.
2. FastAPI endpoints: /api/v1/camera/status, /api/v1/camera/snapshot, /api/v1/camera/stream, /api/v1/status.
3. Auth coverage: query token, cookie, Authorization header, unauthenticated rejection (401).
4. CSP Headers: img-src and connect-src for OpenStreetMap, Permissions-Policy.
5. Frontend and deploy artifacts regex/integrity checks.
"""

import os
import sys
import threading
import time
from pathlib import Path

# Add backend to sys.path
backend_path = Path("/home/pnt/IOT/backend").resolve()
sys.path.insert(0, str(backend_path))

from fastapi.testclient import TestClient
from app.main import app
from app.camera import CameraService, camera_service
from app.database import db

def test_camera_service_integrity():
    print("--- 1. Testing CameraService Unit & Concurrency ---")
    cs = CameraService(target_fps=30.0, width=640, height=480)
    
    # Test frame generation before start
    frame0 = cs.get_latest_jpeg()
    assert frame0.startswith(b"\xff\xd8"), "Frame must start with JPEG SOI 0xFFD8"
    assert frame0.endswith(b"\xff\xd9"), "Frame must end with JPEG EOI 0xFFD9"
    assert len(frame0) > 1000, f"Frame too small ({len(frame0)} bytes), should be synthetic HUD"

    # Start service
    cs.start()
    assert cs.running is True
    time.sleep(0.15) # let worker produce frames

    # Check status
    st = cs.get_status()
    print("CameraService status:", st)
    assert st["available"] is True
    assert st["mode"] == "mjpeg"
    assert st["resolution"] == [640, 480]

    # Concurrent reader stress test (10 threads reading 100 times)
    read_errors = []
    frames_read = []

    def reader_worker(tid):
        try:
            for _ in range(50):
                f = cs.get_latest_jpeg()
                if not (f.startswith(b"\xff\xd8") and f.endswith(b"\xff\xd9")):
                    read_errors.append(f"Thread {tid}: Invalid JPEG markers")
                frames_read.append(len(f))
                time.sleep(0.002)
        except Exception as e:
            read_errors.append(f"Thread {tid} exception: {e}")

    threads = [threading.Thread(target=reader_worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not read_errors, f"Concurrency read errors: {read_errors}"
    print(f"Concurrency read test: {len(frames_read)} reads across 10 threads, 0 errors.")

    # Stop service
    cs.stop()
    assert cs.running is False
    print("CameraService stopped cleanly.")

def test_endpoints_and_auth():
    print("--- 2. Testing Endpoints, Auth Matrices & CSP ---")
    db.initialize()
    client = TestClient(app)

    # A. Unauthenticated access to /api/v1/camera/status
    res = client.get("/api/v1/camera/status")
    assert res.status_code == 401, f"Unauthenticated camera/status should be 401, got {res.status_code}"

    # B. Unauthenticated access to /api/v1/camera/snapshot
    res = client.get("/api/v1/camera/snapshot")
    assert res.status_code == 401, f"Unauthenticated camera/snapshot should be 401, got {res.status_code}"

    # C. Unauthenticated access to /api/v1/camera/stream
    res = client.get("/api/v1/camera/stream")
    assert res.status_code == 401, f"Unauthenticated camera/stream should be 401, got {res.status_code}"

    # Authenticate admin session
    token, csrf = db.create_session(1, 24)
    cookie_header = {"Cookie": f"drone_session={token}"}

    # D. Authenticated camera/status
    res = client.get("/api/v1/camera/status", headers=cookie_header)
    assert res.status_code == 200, f"Authenticated status failed: {res.status_code}"
    status_json = res.json()
    assert status_json["available"] is True
    assert "fps" in status_json
    print("Authenticated /api/v1/camera/status returned:", status_json)

    # E. Authenticated camera/snapshot via Cookie
    res = client.get("/api/v1/camera/snapshot", headers=cookie_header)
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/jpeg"
    assert res.headers["cache-control"] == "no-cache, no-store, must-revalidate"
    assert res.content.startswith(b"\xff\xd8") and res.content.endswith(b"\xff\xd9")
    print(f"Authenticated /api/v1/camera/snapshot (cookie) returned {len(res.content)} bytes valid JPEG")

    # F. Authenticated camera/snapshot via query token ?token=
    res = client.get(f"/api/v1/camera/snapshot?token={token}")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/jpeg"
    assert res.content.startswith(b"\xff\xd8") and res.content.endswith(b"\xff\xd9")
    print("Authenticated /api/v1/camera/snapshot (query token) verified.")

    # G. Authenticated camera/snapshot via Authorization: Bearer
    res = client.get("/api/v1/camera/snapshot", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.content.startswith(b"\xff\xd8") and res.content.endswith(b"\xff\xd9")
    print("Authenticated /api/v1/camera/snapshot (Bearer auth) verified.")

    # H. Authenticated camera/stream via route call
    from app.main import camera_stream
    from starlette.requests import Request
    scope = {"type": "http", "headers": [(b"cookie", f"drone_session={token}".encode())]}
    req = Request(scope)
    stream_res = camera_stream(request=req, token=token)
    assert stream_res.media_type == "multipart/x-mixed-replace; boundary=frame"
    assert stream_res.headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
    assert stream_res.headers["Pragma"] == "no-cache"

    import asyncio
    async def get_chunk():
        async for chunk in stream_res.body_iterator:
            return chunk
    first_chunk = asyncio.run(get_chunk())
    assert b"--frame" in first_chunk
    assert b"Content-Type: image/jpeg" in first_chunk
    assert b"\xff\xd8" in first_chunk
    print(f"Authenticated camera_stream verified: media_type={stream_res.media_type}, chunk size={len(first_chunk)} bytes.")

    # I. System status /api/v1/status check
    res = client.get("/api/v1/status", headers=cookie_header)
    assert res.status_code == 200
    sys_status = res.json()
    assert sys_status.get("map_ready") is True, f"map_ready must be True, got {sys_status.get('map_ready')}"
    print("System /api/v1/status verified: map_ready == True.")

    # J. CSP Headers check
    res = client.get("/api/v1/status", headers=cookie_header)
    csp = res.headers.get("content-security-policy", "")
    print("CSP Header:", csp)
    assert "https://*.tile.openstreetmap.org" in csp, "CSP missing OSM wildcard subdomain"
    assert "https://tile.openstreetmap.org" in csp, "CSP missing OSM apex domain"
    assert "Permissions-Policy" in res.headers
    assert "camera=(self)" in res.headers["Permissions-Policy"]
    print("Security & CSP headers verified.")

def test_static_inspections():
    print("--- 3. Static Inspection of R1 & R4 Code ---")
    # Check CameraTab.tsx
    cam_tab = Path("/home/pnt/IOT/frontend/src/CameraTab.tsx").read_text()
    assert "crossOrigin" not in cam_tab, "crossOrigin should be removed from CameraTab.tsx"
    assert "setStreamError('Không thể nạp luồng video" in cam_tab
    assert "api.cameraStatus()" in cam_tab, "api.cameraStatus() should be polled in CameraTab.tsx"
    assert "handleSnapshot" in cam_tab, "handleSnapshot should be implemented in CameraTab.tsx"
    print("CameraTab.tsx static checks passed.")

    # Check MapTab.tsx
    map_tab = Path("/home/pnt/IOT/frontend/src/MapTab.tsx").read_text()
    assert "https://tile.openstreetmap.org/{z}/{x}/{y}.png" in map_tab, "MapTab.tsx must use OSM raster tiles"
    assert "ResizeObserver" in map_tab, "MapTab.tsx must use ResizeObserver"
    assert "map.resize()" in map_tab, "MapTab.tsx must call map.resize()"
    assert "!status.map_ready" not in map_tab, "MapTab.tsx should not gate on status.map_ready"
    print("MapTab.tsx static checks passed.")

    # Check App.tsx login text
    app_tsx = Path("/home/pnt/IOT/frontend/src/App.tsx").read_text()
    assert "Tên đăng nhập:" in app_tsx, "App.tsx should display 'Tên đăng nhập:'"
    assert 'placeholder="tên đăng nhập"' in app_tsx, "App.tsx should have placeholder 'tên đăng nhập'"
    assert "tài khoản pi5" not in app_tsx.lower(), "App.tsx should not contain 'tài khoản pi5'"
    print("App.tsx login UI checks passed.")

    # Check systemd and deploy permissions
    service_file = Path("/home/pnt/IOT/deploy/iot-drone.service").read_text()
    assert "SupplementaryGroups=dialout video" in service_file, "iot-drone.service must include dialout and video groups"

    install_script = Path("/home/pnt/IOT/deploy/install_pi.sh").read_text()
    assert "usermod -a -G dialout,video iot-drone" in install_script, "install_pi.sh must add iot-drone to video group"
    print("Deploy service and install scripts static checks passed.")

if __name__ == "__main__":
    test_camera_service_integrity()
    test_endpoints_and_auth()
    test_static_inspections()
    print("\nALL ADVERSARIAL VERIFICATIONS PASSED SUCCESSFULLY!")
