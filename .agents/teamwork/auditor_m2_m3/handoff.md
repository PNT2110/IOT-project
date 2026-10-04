# Forensic Audit Report: Milestone 2 & Milestone 3

**Work Product**: Milestone 2 (Server Backend APIs & Features) & Milestone 3 (Pi 5 Local UI & Features)  
**Profile**: General Project  
**Integrity Mode**: Development (from `ORIGINAL_REQUEST.md`)  
**Verdict**: CLEAN  

---

## 1. Observation

### 1.1 Forensic Check Phase Results
- **Hardcoded Output Detection**: PASS — No hardcoded test responses, fake bypasses, or static mocked payloads found in `device.py`, `telemetry.py`, `flights.py`, `zones.py`, `camera.py`, `extra_routes.py`, `firmware.py`, or UI modules.
- **Facade Detection**: PASS — Endpoints and modules execute authentic cryptographic validation (AES-256-GCM), database queries via SQLAlchemy, file I/O, and streaming generators.
- **Pre-populated Artifact Detection**: PASS — No stale result artifacts or pre-generated attestation logs present.
- **Self-certifying Test Detection**: PASS — Test suites construct dynamic data, encrypt envelopes, assert against actual error codes, and verify file and memory state.
- **Camera Stream Disconnect Authenticity**: PASS — `edge/pi5/pi5/web/ui/views/camera.js` (lines 41–42) sets `image.src = ""` and cleanup handler (lines 24–27) drops the connection. `edge/pi5/pi5/web/extra_routes.py` (lines 131–137) `finally` block invokes `state.camera.disconnect_consumer()`, which decrements `consumer_count` and stops the capture process (`V4L2CameraAdapter` and `MockCameraAdapter`). This is an authentic socket disconnect, not a CSS `display: none` trick.
- **OTA Firmware Upload Authenticity**: PASS — `edge/pi5/pi5/web/extra_routes.py` (lines 310–316) and `firmware.py` (lines 232–240) validate the ESP32 magic byte (`0xe9`), enforce the 4MB limit, reject when armed (`409 DRONE_ARMED`), write the binary and SHA-256 hash to disk, bracket the serial link (`link.pause()` and `link.resume()`), and invoke `esptool`.

### 1.2 Fresh Verification Evidence (Empirical Test Outputs)

#### Check 1: Milestone 2 Standalone Server Suite
Command: `pytest tests/test_milestone2_server.py -v`
```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
collected 14 items

tests/test_milestone2_server.py::test_telemetry_ingest_happy_path PASSED [  7%]
tests/test_milestone2_server.py::test_telemetry_ingest_replay_attack_rejected PASSED [ 14%]
tests/test_milestone2_server.py::test_telemetry_ingest_invalid_key_rejected PASSED [ 21%]
tests/test_milestone2_server.py::test_telemetry_query_latest_found PASSED [ 28%]
tests/test_milestone2_server.py::test_telemetry_query_latest_not_found PASSED [ 35%]
tests/test_milestone2_server.py::test_telemetry_query_unauthenticated PASSED [ 42%]
tests/test_milestone2_server.py::test_flight_request_notifications_flow PASSED [ 50%]
tests/test_milestone2_server.py::test_flight_request_notifications_rbac PASSED [ 57%]
tests/test_milestone2_server.py::test_zone_geojson_export PASSED         [ 64%]
tests/test_milestone2_server.py::test_flight_history_csv_export PASSED   [ 71%]
tests/test_milestone2_server.py::test_flight_history_csv_export_empty PASSED [ 78%]
tests/test_milestone2_server.py::test_zone_geojson_export_empty PASSED   [ 85%]
tests/test_milestone2_server.py::test_telemetry_sse_stream_endpoint PASSED [ 92%]
tests/test_milestone2_server.py::test_telemetry_ingest_extreme_coordinates PASSED [100%]

============================= 14 passed in 7.50s ==============================
```

