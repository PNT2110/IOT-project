# DISPATCH — Reviewer R6-1 (Camera, Map, and Login UI)

## Working Directory
/home/pnt/IOT/.agents/reviewer_r6_1

## Mandatory References
1. Original request: `/home/pnt/IOT/.agents/ORIGINAL_REQUEST.md` (section `## 2026-09-14T05:07:21Z`)
2. Worker handoff report: `/home/pnt/IOT/.agents/worker_r6_1/handoff.md`
3. Project Architecture: `/home/pnt/IOT/PROJECT.md`

## Task
Perform thorough independent review and verification of:
1. **R1: Camera & Map**:
   - Inspect `backend/app/camera.py`: CameraService singleton, OpenCV/V4L2 CSI/USB capture, background daemon, synthetic HUD fallback with valid JPEG SOI/EOI, thread safety.
   - Inspect `backend/app/main.py`: camera endpoints (`/stream`, `/status`, `/snapshot`), auth handling (cookie, token query param, header), CSP headers allowing OpenStreetMap tiles, `map_ready: True`.
   - Inspect `frontend/src/CameraTab.tsx`: removal of `crossOrigin`, removal of broken DOM `onLoad` watchdog, backend status polling for FPS, snapshot download.
   - Inspect `frontend/src/MapTab.tsx`: OpenStreetMap raster tiles, removal of `map_ready` gate, container resizing.
   - Inspect deploy permissions (`iot-drone.service`, `install_pi.sh`).
2. **R4: Login UI**:
   - Inspect `frontend/src/App.tsx`: label changed to "Tên đăng nhập:", placeholder to "tên đăng nhập".

## Verification Commands
Run builds and tests:
- `cd /home/pnt/IOT/frontend && npm run build`
- `cd /home/pnt/IOT/backend && PYTHONPATH=. /home/pnt/miniconda3/envs/antidrone/bin/pytest tests/test_api.py -v`
- `cd /home/pnt/IOT && PYTHONPATH=. /home/pnt/miniconda3/envs/antidrone/bin/python tests/test_scenario_07_camera.py`

Write your comprehensive review to `/home/pnt/IOT/.agents/reviewer_r6_1/handoff.md` with a clear verdict: `APPROVE` or `REQUEST_CHANGES`. Send a completion message to parent when done.

## 2026-09-14T05:29:06Z
Independently review and verify:
1. R1: CameraService in backend/app/camera.py, stream/status/snapshot routes in backend/app/main.py, CSP headers allowing OpenStreetMap, map_ready: True, frontend CameraTab.tsx (crossOrigin removal, backend status FPS, snapshot), MapTab.tsx (OSM raster tiles, container resizing).
2. R4: Login UI text update in frontend/src/App.tsx ("Tên đăng nhập:").
Run verification tests (frontend build, backend pytest on api/camera).
Write your final review to /home/pnt/IOT/.agents/reviewer_r6_1/handoff.md with a clear verdict: APPROVE or REQUEST_CHANGES. Send a completion message to parent when done.

