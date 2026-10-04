# BRIEFING — 2026-10-03T20:47:30Z

## Mission
Investigate Firmware tier (flight_gate.h, Baro.ino, tests) and Pi 5 Gateway & Local UI tier (app.js, camera stream, OTA flow, scope05 tests) and synthesize findings into a comprehensive handoff report.

## 🔒 My Identity
- Archetype: explorer
- Roles: explorer_survey_1 (Firmware & Gateway Explorer)
- Working directory: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_1
- Original parent: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81
- Milestone: Firmware & Gateway Tier Survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Verify facts by inspecting actual code files and test commands
- Write findings to handoff.md in working directory
- Communicate via send_message to parent (3be5ec9a-8b7d-4356-b0b8-0a206dabba81)

## Current Parent
- Conversation ID: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `firmware/FC_can_bang/flight_gate.h` (lines 59-83, AltLimiter and altitude_throttle_cap)
  - `firmware/FC_can_bang/Baro.ino` (baro_vspeed_mps, Altitude_barometer)
  - `firmware/FC_can_bang/MODE.ino` (apply_altitude_limit, angle_mode)
  - `firmware/FC_can_bang/FC_can_bang.ino` (main flight control loop, update_arm_state)
  - `tests/firmware/test_flight_gate.cpp` & `tests/firmware/test_host_build.py`
  - `edge/pi5/pi5/web/ui/app.js` (589 lines monolith using h(), cameraView, firmwareView)
  - `edge/pi5/pi5/web/camera.py` (MjpegStreamer, V4L2CameraAdapter, MockCameraAdapter)
  - `edge/pi5/pi5/web/firmware.py` (FirmwareUpdater, FirmwareReadiness)
  - `edge/pi5/pi5/web/extra_routes.py` & `edge/pi5/pi5/web/app.py` (FastAPI routes)
  - `tests/scope05/` (35 test cases across 6 modules)
  - `tests/scope07/test_firmware_update.py` & `tests/scope04/test_pi_features.py`
- **Key findings**:
  - `altitude_throttle_cap()` clamps to static `ALT_LIMIT_FLOOR_US = 1100` µs which causes free-fall on F450 drones (hover throttle ~1400-1500 µs). `Baro.ino` computes `baro_vspeed_mps` but it is unused in `apply_altitude_limit()`. Passing `baro_vspeed_mps` and using a dynamic floor tied to latch throttle / vertical speed prevents uncontrolled descent while preserving existing test assertions via optional/default arguments.
  - `edge/pi5/pi5/web/ui/app.js` is loaded via `<script type="module" src="/ui/app.js"></script>` in `index.html`. It can be cleanly decomposed into ES modules (`dom.js`, `api.js`, `camera.js`, `map.js`, `telemetry.js`, `firmware.js`, `users.js`, `auth.js`, `flight.js`) without any external build bundler.
  - Camera pause/resume can be cleanly implemented on the client by toggling `img.src` (setting to `""` drops the HTTP stream and triggers backend idle cleanup in `MjpegStreamer`, setting to `${API}/camera/mjpeg?t=...` resumes), saving both mobile data bandwidth and CPU.
  - Existing Pi backend firmware updater (`FirmwareUpdater`) only downloads releases from GitHub. Field operations at `192.168.4.1` often lack internet, necessitating a direct `.bin` file upload flow and status reporting.
  - `pytest tests/firmware/` and `pytest tests/scope07/` pass completely. In `tests/scope05/`, 34 tests pass out of 35; the only failure is `ModuleNotFoundError: No module named 'fastapi'` because fastapi is not yet installed in the machine's global python environment. Pip has wheel access to install `requirements-scope04.lock`.
- **Unexplored areas**: None within assigned scope.

## Key Decisions Made
- Fully documented exact file locations, signatures, physical drone calculations, modularization scheme, and test verification methods for handoff.

## Artifact Index
- c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_1\BRIEFING.md — Context memory
- c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_1\progress.md — Progress and heartbeat log
- c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_1\handoff.md — Comprehensive survey report
