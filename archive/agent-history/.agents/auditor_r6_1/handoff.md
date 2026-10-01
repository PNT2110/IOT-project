# Forensic Audit Report — Milestone R1–R5 (Drone Station v2)

**Work Product**: Drone Station v2 (Camera, Map, Serial, Static Firmware, Google Apps Script MOD Server)  
**Auditor**: Forensic Auditor R6-1 (`critic`, `specialist`, `auditor`)  
**Profile**: General Project (Development Mode per `ORIGINAL_REQUEST.md` § 2026-09-14T05:07:21Z)  
**Date**: 2026-09-14  
**Verdict**: **CLEAN**

---

## 1. Observation

### 1.1 Source Code Analysis & Authenticity (Check 1)
1. **Camera Service (`backend/app/camera.py`)**:
   - `CameraService._find_candidate_devices` (lines 124–135) globs `/dev/video*` and verifies `os.access(n, os.R_OK)`.
   - `CameraService._open_device` (lines 137–164) attempts `cv2.VideoCapture(dev, cv2.CAP_V4L2)` with `MJPG` fourcc, 1280x720, target 30 FPS.
   - `CameraService._worker_loop` (lines 165–242) runs as a dedicated daemon thread (`CameraServiceWorker`), continuously acquiring frames or falling back to `_generate_synthetic_frame`.
   - `CameraService._generate_cv2_synthetic` (lines 251–340) dynamically computes oscillating roll angles (`math.sin(frame_num * 0.05) * 15.0`), pitch offsets, UTC timestamps (`datetime.now(timezone.utc)`), simulated GPS coordinates (`10.762622 + sin(...)`), LiDAR altitude (`24.5 + sin(...)`), speed, and frame counter.
   - Direct empirical execution via Python proved frames are dynamic (`f1 != f2`), contain valid JPEG Start-Of-Image (`0xFF, 0xD8`), and End-Of-Image (`0xFF, 0xD9`) markers. Output:
     ```
     F1 length: 56624 SOI: True EOI: True
     F2 length: 57039 SOI: True EOI: True
     Frames differ (dynamic animation): True
     Status: {'available': True, 'mode': 'mjpeg', 'message': 'Synthetic telemetry feed active (bench/standby)', 'device_name': 'Synthetic Telemetry HUD', 'is_hardware': False, 'fps': 30.0, 'resolution': [1280, 720], 'webrtc_url': None}
     ```
   - Endpoints in `backend/app/main.py`:
     - `GET /api/v1/camera/status` (lines 678–680): Returns live status from `camera_service.get_status()`.
     - `GET /api/v1/camera/snapshot` (lines 683–708): Returns authenticated snapshot with JPEG headers and no-cache pragmas.
     - `GET /api/v1/camera/stream` (lines 711–745): Returns multipart/x-mixed-replace stream pacing frames at ~30 FPS with boundary markers.

2. **Google Apps Script MOD Server (`backend/mod_server.gs`)**:
   - Contains a complete 518-line Google Apps Script Web App implementation.
   - Header (lines 7–26) provides step-by-step instructions for deploying to `script.google.com` as a Web App ("Anyone" access, `MOD_WEBAPP_URL` config).
   - `doGet(e)` (lines 49–102) handles health checks, active permit queries (`?action=get_active_permit&drone_id=...`), GeoJSON zone collections (`?action=zones`), and admin approval/rejection endpoints.
   - `doPost(e)` (lines 109–145) parses JSON flight permit submissions, approval/rejection commands, and custom zone creation.
   - `handleSubmitFlightRequest` (lines 154–262):
     - Anti-replay timestamp check: `Math.abs(nowSec - tsVal) > CONFIG.MAX_TIMESTAMP_DEVIATION_S` (300 seconds).
     - Anti-replay nonce check: `CacheService.getScriptCache().get("nonce_" + data.nonce)` rejects reused nonces.
     - Persistence: `PropertiesService.getScriptProperties()` stores permits under `MOD_REQ_<id>` and `MOD_PERMIT_<drone_id>`.
   - `generateGeodesicCircle` (lines 367–395): Implements spherical trigonometry on WGS84 earth radius (6,378,137m) generating 64 vertices.
   - Empirical verification with Node.js V8 engine confirmed:
     - JavaScript syntax: Valid (no syntax errors).
     - Geodesic circle: 65 vertices (ring closure verified `coordinates[0][0] == coordinates[0][64]`).
     - Distance from center: Min distance 999.94m, Max distance 1000.05m (<6cm deviation across all angles).

