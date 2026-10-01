# DISPATCH — Explorer R6-1 (Camera & Map)

## Working Directory
/home/pnt/IOT/.agents/explorer_r6_1

## Task
You are Explorer R6-1. Investigate the codebase for Requirement R1:
1. **Camera Stream**:
   - Inspect current backend video stream implementation in `backend/` (FastAPI routes, video capture, OpenCV/v4l2, CSI/USB camera handling).
   - Inspect frontend Camera tab in `frontend/` (how video stream is displayed, video element/img tag, reconnect logic).
   - Identify why video stream might fail or not be displayed, and specify exact changes needed to provide a reliable OpenCV/v4l2 MJPEG or direct streaming endpoint on FastAPI and display on frontend.
2. **Admin Map**:
   - Inspect MapLibre GL integration in `frontend/` (Map tab, tile sources, style URLs, OSM tiles, offline fallbacks).
   - Identify why Map might display a blank white screen (e.g., missing CSS, invalid tile URL, WebGL context, style spec error).
   - Detail the exact tile source config and fix needed for reliable rendering.

## Requirements
- Read `/home/pnt/IOT/.agents/ORIGINAL_REQUEST.md` (section `## 2026-09-14T05:07:21Z`).
- Read `/home/pnt/IOT/PROJECT.md` and related source files.
- DO NOT modify source code. Produce an exhaustive analysis report with file paths, line numbers, and proposed implementation plan.
- Write your final report to `/home/pnt/IOT/.agents/explorer_r6_1/handoff.md`.
- Send completion message to parent when done.

## 2026-09-14T05:09:01Z
You are Explorer R6-1.
Your working directory is /home/pnt/IOT/.agents/explorer_r6_1.
Read your instructions in /home/pnt/IOT/.agents/explorer_r6_1/DISPATCH.md.
Also read /home/pnt/IOT/.agents/ORIGINAL_REQUEST.md (section ## 2026-09-14T05:07:21Z) and /home/pnt/IOT/PROJECT.md.

Task:
Investigate Requirement R1:
1. Camera Stream: Inspect backend video stream in backend/ (OpenCV/v4l2, CSI/USB camera support, FastAPI streaming response) and frontend Camera tab. Determine root causes of display issues and specify exact changes needed for reliable streaming.
2. Admin Map: Inspect frontend MapLibre GL implementation (Map tab, tile source, OSM/offline styling, container sizing/CSS). Determine root causes of blank white screen and specify exact tile source/style fixes needed.

DO NOT write source code. Write a comprehensive analysis and implementation plan to /home/pnt/IOT/.agents/explorer_r6_1/handoff.md following the Handoff Protocol. Send a completion message to parent when done.

