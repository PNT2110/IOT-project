## 2026-09-09T19:51:32Z
You are Challenger 1 (Geospatial & Boundary Challenger).
Your working directory is: c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\challenger_r2_1
Project root: c:\Users\pnt21\OneDrive\Máy tính\IOT

MANDATORY FIRST STEP:
Read c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\ORIGINAL_REQUEST.md (especially ## 2026-09-09T19:36:18Z).

CONTEXT & INPUT FILES:
1. `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\orchestrator_2\PROJECT.md`
2. `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\worker_impl_r2_1\handoff.md`
3. `backend/data/zones.geojson`, `backend/app/geofence.py`

TASK:
Adversarially stress-test the geospatial accuracy and boundary behavior of the zone dataset:
1. Write Python verification scripts to test:
   - Boundary coordinates across all 2,745 features: verify no invalid coordinates, no NaN/Inf, all rings closed (`coord[0] == coord[-1]`).
   - Coordinate bounding box check: verify all longitudes are within [106, 109] and latitudes [8, 12]. Assert NO coordinate inversion exists anywhere in the 195,143 vertices.
   - Point-in-polygon edge cases: test points directly on boundary, points strictly inside (e.g. Tan Son Nhat airport runway, Con Dao), points outside (e.g. Mekong Delta safe area), points far away (Hanoi, Greenwich).
   - Performance benchmark: measure `GeofenceEngine.evaluate()` execution time across representative points.
2. Report any anomalies, edge-case failures, or performance concerns.
3. Write your report in:
   - `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\challenger_r2_1\report.md`
   - `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\challenger_r2_1\handoff.md`
   Must state your verdict: **APPROVE** or **REQUEST_CHANGES**.
4. Call `send_message` to your caller (parent) when complete.
