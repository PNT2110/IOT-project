# DISPATCH — Explorer R6-3 (Login UI & MOD Server Apps Script)

## Working Directory
/home/pnt/IOT/.agents/explorer_r6_3

## Task
You are Explorer R6-3. Investigate the codebase for Requirements R4 and R5:
1. **Login UI Adjustment (R4)**:
   - Search frontend codebase (`frontend/src/`) for all occurrences of "tài khoản pi5" or similar phrases.
   - Specify the exact files, lines, and replacements to make the label concise: "tên đăng nhập".
2. **Migrate MOD Server to Google Apps Script (R5)**:
   - Inspect existing `backend/mod_server.py` and any related scripts (`mod_server/`, `backend/app/geofence.py`, `backend/app/main.py`).
   - Detail the architecture and implementation of `backend/mod_server.gs` (Google Apps Script) handling:
     - `doGet()` and/or `doPost()` endpoints.
     - Flight authorization / permission requests.
     - 1km circular geofence generation (coordinates, GeoJSON polygon or circle points, expiration).
     - Clean JSON response format.
     - Include step-by-step deployment instructions in the script header / comments so users can deploy as a Google Web App and get an `/exec` URL.
   - Detail changes in `backend/app/main.py` (and any client modules) to:
     - Read `MOD_WEBAPP_URL` from `.env` instead of hardcoded `localhost:9000`.
     - Properly handle the response format from Google Apps Script Web App.
     - Support clean mocking of `MOD_WEBAPP_URL` in pytest tests without requiring live internet connection.
   - Review existing test suite for MOD server and specify updates needed.

## Requirements
- Read `/home/pnt/IOT/.agents/ORIGINAL_REQUEST.md` (section `## 2026-09-14T05:07:21Z`).
- Read `/home/pnt/IOT/PROJECT.md` and related source files.
- DO NOT modify source code. Produce an exhaustive analysis report with file paths, line numbers, and proposed implementation plan.
- Write your final report to `/home/pnt/IOT/.agents/explorer_r6_3/handoff.md`.
## 2026-09-14T05:09:01Z

You are Explorer R6-3.
Your working directory is /home/pnt/IOT/.agents/explorer_r6_3.
Read your instructions in /home/pnt/IOT/.agents/explorer_r6_3/DISPATCH.md.
Also read /home/pnt/IOT/.agents/ORIGINAL_REQUEST.md (section ## 2026-09-14T05:07:21Z) and /home/pnt/IOT/PROJECT.md.

Task:
Investigate Requirements R4 & R5:
1. Login UI Adjustment (R4): Search frontend/src/ for "tài khoản pi5" and related text. Identify exact occurrences and replacements to display concisely "tên đăng nhập".
2. Migrate MOD Server to Google Apps Script (R5): Inspect backend/mod_server.py, backend/app/main.py, backend/app/geofence.py. Design backend/mod_server.gs with doGet/doPost, 1km geofence generation, flight authorization, JSON responses, and deployment guide. Specify how backend/app/main.py reads MOD_WEBAPP_URL from .env and handles responses, and how tests mock MOD_WEBAPP_URL without live network calls.

DO NOT write source code. Write a comprehensive analysis and implementation plan to /home/pnt/IOT/.agents/explorer_r6_3/handoff.md following the Handoff Protocol. Send a completion message to parent when done.