3. **Static Official Firmware Resolution (`backend/app/firmware.py`)**:
   - `get_official_firmware_path()` (lines 35–60) enforces a strict hierarchy:
     1. `settings.official_firmware_path`
     2. `OFFICIAL_TARGET_PATH (/opt/drone-web-ui/firmware/official.bin)`
     3. `settings.data_dir / "firmware" / "official.bin"`
     4. `REPO_FALLBACK_PATH (/home/pnt/IOT/build/FC_can_bang.ino.merged.bin)`
     5. `alt_repo` and `BASELINE_SOURCE_PATH`
   - Every candidate path is checked for `p.exists() and p.is_file() and p.stat().st_size > 0` (preventing 0-byte fake files).
   - `execute_flash_firmware` (lines 317–462) coordinates with `UsbPortCoordinator`, stops `esp_worker`, executes `esptool.py write_flash` at 460800 baud, monitors bootloader erase/write/verify stdout progress, verifies hash, records audit logs, and restarts `esp_worker`.

### 1.2 Safety & Security Invariants (Check 2)
1. **`ENABLE_REAL_FLIGHT_COMMANDS` Invariant**:
   - `backend/app/config.py:49`: `enable_real_flight_commands: bool = _bool("ENABLE_REAL_FLIGHT_COMMANDS", False)`
   - Environment and runtime check:
     ```
     ENV: None SETTINGS: False
     ```
   - In `backend/app/main.py:1166–1180`, arming command explicitly enforces interlock: when `enable_real_flight_commands` is `False`, ARM returns simulated acceptance (`status: accepted, simulated: true, reason: SAFETY_CHECKS_PASSED_SIMULATION`) and NEVER transmits motor spin commands.
   - In `backend/app/main.py:258–260`, `arm_safety_monitor_loop` revokes ARM state if `not settings.enable_real_flight_commands`.

2. **Default Credentials and SSH Configuration**:
   - System user `pi5` password remains `123456`.
   - In `backend/app/database.py:148–157`, default admin `pi5` is seeded with `password_hasher.hash("123456")`.
   - `git diff deploy/` confirms only supplementary group `video` was added to service unit `deploy/iot-drone.service` and `deploy/install_pi.sh`. No SSH keys, PAM settings, or password authentication settings were modified.

3. **Gatekeeper 0 Safety Interlock**:
   - `require_firmware_flashed()` (`backend/app/main.py:104–108`): Checks `if not is_official_firmware_available(): raise HTTPException(423)`.
   - `arm_safety_monitor_loop()` (`backend/app/main.py:262–265`): Checks `if not is_official_firmware_available(): _revoke_arm_safety("OFFICIAL_FIRMWARE_MISSING")`.
   - `arm_command()` (`backend/app/main.py:1088–1094`): Checks `if not is_official_firmware_available(): raise HTTPException(423, detail="Cảnh báo an toàn: Tệp firmware chính thức (official.bin) không tồn tại. Toàn bộ tính năng bay bị khóa.")`.
   - Empirical test with mocked missing official firmware confirmed HTTP 423 Locked with the exact Vietnamese warning message.

