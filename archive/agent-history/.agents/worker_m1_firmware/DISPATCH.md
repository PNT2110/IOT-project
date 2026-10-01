## 2026-09-13T09:38:32Z

You are the Firmware Worker for Milestone 1 (M1: ESP32 Firmware & Serial Protocol).
Your working directory: /home/pnt/IOT/.agents/worker_m1_firmware
User request record: /home/pnt/IOT/.agents/ORIGINAL_REQUEST.md (read section ## 2026-09-13T09:30:16Z)
Specification file: /home/pnt/IOT/prompt-du-an-drone-v2.md (pay special attention to Sections 1, 2, 4, 6, 8, 9, 10, 11)
Project documentation: /home/pnt/IOT/PROJECT.md
Explorer survey: /home/pnt/IOT/.agents/explorer_v2_survey_1/report.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & Boundaries:
You have exclusive write ownership of `/home/pnt/IOT/FC_can_bang/`.
CRITICAL CONSTRAINT: You MUST NOT create new files, rename files, or alter the directory structure in `FC_can_bang/`. All changes must be made directly within the 7 existing `.ino` files:
- `FC_can_bang.ino`
- `display.ino`
- `ESCino.ino`
- `ICM20602.ino`
- `MODE.ino`
- `PID.ino`
- `Sbus.ino`

Your Mission:
1. Wi-Fi Provisioning (AP + Captive Portal):
   - In unconfigured state (or when Wi-Fi setup is requested), ESP32 starts SoftAP with SSID based on MAC address (e.g. `DRONE-` + last 6 hex chars of MAC) and DNS server on port 53 for captive portal redirection.
   - Serve a lightweight, responsive Captive Portal web page styled in a Blue-White theme (`#0066cc` / `#ffffff` / `#f0f4f8`).
   - Portal lists scanned Wi-Fi SSIDs, allows selecting one and inputting password.
   - On submission, ESP32 transmits JSONL to Pi5: `{"type": "wifi_setup", "ssid": "...", "password": "..."}`.
   - ESP32 listens for Pi5 response: `{"type": "wifi_status", "status": "connected", "ip": "...", "url": "...", "drone_id": "...", "default_account": "..."}`.
   - Portal displays the connection confirmation, IP/URL, drone ID, and default account credentials.
   - ESP32 then shuts down SoftAP (`WiFi.softAPdisconnect(true)`) and transitions to normal serial operation.
2. Non-blocking Bidirectional Serial Protocol (115200 baud):
   - In `display.ino`, eliminate all blocking reads (`Serial.readStringUntil('\n')`). Implement a fast, non-blocking byte buffer accumulator that parses complete JSONL lines on `\n`.
   - Telemetry frame (5Hz): Include `roll`, `pitch`, `yaw`, `lidar_altitude_m` (using `Altitude_kalman`), `armed`, `flight_permission`, and current PID gains (`p_gain`, `i_gain`, `d_gain`).
   - PID Tuning:
     - On receiving `{"type": "pid_get"}`, reply with `{"type": "pid_data", "kp": ..., "ki": ..., "kd": ...}`.
     - On receiving `{"type": "pid_set", "kp": ..., "ki": ..., "kd": ...}`, update live PID gains and reply with `{"type": "ack", "command": "pid_set", "status": "ok"}`.
3. Fail-Safe ARM Latch & Watchdog:
   - In `FC_can_bang.ino`, enforce strict fail-safe:
     - `flight_permission` is false by default.
     - Pi5 sends periodic heartbeat: `{"type": "permission", "granted": bool, "reason": "..."}`.
     - Record `last_permission_time = millis()`.
     - In the main loop: if `!flight_permission` OR `(millis() - last_permission_time > 2000)`, immediately set `status_arm = 0`, call `reset_status_flight()`, and activate `no_fly()`.
4. Bench-testing sensor resilience:
   - In `ICM20602.ino`, ensure that if the IMU is not wired (e.g. during bench testing on Pi5), the firmware does not hang in an infinite `while(1)` in `setup()`, but logs a warning and proceeds with simulated or zeroed IMU data so serial communication remains fully alive.
5. Compilation Verification:
   - Run `/home/pnt/IOT/bin/arduino-cli compile --fqbn esp32:esp32:esp32 /home/pnt/IOT/FC_can_bang`.
   - Verify exit code 0 and successful generation of binaries.

Deliverables:
- Updated `.ino` files in `/home/pnt/IOT/FC_can_bang/`
- Successful compilation log
- Work report in `/home/pnt/IOT/.agents/worker_m1_firmware/report.md` and handoff in `/home/pnt/IOT/.agents/worker_m1_firmware/handoff.md`
When done, notify parent via send_message.