#### Check 2: Milestone 3 OTA & Camera Suite
Command: `pytest tests/scope05/test_ota_and_camera.py -v`
```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
collected 7 items

tests/scope05/test_ota_and_camera.py::test_ota_upload_valid_binary_and_job_query PASSED [ 14%]
tests/scope05/test_ota_and_camera.py::test_ota_upload_raw_binary_octet_stream PASSED [ 28%]
tests/scope05/test_ota_and_camera.py::test_ota_upload_rejected_when_drone_armed PASSED [ 42%]
tests/scope05/test_ota_and_camera.py::test_ota_upload_rejected_invalid_magic_byte PASSED [ 57%]
tests/scope05/test_ota_and_camera.py::test_ota_upload_rejected_empty_payload PASSED [ 71%]
tests/scope05/test_ota_and_camera.py::test_ota_upload_rejected_oversized PASSED [ 85%]
tests/scope05/test_ota_and_camera.py::test_camera_consumer_disconnect_behavior PASSED [100%]

============================== 7 passed in 1.79s ==============================
```

#### Check 3: Pi Local UI ES Modules Syntax
Command: `node --check edge/pi5/pi5/web/ui/core/dom.js edge/pi5/pi5/web/ui/core/api.js edge/pi5/pi5/web/ui/views/wifi.js edge/pi5/pi5/web/ui/views/auth.js edge/pi5/pi5/web/ui/views/camera.js edge/pi5/pi5/web/ui/views/map.js edge/pi5/pi5/web/ui/views/telemetry.js edge/pi5/pi5/web/ui/views/users.js edge/pi5/pi5/web/ui/views/firmware.js edge/pi5/pi5/web/ui/views/flight.js edge/pi5/pi5/web/ui/app.js`
- Returncode: 0
- Output: 0 errors across all 11 modular JavaScript files.

#### Check 4: Pi Gateway & Firmware Regression Suites (Scope 04, Scope 05, Scope 07)
Commands and Results:
- `pytest tests/scope05/ -q`: `42 passed in 0.83s`
- `pytest tests/scope04/ -q`: `47 passed in 6.95s`
- `pytest tests/scope07/ -q`: `7 passed in 0.08s`

#### Check 5: E2E Tier 1 Features & Tier 2 Boundary Suites
- Tier 1 (Features 01–11, 18): `12 passed in 3.18s` (Features 04–08 for M2 and 09–11 for M3 passed without exception)
- Tier 2 (Boundary & Corner cases): `18 passed in 5.04s` (including extreme telemetry coords, tampered ciphertext, replay attacks, skew reject, empty notifications, unauth access, empty geojson, csv escaping, invalid magic byte, oversized binary, zero-byte file).

#### Check 6: Server Core Regression Suite
Command: `pytest tests/scope01/ tests/scope02/ tests/scope03/ tests/scope05/ tests/scope06/ tests/scope07/ -q`
```
........................................................................ [ 35%]
........................................................................ [ 70%]
...........................................................              [100%]
203 passed in 51.46s
```

---

## 2. Logic Chain

1. **Telemetry Security & Live Delivery (Feature 4 & 5)**:
   - `DeviceEnvelope` requires valid cryptographic signature / AES-256-GCM decryption using the shared device key.
   - `server/app/routers/device.py` invokes `_open(request, db, envelope)` which validates replay protection, timestamp tolerance (< 300s), and device active status.
   - Decrypted payloads populate `request.app.state.latest_telemetry`, allowing instantaneous retrieval by `/telemetry/latest` and streaming via SSE `/telemetry/stream` without database lock bottlenecks.
   - Tests prove invalid keys and repeated nonces are rejected with HTTP 401.

2. **Operator Notifications & History Export (Feature 6 & 8)**:
   - Route placement: `@router.get("/flight-requests/notifications")` and `/export/csv` are registered before `/{request_id}`, avoiding route parameter collision.
   - Notifications endpoint executes real database queries (`SimulatedFlightRequest.status == "SUBMITTED"`) and requires reviewer privileges (`_require_workflow_reviewer`).
   - CSV export decrypts `request_details_ciphertext` with `decrypt_secret()`, handles quotation and commas correctly, and writes RFC 4180 standard CSV headers and records.

