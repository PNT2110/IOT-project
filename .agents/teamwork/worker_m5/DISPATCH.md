# Dispatch: worker_m5

## Role
Worker for Milestone 5 Phase 1 (100% E2E Test Suite Pass across Tiers 1–4).

## Context
Explorers 1, 2, and 3 have mapped the entire E2E test suite:
- Tier 1: 18/18 PASSED (100%)
- Tier 2: 18/18 PASSED (100%)
- Tier 3: 3 passed, 3 failed due to test database fixtures and SQLAlchemy API syntax
- Tier 4: 2 passed, 1 failed due to missing non-null columns in `SimulatedFlightRequest`

## Authoritative Files to Read
- `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\pnt21\Desktop\IOT\PROJECT.md`
- `c:\Users\pnt21\Desktop\IOT\TEST_READY.md`
- `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_m5_1\handoff.md`
- `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_m5_2\handoff.md`
- `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_m5_3\handoff.md`
- `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\explorer_m5_3\proposed_tier4_fixes.patch`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## File Ownership
You exclusively own:
- `tests/e2e/test_tier3_cross_feature.py`
- `tests/e2e/test_tier4_scenarios.py`
- `server/app/models.py`
- `server/app/routers/deps.py`

## Instructions
1. In `server/app/models.py`:
   - On `SimulatedFlightRequest`, set default values: `scheduled_start_at` (`default=utcnow`), `scheduled_end_at` (`default=utcnow`), `simulated_geometry_json` (`default="null"`).
   - On `Zone`, ensure `updated_at` has `default=utcnow`.
2. In `server/app/routers/deps.py`:
   - Ensure `_flight_view` and `_iso` gracefully handle potential null/empty dates and geometry.
3. In `tests/e2e/test_tier3_cross_feature.py`:
   - Import `select` from `sqlalchemy` and `ZoneSource` from `server.app.models`.
   - In Test 1 (`test_combination_flight_submission_triggers_operator_notification`): replace `db.select(User)` with `select(User)`, provide `scheduled_start_at=now`, `scheduled_end_at=now`, `simulated_geometry_json="null"`.
   - In Test 3 (`test_combination_zone_creation_to_geojson_export`): create `ZoneSource(id="local_e2e", ...)` before creating `Zone`, and provide `updated_at=now`.
   - In Test 4 (`test_combination_flight_lifecycle_to_csv_export`): provide `scheduled_start_at=now`, `scheduled_end_at=now`, `simulated_geometry_json="null"`.
4. In `tests/e2e/test_tier4_scenarios.py`:
   - In `test_scenario_1_complete_mission_workflow` (lines 74–85): explicitly supply `scheduled_start_at=now`, `scheduled_end_at=now`, `simulated_geometry_json="null"`.
5. Run full E2E verification:
   - `pytest tests/e2e/test_tier1_feature_coverage.py -v` (18 passed)
   - `pytest tests/e2e/test_tier2_boundary_corner.py -v` (18 passed)
   - `pytest tests/e2e/test_tier3_cross_feature.py -v` (6 passed)
   - `pytest tests/e2e/test_tier4_scenarios.py -v` (3 passed)
   - `pytest tests/e2e/ -v` (All 45 passed!)
6. Run regression test suites:
   - `pytest tests/scope01 tests/scope02 tests/scope03 tests/scope04 tests/scope05 tests/scope06 tests/scope07 tests/firmware -q` (all passed)
   - `cmd /c npm --prefix frontend run typecheck` (0 errors)
   - `cmd /c npm --prefix frontend run build` (0 errors)

## Deliverable
Write your completion report in:
`c:\Users\pnt21\Desktop\IOT\.agents\teamwork\worker_m5\handoff.md`
Update `progress.md` in your directory.
Send a completion message back to parent orchestrator (`3be5ec9a-8b7d-4356-b0b8-0a206dabba81`).
