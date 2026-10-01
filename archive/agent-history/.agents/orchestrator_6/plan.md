# Execution Plan — Orchestrator 6

## Objectives
1. **R1: Camera & Map**:
   - Fix camera stream: CSI/USB on Raspberry Pi 5. Implement stream handler (OpenCV/v4l2) on FastAPI backend to stream to frontend.
   - Fix Map: Ensure MapLibre GL has valid tile source (offline or public OSM) and UI loads without blank screen.
2. **R2: Serial USB Connection (Pi5 <-> ESP32)**:
   - Dynamic auto-scan of `/dev/ttyUSB*` and `/dev/ttyACM*` ports.
   - Auto-reconnection logic and resilient JSONL parsing.
3. **R3: Static Manufacturer Firmware Flashing**:
   - Remove custom file upload UI and API endpoints.
   - Flash standard pre-stored official firmware file (`official.bin`).
   - If firmware file is missing, warn and lock ARM.
4. **R4: Login UI Adjustment**:
   - Remove "tài khoản pi5" phrasing from login form; display concise "tên đăng nhập".
5. **R5: Migrate MOD Server to Google Apps Script**:
   - Create `backend/mod_server.gs` with `doGet()` / `doPost()` handling flight authorization, 1km circular geofence generation, JSON responses.
   - Update `backend/app/main.py` (and related MOD client logic) to read `MOD_WEBAPP_URL` from `.env`.
   - Provide deployment documentation and instructions. Ensure automated tests mock the URL cleanly.

## Phases
1. **Phase 1: Survey (3 Explorers in parallel)**:
   - Explorer 1 (`explorer_r6_1`): Survey Camera stream backend/frontend & MapLibre GL setup (R1).
   - Explorer 2 (`explorer_r6_2`): Survey Serial USB handling in `serial_io.py`/backend & Firmware flashing flow in backend/frontend (R2 & R3).
   - Explorer 3 (`explorer_r6_3`): Survey Login UI in frontend & MOD Server migration to Apps Script in backend/tests (R4 & R5).
2. **Phase 2: Synthesis & Feature Inventory Update**:
   - Consolidate explorer findings, verify exact code locations, dependencies, and potential regressions.
3. **Phase 3: Implementation (Worker)**:
   - Dispatch Worker (`worker_r6_1`) to execute all code changes, unit tests, and mock tests across R1-R5.
4. **Phase 4: Gate Verification**:
   - 2 Reviewers (`reviewer_r6_1`, `reviewer_r6_2`).
   - 2 Challengers (`challenger_r6_1`, `challenger_r6_2`).
   - 1 Forensic Auditor (`auditor_r6_1`).
   - Collect verdicts in `GATE_STATUS.md`.
5. **Phase 5: Final Report & Handoff**:
   - Compile handoff report and notify Sentinel via `send_message`.
