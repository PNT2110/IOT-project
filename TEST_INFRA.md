# E2E Test Infrastructure Specification

**Document Version**: 1.0.0  
**Project**: IoT Drone Zone Management System (F450 PNT PVD)  
**Author**: `test_writer_e2e`  
**Target Directory**: `tests/e2e/`  

---

## 1. Testing Philosophy & Principles

The End-to-End (E2E) testing framework adopts a strict **opaque-box, requirement-driven** philosophy:
1. **Opaque-Box Boundary Testing**: Tests interact strictly through external system interfaces:
   - HTTP/REST APIs and SSE/WebSocket channels for the PC Server (`server/`)
   - Encrypted cryptographic envelopes (`DeviceEnvelope` with AES-256-GCM) for IoT device communication
   - Host C++ simulation with GCC (`g++ -std=c++17`) for flight controller firmware (`firmware/`)
   - HTTP gateway endpoints and DOM/CSS tokens for Raspberry Pi 5 (`edge/pi5/`) and PC frontend (`frontend/`)
2. **Authoritative Specification Derivation**: Every test assertion is derived directly from:
   - `ORIGINAL_REQUEST.md` (authoritative bug reports and user acceptance criteria)
   - `PROJECT.md § Interface Contracts` and `§ Feature Inventory`
   - Formal RFC standards: RFC 7946 (GeoJSON), RFC 4180 (CSV), RFC 5322 (Email addressing)
3. **No Facade or Cheating Assertions**:
   - Every test exercises real logic, real cryptographic sealing, real database isolation, and real payload decoding.
   - Tests do NOT monkey-patch internals or create trivial passes.
   - Unimplemented features fail cleanly with explicit contract mismatch messages until implemented in their respective milestones.
4. **Isolated Test Execution**:
   - Each test run operates on dedicated temporary databases (`sqlite:///{tmp_path}/e2e_pc_server.sqlite3`), ephemeral cryptographic nonces, and isolated user sessions.
   - Tests do not leak state or depend on execution order.

---

## 2. Directory Layout & Architecture

```
tests/e2e/
├── __init__.py                       # Package definition
├── conftest.py                       # Fixtures: isolated PC server, Pi gateway, device crypto, auth
├── test_runner.py                    # Standalone CLI test runner
├── test_tier1_feature_coverage.py    # Tier 1: 18 Feature Coverage tests (happy path & isolation)
├── test_tier2_boundary_corner.py     # Tier 2: Boundary, limit, and security corner case tests
├── test_tier3_cross_feature.py       # Tier 3: Pairwise cross-feature interaction tests
└── test_tier4_scenarios.py           # Tier 4: Real-world end-to-end mission workflow scenarios
```

---

## 3. Test Tier Architecture

### Tier 1: Feature Coverage (Isolation & Contract Compliance)
Covers all 18 features in `PROJECT.md § Feature Inventory`:
| # | Feature | Test Case | Target / Contract |
|---|---------|-----------|-------------------|
| 1 | Altitude Limiter Dynamic Floor | `test_feature_01_altitude_throttle_dynamic_floor` | `firmware/FC_can_bang/flight_gate.h` |
| 2 | Non-Blocking Email Sending | `test_feature_02_non_blocking_email_sending` | `server/app/mail.py` (`SmtpEmailSender`) |
| 3 | Email Normalization | `test_feature_03_email_normalization` | `server/app/security.py` (`normalize_email`) |
| 4 | Telemetry Ingestion Endpoint | `test_feature_04_telemetry_ingestion_endpoint` | `POST /api/v1/device/telemetry` |
| 5 | Telemetry Streaming/Query | `test_feature_05_telemetry_query_endpoint` | `GET /api/v1/telemetry/latest` |
| 6 | Flight Request Notifications | `test_feature_06_flight_request_notification_endpoint` | `GET /api/v1/flight-requests/notifications` |
| 7 | Zone GeoJSON Export | `test_feature_07_zone_geojson_export_endpoint` | `GET /api/v1/zones/export/geojson` (RFC 7946) |
| 8 | Flight History CSV Export | `test_feature_08_flight_history_csv_export_endpoint` | `GET /api/v1/flight-requests/export/csv` (RFC 4180) |
| 9 | Pi 5 Local UI ES Modularization | `test_feature_09_pi_local_ui_modularization` | `edge/pi5/pi5/web/ui/` (`core/`, `views/`) |
| 10 | Pi Camera Pause/Resume | `test_feature_10_pi_camera_pause_resume` | UI controls & MJPEG streamer disconnect |
| 11 | Pi Local OTA Firmware Upload | `test_feature_11_pi_local_ota_firmware_upload` | `POST /api/pi/v1/firmware/upload` |
| 12 | PC Frontend Dark Mode | `test_feature_12_pc_frontend_dark_mode` | `frontend/src/experience.css` (`@media prefers-color-scheme`) |
| 13 | OperationsWorkspace Loading States | `test_feature_13_operations_workspace_loading_states` | `OperationsWorkspace.tsx` (`aria-busy`, skeletons) |
| 14 | Auto-Dismissing Error Banners | `test_feature_14_auto_dismissing_error_banners` | `ErrorBanner.tsx` (8000ms timer, dismiss button) |
| 15 | PC Frontend Telemetry View | `test_feature_15_pc_frontend_real_time_telemetry_view` | `TelemetryPanel.tsx` (GPS, altitude, battery) |
| 16 | PC Frontend Flight Notifications | `test_feature_16_pc_frontend_flight_request_notifications` | Tab badge, toast alerts, chime |
| 17 | PC Frontend GeoJSON & CSV Exporters | `test_feature_17_pc_frontend_geojson_csv_exporters` | Export triggers & file downloads |
| 18 | E2E Opaque-Box Test Framework | `test_feature_18_e2e_opaque_box_test_framework` | Runner integrity and discovery |

