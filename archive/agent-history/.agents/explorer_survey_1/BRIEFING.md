# BRIEFING — 2026-09-09T13:10:30Z

## Mission
Survey backend serial architecture, GPS reader service, ESP32 handler, baud rates, and serial configuration for USB serial migration and concurrent device handling.

## 🔒 My Identity
- Archetype: explorer
- Roles: Serial Architecture Explorer
- Working directory: c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_1
- Original parent: 94568146-c35e-44d3-9a12-47c93b67809f
- Milestone: Survey Phase

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify source code files
- Survey backend serial architecture, GPS reader service, ESP32 handler, baud rates, serial configuration
- Produce comprehensive analysis.md and handoff.md in working directory
- Communicate via send_message to parent

## Current Parent
- Conversation ID: 94568146-c35e-44d3-9a12-47c93b67809f
- Updated: 2026-09-09T13:10:30Z

## Investigation State
- **Explored paths**:
  - `ORIGINAL_REQUEST.md`, `PROJECT_STATUS.md`, `WORKLOG.md`
  - `backend/app/config.py`, `backend/app/serial_io.py`, `backend/app/models.py`, `backend/app/main.py`, `backend/app/db.py`
  - `backend/.env.example`, `deploy/iot-drone.service`, `deploy/install_pi.sh`
  - `scripts/test_gps_uart.py`
  - `backend/tests/test_core.py`, `backend/tests/test_api.py`
  - `frontend/src/App.tsx`, `frontend/src/types.ts`
- **Key findings**:
  - GPS is configured at 38400 baud, currently pointing to `/dev/serial0` (GPIO UART).
  - ESP is configured at 115200 baud, currently using greedy glob matching (`candidates[0]`) from `/dev/serial/by-id/*`, `/dev/ttyACM*`, `/dev/ttyUSB*`.
  - Migrating GPS to USB creates a severe collision risk with ESP if both use CH340 adapters (identical VID:PID 1a86:7523, no unique serial number).
  - Disambiguation requires: mutual exclusion in resolver, stream/content-based sniffing (NMEA `$` vs JSON `{`), and physical port path binding (`/dev/serial/by-path/...`).
  - All concrete code points mapped in `analysis.md` and `handoff.md`.
- **Unexplored areas**:
  - Physical in-loop hardware test on Pi 5 (deferred to implementation/validation phase).

## Key Decisions Made
- Fully documented all 5 survey task points with code snippets, architecture tables, and clear verification steps.
- Produced comprehensive `analysis.md` and standard 5-component `handoff.md`.

## Artifact Index
- `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_1\analysis.md` — Detailed serial architecture analysis and USB migration guide.
- `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_1\handoff.md` — 5-component structured handoff report.
- `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_1\progress.md` — Progress log and liveness heartbeat.
- `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_1\DISPATCH.md` — Log of initial dispatch directives.
