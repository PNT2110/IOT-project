# BRIEFING — 2026-09-10T02:47:30+07:00

## Mission
Investigate and extract historical/legacy no-fly zone (vùng cấm bay) data across the entire IOT project and git history.

## 🔒 My Identity
- Archetype: explorer
- Roles: Legacy Zone Data Miner, Investigator, Synthesizer
- Working directory: c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_r2_1
- Original parent: 4778195a-e400-4dc6-9497-5cada5624654
- Milestone: Legacy Zone Data Survey & Extraction

## 🔒 Key Constraints
- Read-only investigation — do NOT modify project source code
- File Workspace Convention: only write within c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_r2_1

## Current Parent
- Conversation ID: 4778195a-e400-4dc6-9497-5cada5624654
- Updated: 2026-09-10T02:47:30+07:00

## Investigation State
- **Explored paths**:
  - `c:\Users\pnt21\OneDrive\Máy tính\IOT` (all files, tests, backend, frontend, deploy, scripts)
  - `backend/data/zones.geojson`
  - `backend/app/zone_sync.py`
  - `backend/app/geofence.py`
  - `frontend/src/App.tsx`
  - `backend/data/drone.sqlite3`
  - All logical drives (`C:`, `D:`, `F:`, `G:`) and user directories (`Downloads`, `Documents`, `OneDrive`)
  - Remote Raspberry Pi 5 (`192.168.1.118`) via SSH (`/home/pi5`, `/home/pi5/iot-drone`, `/var/lib/iot-drone`)
  - Antigravity session databases (`C:\Users\pnt21\.gemini\antigravity\conversations\*.db`)
- **Key findings**:
  - Definitive historical/legacy dataset is `backend/data/zones.geojson` (8.2 MB, SHA256: `a06204a4a2f6b92ebc0e2bfa32b8fe9740987cc209ab9b30f8f461ba857fdc0e`).
  - No Git repository exists in the project (`.git` was never initialized).
  - Data structure: 2,745 features (2,378 prohibited, 367 restricted), 195,143 vertices.
  - Coordinate order: GeoJSON RFC 7946 standard `[longitude, latitude]` in WGS 84.
  - Properties: `id`, `layer_id` (1 or 2), `zone_type` (`prohibited` or `restricted`), `source` (`https://cambay.mod.gov.vn`). No altitude bounds, no textual names.
  - Pi deployment has identical `zones.geojson`.
  - Pytest test suite verified: 78 passed, 1 skipped.
- **Unexplored areas**: None within survey scope.

## Key Decisions Made
- Confirmed `backend/data/zones.geojson` is the definitive legacy dataset.
- Completed comprehensive analysis report `report.md` and 5-component handoff `handoff.md`.

## Artifact Index
- `DISPATCH.md` — Initial dispatch message
- `progress.md` — Liveness heartbeat and status checklist (COMPLETE)
- `report.md` — Detailed historical zone data mining and analysis report
- `handoff.md` — 5-component handoff report for orchestrator
