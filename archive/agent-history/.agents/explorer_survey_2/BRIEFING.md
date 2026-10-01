# BRIEFING — 2026-09-09T13:15:00Z

## Mission
Survey the design and architecture for Concurrent USB Device Handling (R2): reliable port disambiguation (GPS at 38400 baud vs ESP32), content-based auto-detection, dynamic reconnection, backend integration, and pytest simulation.

## 🔒 My Identity
- Archetype: Explorer
- Roles: USB Auto-Detect Explorer, Read-only investigation
- Working directory: c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_2
- Original parent: 94568146-c35e-44d3-9a12-47c93b67809f
- Milestone: Milestone 0 - Comprehensive Survey & Architecture (R2)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify project source code
- Files for content delivery (analysis.md, handoff.md, progress.md)
- Messages for coordination via send_message to parent (94568146-c35e-44d3-9a12-47c93b67809f)
- Thorough evidence chains referencing exact file paths, line numbers, and protocols

## Current Parent
- Conversation ID: 94568146-c35e-44d3-9a12-47c93b67809f
- Updated: 2026-09-09T13:07:30Z

## Investigation State
- **Explored paths**:
  - `backend/app/serial_io.py`
  - `backend/app/config.py`
  - `backend/app/main.py`
  - `backend/app/models.py`
  - `backend/tests/test_core.py`, `backend/tests/test_api.py`
  - `scripts/test_gps_uart.py`
  - `PROJECT_STATUS.md`, `WORKLOG.md`, `ORIGINAL_REQUEST.md`
- **Key findings**:
  - Static `gps_device` default (`/dev/serial0`) and greedy first-match `esp_device` (`candidates[0]`) will collide and starve when GPS is moved to USB.
  - Double-CH340 collision: identical VID/PID (`0x1A86:0x7523`) and missing serial number descriptors break `/dev/serial/by-id`.
  - ESP32 DTR/RTS auto-reset trap: standard serial port opens cause microcontroller reset unless `dtr=False, rts=False` is enforced.
  - Safe two-stage content-based probe: 38,400 baud NMEA checksum check first, then 115,200 baud JSONL/boot check.
  - Centralized `UsbPortCoordinator` prevents worker race conditions and handles hotplug/unplug lifecycle.
  - Portable duck-typed `MockSerialPort` pytest fixture enables cross-platform testing on both Windows and Linux without POSIX `pty`.
- **Unexplored areas**: None for survey scope. Ready for implementation phase.

## Key Decisions Made
- Recommended content-based auto-detection with centralized `UsbPortCoordinator`.
- Recommended two-stage probe: 38,400 baud passive listen first, then 115,200 baud.
- Mandated `dtr=False, rts=False` on all serial port open operations.
- Selected duck-typed `MockSerialPort` over POSIX `pty` for cross-platform test fidelity.

## Artifact Index
- `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_2\DISPATCH.md` — Dispatch record
- `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_2\BRIEFING.md` — Persistent briefing
- `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_2\progress.md` — Liveness heartbeat
- `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_2\analysis.md` — Full technical analysis and specification
- `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_2\handoff.md` — 5-component handoff report
