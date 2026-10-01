# Handoff Report: ESP32 Firmware & Serial Survey (v2 Upgrade)

**Agent:** Explorer 1 (Firmware & Serial Interface Specialist)  
**Working Directory:** `/home/pnt/IOT/.agents/explorer_v2_survey_1`  
**Target Delivery Path:** `/home/pnt/IOT/.agents/explorer_v2_survey_1/report.md`  
**Handoff Type:** Hard (Task Complete)

---

## 1. Observation

1. **`FC_can_bang` File Inventory & Architecture:**
   - Listing `/home/pnt/IOT/FC_can_bang` confirmed exactly 7 `.ino` files and 1 `build` directory:
     - `FC_can_bang.ino` (228 lines, 6,886 bytes)
     - `display.ino` (89 lines, 2,987 bytes)
     - `ESCino.ino` (75 lines, 1,775 bytes)
     - `ICM20602.ino` (403 lines, 7,618 bytes)
     - `MODE.ino` (33 lines, 1,029 bytes)
     - `PID.ino` (153 lines, 3,892 bytes)
     - `Sbus.ino` (125 lines, 2,955 bytes)
   - No `.cpp`, `.h`, `platformio.ini`, `CMakeLists.txt`, or `Makefile` exist in the directory.

2. **Toolchain & Compilation Execution:**
   - `arduino-cli` binary found at `/home/pnt/IOT/bin/arduino-cli` (v1.5.1, commit `01f3d4f2b`).
   - Hardware package at `/home/pnt/.arduino15/packages/esp32/hardware/esp32/3.3.11`.
   - Tool `esptool` (v5.3.1) at `/home/pnt/.arduino15/packages/esp32/tools/esptool_py/5.3.1/esptool`.
   - Library `ArduinoJson` (v7.4.3) at `/home/pnt/Arduino/libraries/ArduinoJson`.
   - Running `/home/pnt/IOT/bin/arduino-cli compile --fqbn esp32:esp32:esp32 /home/pnt/IOT/FC_can_bang` yielded exit code 0:
     ```
     Sketch uses 963731 bytes (73%) of program storage space. Maximum is 1310720 bytes.
     Global variables use 48148 bytes (14%) of dynamic memory, leaving 279532 bytes for local variables. Maximum is 327680 bytes.
     ```
   - Produced artifacts in `FC_can_bang/build/esp32.esp32.esp32/`: `FC_can_bang.ino.bin` (963,872 bytes), `boot_app0.bin` (8,192 bytes), and merged flash binary `FC_can_bang.ino.merged.bin` (4,194,304 bytes).

3. **Remote Raspberry Pi 5 Serial Environment (`192.168.1.118`):**
   - Host `192.168.1.118` ping responded in 26.4 ms.
   - Querying serial ports on Pi5 revealed:
     ```
     crw-rw-rw- 1 root dialout 188, 0 Sep 13 16:05 /dev/ttyUSB0
     /dev/serial/by-id/usb-1a86_USB_Serial-if00-port0 -> ../../ttyUSB0
     ```
   - Attempting `esptool chip-id` on `/dev/ttyUSB0` failed with:
     ```
     ERROR: A fatal error occurred: Failed to connect to Espressif device: Invalid head of packet (0x1C)
     ```
   - Sampling 100 bytes from `/dev/ttyUSB0` at 38400 baud confirmed:
     ```
     b'$GNRMC,,V,,,,,,,,,,N,V*37\r\n$GNVTG,,,,,,,,,N*2E\r\n$GNGGA,,,,,,0,00,99.99,,,,,,*56\r\n$GNGSA,A,1,,,,,,,,,'
     ```
     Verbatim evidence that `/dev/ttyUSB0` on Pi5 is the BZ251 GPS receiver (transmitting NMEA at 38400 baud), not an ESP32.

4. **Existing Serial & Provisioning Code in Repository:**
   - In `FC_can_bang/FC_can_bang.ino`:
     - Lines 148-150: `WiFi.mode(WIFI_AP); WiFi.softAP("DRONE-123456");`
     - Lines 85-104: `handleRoot()` renders HTML with blue/grey styling (`#0056b3`).
     - Lines 106-131: `handleConnect()` emits `{"type":"wifi_setup","ssid":...,"password":...}` over `Serial`.
     - Lines 201-204: Fail-safe check: `if (!flight_permission) { status_arm = 0; }`.
   - In `FC_can_bang/display.ino`:
     - Line 18: `String line = Serial.readStringUntil('\n');` (blocking read).
     - Lines 24-30: Reads `wifi_status` (`ip`, `url`, `drone_id`, `default_account`).
     - Lines 31-33: Reads `permission` (`granted`).
     - Lines 34-39: Reads `command` (`LAND`, `LOCK_ARM` resets `flight_permission = false`).
     - Lines 57-87: Emits `telemetry` at 5Hz (200ms) with hardcoded PID constants, omitting LiDAR altitude.
   - In `backend/app/serial_io.py`:
     - Lines 210-478: `UsbPortCoordinator` probes candidate ports using `_probe_gps` (38400 baud NMEA checksum) and `_probe_esp` (115200 baud JSON/ping).
     - Lines 491-569: `SerialWorker` manages serial connection loops with reconnect handling.
   - In `backend/app/wifi_handler.py`:
     - Lines 5-37: Executes `sudo nmcli dev wifi connect <ssid> password <password>` and reports back `{"type": "wifi_status", "status": "connected", "ip": ..., "url": ...}`.
   - In `backend/app/main.py`:
     - Line 427 contains an unescaped raw string syntax bug from a previous patch (`GLOBAL_FLIGHT_PERMISSION = None\nfrom fastapi import UploadFile, File`).

