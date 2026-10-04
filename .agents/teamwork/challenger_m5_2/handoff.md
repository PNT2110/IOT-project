# Milestone 5 Phase 1 Adversarial Verification Report

**Agent**: `challenger_m5_2`  
**Role**: Challenger 2 (Adversarial Tester) for Milestone 5 Phase 1  
**Parent Orchestrator ID**: `3be5ec9a-8b7d-4356-b0b8-0a206dabba81`  
**Timestamp**: 2026-10-04T01:08:00Z  
**Verdict**: **APPROVE**  
**Handoff Type**: Hard Handoff (Verification Complete)

---

## 1. Observation

### 1.1 Verification of Worker Claims & Test Execution
All baseline verification commands were independently executed with the following verbatim results:

1. **Full E2E Test Suite**:
   - Command: `pytest tests/e2e/ -v`
   - Output:
     ```text
     collected 45 items
     tests/e2e/test_tier1_feature_coverage.py (18 passed)
     tests/e2e/test_tier2_boundary_corner.py (18 passed)
     tests/e2e/test_tier3_cross_feature.py (6 passed)
     tests/e2e/test_tier4_scenarios.py (3 passed)
     ============================= 45 passed in 12.15s =============================
     ```

2. **Standalone E2E Test Runner CLI**:
   - Command: `python -m tests.e2e.test_runner`
   - Output:
     ```text
     === Running E2E Test Suite [Tier: all] ===
     ============================= 45 passed in 14.58s =============================
     ```

3. **Complete Regression Test Suites**:
   - Command: `pytest tests/scope01 tests/scope02 tests/scope03 tests/scope04 tests/scope05 tests/scope06 tests/scope07 tests/firmware -q`
   - Output:
     ```text
     ........................................................................ [ 28%]
     ........................................................................ [ 57%]
     ........................................................................ [ 85%]
     ....................................                                     [100%]
     252 passed in 100.18s (0:01:40)
     ```

4. **Frontend TypeScript Typecheck**:
   - Command: `cmd /c npm --prefix frontend run typecheck`
   - Output:
     ```text
     > iot-research-pc-foundation-ui@0.1.0 typecheck
     > tsc --noEmit
     ```
   - Exit code: 0 (0 errors).

5. **Frontend Production Build**:
   - Command: `cmd /c npm --prefix frontend run build`
   - Output:
     ```text
     > iot-research-pc-foundation-ui@0.1.0 build
     > tsc -b && vite build
     ✓ 96 modules transformed.
     ✓ built in 8.36s
     ```
   - Exit code: 0.

### 1.2 Adversarial Probing & Stress Suite (`tests/test_m5_challenger2_empirical.py`)
To probe the attack surface specified in dispatch, 17 adversarial empirical tests were created and executed (`pytest tests/test_m5_challenger2_empirical.py -v`). All 17 passed in 14.85s (and 62 passed in 26.36s when run together with `tests/e2e/`):

1. **Database Schema & Constraints (`server/app/models.py`)**:
   - `Zone.updated_at`:
     - Omission in constructor: SQLAlchemy ORM `default=utcnow` assigns a valid UTC timestamp within <5s of current time.
     - ORM `default=utcnow` intercepts explicit `updated_at=None` during model instantiation, providing defense-in-depth against accidental null injection.
     - SQLite DDL enforcement: Bypassing ORM defaults via direct table insert (`insert(Zone.__table__).values(..., updated_at=None)`) triggers `sqlite3.IntegrityError: NOT NULL constraint failed: zones.updated_at`.
     - Timestamp fidelity: Correctly handles microsecond resolution (`987654 us`) and epoch boundaries (1970 to 2099).
   - `SimulatedFlightRequest`:
     - `scheduled_start_at` and `scheduled_end_at`: ORM `default=utcnow` assigns valid timestamps on omission.
     - Direct SQL insert with `NULL` is rejected: `NOT NULL constraint failed: simulated_flight_requests.scheduled_start_at`.
     - `simulated_geometry_json`: Defaults to `"null"`. Direct SQL insert with `NULL` is rejected: `NOT NULL constraint failed: simulated_flight_requests.simulated_geometry_json`.
     - Check constraints: `ck_simulated_request_flag` correctly rejects `simulated=False`; `ck_simulated_request_status` rejects illegal status strings.

2. **Router Helpers Robustness (`server/app/routers/deps.py`)**:
   - `_iso(value)`:
     - `_iso(None)` cleanly returns `None`.
     - Correctly handles naive datetimes, UTC datetimes, positive timezone offsets (`+07:00`), and negative offsets (`-05:00`), normalizing all to ISO UTC (`+00:00`).
     - Preserves microsecond resolution (`2026-10-04T10:30:00.123456+00:00`).
   - `_flight_view(item)`:
     - Safely returns `scheduled_start_at=None` and `scheduled_end_at=None` when item dates are `None`.
     - Safely returns `geometry=None` when `simulated_geometry_json` is `"null"`, `""`, or `None`.
     - Correctly parses valid GeoJSON geometry objects into Python dicts.
     - Gracefully degrades when `request_details_ciphertext` is corrupted or undecryptable: returns `{"error": "DETAILS_UNAVAILABLE"}` without raising unhandled exceptions.

