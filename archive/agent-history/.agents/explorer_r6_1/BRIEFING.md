# BRIEFING — 2026-09-14T05:14:00Z

## Mission
Investigate Requirement R1: Camera Stream (OpenCV/v4l2, CSI/USB camera, FastAPI streaming, frontend Camera tab) and Admin Map (MapLibre GL, tile sources, CSS/container sizing, blank screen fixes).

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: /home/pnt/IOT/.agents/explorer_r6_1
- Original parent: 4c855de6-0522-4b87-a2f3-957fdcc3bfbb
- Milestone: R6-1 / Requirement R1 (Camera & Map)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Do NOT write source code (only write to .agents/explorer_r6_1/)
- Handoff Protocol required: 5-component report in handoff.md
- Send completion message to parent when done

## Current Parent
- Conversation ID: 4c855de6-0522-4b87-a2f3-957fdcc3bfbb
- Updated: 2026-09-14T05:09:01Z

## Investigation State
- **Explored paths**:
  - `backend/app/main.py` (routes `/api/v1/camera/stream`, `/api/v1/camera/status`, `/api/v1/status`, `/api/v1/map-pack/*`, `/api/v1/map/satellite/*`, `/api/v1/geofence/zones`, CSP security headers)
  - `backend/app/config.py` (`map_path`, `satellite_configured`)
  - `backend/app/auth.py` (`session_user`, cookie vs query auth)
  - `backend/requirements.txt` (missing OpenCV)
  - `frontend/src/CameraTab.tsx` (img tag, crossOrigin="anonymous", watchdog bug)
  - `frontend/src/MapTab.tsx` (Protomaps vector tiles, status.map_ready check, blank screen)
  - `frontend/src/styles.css` (map container CSS)
  - `deploy/iot-drone.service` & `deploy/install_pi.sh` (missing video group)
  - `tests/test_scenario_07_camera.py`, `tests/test_api.py`, `tests/test_m2_auth_and_wifi.py`
- **Key findings**:
  - Camera: Hardcoded 1x1 dummy frame in backend; missing camera manager/OpenCV capture; V4L2 concurrency lock vulnerability; frontend `crossOrigin="anonymous"` strips auth cookies causing 401; frontend watchdog falsely resets FPS to 0 after 2s due to multipart onLoad misconception; systemd user lacks `video` group.
  - Map: Backend reports `map_ready=false` because `hcm.pmtiles` (8GB download) doesn't exist; frontend `MapTab` never renders `<div ref={container} />` when `!map_ready`; if bypassed, vector style requests 404 local fonts/sprites/pmtiles; backend CSP blocks external OSM tiles.
- **Unexplored areas**: None, full evidence chain established for both camera and map.

## Key Decisions Made
- Formulated comprehensive architectural plan for CameraManager singleton + MJPEG streaming response.
- Formulated raster OSM basemap switch + CSP update + tab resize trigger for MapLibre GL.

## Artifact Index
- /home/pnt/IOT/.agents/explorer_r6_1/DISPATCH.md — Dispatch instructions
- /home/pnt/IOT/.agents/explorer_r6_1/BRIEFING.md — Working memory
- /home/pnt/IOT/.agents/explorer_r6_1/progress.md — Liveness & progress tracker
- /home/pnt/IOT/.agents/explorer_r6_1/handoff.md — Final handoff report