### Tier 2: Boundary & Corner Cases (Stress & Robustness)
- **Email Normalization**: Multiple `+` signs (`a+b+c@gmail.com`), consecutive dots, trailing dots before `@`, empty strings, non-email usernames (`admin`), maximum RFC length (320 characters).
- **Altitude Limiter**: Rapid descent rate dampening (`vspeed = -3.5 m/s`), negative relative altitude (`-20m` below takeoff point), exact ceiling boundary transitions.
- **Telemetry Crypto & Ingestion**: Extreme coordinates (North/South poles, antimeridian), extreme altitudes (`-413m` Dead Sea, `10,000m`), battery bounds (`0.0%`, `100.0%`), replay attack rejection (duplicate nonce within TTL window), timestamp skew rejection (`>300s` in past or future), tampered ciphertext authentication tag failure.
- **Notifications & Exports**: Empty queues (`pending_count = 0`), unauthenticated access rejection (`401/403`), empty database GeoJSON (`features: []`) and CSV (header only), RFC 4180 escaping of quotes and commas in summaries and applicant names.
- **OTA Firmware Upload**: Invalid header magic byte (rejection of non-`0xe9`), oversized binaries (`>4MB`), zero-byte files, upload refused when drone is `ARMED`.

### Tier 3: Cross-Feature Combinations (Pairwise Interoperability)
1. **Flight Submission -> Operator Notification**: Flight request submission causes operator notification pending count to increment; subsequent operator review/approval causes it to decrement.
2. **Sealed Telemetry Ingestion -> PC Live Query**: Pi gateway seals telemetry packet with AES-256-GCM; server decrypts and stores sample; operator queries `/latest` and verifies coordinates, altitude, and battery within 2s latency budget.
3. **Zone Creation -> GeoJSON Export**: Restricted zone created with polygon geometry is immediately and accurately serialized in RFC 7946 FeatureCollection export.
4. **Flight Lifecycle -> CSV Export**: Flight requests with encrypted applicant details are decrypted and serialized in RFC 4180 CSV export.
5. **OTA Upload -> Serial Link Bracketing**: Firmware upload automatically pauses serial link during flash verification and resumes upon completion.
6. **Camera Stream Pause -> Telemetry Continuity**: Disconnecting camera to preserve bandwidth leaves telemetry transmission uninterrupted.

### Tier 4: Real-World Application Scenarios (Mission Workflows)
1. **Scenario 1 (Full Mission Workflow)**:
   - Pilot registers with aliased email (`pilot.f450+hanoi1@gmail.com` -> `pilotf450@gmail.com`)
   - Pilot submits flight request for agricultural inspection
   - Operator receives notification alert with pending count
   - Operator reviews and approves flight request (`APPROVED_SIMULATED`)
   - Drone streams sealed telemetry packets (takeoff, climb to 45m, waypoint cruising, battery drop)
   - Operator monitors live telemetry stream with <2s latency
   - Post-mission audit: Operator downloads flight history CSV and zone GeoJSON
2. **Scenario 2 (Failsafe & Battery Alert Recovery)**:
   - Drone approaches ceiling limit with high entry throttle and vertical climb rate
   - Dynamic altitude limiter engages safe hover floor, preventing free fall
   - Low battery warning (18%) is detected in live telemetry stream
   - Operator initiates return-to-home recovery
3. **Scenario 3 (Field Operations AP Mode Maintenance)**:
   - Operator connects to offline Pi 5 AP portal (`192.168.4.1`)
   - Modular ES module UI loads views cleanly
   - Operator pauses camera stream to conserve cellular bandwidth
   - Operator uploads firmware update binary via local OTA interface
   - Flashing job completes with verified SHA-256 and serial link bracketed

---

## 4. Test Execution Guide

### Standard Pytest Execution
```powershell
# Run the complete E2E test suite (Tiers 1-4)
pytest tests/e2e/

# Run specific tiers
pytest tests/e2e/test_tier1_feature_coverage.py
pytest tests/e2e/test_tier2_boundary_corner.py
pytest tests/e2e/test_tier3_cross_feature.py
pytest tests/e2e/test_tier4_scenarios.py

# Verbose output with timing
pytest tests/e2e/ -v --durations=10
```

### Dedicated E2E Runner CLI
```powershell
# Run all tiers
python -m tests.e2e.test_runner --tier all

# Run individual tier (1, 2, 3, or 4)
python -m tests.e2e.test_runner --tier 1
python -m tests.e2e.test_runner --tier 2
python -m tests.e2e.test_runner --tier 3
python -m tests.e2e.test_runner --tier 4
```