3. **Flakiness & Race Conditions in E2E Suite**:
   - No `time.sleep` calls exist in `tests/e2e/` (0 matches for `sleep`).
   - Each test using `app_env` runs against an isolated SQLite file in `tmp_path`.
   - Repeated sequential runs (3x loop of Tier 4 scenarios, individual tier runs `--tier 3` and `--tier 4`) yielded 100% pass with 0 intermittent failures.

---

## 2. Logic Chain

1. **Verification of Baseline**: Observation §1.1 confirms that worker_m5's claims of 45/45 E2E tests passing, 252/252 regression tests passing, clean typecheck, and clean Vite production build are accurate and fully reproducible on this system.
2. **Database Integrity**: The worker added `default=utcnow` to `Zone.updated_at`, `SimulatedFlightRequest.scheduled_start_at/end_at`, and `default="null"` to `simulated_geometry_json` in `server/app/models.py`. Observation §1.2 confirms that this fix is sound:
   - When test fixtures omit these fields, ORM defaults prevent SQL-level NOT NULL errors.
   - When raw SQL inserts attempt to bypass ORM defaults, SQLite DDL constraints immediately reject `NULL` values. Relational integrity is strictly preserved.
3. **Serialization Robustness**: Observation §1.2 confirms that `deps._iso` and `deps._flight_view` handle edge cases (None dates, "null" geometry, corrupted ciphertext, timezone conversions) without crashing.
4. **Test Suite Stability**: Because test fixtures use per-test `tmp_path` SQLite files and ASGI in-memory TestClients without hardcoded network ports or unbracketed sleep calls, all 45 E2E tests are deterministic, non-flaky, and free from race conditions (confirmed by Observation §1.2 Suite 4).
5. **Zero Regressions**: No existing functionality was broken across Scope 01–07 or firmware tests (252 passed).

---

## 3. Caveats

1. **`simulated_geometry_json` Corrupted String Handling**:
   - In `deps._flight_view`, `geometry` is parsed as `json.loads(item.simulated_geometry_json) if item.simulated_geometry_json else None`.
   - If a database record were to contain invalid JSON (e.g. `"{broken"`), `_flight_view` would raise `json.JSONDecodeError` because unlike `request_details_ciphertext`, `geometry` does not have a `try/except` guard.
   - However, in all application ingestion paths (`/api/v1/flight-requests` and `/api/v1/device/flight-requests`), geometry is generated server-side using `json.dumps()` from validated coordinates or set to `"null"`. Thus, invalid JSON cannot enter via public or device APIs. A `try/except` could be added in a future hardening phase as defense-in-depth against direct database corruption.
2. **Mock Hardware**:
   - Camera and serial link interactions in E2E tests use `MockCameraAdapter` and mock firmware protocols rather than physical Raspberry Pi 5 camera ribbons and hardware UARTs.

---

## 4. Conclusion

The Milestone 5 Phase 1 deliverables meet all specified requirements:
- **E2E Test Suite**: 45 / 45 tests passing across all 4 tiers (100%).
- **CLI Test Runner**: Fully operational with individual tier flags (`--tier 1..4`, `--tier all`).
- **Regression Suite**: 252 / 252 tests passing (0 regressions).
- **Frontend**: Clean TypeScript compilation (`tsc --noEmit`), clean production Vite build.
- **Adversarial Resilience**: Models and helpers withstand boundary timestamps, missing dates, "null" geometries, and corrupted ciphertexts.
- **Verdict**: **APPROVE**.

---

## 5. Verification Method

To independently verify this report:

1. **Run Full E2E Test Suite**:
   ```powershell
   pytest tests/e2e/ -v
   ```
   *Expected*: `45 passed` (exit code 0).

2. **Run E2E Standalone Test Runner**:
   ```powershell
   python -m tests.e2e.test_runner
   ```
   *Expected*: `45 passed` (exit code 0).

3. **Run Challenger Adversarial Suite**:
   ```powershell
   pytest tests/test_m5_challenger2_empirical.py -v
   ```
   *Expected*: `17 passed` (exit code 0).

4. **Run Regression Suites**:
   ```powershell
   pytest tests/scope01 tests/scope02 tests/scope03 tests/scope04 tests/scope05 tests/scope06 tests/scope07 tests/firmware -q
   ```
   *Expected*: `252 passed` (exit code 0).

5. **Run Frontend Typecheck & Build**:
   ```powershell
   cmd /c npm --prefix frontend run typecheck
   cmd /c npm --prefix frontend run build
   ```
   *Expected*: 0 errors, build exit code 0.

6. **Invalidation Conditions**:
   - Any failure in `tests/e2e/` or `tests/test_m5_challenger2_empirical.py`.
   - Any failure in regression suites `tests/scope01`–`tests/scope07` or `tests/firmware`.
   - Any failure in `frontend` typecheck or build.
