# DISPATCH — Explorer R6-2 (Serial USB & Firmware Flashing)

## Working Directory
/home/pnt/IOT/.agents/explorer_r6_2

## Task
You are Explorer R6-2. Investigate the codebase for Requirements R2 and R3:
1. **Serial USB Connection (R2)**:
   - Inspect `backend/app/serial_io.py` and any related serial scanning/worker modules.
   - Analyze how `/dev/ttyUSB*` and `/dev/ttyACM*` ports are discovered and opened. Currently is it hardcoded or flawed?
   - Detail how dynamic scanning, auto-detection of ESP32 (e.g. probing or reading JSONL), auto-reconnect on disconnect, and robust JSONL line parsing are structured.
   - Review pytest mocks for serial communication to ensure testability without physical hardware.
2. **Static Manufacturer Firmware Flashing (R3)**:
   - Inspect firmware handling in `backend/app/firmware.py`, `backend/app/main.py`, and `frontend/src/components/tabs/FirmwareTab.tsx`.
   - Identify where custom `.bin` file upload is allowed in UI and API.
   - Design the change to remove user file upload, instead always using a pre-stored static official firmware file (e.g., `/opt/drone-web-ui/firmware/official.bin` or configurable fallback like `backend/firmware/official.bin`).
   - Analyze ARM locking logic: if `official.bin` is missing or not flashed, system must warn and lock ARM fail-safe.

## Requirements
- Read `/home/pnt/IOT/.agents/ORIGINAL_REQUEST.md` (section `## 2026-09-14T05:07:21Z`).
- Read `/home/pnt/IOT/PROJECT.md` and related source files.
- DO NOT modify source code. Produce an exhaustive analysis report with file paths, line numbers, and proposed implementation plan.
- Write your final report to `/home/pnt/IOT/.agents/explorer_r6_2/handoff.md`.
- Send completion message to parent when done.

## 2026-09-14T05:09:01Z
You are Explorer R6-2.
Your working directory is /home/pnt/IOT/.agents/explorer_r6_2.
Read your instructions in /home/pnt/IOT/.agents/explorer_r6_2/DISPATCH.md.
Also read /home/pnt/IOT/.agents/ORIGINAL_REQUEST.md (section ## 2026-09-14T05:07:21Z) and /home/pnt/IOT/PROJECT.md.

Task:
Investigate Requirements R2 & R3:
1. Serial USB (R2): Inspect backend/app/serial_io.py and related modules. Investigate port discovery for /dev/ttyUSB* and /dev/ttyACM*, auto-reconnection logic, JSONL parsing resilience, and how tests/mocks simulate this.
2. Static Firmware Flashing (R3): Inspect backend/app/firmware.py, backend/app/main.py, frontend/src/components/tabs/FirmwareTab.tsx. Analyze removal of custom .bin file upload from UI & API, enforcement of pre-stored official.bin (e.g. at /opt/drone-web-ui/firmware/official.bin or fallback in repo), and ARM locking if official.bin is missing.

DO NOT write source code. Write a comprehensive analysis and implementation plan to /home/pnt/IOT/.agents/explorer_r6_2/handoff.md following the Handoff Protocol. Send a completion message to parent when done.

