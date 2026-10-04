# Milestone 2 & Milestone 3 Independent Reviewer 2 Report

- **Reviewer**: reviewer_m2_m3_2 (Code Reviewer 2: Milestone 2 & Milestone 3)
- **Roles**: reviewer, critic
- **Parent Conversation ID**: `3be5ec9a-8b7d-4356-b0b8-0a206dabba81`
- **Working Directory**: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\reviewer_m2_m3_2`
- **Date**: 2026-10-04T06:05:00Z
- **Verdict**: **APPROVE**

---

## Review Summary

**Verdict**: **APPROVE**

Milestone 2 (Server Backend APIs: Features 4–8) and Milestone 3 (Pi Gateway & UI Modernization: Features 9–11) have been subjected to an independent, adversarial second code review. All access controls, cryptographic boundaries, route registrations, ES module dependency structures, and regression suites were examined and stress-tested. Zero integrity violations, zero facades, and zero circular dependencies were found. All 266 scoped unit/integration tests and all 26 Tier 1/2 E2E tests for Features 4–11 pass cleanly.

---

## 1. Observation

### 1.1 Milestone 2 Source Code & Route Declarations
1. **Telemetry Ingestion (`server/app/routers/device.py`, lines 112–132)**:
   - Route `POST /api/v1/device/telemetry` validates envelopes via `_open(request, db, envelope)`.
   - `_open` (lines 26–45) loads `device = db.get(Device, envelope.device_id)`, checks `device.revoked_at`, decrypts `device.key_encrypted` with `decrypt_secret()`, invokes `open_sealed(key, envelope.model_dump(), now)` enforcing AES-256-GCM authentication and ±300s timestamp skew, and checks `request.app.state.device_nonces` for replay attacks within a 600-second TTL.
   - Telemetry payload is validated using `TelemetryPayload.model_validate(raw)` and stored into `request.app.state.latest_telemetry[device.id]` and `request.app.state.latest_telemetry["__latest__"]`.
2. **Telemetry Query & SSE Streaming (`server/app/routers/telemetry.py`, lines 16–64)**:
   - `GET /api/v1/telemetry/latest`: Requires authenticated user session via `_session(request, db)` (line 23). Returns 404 with `TELEMETRY_NOT_FOUND` if no sample is cached.
   - `GET /api/v1/telemetry/stream`: Returns SSE `StreamingResponse` with `media_type="text/event-stream"`, polling every 100ms and yielding event frames on new sequence numbers, breaking on client disconnect (`request.is_disconnected()`) or optional `limit`.
3. **Flight Notifications (`server/app/routers/flights.py`, lines 55–76)**:
   - `GET /api/v1/flight-requests/notifications` is defined BEFORE `@router.get("/flight-requests/{request_id}")` (line 132), preventing Starlette route shadowing.
   - Enforces RBAC via `_require_workflow_reviewer(request, db)` (line 58), which verifies `user.status == "ACTIVE"` and `user.role in {"OPERATOR", "ADMIN", "OWNER"}`.
   - Queries `SimulatedFlightRequest` where `status == "SUBMITTED"`.
4. **Flight History CSV Export (`server/app/routers/flights.py`, lines 79–129)**:
   - `GET /api/v1/flight-requests/export/csv` is defined BEFORE `@router.get("/flight-requests/{request_id}")`.
   - Requires `_require_workflow_reviewer(request, db)`.
   - Generates RFC 4180 CSV with CRLF line terminators (`lineterminator="\r\n"`), decrypting `request_details_ciphertext` via `decrypt_secret(settings.session_secret, ...)`.
   - Returns `media_type="text/csv; charset=utf-8"` with `Content-Disposition: attachment; filename="flight_history.csv"`.
5. **Zone GeoJSON Export (`server/app/routers/zones.py`, lines 154–205)**:
   - `GET /api/v1/zones/export/geojson`: Filters out deleted zones (`Zone.deleted_at.is_(None)`).
   - Validates user session; non-reviewers are restricted to `visibility == "PUBLIC"`.
   - Emits RFC 7946 `FeatureCollection` with `media_type="application/geo+json"` and `Content-Disposition: attachment; filename="zones.geojson"`.

### 1.2 Milestone 3 Pi Local UI Modularization & Gateway Features
1. **ES Module Topology (`edge/pi5/pi5/web/ui/`)**:
   - `core/dom.js`: 0 imports. Pure DOM helpers (`h`, `banner`, `form`, `field`, `modal`, `closeModal`).
   - `core/api.js`: 0 imports. API client, screen lifecycle (`clearScreen`, `every`, `addCleanup`), and session state (`getMe`, `setMe`).
   - `views/` modules (`camera.js`, `wifi.js`, `auth.js`, `map.js`, `telemetry.js`, `users.js`, `firmware.js`, `flight.js`): Import strictly from `../core/dom.js` and `../core/api.js`. Zero cross-imports between view files.
   - `app.js`: Imports `core/dom.js`, `core/api.js`, and the view modules.
   - Result: Strict DAG hierarchy (`app.js` -> `views/*` -> `core/*`) with zero circular dependencies.
2. **Camera Stream Disconnect (`edge/pi5/pi5/web/ui/views/camera.js`, `edge/pi5/pi5/web/camera.py`, `edge/pi5/pi5/web/extra_routes.py`)**:
   - `views/camera.js`: "Tạm dừng" button sets `image.src = ""` and updates chip to `TẠM DỪNG`. `addCleanup` also clears `image.src = ""`.
   - `extra_routes.py`: Generator in `GET /api/pi/v1/camera/mjpeg` wraps iteration in `try...finally: state.camera.disconnect_consumer()`.
   - `camera.py`: `V4L2CameraAdapter.disconnect_consumer()` and `MockCameraAdapter.disconnect_consumer()` decrement consumer counts; when consumer count reaches 0, the capture process is stopped.
3. **Local OTA Upload (`edge/pi5/pi5/web/extra_routes.py`, `firmware.py`, `views/firmware.js`)**:
   - `extra_routes.py` (lines 278–336): `POST /api/pi/v1/firmware/upload` handles multipart form data and raw binary streams.
   - `firmware.py` (lines 227–293): Enforces ESP32 magic byte `0xe9` (`INVALID_MAGIC_BYTE`), size <= 4MB (`PAYLOAD_TOO_LARGE`), non-empty (`EMPTY_FILE`), and disarmed state (`DRONE_ARMED`). Pauses serial link before flashing and resumes in `finally`.
   - `views/firmware.js`: Renders file input, size validation, confirmation prompt, progress banner, and SHA-256 verification indicator.

### 1.3 Independent Test Verification Runs
- `pytest tests/test_milestone2_server.py tests/scope05/ -v`: **56 passed in 11.14s**.
- `pytest tests/scope01/ tests/scope02/ tests/scope03/ tests/scope04/ tests/scope07/ -q`: **176 passed in 73.72s**.
- `pytest tests/scope06/ -v`: **32 passed in 4.02s**.
- `pytest tests/firmware/ -v`: **2 passed in 1.40s**.
- `pytest tests/e2e/test_tier1_feature_coverage.py -k "feature_04 or feature_05 or feature_06 or feature_07 or feature_08 or feature_09 or feature_10 or feature_11" -v`: **8 passed, 10 deselected in 2.15s**.
- `pytest tests/e2e/test_tier2_boundary_corner.py -v`: **18 passed in 5.48s**.
- `node --check` on all 11 JavaScript ES modules: **exit code 0 (no syntax errors)**.

---

## 2. Logic Chain

1. **Integrity Violation Analysis**:
   - Observed that all new routes in `server/app/routers/` execute genuine database queries using SQLAlchemy ORM (`select(SimulatedFlightRequest)`, `select(Zone)`), evaluate live request contexts, perform real AES-256-GCM authenticated decryption (`open_sealed()`), and invoke Argon2 / session verification (`_session()`, `_require_workflow_reviewer()`).
   - Observed that all Pi gateway routes and UI components interact with real DOM nodes, actual camera streaming generators, and true binary header checks (`0xe9`).
   - Inference: No dummy implementations, hardcoded return fixtures, or integrity shortcuts exist.

2. **Access Control & RBAC Verification**:
   - Flight notifications (`GET /flight-requests/notifications`) and CSV export (`GET /flight-requests/export/csv`) invoke `_require_workflow_reviewer(request, db)`.
   - `deps.py` line 339 asserts `user.status == "ACTIVE" and user.role in {"OPERATOR", "ADMIN", "OWNER"}`.
   - Normal authenticated users (such as `PILOT`) are rejected with HTTP 403 `FORBIDDEN`. Unauthenticated callers receive HTTP 401 `AUTH_REQUIRED`.
   - Telemetry query (`GET /telemetry/latest`) invokes `_session(request, db)`, rejecting unauthenticated callers with HTTP 401.
   - Ingestion (`POST /device/telemetry`) authenticates via sealed envelope AES-256-GCM key derivation from device secrets, rejecting tampered payloads, clock skew >300s, and replayed nonces.
   - Inference: All access controls satisfy zero-trust security requirements without bypass vectors.

3. **Route Precedence & Absence of Route Shadowing**:
   - In FastAPI/Starlette, routes are evaluated in registration order. A parameterized route like `/{request_id}` placed before `/notifications` would match `"notifications"` as a parameter ID and return 404.
   - Observations confirm `/flight-requests/notifications` and `/flight-requests/export/csv` are registered at lines 55 and 79, whereas `/{request_id}` is registered at line 132.
   - Inference: Route ordering is strictly correct and immune to shadowing.

4. **ES Module Architectural Integrity**:
   - Static analysis of import paths across `edge/pi5/pi5/web/ui/` reveals a strict two-layer DAG:
     - Layer 0 (Foundation): `core/dom.js` (0 imports), `core/api.js` (0 imports).
     - Layer 1 (Views): `views/*.js` (import only from `core/*`).
     - Layer 2 (Application Bootstrap): `app.js` (imports from `core/*` and `views/*`).
   - Inference: The dependency graph contains zero cycles, is completely modular, and passes native browser ES module resolution.

5. **Camera Stream Resource Conservation**:
   - When a user pauses or navigates away, the client sets `image.src = ""`.
   - The browser closes the HTTP request stream.
   - The streaming generator in `extra_routes.py` catches disconnection and triggers the `finally` block, calling `disconnect_consumer()`.
   - `disconnect_consumer()` terminates the `MjpegStreamer` capture process when active consumers drop to zero.
   - Inference: Prevents network bandwidth and Pi CPU exhaustion.

6. **Regression Invariance**:
   - 266 scoped unit/integration tests spanning scopes 01 through 07, firmware, and Milestone 2 pass without failure.
   - Inference: Milestone 2 and Milestone 3 changes caused zero regressions in existing system capabilities.

---

## 3. Caveats

- **Milestone 4 Pending Implementation**: In the opaque-box test runner `tests/e2e/test_tier1_feature_coverage.py`, tests for Features 12–17 failed as expected because Milestone 4 (PC Frontend UI/UX) is assigned to worker_m4 and has not yet been implemented. All Milestone 2 and 3 features (Features 4–11) passed 100%.
- **Physical Hardware in Test Environments**: ESP32 hardware flashing (`esptool` writing to `/dev/ttyUSB0`) is mocked/bracketed during virtual automated test execution, while all link pause/resume bracketing, magic byte checks, and checksum logic are tested directly.
- **No other caveats**: The implementation is genuine, clean, and complete.

---

## 4. Conclusion

- Milestone 2 (Server Backend APIs: Sealed Telemetry Ingestion, Live Telemetry Query/SSE Stream, Flight Request Notifications, RFC 7946 GeoJSON Export, RFC 4180 CSV Export) is **CORRECT**, **SECURE**, and **VERIFIED**.
- Milestone 3 (Pi 5 Gateway & Local UI Modernization: Modular ES Components, Camera Stream Pause/Resume with Consumer Disconnect Tracking, Local OTA Firmware Upload Endpoint & UI) is **CORRECT**, **MODULAR**, and **VERIFIED**.
- Zero regressions across `tests/scope01` through `tests/scope07`.
- Zero integrity violations detected.
- **Final Verdict**: **APPROVE**.

---

## 5. Verification Method

To independently verify this evaluation, execute the following commands in powershell:

### 5.1 Validate JavaScript ES Module Syntax
```powershell
node --check edge/pi5/pi5/web/ui/core/dom.js edge/pi5/pi5/web/ui/core/api.js edge/pi5/pi5/web/ui/views/wifi.js edge/pi5/pi5/web/ui/views/auth.js edge/pi5/pi5/web/ui/views/camera.js edge/pi5/pi5/web/ui/views/map.js edge/pi5/pi5/web/ui/views/telemetry.js edge/pi5/pi5/web/ui/views/users.js edge/pi5/pi5/web/ui/views/firmware.js edge/pi5/pi5/web/ui/views/flight.js edge/pi5/pi5/web/ui/app.js
```
*Expected*: Exit code 0, no syntax errors.

### 5.2 Execute Milestone 2 & Scope 05 Test Suites
```powershell
pytest tests/test_milestone2_server.py tests/scope05/ -v
```
*Expected*: `56 passed in ~11s`.

### 5.3 Execute Full Regression Suites (Scopes 01–04, 06, 07 & Firmware)
```powershell
pytest tests/scope01/ tests/scope02/ tests/scope03/ tests/scope04/ tests/scope06/ tests/scope07/ tests/firmware/ -q
```
*Expected*: `210 passed in ~80s`.

### 5.4 Execute Milestone 2 & 3 Tier 1 and Tier 2 E2E Tests
```powershell
pytest tests/e2e/test_tier1_feature_coverage.py -k "feature_04 or feature_05 or feature_06 or feature_07 or feature_08 or feature_09 or feature_10 or feature_11" -v
pytest tests/e2e/test_tier2_boundary_corner.py -v
```
*Expected*: All 8 Tier 1 tests and all 18 Tier 2 tests pass.