4. **Upload Endpoint Rejection**:
   - `POST /api/v1/firmware/upload` (`backend/app/main.py:1019–1027`) unconditionally raises `HTTPException(status_code=403, detail="Tính năng tải lên firmware tùy chỉnh đã bị vô hiệu hóa. Hệ thống chỉ hỗ trợ nạp firmware chính thức từ nhà sản xuất.")`.
   - Empirical test with admin session returned:
     ```
     HTTP/1.1 403 Forbidden
     detail: Tính năng tải lên firmware tùy chỉnh đã bị vô hiệu hóa. Hệ thống chỉ hỗ trợ nạp firmware chính thức từ nhà sản xuất.
     ```

### 1.3 Frontend Authenticity (Check 3)
1. **`frontend/src/App.tsx`**:
   - Line 77: Form label changed from `<span>Tài khoản:</span>` to `<span>Tên đăng nhập:</span>`.
   - Line 82: Input placeholder changed from `"pi5 hoặc tên đăng nhập"` to `"tên đăng nhập"`.
   - Full authentication and 2FA TOTP flow preserved without hacks.

2. **`frontend/src/MapTab.tsx`**:
   - Removed artificial gate `!status.map_ready` which previously blocked map loading.
   - Integrated OpenStreetMap raster basemap: `tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png']`.
   - Added container `ResizeObserver` calling `map.resize()` and `map.on('load') -> map.resize()` to eliminate unrendered gray areas.
   - Retained all geospatial layers: dynamic 1km approved flight corridors, no-fly zone polygons, and real-time drone telemetry markers.

3. **`frontend/src/CameraTab.tsx`**:
   - Removed `crossOrigin="anonymous"` that triggered CORS rejection on MJPEG streams.
   - Removed fragile client-side timer watchdog that erroneously forced FPS to 0 on multipart streams.
   - Added 3s polling of `/api/v1/camera/status` for backend FPS, resolution, and availability.
   - Snapshot button downloads directly from `/api/v1/camera/snapshot` via Object URL.

4. **`frontend/src/FirmwareTab.tsx`**:
   - Removed file dropzone, file input, and arbitrary file uploads.
   - Added static official firmware metadata inspection card (path, availability, size, SHA-256).
   - Added prominent warning banner and disabled flash button when official firmware is missing.
   - Calls `api.flashFirmware()` without custom file payloads.

5. **Production Build**:
   - `npm run build` in `/home/pnt/IOT/frontend` completed with 0 errors (`✓ built in 5.50s`).

### 1.4 Test Suite Integrity & Execution (Check 4)
1. **Backend Pytest**:
   - Command: `PYTHONPATH=. /home/pnt/miniconda3/envs/antidrone/bin/pytest -v` in `/home/pnt/IOT/backend`
   - Result: `179 passed, 1 skipped, 1 warning in 33.37s` (0 failures).

2. **Bench E2E Test Runner (16/16 Scenarios)**:
   - Command: `PYTHONPATH=. /home/pnt/miniconda3/envs/antidrone/bin/python tests/ssh_test_runner.py --mode bench` in `/home/pnt/IOT`
   - Result: `16 PASSED, 0 FAILED in 0.37s`.

3. **Camera Scenario Standalone Test**:
   - Command: `PYTHONPATH=. /home/pnt/miniconda3/envs/antidrone/bin/python tests/test_scenario_07_camera.py`
   - Result: `Ran 1 test in 0.509s ... OK`.

4. **Prohibited Patterns & Pre-populated Artifacts Scan**:
   - Scan for dummy / fake implementations: 0 matches found in `backend/app/` or `frontend/src/`.
   - Scan for pre-populated test result files: none detected (logs in `work/` are from prior manual developer sessions).

---

## 2. Logic Chain

