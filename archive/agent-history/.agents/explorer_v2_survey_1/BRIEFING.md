# BRIEFING — 2026-09-13T09:36:30Z

## Mission
Conduct a comprehensive, read-only survey of the ESP32 flight controller code in FC_can_bang, build system, Wi-Fi AP captive portal, and serial JSONL protocol with Pi5.

## 🔒 My Identity
- Archetype: explorer
- Roles: Firmware & Serial Interface Specialist
- Working directory: /home/pnt/IOT/.agents/explorer_v2_survey_1
- Original parent: 1a8433ed-32ff-4d20-9edc-6916609b0233
- Milestone: Survey & Architecture Analysis for ESP32 FC & Serial

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- DO NOT CHANGE directory/file structure of FC_can_bang (only rewrite internal logic in future implementation phase)
- Write only to your own folder (/home/pnt/IOT/.agents/explorer_v2_survey_1)
- Produce structured report.md and handoff.md

## Current Parent
- Conversation ID: 1a8433ed-32ff-4d20-9edc-6916609b0233
- Updated: 2026-09-13T09:36:30Z

## Investigation State
- **Explored paths**:
  - `/home/pnt/IOT/FC_can_bang/*` (all 7 .ino files: FC_can_bang.ino, display.ino, ESCino.ino, ICM20602.ino, MODE.ino, PID.ino, Sbus.ino)
  - `/home/pnt/IOT/FC_can_bang/build/esp32.esp32.esp32/*`
  - `/home/pnt/IOT/backend/app/serial_io.py`, `backend/app/wifi_handler.py`, `backend/app/main.py`
  - Hardware toolchain: `/home/pnt/IOT/bin/arduino-cli`, `/home/pnt/.arduino15/packages/esp32/...`, `/opt/iot-drone/venv/bin/esptool`
  - Remote Raspberry Pi 5 (`192.168.1.118`): queried serial ports, inspected `/dev/ttyUSB0` (BZ251 GPS at 38400 baud)
- **Key findings**:
  - `arduino-cli` v1.5.1 with core 3.3.11 compiles `FC_can_bang` cleanly (963 KB binary, 4MB merged).
  - Directory structure of `FC_can_bang` has 7 .ino files; preserving layout is 100% feasible.
  - Pi5 `/dev/ttyUSB0` is live with BZ251 GPS at 38400 baud. ESP32 connects on secondary port.
  - Fail-safe ARM mechanism identified: deny-by-default + 2000ms serial heartbeat watchdog.
  - Serial protocol gaps identified: PID tuning exchange, LiDAR altitude in telemetry, non-blocking serial reading, IMU calibration timeout.
- **Unexplored areas**: None within the firmware/serial survey scope.

## Key Decisions Made
- Confirmed Arduino CLI build system and toolchain path (`/home/pnt/IOT/bin/arduino-cli`).
- Defined complete JSONL message schemas for Pi5 ⇄ ESP32.
- Designed Wi-Fi provisioning lifecycle and blue-white styling.
- Designed 2000ms serial heartbeat watchdog for fail-safe ARM locking.

## Artifact Index
- `/home/pnt/IOT/.agents/explorer_v2_survey_1/report.md` — Full investigation report
- `/home/pnt/IOT/.agents/explorer_v2_survey_1/handoff.md` — Handoff report
- `/home/pnt/IOT/.agents/explorer_v2_survey_1/progress.md` — Progress tracker
