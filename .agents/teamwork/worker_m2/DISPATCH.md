# Dispatch Task: Milestone 2 — Server Backend APIs & Features

## Identity
- Role: Milestone 2 Worker
- TypeName: teamwork_preview_worker
- Working Directory: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m2
- Parent Conversation ID: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81

## Authoritative Requirements & References
- Requirements: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md` (R4.1, R4.2, R4.3)
- Project Spec: `c:\Users\pnt21\Desktop\IOT\PROJECT.md § Interface Contracts`
- Server Survey Report: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_2\handoff.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Exclusive Write Ownership
You exclusively own and may edit ONLY the following files:
1. `server/app/routers/device.py`
2. `server/app/routers/telemetry.py` (create if needed and mount in `server/app/main.py`)
3. `server/app/routers/flights.py`
4. `server/app/routers/zones.py`
5. `server/app/schemas.py`
6. `server/app/main.py`
7. New test files in `tests/test_milestone2_server.py` or `tests/scope08/`
DO NOT modify `mail.py`, `security.py`, or any files in `edge/` or `frontend/`.

## Detailed Tasks
1. **Feature 4: Telemetry Ingestion Endpoint (`POST /api/v1/device/telemetry`)**:
   - In `server/app/routers/device.py`, add `telemetry_ingest` endpoint receiving sealed `DeviceEnvelope` (AES-256-GCM).
   - Decrypts via existing `_open(request, db, envelope)`.
   - Payload schema: `{"device_id": str, "seq": int, "observed_at": str, "latitude": float, "longitude": float, "altitude_m": float, "battery_pct": float, "voltage_v": float, "fix_state": str, "stale": bool}`.
   - Stores the latest sample in memory `request.app.state.latest_telemetry[device.id] = payload`.
2. **Feature 5: Telemetry Query / Streaming Endpoint (`GET /api/v1/telemetry/latest`)**:
   - In `server/app/routers/telemetry.py` (mounted under `/api/v1/telemetry`), add `GET /api/v1/telemetry/latest?device_id=...`.
   - Requires authenticated user (`_get_current_account` or operator/reviewer).
   - Returns latest telemetry dict or 404 if no telemetry has been received yet.
   - Optionally provide SSE `/api/v1/telemetry/stream` endpoint for live push.
3. **Feature 6: Flight Request Notification Endpoint (`GET /api/v1/flight-requests/notifications`)**:
   - In `server/app/routers/flights.py`, add `GET /api/v1/flight-requests/notifications`.
   - Requires reviewer/operator role (`_require_workflow_reviewer` or authenticated account).
   - Queries `SimulatedFlightRequest` where `status == "SUBMITTED"`.
   - Returns `{"pending_count": int, "latest_request_id": str | None, "latest_submitted_at": str | None}`.
4. **Feature 7: Zone GeoJSON Export Endpoint (`GET /api/v1/zones/export/geojson`)**:
   - In `server/app/routers/zones.py`, add `GET /api/v1/zones/export/geojson`.
   - Queries active non-deleted zones (`deleted_at.is_(None)`).
   - Returns RFC 7946 compliant FeatureCollection with `media_type="application/geo+json"` and `Content-Disposition: attachment; filename="zones.geojson"`.
5. **Feature 8: Flight History CSV Export Endpoint (`GET /api/v1/flight-requests/export/csv`)**:
   - In `server/app/routers/flights.py`, add `GET /api/v1/flight-requests/export/csv`.
   - Requires reviewer role.
   - Queries flight requests, decrypts details with `decrypt_secret()`, generates RFC 4180 CSV with headers:
     `id,status,source,device_name,summary,applicant_name,license_code,vehicle,scheduled_start_at,scheduled_end_at,created_at,updated_at`.
   - Returns with `media_type="text/csv; charset=utf-8"` and `Content-Disposition: attachment; filename="flight_history.csv"`.

## Verification Requirements
- Write comprehensive tests in `tests/test_milestone2_server.py`.
- Run `pytest tests/test_milestone2_server.py`.
- Run E2E contract tests: `pytest tests/e2e/test_tier1_feature_coverage.py -k "telemetry or notification or export"`.
- Run regression tests: `pytest tests/scope01/ tests/scope02/ tests/scope03/`.
- Ensure all tests pass. Write report to `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m2\handoff.md`.


## 2026-10-03T22:10:54Z
You are worker_m2, the Milestone 2 Worker for Server Backend APIs & Features.
Your working directory is: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m2
The authoritative requirements are in: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md
The project specification is in: c:\Users\pnt21\Desktop\IOT\PROJECT.md
The server survey report is in: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_survey_2\handoff.md
Please read your dispatch instructions at: c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m2\DISPATCH.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

You exclusively own:
- server/app/routers/device.py (telemetry ingestion endpoint POST /api/v1/device/telemetry)
- server/app/routers/telemetry.py (telemetry query GET /api/v1/telemetry/latest and optional SSE)
- server/app/routers/flights.py (flight notifications GET /api/v1/flight-requests/notifications and CSV export GET /api/v1/flight-requests/export/csv)
- server/app/routers/zones.py (GeoJSON export GET /api/v1/zones/export/geojson)
- server/app/schemas.py (models)
- server/app/main.py (mounting routes)
- new backend tests in tests/test_milestone2_server.py or tests/

Implement all 5 endpoints per specifications and interface contracts in PROJECT.md.
Run tests with pytest. Verify E2E contract tests in tests/e2e/test_tier1_feature_coverage.py pass for features 4, 5, 6, 7, 8.
Write your handoff report to c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m2\handoff.md, update progress.md, and send a message back to parent orchestrator (conversation ID: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81).