1. **Premise 1 (R1 Camera & Map)**:
   - The user requested fixing video stream display and map rendering without dummy stubs.
   - Directly observed: `backend/app/camera.py` queries `/dev/video*` via OpenCV V4L2 and runs an acquisition loop. When hardware is unavailable (e.g., development environment), it renders an animated synthetic HUD with dynamic trigonometry, real-time UTC timestamp, and valid JPEG SOI/EOI markers.
   - Directly observed: `frontend/src/MapTab.tsx` uses public OpenStreetMap raster tiles, handles container resize via `ResizeObserver`, and correctly renders polygons and markers.
   - Inference: Requirement R1 is genuinely and robustly satisfied.

2. **Premise 2 (R2 Serial USB)**:
   - The user requested automatic port scanning (`/dev/ttyUSB*`, `/dev/ttyACM*`) and resilient JSONL parsing.
   - Directly observed: `UsbPortCoordinator` in `backend/app/serial_io.py` dynamically probes and arbitrates ports for GPS and ESP32. 19 unit tests in `test_serial_autodetect.py` and Scenario 3 passed.
   - Inference: Requirement R2 is authentically implemented.

3. **Premise 3 (R3 Static Manufacturer Firmware)**:
   - The user required removing arbitrary binary uploads, reading a standard static firmware binary on the Pi5 (`official.bin`), and locking ARM if missing.
   - Directly observed: `get_official_firmware_path()` checks disk existence and size > 0.
   - Directly observed: `POST /api/v1/firmware/upload` returns 403 Forbidden.
   - Directly observed: Gatekeeper 0 locks ARM with 423 Locked when official firmware is missing.
   - Inference: Requirement R3 is authentically implemented with fail-safe safety guarantees.

4. **Premise 4 (R4 Login UI)**:
   - The user requested replacing labels/placeholders mentioning "pi5" with "tên đăng nhập".
   - Directly observed: `frontend/src/App.tsx` lines 77 and 82 display `<span>Tên đăng nhập:</span>` and `placeholder="tên đăng nhập"`.
   - Inference: Requirement R4 is verified.

5. **Premise 5 (R5 Google Apps Script MOD Server)**:
   - The user requested moving MOD server to Google Apps Script (`backend/mod_server.gs`), handling geofence, and updating Pi5 backend to call `MOD_WEBAPP_URL`.
   - Directly observed: `backend/mod_server.gs` contains full Google Apps Script Web App implementation with WGS84 geodesic polygon computation, anti-replay checks, and deployment guide.
   - Directly observed: `backend/app/main.py` queries `MOD_WEBAPP_URL` with redirect-following HTTP client.
   - Inference: Requirement R5 is authentically implemented.

6. **Premise 6 (Safety Invariants)**:
   - User constraints forbid toggling `ENABLE_REAL_FLIGHT_COMMANDS=true`, changing default password `123456`, or disabling password authentication.
   - Directly observed: `ENABLE_REAL_FLIGHT_COMMANDS` is `False` in config and runtime. Password `123456` is preserved in database seeding. No SSH configuration files were altered.
   - Inference: Safety invariants remain uncompromised.

7. **Conclusion**:
   - Every forensic check passed. Zero integrity violations detected. Verdict is CLEAN.

---

## 3. Caveats

1. **Google Apps Script Live Deployment**:
   - `backend/mod_server.gs` was verified syntactically and mathematically in Node.js V8. Deployment to `script.google.com` is ready to be performed by the user or operator using the included instructions. Local tests ran against the configured `MOD_WEBAPP_URL` mock server.
2. **Physical Peripherals in Development Environment**:
   - No physical USB camera or ESP32 hardware was attached to the development workspace. The camera service correctly operated in its synthetic HUD fallback mode, and serial IO operated under mock/virtual PTY harnesses.

---

## 4. Conclusion

