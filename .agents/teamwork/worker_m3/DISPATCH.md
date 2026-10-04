# Dispatch Task: Milestone 3 — Pi 5 Gateway & Local UI Modernization

## Identity
- Role: Milestone 3 Worker
- TypeName: teamwork_preview_worker
- Working Directory: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m3
- Parent Conversation ID: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81

## Authoritative Requirements & References
- Requirements: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md` (R3, R4.4)
- Project Spec: `c:\Users\pnt21\Desktop\IOT\PROJECT.md`
- Firmware/Pi Survey Report: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_1\handoff.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive Write Ownership
You exclusively own and may edit ONLY the following files:
1. `edge/pi5/pi5/web/ui/` (`app.js`, `core/dom.js`, `core/api.js`, `views/wifi.js`, `views/auth.js`, `views/camera.js`, `views/map.js`, `views/telemetry.js`, `views/users.js`, `views/firmware.js`, `views/flight.js`, `index.html`)
2. `edge/pi5/pi5/web/camera.py` (ensure camera disconnect behavior supports pause)
3. `edge/pi5/pi5/web/extra_routes.py` (OTA firmware upload endpoint)
4. `edge/pi5/pi5/web/firmware.py` (support local file flashing in addition to GitHub)
5. `tests/scope05/` (Pi gateway tests)
DO NOT modify `server/` or `frontend/` files.

## Detailed Tasks
1. **Feature 9: Pi 5 Local UI ES Module Modularization**:
   - Refactor the monolithic 589-line `edge/pi5/pi5/web/ui/app.js` into structured ES modules:
     - `core/dom.js`: `h()`, `banner()`, `field()`, `form()`, `modal()`, `closeModal()`
     - `core/api.js`: `API`, `cookie()`, `api()`, `clearScreen()`, `every()`
     - `views/wifi.js`: `wifiScreen()`
     - `views/auth.js`: `authScreen()`, `showTerms()`, `termsCheck()`
     - `views/camera.js`: `cameraView()` with Pause/Resume toggle
     - `views/map.js`: `mapView()`
     - `views/telemetry.js`: `telemetryView()`, `droneModel()`
     - `views/users.js`: `usersView()`
     - `views/firmware.js`: `firmwareView()` with local OTA upload & flashing status
     - `views/flight.js`: `flightModal()`, `profileModal()`, `roleRequestModal()`
     - `app.js`: Main coordinator: imports views, sets up navigation tabs, and boots.
   - Preserve 100% of existing CSS classes, visual appearance, features, and accessibility attributes.
2. **Feature 10: Camera Stream Pause/Resume**:
   - In `views/camera.js`, add a toggle button (`Tạm dừng` / `Tiếp tục`) with a status chip (`TRỰC TIẾP` / `TẠM DỪNG`).
   - Clicking `Tạm dừng` sets `image.src = ""` or placeholder, closing the HTTP MJPEG connection and saving mobile bandwidth.
   - Clicking `Tiếp tục` sets `image.src = `${API}/camera/mjpeg?t=${Date.now()}`, resuming live stream.
3. **Feature 11: Local OTA Firmware Upload Endpoint & UI**:
   - In `edge/pi5/pi5/web/extra_routes.py` and `firmware.py`:
     - Add `POST /api/pi/v1/firmware/upload` accepting multipart file upload (`.bin` file).
     - Validates ESP32 magic byte (`0xe9`), max size 4MB, drone disarmed.
     - Saves binary, verifies SHA-256, and integrates with `FirmwareUpdater.flash()` / job status queue.
   - In `views/firmware.js`:
     - Add file picker `<input type="file" accept=".bin">` with upload button, progress/status indicator, and flash trigger.

## Verification Requirements
- Verify that `edge/pi5/pi5/web/ui/` loads modularly and syntax is 100% valid JavaScript.
- Test OTA firmware upload and camera routes via pytest in `tests/scope05/` and `tests/e2e/`.
- Run `pytest tests/e2e/test_tier1_feature_coverage.py -k "pi"`.
- Write your handoff report to `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m3\handoff.md`.

## 2026-10-03T22:10:54Z
Received assignment from parent orchestrator 3be5ec9a-8b7d-4356-b0b8-0a206dabba81:
"You are worker_m3, the Milestone 3 Worker for Pi 5 Gateway & Local UI Modernization.
Your working directory is: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m3
The authoritative requirements are in: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md
The project specification is in: c:\Users\pnt21\Desktop\IOT\PROJECT.md
The survey report is in: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_1\handoff.md
Please read your dispatch instructions at: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m3\DISPATCH.md
..."
