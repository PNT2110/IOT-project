# DISPATCH — Orchestrator 6

## Mission
Khắc phục lỗi tồn đọng (Camera, Serial USB, Map) và điều chỉnh kiến trúc dự án IOT Drone Station v2 (Chuyển MOD Server sang Google Apps Script).

## Working Directory
/home/pnt/IOT/.agents/orchestrator_6

## Project Root
/home/pnt/IOT

## Original Request Reference
See `/home/pnt/IOT/.agents/ORIGINAL_REQUEST.md` (section `## 2026-09-14T05:07:21Z`).

## Core Requirements
1. **Camera & Map (R1)**:
   - Fix camera stream: CSI/USB directly on Raspberry Pi 5. Implement stream handler (e.g. OpenCV/v4l2) on backend FastAPI to stream to frontend.
   - Fix Admin Map: Ensure MapLibre GL has valid tile source (offline or public OSM) and UI loads properly without white blank screen.
2. **Serial USB Connection (R2)**:
   - Fix Pi5 reading data from ESP32 over USB cable.
   - Backend Python auto-scans `/dev/ttyUSB*` and `/dev/ttyACM*` ports dynamically to discover ESP32 instead of hardcoding; auto-reconnects if disconnected.
3. **Static Manufacturer Firmware Flashing (R3)**:
   - Update UI and firmware flashing API: Remove custom `.bin` file upload by users.
   - System always reads and flashes standard pre-stored official firmware file on Pi5 (e.g., `/opt/drone-web-ui/firmware/official.bin` or configured path). If file missing, warn and lock ARM.
4. **Login UI Adjustment (R4)**:
   - Remove texts like "tài khoản pi5" from login form. Label must concisely be "tên đăng nhập".
5. **Migrate MOD Server to Google Apps Script (R5)**:
   - Replace local `mod_server.py` with `backend/mod_server.gs` (ready for user copy/paste and deploy as Web App).
   - Implement `doGet()` or `doPost()` in `.gs` to handle flight authorization, generate 1km geofence, return JSON.
   - Update Pi5 `backend/app/main.py` (and related MOD client logic): Read URL from `.env` (`MOD_WEBAPP_URL=...`) instead of `localhost:9000`. Parse token/response from Apps Script Web App.
   - Provide deployment instructions in doc/comments. Support mock URL during automated testing.

## Constraints & Acceptance Criteria
- Full test verification across all 5 requirements.
- Maintain existing security constraints (no hardcoded credentials leak, fail-safe ARM locking preserved).
- Write comprehensive plan and update `progress.md` and `BRIEFING.md`.