3. **Airspace Zone GeoJSON Export (Feature 7)**:
   - `server/app/routers/zones.py` filters `Zone.deleted_at.is_(None)` and parses stored geometry into RFC 7946 GeoJSON Feature objects.
   - Soft-deleted zones and invalid geometries are properly excluded.

4. **Camera Stream Control (Feature 10)**:
   - The UI view in `views/camera.js` clears `image.src = ""` and registers lifecycle cleanups.
   - The server streaming generator terminates on client disconnection, and its `finally` block executes `disconnect_consumer()`.
   - `camera.py` decreases active consumers and halts underlying `v4l2-ctl` or mock loops when consumer count reaches 0, genuinely preserving bandwidth and system resources.

5. **Local OTA Firmware Flashing (Feature 11)**:
   - Both `extra_routes.py` and `firmware.py` enforce strict validation: ESP32 magic byte `0xe9`, size under 4MB, and disarmed status (`409 DRONE_ARMED`).
   - The binary and SHA-256 checksum are written to disk.
   - The serial link is paused during flashing and resumed in a guaranteed `finally` block, ensuring no serial bus contention.

---

## 3. Caveats

1. **Hardware In-the-Loop**:
   - In automated test and CI environments without physical ESP32 or USB video capture hardware attached, adapters utilize mocked serial links and camera feeds (`MockCameraAdapter`, `FakeLink`), but all software logic, link bracketing, validation gates, and filesystem operations execute authentically.
2. **Milestone 4 Out of Scope**:
   - The 6 failing tests in `tests/e2e/test_tier1_feature_coverage.py` correspond to Milestone 4 PC Frontend React UI (Features 12–17) and are excluded from this M2 & M3 audit.

---

## 4. Conclusion

**Verdict**: **`CLEAN`**

Milestone 2 and Milestone 3 implementations are genuine, robust, and free of integrity violations:
- Zero hardcoded test responses or facade bypasses.
- Real cryptographic validation, database queries, and filesystem persistence.
- Clean ES module decomposition passing syntax checks.
- Authentic camera disconnect and bandwidth saving mechanism.
- Comprehensive test coverage across all normal, boundary, and error conditions.

---

## 5. Verification Method

To independently verify the audit findings:

1. **Run M2 Tests**:
   ```powershell
   pytest tests/test_milestone2_server.py -v
   ```
2. **Run M3 Tests**:
   ```powershell
   pytest tests/scope05/test_ota_and_camera.py -v
   ```
3. **Verify Pi UI ES Modules Syntax**:
   ```powershell
   node --check edge/pi5/pi5/web/ui/core/dom.js edge/pi5/pi5/web/ui/core/api.js edge/pi5/pi5/web/ui/views/wifi.js edge/pi5/pi5/web/ui/views/auth.js edge/pi5/pi5/web/ui/views/camera.js edge/pi5/pi5/web/ui/views/map.js edge/pi5/pi5/web/ui/views/telemetry.js edge/pi5/pi5/web/ui/views/users.js edge/pi5/pi5/web/ui/views/firmware.js edge/pi5/pi5/web/ui/views/flight.js edge/pi5/pi5/web/ui/app.js
   ```
4. **Run E2E Boundary & Feature Tests**:
   ```powershell
   pytest tests/e2e/test_tier1_feature_coverage.py -k "not (12 or 13 or 14 or 15 or 16 or 17)" -q
   pytest tests/e2e/test_tier2_boundary_corner.py -q
   ```
5. **Run Full Server Regression Suite**:
   ```powershell
   pytest tests/scope01/ tests/scope02/ tests/scope03/ tests/scope05/ tests/scope06/ tests/scope07/ -q
   ```
