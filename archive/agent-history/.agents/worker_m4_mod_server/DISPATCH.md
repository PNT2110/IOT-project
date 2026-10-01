## 2026-09-13T09:52:20Z
You are the MOD Server Worker for Milestone 4 (M4: Independent Standalone MOD Server).
Your working directory: /home/pnt/IOT/.agents/worker_m4_mod_server
User request record: /home/pnt/IOT/.agents/ORIGINAL_REQUEST.md (read section ## 2026-09-13T09:30:16Z)
Specification file: /home/pnt/IOT/prompt-du-an-drone-v2.md (pay special attention to Section 7, 8, 10, 11, 13)
Project documentation: /home/pnt/IOT/PROJECT.md and /home/pnt/IOT/TEST_INFRA.md
Survey & Test findings: /home/pnt/IOT/.agents/explorer_v2_survey_3/report.md and /home/pnt/IOT/tests/test_scenario_10_mod_request.py, `test_scenario_11_mod_approval_zone.py`, `test_scenario_15_mod_auth_approval.py`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & Boundaries:
You have exclusive write ownership of `backend/mod_server.py` or `mod_server/`. DO NOT modify `frontend/src/` or `FC_can_bang/`.

Your Mission:
Build a complete, production-grade independent MOD (Ministry of Defense) Authorization Server running as a FastAPI application on port 9000.
1. Standalone Architecture:
   - Dedicated SQLite WAL database (`mod_database.sqlite3`).
   - CORS enabled for any origin (accessible across LAN and WAN per spec Section 7).
   - Can be run independently via `python3 -m uvicorn backend.mod_server:app --host 0.0.0.0 --port 9000` or standalone script.
2. Account & Registration Approval (Section 7.1):
   - Default admin account: username `admin_mod` (or `mod_admin`), password `ModAdmin2026!`, role `admin`.
   - Registration endpoint `POST /api/v1/mod/auth/register`:
     - Fields: username, email, full_name, password.
     - New registrations have status `pending`.
     - Login `POST /api/v1/mod/auth/login` is BLOCKED with 403 Forbidden until approved by MOD admin.
   - Admin user management:
     - `GET /api/v1/mod/admin/pending-users` (requires admin auth).
     - `POST /api/v1/mod/admin/approve-user` (approves or rejects).
3. Flight Permission Request & Approval Workflow (Section 7.2 & 7.3):
   - `POST /api/v1/mod/flight-requests`:
     - Receives: `drone_id`, `pilot_name`, `license_id`, `flight_date`, `time_from`, `time_to`, `latitude`, `longitude`, `timestamp`, `nonce`, `signature` (optional or validated).
     - Validates anti-replay: timestamp within +/- 300s, nonce not reused.
     - Stores flight request in state `pending`.
   - `GET /api/v1/mod/flight-requests`: lists flight requests with filter (`status`).
   - `POST /api/v1/mod/flight-requests/{id}/approve`:
     - Admin approves request.
     - Automatically generates a 1km circular geofence (32-point polygon) around `(latitude, longitude)`.
     - Sets status to `approved`, associates with `drone_id`, `valid_from = flight_date + time_from`, `valid_to = flight_date + time_to`.
   - `POST /api/v1/mod/flight-requests/{id}/reject`: marks request `rejected`.
   - `GET /api/v1/mod/flight-requests/{drone_id}/active`:
     - Pi5 queries this endpoint to check permission status.
     - Returns `{ "status": "approved" | "rejected" | "expired" | "none", "center_lat": float, "center_lon": float, "radius_m": 1000, "valid_from": str, "valid_to": str }`.
     - If current time > `valid_to`, automatically transitions status to `expired`.
4. No-Fly Zone Management (Section 7.2):
   - `GET /api/v1/mod/zones`: returns GeoJSON FeatureCollection of:
     * Active approved 1km flight zones (type: `approved_zone`, properties include `drone_id`, `valid_to`).
     * Permanent and temporary no-fly zones (type: `prohibited` or `restricted`).
   - `POST /api/v1/mod/zones`: add a new polygon no-fly zone (GeoJSON polygon).
   - `DELETE /api/v1/mod/zones/{id}`: delete a no-fly zone polygon.
5. Embedded Web Admin UI:
   - Provide clean, Blue-White styled HTML/JS admin dashboard served at `GET /` on port 9000:
     - Tab 1: Account Management & Pending Flight Requests (one-click Approve / Reject).
     - Tab 2: Map with No-Fly Zone drawing tool (Leaflet/MapLibre) and visualization of active 1km flight corridors.
6. Verification:
   - Test using `pytest` or direct HTTP requests.
   - Verify scenario 10, 11, 15, 16 using `python3 tests/ssh_test_runner.py --mode=bench`.
