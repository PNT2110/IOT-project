# Plan: Legacy No-Fly Zone Data Extraction and Map Visualization Update

## Objective
Identify legacy no-fly zone (vùng cấm bay) data in the IOT project (JSON, GeoJSON, Python/JS source, or old git history/backup files), extract and convert the polygons and properties, update `backend/data/zones.geojson` (and backend geofence logic if needed), and adjust the frontend (`App.tsx`) MapLibre visualization so that prohibited and restricted zones render identically in shape, coordinates, and styling to the original design, ensuring 100% test pass on backend pytest and successful frontend build.

## Phase 0: Survey & Discovery
1. Spawn 3 Explorers:
   - Explorer 1 (`survey_1`): Scan entire workspace (including root, docs, backup, git commits/stashes, other directories, old files) to locate any historical/legacy no-fly zone data files or embedded coordinates (e.g. prohibited, restricted zones, lat/lng or lng/lat conventions, coordinates of airports, military areas, etc.).
   - Explorer 2 (`survey_2`): Analyze the current backend geofence implementation (`backend/data/zones.geojson`, `backend/app/services/geofence.py`, endpoints `/api/v1/geofence/zones`, tests in `backend/tests/test_geofence.py`) to understand current data expectations, validation, and APIs.
   - Explorer 3 (`survey_3`): Analyze current frontend implementation (`frontend/src/App.tsx`, MapLibre layers, map styling, coordinate system, colors for prohibited vs restricted) and determine what changes are needed to display identical old zones.
2. Synthesize findings into `PROJECT.md` at project root with Feature Inventory, Milestones, and Interface Contracts.

## Phase 1: Implementation & Iteration
1. Worker (`worker_impl_1`):
   - Convert old no-fly zone coordinates into standard GeoJSON with correct lng/lat ordering and property schema.
   - Update `backend/data/zones.geojson` and any backend data models/services.
   - Update `frontend/src/App.tsx` (and any related components/styles) to correctly render prohibited and restricted zones with matching styling.
   - Run backend test suite (`pytest`) and frontend build (`npm run build` or similar) to verify everything passes without regression.
2. Reviewers (`reviewer_1`, `reviewer_2`):
   - Review code quality, GeoJSON validity, coordinate integrity (lng/lat order, no inverted coordinates), API contracts, and visual styling fidelity.
3. Challengers (`challenger_1`, `challenger_2`):
   - Adversarially verify boundary checks, polygon containment, coordinate limits, API response schemas, and rendering consistency.
4. Forensic Auditor (`auditor_1`):
   - Conduct strict integrity audit verifying genuine implementation (no dummy mock bypasses or hardcoded test cheats).

## Phase 2: Final Verification & Reporting
1. Confirm all gates pass (Tests pass, Reviews APPROVE, Challenges pass, Auditor CLEAN).
2. Report final completion back to parent/sentinel.
