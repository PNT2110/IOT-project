# DISPATCH — Worker R6-1 (Complete Implementation for R1-R5)

## Working Directory
/home/pnt/IOT/.agents/worker_r6_1

## Mandatory References
1. Original user request: `/home/pnt/IOT/.agents/ORIGINAL_REQUEST.md` (section `## 2026-09-14T05:07:21Z`). Subagents MUST read it before starting work.
2. Explorer handoff reports:
   - `/home/pnt/IOT/.agents/explorer_r6_1/handoff.md` (Camera stream & Admin Map)
   - `/home/pnt/IOT/.agents/explorer_r6_2/handoff.md` (Serial USB & Static Firmware Flashing)
   - `/home/pnt/IOT/.agents/explorer_r6_3/handoff.md` (Login UI & MOD Server Google Apps Script)
3. Project Scope & Architecture: `/home/pnt/IOT/PROJECT.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Tasks & Files Owned Exclusively
1. **R1: Camera & Map**:
   - Create `backend/app/camera.py`: Implement singleton `CameraService` probing `/dev/video*` (V4L2/OpenCV), background frame grabbing daemon, fallback animated synthetic frame (with drone station telemetry overlay, timestamp, valid JPEG SOI `0xFFD8`/EOI `0xFFD9`), thread-safe JPEG buffer.
   - Update `backend/app/main.py`:
     - Lifespan startup/shutdown starts/stops `CameraService`.
     - Route `/api/v1/camera/stream`: streams multipart/x-mixed-replace JPEG from `CameraService` (support cookie or `?token=` query param).
     - Route `/api/v1/camera/status`: returns device name, resolution, FPS, hardware status.
     - Route `/api/v1/camera/snapshot`: returns single JPEG frame.
     - In `/api/v1/status`: set `"map_ready": True`.
     - In CSP middleware: allow `https://*.tile.openstreetmap.org` and `https://tile.openstreetmap.org` in `img-src` and `connect-src`.
   - Update `deploy/iot-drone.service`: Add `video` to `SupplementaryGroups`.
   - Update `deploy/install_pi.sh`: Add `video` to `usermod -a -G dialout,video`.
   - Update `backend/requirements.txt`: Add `opencv-python-headless>=4.8.0`.
   - Update `frontend/src/CameraTab.tsx`: Remove `crossOrigin="anonymous"` from `<img>`, remove broken DOM `onLoad` watchdog, use backend status for FPS, allow snapshot download.
   - Update `frontend/src/MapTab.tsx`: Remove `!status.map_ready` gate. Configure raster OSM basemap `https://tile.openstreetmap.org/{z}/{x}/{y}.png`. Retain GeoJSON no-fly zones and dynamic 1km approved flight zone layers, and live drone marker. Add `map.resize()` on map load and container resize.
2. **R2: Serial USB Connection**:
   - Verify `backend/app/serial_io.py` port auto-scan across `/dev/ttyUSB*` and `/dev/ttyACM*`, auto-reconnect, and JSONL resilience. Run `backend/tests/test_serial_autodetect.py` to ensure all tests pass.
3. **R3: Static Manufacturer Firmware Flashing**:
   - Update `backend/app/config.py`: Add `official_firmware_path: Path = Path(os.getenv("OFFICIAL_FIRMWARE_PATH", "/opt/drone-web-ui/firmware/official.bin"))`.
   - Update `backend/app/firmware.py`:
     - Implement `get_official_firmware_path()` with resolution order: `/opt/drone-web-ui/firmware/official.bin` -> repo fallback `/home/pnt/IOT/build/FC_can_bang.ino.merged.bin`.
     - Implement `is_official_firmware_available()`.
     - Update `get_firmware_status()` to return `official_firmware_present` and `official_firmware_path`.
     - Update `execute_flash_firmware()` to always flash official firmware file (no user filename param), raising 404 if not found.
     - Fix mock compatibility bug on line 376 (`isinstance(line, (bytes, bytearray))`).
   - Update `backend/app/main.py`:
     - In `POST /api/v1/firmware/upload`: return 403 Forbidden explaining custom upload is disabled.
     - In `POST /api/v1/firmware/flash`: remove file upload parameter, invoke `execute_flash_firmware()` directly.
     - Add Gatekeeper 0 in `require_firmware_flashed()`, `arm_command()`, and `arm_safety_monitor_loop()`: if `not is_official_firmware_available()`, reject/revoke ARM with HTTP 423 Locked.
   - Update `frontend/src/FirmwareTab.tsx`:
     - Remove custom file upload dropzone and file input.
     - Display official firmware status card (`/opt/drone-web-ui/firmware/official.bin`, SHA256, status).
     - "Nạp Firmware" button directly invokes flash without file dialog.
     - Show warning banner and disable button if `official.bin` is missing.
   - Update `frontend/src/api.ts`: Remove `uploadFirmware` and clean `flashFirmware`.
4. **R4: Login UI Adjustment**:
   - Update `frontend/src/App.tsx`: Lines 77-82: Change label `<span>Tài khoản:</span>` to `<span>Tên đăng nhập:</span>`, change placeholder to `"tên đăng nhập"`.
5. **R5: Migrate MOD Server to Google Apps Script**:
   - Create `backend/mod_server.gs`: Full Google Apps Script Web App implementation per Explorer R6-3 blueprint with `doGet()` and `doPost()`, 1km geodesic circle polygon generation (64 vertices WGS84), anti-replay timestamp/nonce verification, and deployment instructions in header.
   - Update `backend/app/config.py`: Add `mod_webapp_url` setting reading `MOD_WEBAPP_URL` from `.env`.
   - Update `backend/app/main.py`: Update `fetch_active_mod_permit` and `submit_flight_request` to support `MOD_WEBAPP_URL`, and use `httpx.AsyncClient(timeout=8.0, follow_redirects=True)` to support Google 302 redirects.
   - Update `.env`: Add `MOD_WEBAPP_URL=http://127.0.0.1:9000` (for local test fallback).
   - Fix `backend/tests/test_mod_server.py:168`: replace hardcoded past date with today's date dynamically.

## Verification Requirements
Worker MUST run all builds and tests and include results in handoff:
1. Backend tests:
   ```bash
   cd /home/pnt/IOT/backend
   PYTHONPATH=. /home/pnt/miniconda3/envs/antidrone/bin/pytest -v
   ```
2. Scenario tests:
   ```bash
   cd /home/pnt/IOT
   /home/pnt/miniconda3/envs/antidrone/bin/python tests/ssh_test_runner.py --mode bench
   ```
3. Frontend build:
   ```bash
   cd /home/pnt/IOT/frontend
   npm run build
   ```

Document all commands and verification results in `/home/pnt/IOT/.agents/worker_r6_1/handoff.md`.
Send completion message to parent when done.

## 2026-09-14T05:14:56Z
You are Worker R6-1.
Tasks: R1-R5 implementation, verification, and handoff report.