---

## 2. Logic Chain

1. **Directory Structure Preservation:**
   - *Premise (Prompt & Section 1/4):* We must not alter the directory or file names in `FC_can_bang`.
   - *Observation:* The project is built by Arduino CLI where all `.ino` files in the folder are automatically merged into one compilation unit.
   - *Deduction:* All new functionality (Wi-Fi AP enhancements, non-blocking serial, PID getters/setters, watchdog timer, LiDAR altitude) can be integrated seamlessly inside the existing seven `.ino` files without creating new headers or source files.

2. **Dual Serial Role Separation on Pi5:**
   - *Observation:* `/dev/ttyUSB0` is continuously streaming BZ251 NMEA data at 38400 baud.
   - *Deduction:* When ESP32 is attached via USB to Pi5, it will register as a separate device (e.g. `/dev/ttyUSB1` or `/dev/ttyACM0`). The `UsbPortCoordinator` in `backend/app/serial_io.py` must dynamically bind `/dev/ttyUSB0` to `gps_worker` and `/dev/ttyUSB1` to `esp_worker`. Firmware flashing scripts must target the assigned ESP port, avoiding `/dev/ttyUSB0` to prevent flash corruption.

3. **Fail-Safe ARM Mechanism:**
   - *Observation:* In `FC_can_bang.ino`, `if (!flight_permission) status_arm = 0;` disables motors. However, in `display.ino`, `flight_permission` is updated only when a serial message is received and never times out.
   - *Deduction:* If Pi5 crashes, halts, or gets disconnected while `flight_permission == true`, the ESP32 would remain armed indefinitely.
   - *Conclusion:* A time-based serial heartbeat watchdog (`millis() - last_permission_time < 2000`) is mandatory in `FC_can_bang.ino`. If Pi5 stops refreshing permission for >2 seconds, ESP32 must automatically drop `flight_permission = false`, zero the I-terms (`reset_status_flight()`), and engage `no_fly()`.

4. **Serial Communication Non-Blocking Imperative:**
   - *Observation:* `display.ino` currently calls `Serial.readStringUntil('\n')` inside the 200Hz loop.
   - *Deduction:* `readStringUntil` blocks for up to 1000ms if a character is delayed, which stalls the PID loop and causes drone crash.
   - *Conclusion:* In the implementation phase, serial reading must use a non-blocking byte accumulator that processes frames only after `\n` is received.

---

## 3. Caveats

1. **ICM-20602 Bench Testing:**
   - In `ICM20602.ino`, `setup_icm20602()` contains an infinite `while(1)` calibration loop. If an ESP32 board is plugged into Pi5 without the physical ICM-20602 sensor wired, it will hang in `setup()` and never enter `loop()`. A fallback timeout or mock sensor mode is necessary for bench verification.
2. **Wi-Fi Spectrum Coexistence:**
   - Operating an active SoftAP on the ESP32 WROOM while simultaneously stabilizing flight can introduce interrupt jitter from the Wi-Fi stack. Transitioning the SoftAP to deep power-down (`WiFi.softAPdisconnect(true)`) after commissioning is strongly recommended.
3. **Pi5 Backend Syntax Glitch:**
   - As observed in `backend/app/main.py:427`, an unescaped literal `\n` exists from a prior external edit. While out-of-scope for this read-only survey, this must be corrected by the backend implementation agent before running backend unit tests.

---

## 4. Conclusion

1. **Feasibility:** Full implementation of Drone Station v2 requirements (AP provisioning, blue-white portal, Pi5 serial handoff, fail-safe ARM locking, live PID tuning, LiDAR telemetry) is completely feasible within the existing seven `.ino` files of `FC_can_bang`.
2. **Build Readiness:** The build toolchain (`arduino-cli` v1.5.1, ESP32 core 3.3.11, ArduinoJson 7.4.3) is verified, fully functional, and compiles the firmware cleanly.
3. **Comprehensive Report:** The complete survey, file inventory, toolchain commands, serial JSONL specifications, and architectural diagrams have been written to `/home/pnt/IOT/.agents/explorer_v2_survey_1/report.md`.

---

## 5. Verification Method

To independently verify the observations and conclusions in this report:

1. **Verify Compilation:**
   ```bash
   /home/pnt/IOT/bin/arduino-cli compile --fqbn esp32:esp32:esp32 /home/pnt/IOT/FC_can_bang
   ```
   *Expected:* Exit code 0, sketch size ~963 KB, no compilation errors.

2. **Verify GPS Port on Pi5:**
   ```bash
   python3 /home/pnt/IOT/run_with_pass.py "ssh -o StrictHostKeyChecking=no pi5@192.168.1.118 '/opt/iot-drone/venv/bin/python3 -c \"import serial; s=serial.Serial(\\\"/dev/ttyUSB0\\\", 38400, timeout=1); print(s.readline())\"'" 123456
   ```
   *Expected:* Output starts with `$GN` or `$GP` NMEA sentence.

3. **Inspect Deliverable Report:**
   View `/home/pnt/IOT/.agents/explorer_v2_survey_1/report.md` to review the architectural survey and protocol specifications.
