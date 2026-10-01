## 2026-09-13T13:04:04Z
You are the Firmware Flashing & ARM Safety Worker for Milestone 3 (M3).
Your working directory: /home/pnt/IOT/.agents/worker_m3_firmware_arm_r2
User request record: /home/pnt/IOT/.agents/ORIGINAL_REQUEST.md (read section ## 2026-09-13T09:30:16Z)
Specification file: /home/pnt/IOT/prompt-du-an-drone-v2.md (pay special attention to Sections 4, 8, 10, 11, 13)
Project documentation: /home/pnt/IOT/PROJECT.md and /home/pnt/IOT/TEST_INFRA.md
Survey & Test findings: /home/pnt/IOT/.agents/explorer_v2_survey_2/report.md and /home/pnt/IOT/tests/common.py

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & Boundaries:
You have exclusive write ownership of `backend/app/firmware.py` and the firmware & ARM safety endpoints in `backend/app/main.py` and `backend/app/models.py`. DO NOT touch `frontend/` or `FC_can_bang/`.

Your Mission:
1. Firmware Flashing Pipeline on Pi5:
   - Implement `backend/app/firmware.py` to manage firmware files:
     - Storage path: `backend/data/firmware/` (auto-create if missing).
     - Copy the compiled production binary `/home/pnt/IOT/FC_can_bang/build/esp32.esp32.esp32/FC_can_bang.ino.merged.bin` as the initial baseline firmware if not present.
     - Upload endpoint `POST /api/v1/firmware/upload`: validates `.bin` format, checks size, calculates SHA-256 hash.
     - Status endpoint `GET /api/v1/firmware/status`: returns `{ "firmware_flashed": bool, "firmware_version": str, "last_flash_time": str | None, "flash_in_progress": bool, "available_files": list }`.
     - Flash endpoint `POST /api/v1/firmware/flash`:
       * Coordinates with `UsbPortCoordinator` / `esp_worker` in `backend/app/serial_io.py` to temporarily pause/release the serial port lease.
       * Executes `esptool` (`/opt/iot-drone/venv/bin/esptool` or system `esptool` or mock in test mode) to flash the binary at address `0x0` (merged binary) or standard offsets.
       * Resumes serial worker on completion.
       * Sets `firmware_flashed = True` in SQLite database (`system_state` or `firmware_state` table).
       * Records action in `audit_log`.
     - Delete endpoint `DELETE /api/v1/firmware/{filename}`: deletes uploaded binary.
2. Pre-Flash Flight Feature Lockout:
   - If `firmware_flashed == False`:
     - ALL flight control actions (`POST /api/v1/commands/arm`, takeoff, land, mission waypoints, PID write) MUST return `423 Locked` or `403 Forbidden` with a clear message: `"Firmware must be flashed before flight control features can be used."`.
     - Only firmware endpoints, video stream, and session endpoints remain accessible.
3. Fail-Safe ARM Locking Logic (`POST /api/v1/commands/arm`):
   - Implement strict ARM command validation:
     * Check 1: `firmware_flashed == True`.
     * Check 2: MOD flight permission granted (`flight_permission == True`).
     * Check 3: Current time is within the approved flight time window (`valid_from <= now <= valid_to`).
     * Check 4: Current GPS coordinates are within 1000 meters (1km) radius from the approved permit center coordinates.
     * Check 5: GPS fix is healthy and not stale (< 5 seconds old).
     * If ALL checks pass: accept ARM command, emit serial permission heartbeat to ESP32: `{"type": "permission", "granted": true, "reason": "authorized"}`.
     * If ANY check fails: REJECT ARM command with 403 Forbidden (`status: "rejected"`, `reason: "..."`), immediately emit `{"type": "permission", "granted": false, "reason": "..."}` and `{"type": "command", "action": "LOCK_ARM"}` down to ESP32.
   - ABSOLUTE HARD REQUIREMENT: NEVER set `ENABLE_REAL_FLIGHT_COMMANDS = True`.
4. Background ARM Safety Loop:
   - Implement a 1-second continuous background loop in `main.py` that evaluates the above 5 checks. If the drone is armed or permission was previously granted, but the time window expires or drone moves outside 1km, it immediately commands `LOCK_ARM` to ESP32 and revokes permission.
5. Verification:
   - Run unit tests and verification with pytest: `cd backend && PYTHONPATH=. pytest tests/`.
   - Run test scenarios 6, 12, 13, 14 using `python3 tests/ssh_test_runner.py --mode=bench` and verify they pass.

Deliverables:
- Implementation in `backend/app/firmware.py`, `backend/app/main.py`, `backend/app/models.py`
- Test logs
- Report in `/home/pnt/IOT/.agents/worker_m3_firmware_arm_r2/report.md` and handoff in `/home/pnt/IOT/.agents/worker_m3_firmware_arm_r2/handoff.md`
When done, notify parent via send_message.
