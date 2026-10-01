## 2026-09-09T19:51:32Z

You are Challenger 2 (API & Data Stress Challenger).
Your working directory is: c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\challenger_r2_2
Project root: c:\Users\pnt21\OneDrive\Máy tính\IOT

MANDATORY FIRST STEP:
Read c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\ORIGINAL_REQUEST.md (especially ## 2026-09-09T19:36:18Z).

CONTEXT & INPUT FILES:
1. `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\orchestrator_2\PROJECT.md`
2. `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\worker_impl_r2_1\handoff.md`
3. `backend/app/main.py`, `backend/data/drone.sqlite3`, `backend/data/zones.geojson`

TASK:
Adversarially stress-test API endpoints, database sync states, and frontend-backend interaction:
1. Test `/api/v1/geofence/zones`:
   - Verify response size, JSON parsing time, gzip transfer, and schema compliance.
   - Test behavior when `zones.geojson` is missing, empty, or unreadable (graceful fallback).
2. Test `/api/v1/preflight` and `geofence_sync_is_fresh`:
   - Test behavior with fresh timestamp, stale timestamp (>24h), corrupt timestamp, missing record in SQLite.
3. Test edge case properties in GeoJSON:
   - Verify frontend paint rules handle missing `layer_id`, string `layer_id`, missing `zone_type`, or custom zone types gracefully without crashing MapLibre.
4. Document all stress tests and results in:
   - `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\challenger_r2_2\report.md`
   - `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\challenger_r2_2\handoff.md`
   Must state your verdict: **APPROVE** or **REQUEST_CHANGES**.
5. Call `send_message` to your caller (parent) when complete.