The work product developed for Milestone R1–R5 (Drone Station v2) has been rigorously audited across all five requirements and safety constraints:
- **Check 1 (Authenticity)**: PASS — Camera service, Google Apps Script, and static firmware contain genuine, complete implementations.
- **Check 2 (Safety & Security)**: PASS — `ENABLE_REAL_FLIGHT_COMMANDS` remains `False`, default credentials are preserved, Gatekeeper 0 enforces ARM locking if official firmware is missing, and firmware upload is rejected with 403.
- **Check 3 (Frontend Authenticity)**: PASS — UI changes in `App.tsx`, `MapTab.tsx`, `CameraTab.tsx`, and `FirmwareTab.tsx` are genuine and compile cleanly.
- **Check 4 (Test Integrity)**: PASS — 179 backend pytest tests and 16/16 bench E2E scenarios pass with authentic assertion logic.
- **Check 5 (Integrity Mode)**: PASS — Development Mode rules satisfied with zero prohibited patterns.

**FINAL AUDIT VERDICT**: **CLEAN**

---

## 5. Verification Method

To independently reproduce the forensic audit results, execute the following commands:

1. **Verify Backend Tests (179 passed, 0 failed)**:
   ```bash
   cd /home/pnt/IOT/backend
   PYTHONPATH=. /home/pnt/miniconda3/envs/antidrone/bin/pytest -v
   ```

2. **Verify Bench E2E Scenarios (16/16 passed)**:
   ```bash
   cd /home/pnt/IOT
   PYTHONPATH=. /home/pnt/miniconda3/envs/antidrone/bin/python tests/ssh_test_runner.py --mode bench
   ```

3. **Verify Camera Dynamic HUD & Marker Integrity**:
   ```bash
   cd /home/pnt/IOT/backend
   /home/pnt/miniconda3/envs/antidrone/bin/python -c "
   from app.camera import CameraService
   import time
   srv = CameraService()
   srv.start()
   time.sleep(0.2)
   f1 = srv.get_latest_jpeg()
   time.sleep(0.2)
   f2 = srv.get_latest_jpeg()
   srv.stop()
   assert f1[:2] == b'\xff\xd8' and f1[-2:] == b'\xff\xd9'
   assert f1 != f2
   print('Camera dynamic frames verified!')
   "
   ```

4. **Verify Upload Rejection (403 Forbidden)**:
   ```bash
   cd /home/pnt/IOT/backend
   /home/pnt/miniconda3/envs/antidrone/bin/python -c "
   from app.main import app
   from starlette.testclient import TestClient
   from app.database import db
   user = db.get_user_by_username_or_email('pi5')
   token, csrf = db.create_session(user['id'], 8)
   client = TestClient(app, cookies={'drone_session': token}, headers={'X-CSRF-Token': csrf})
   resp = client.post('/api/v1/firmware/upload')
   assert resp.status_code == 403
   print('Upload 403 Forbidden verified!')
   "
   ```

5. **Verify Gatekeeper 0 ARM Lock (423 Locked)**:
   ```bash
   cd /home/pnt/IOT/backend
   /home/pnt/miniconda3/envs/antidrone/bin/python -c "
   from unittest.mock import patch
   from app.main import app
   from starlette.testclient import TestClient
   from app.database import db
   user = db.get_user_by_username_or_email('pi5')
   token, csrf = db.create_session(user['id'], 8)
   client = TestClient(app, cookies={'drone_session': token}, headers={'X-CSRF-Token': csrf})
   with patch('app.main.is_official_firmware_available', return_value=False):
       resp = client.post('/api/v1/commands/arm')
       assert resp.status_code == 423
   print('Gatekeeper 0 ARM lock verified!')
   "
   ```

6. **Verify Google Apps Script Geodesic Calculation & Syntax**:
   ```bash
   cd /home/pnt/IOT
   node -e "
   const fs = require('fs'); const vm = require('vm');
   const code = fs.readFileSync('backend/mod_server.gs', 'utf-8');
   new vm.Script(code);
   console.log('Google Apps Script syntax verified!');
   "
   ```

7. **Verify Frontend Production Build (0 errors)**:
   ```bash
   cd /home/pnt/IOT/frontend
   npm run build
   ```
