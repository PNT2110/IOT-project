# Milestone 5 Phase 2: Tier 5 Adversarial Coverage Hardening Review Report

**Reviewer / Adversarial Critic**: `reviewer_tier5`  
**Date**: 2026-10-04T01:59:00Z  
**Verdict**: **`APPROVE (NO REMAINING GAPS)`**  
**Overall Risk Assessment**: **`LOW`**

---

## 1. Observation

Direct empirical observations and verification executions across all subsystems:

### 1.1 Work Products Inspected
1. **`tests/e2e/test_tier5_adversarial_hardening.py`** (923 lines):
   - Contains 32 white-box adversarial test cases covering all 4 system tiers:
     - Firmware: Lines 83–184 (`test_adv_fw_deadband_hysteresis_oscillation`, `test_adv_fw_terminal_dive_vspeed_damping`, `test_adv_fw_downward_stick_priority`, `test_adv_fw_millis_rollover_link_alive`), Lines 662–710 (`test_adv_fw_step_quantization_long_duration`, `test_adv_fw_zero_throttle_idle_floor_immunity`).
     - Pi 5 Gateway & Web UI: Lines 190–312 (`test_adv_pi_ota_upload_exact_4mb_boundary`, `test_adv_pi_ota_armed_lockout`, `test_adv_pi_ota_filename_sanitization`, `test_adv_pi_camera_disconnect_and_idle_shutdown`, `test_adv_pi_camera_frame_splitter_stress`), Lines 829–887 (`test_adv_pi_camera_stream_failure_handling`, `test_adv_pi_camera_rapid_start_stop_churn`, `test_adv_pi_ui_es_module_graph_integrity`).
     - Server Backend: Lines 315–617 (`test_adv_server_telemetry_ciphertext_bitflip_tamper`, `test_adv_server_telemetry_replay_burst`, `test_adv_server_telemetry_skew_rejection`, `test_adv_server_telemetry_multi_device_isolation`, `test_adv_server_telemetry_unauthenticated_query_rejected`, `test_adv_server_flight_notifications_self_review_forbidden`, `test_adv_server_csv_formula_injection_defense`, `test_adv_server_geojson_export_access_control`, `test_adv_server_email_normalization_matrix`, `test_adv_server_smtp_nonblocking_event_loop`), Lines 712–828 (`test_adv_server_aes_aad_device_and_timestamp_tampering`, `test_adv_server_aes_malformed_envelope_types`, `test_adv_server_geometry_adversarial_validation`, `test_adv_server_rbac_pilot_zone_tamper_rejected`).
     - PC Frontend Contracts: Lines 621–658 (`test_adv_frontend_error_banner_contract`, `test_adv_frontend_csv_and_geojson_export_contract`), Lines 888–923 (`test_adv_frontend_telemetry_polling_decoupling_contract`, `test_adv_frontend_audiocontext_lifecycle_safety`).

2. **`tests/e2e/test_runner.py`** (48 lines):
   - Tier 5 mapping configured at line 30: `"5": [str(e2e_dir / "test_tier5_adversarial_hardening.py")]`.
   - CLI argument choices at line 43: `parser.add_argument("--tier", choices=["1", "2", "3", "4", "5", "all"], default="all")`.

3. **Subsystem Production Code Inspected**:
   - `firmware/FC_can_bang/flight_gate.h`: Lines 75–132 implement dynamic floor clamping [1100, 1450] µs, deadband hysteresis release threshold `rel_alt_m < max_alt_m - ALT_LIMIT_RELEASE_M` (1.0m), descent dampening boost `(-vspeed_mps - 0.4f) * 100.0f` capped to `throttle_us - 20.0f`, and pilot downward override pass-through `throttle_us > (int)s.cap_us ? (int)s.cap_us : throttle_us`.
   - `edge/pi5/pi5/web/extra_routes.py` & `firmware.py`: Lines 278–337 enforce 4MB payload limit (`MAX_FIRMWARE_BYTES`), magic byte `0xe9`, drone arm lock (`DRONE_ARMED`), and stage binaries to fixed `FIRMWARE_ASSET` path, preventing directory traversal.
   - `edge/pi5/pi5/web/camera.py`: Lines 98–116 (`split_jpeg_frames`) enforce 4MB bounded buffer (`MAX_PARTIAL_FRAME`), while lines 81–92 guarantee camera streamer teardown on consumer disconnect.
   - `edge/pi5/pi5/web/ui/`: Modularized into 11 ES modules (`app.js`, `core/api.js`, `core/dom.js`, and 8 view modules in `views/`).
   - `server/app/device_crypto.py`: AES-256-GCM AEAD encryption with AAD `f"{device_id}|{ts}"`, 12-byte nonce enforcement, max 300s skew window, and payload dictionary verification.
   - `server/app/routers/flights.py`: Lines 218 & 250 prohibit self-review (`SELF_REVIEW_FORBIDDEN`) for flight requests; lines 79–130 format CSV according to RFC 4180 with spreadsheet formula prefix escaping (`=`, `+`, `-`, `@`).
   - `server/app/geo.py`: Lines 14–54 validate polygon GeoJSON via Shapely, rejecting self-intersecting bowties, non-finite coords, out-of-bounds WGS84 coords, CRS extensions, and non-polygons.
   - `server/app/mail.py`: Non-blocking async execution offloaded to ThreadPoolExecutor wrapped in `DualModeMailCall` with `inspect.markcoroutinefunction`.
   - `server/app/security.py`: `normalize_email()` strips Gmail dots, tags, and trims whitespace.
   - `frontend/src/components/ErrorBanner.tsx`: 8-second auto-dismiss with `useRef` timer anti-starvation, `window.clearTimeout` cleanup, `role="alert"`, `aria-live="assertive"`, `aria-label="Đóng thông báo"`.
   - `frontend/src/components/operations/OperationsWorkspace.tsx`: AudioContext delayed close (500ms) with autoplay try/catch fallback, RFC 4180 CSV escaping with UTF-8 BOM, and RFC 7946 GeoJSON export.
   - `frontend/src/components/operations/TelemetryPanel.tsx`: Autonomous 1s polling decoupled from parent-provided telemetry (`if (externalTelemetry !== undefined) return;`).

---

### 1.2 Independent Verification Results

All verification commands executed from the repository root:

1. **Full E2E Test Suite (`pytest tests/e2e/ -v`)**:
   ```
   ============================= 77 passed in 19.58s =============================
   ```
   *Observation*: 77/77 tests passed (18 Tier 1, 18 Tier 2, 6 Tier 3, 3 Tier 4, 32 Tier 5).

2. **Dedicated CLI Test Runner (`python -m tests.e2e.test_runner`)**:
   ```
   === Running E2E Test Suite [Tier: all] ===
   ============================= 77 passed in 19.82s =============================
   ```
   *Observation*: Exit code 0, all 77 tests passed.

3. **Dedicated CLI Test Runner for Tier 5 (`python -m tests.e2e.test_runner --tier 5`)**:
   ```
   === Running E2E Test Suite [Tier: 5] ===
   ============================= 32 passed in 8.52s ==============================
   ```
   *Observation*: Exit code 0, all 32 Tier 5 tests passed.

4. **Scoped Regression Suites & Firmware Tests**:
   ```
   pytest tests/scope01 tests/scope02 tests/scope03 tests/scope04 tests/scope05 tests/scope06 tests/scope07 tests/firmware -q
   ........................................................................ [ 28%]
   ........................................................................ [ 57%]
   ........................................................................ [ 85%]
   ....................................                                     [100%]
   252 passed in 58.16s
   ```
   *Observation*: Exit code 0, all 252 existing tests passed with zero regressions.

5. **Frontend TypeScript Strict Typecheck**:
   ```powershell
   cmd /c npm --prefix frontend run typecheck
   # > iot-research-pc-foundation-ui@0.1.0 typecheck
   # > tsc --noEmit
   ```
   *Observation*: Clean, zero errors, exit code 0.

6. **Frontend Production Build**:
   ```powershell
   cmd /c npm --prefix frontend run build
   # > iot-research-pc-foundation-ui@0.1.0 build
   # > tsc -b && vite build
   # ✓ 96 modules transformed.
   # dist/index.html                   0.52 kB │ gzip:   0.33 kB
   # dist/assets/index-2oiI9pXk.css  110.83 kB │ gzip:  30.02 kB
   # dist/assets/index-ChaCNviE.js   713.28 kB │ gzip: 208.16 kB
   # ✓ built in 3.70s
   ```
   *Observation*: Production build succeeded cleanly, exit code 0.

---

## 2. Logic Chain

1. **Code Authenticity and Integrity Verification**:
   - Upstream deliverables were examined for integrity violations:
     - No hardcoded test values or bypass facades were detected.
     - Firmware tests use actual host C++ compilation (`g++ -std=c++17 -Wall -Wextra`) against the production header `firmware/FC_can_bang/flight_gate.h`.
     - Pi 5 tests instantiate live FastAPI test applications with real route handlers, boundary validations, and mock camera/link adapters conforming strictly to production interfaces.
     - Server tests utilize genuine SQLite databases, real AES-256-GCM cryptographic operations, and actual FastAPI route invocations.
     - Frontend contract tests verify exact AST and token patterns in production TypeScript components.
   - Therefore, the test suite provides genuine independent verification without facade or dummy logic.

2. **Adversarial Hardening across All 4 Subsystems**:
   - **Firmware Dynamics**:
     - Rapid altitude flutter near the ceiling boundary confirms that hysteresis deadband (`ALT_LIMIT_RELEASE_M = 1.0m`) prevents release oscillation.
     - Extreme descent rates (-15 m/s) dynamically elevate the floor to arrest dives while capping at `throttle_us - 20` to avoid over-throttling.
     - Downward pilot stick inputs (including idle 1000 µs and emergency 0 µs) immediately pass through to motor outputs, guaranteeing pilot descent authority.
     - Integer rollover at `0xFFFFFFFF` ms maintains link status validity without arithmetic overflow errors.
   - **Pi 5 Gateway**:
     - OTA endpoint accepts exact 4MB binaries (4,194,304 bytes) with magic byte `0xe9`, and rejects 4MB + 1 byte with HTTP 413 `PAYLOAD_TOO_LARGE`.
     - Armed lockout (HTTP 409 `DRONE_ARMED`) protects against in-flight reflashing.
     - Multipart directory traversal attempts are neutralized because firmware images are staged exclusively to constant paths inside the designated work directory.
     - Camera disconnect cleanly terminates the consumer thread and background capture process, avoiding resource exhaustion.
   - **Server Backend**:
     - Single-bit flips in ciphertext or authentication tags are rejected with HTTP 401 `DEVICE_AUTH_FAILED`.
     - Replay attacks within identical or separate sessions are detected and blocked by the 600s TTL nonce cache.
     - Timestamp skew beyond +/-300s is rejected.
     - AAD tampering (modifying unencrypted device IDs or timestamps by even 1 second) causes AES-GCM tag verification failure.
     - Malformed nonces (<12 or >12 bytes) raise `DeviceAuthError`.
     - Self-review prevention prohibits any operator from approving or deciding their own flight request (HTTP 403 `SELF_REVIEW_FORBIDDEN`).
     - Malicious formula injection strings starting with `=`, `+`, `-`, `@` are safely sanitized and quoted in RFC 4180 CSV exports.
     - GeoJSON export strictly separates public and internal zones based on authenticated role.
     - Shapely GeoJSON validation detects self-intersecting bowties, non-finite values, and CRS violations.
   - **PC Frontend**:
     - ErrorBanner auto-dismisses after 8s while supporting manual close, avoiding timer starvation on re-renders, and maintaining ARIA compliance.
     - OperationsWorkspace synthesizes notification chimes via Web Audio API without external audio files, gracefully catching browser autoplay blocks and terminating the AudioContext after 500ms.
     - TelemetryPanel decouples autonomous polling from parent-supplied telemetry, preventing duplicate polling loops.

3. **Regression-Free Execution**:
   - The execution of all 252 unit and scoped regression tests across scopes 1–7 and firmware passed with 100% success rate.
   - TypeScript compilation and Vite production build completed with zero errors.

---

## 3. Caveats

- Hardware-in-the-loop RF radio transmission (e.g., physical SBUS UART wiring and 2.4 GHz packet jitter) is verified in software emulation via host C++ test fixtures and FastAPI TestClients, as physical hardware benches are not present in this software environment.
- Web Audio API chime synthesis requires a user gesture in browsers with strict autoplay policies; the implementation includes try/catch protection that prevents console errors or UI crashes when blocked.
- No other caveats.

---

## 4. Conclusion

The Tier 5 Adversarial Coverage Hardening suite (`tests/e2e/test_tier5_adversarial_hardening.py`) and test runner integration (`tests/e2e/test_runner.py`) satisfy all functional, architectural, adversarial, and quality requirements. The test cases thoroughly exercise edge conditions, boundary extremes, cryptographic integrity, and RBAC policies without dummy mocks or facades.

All 77 E2E tests pass, all 252 scoped/firmware regression tests pass, and frontend typechecking and production build succeed cleanly.

**Final Verdict**: **`APPROVE (NO REMAINING GAPS)`**

---

## 5. Verification Method

To independently verify this evaluation, execute the following commands from the repository root:

```powershell
# 1. Run complete E2E test suite (77 tests across Tiers 1-5)
pytest tests/e2e/ -v

# 2. Run dedicated CLI test runner for all tiers
python -m tests.e2e.test_runner

# 3. Run dedicated CLI test runner specifically for Tier 5 (32 tests)
python -m tests.e2e.test_runner --tier 5

# 4. Run all Scope 1-7 and Firmware regression suites (252 tests)
pytest tests/scope01 tests/scope02 tests/scope03 tests/scope04 tests/scope05 tests/scope06 tests/scope07 tests/firmware -q

# 5. Verify PC Frontend TypeScript type safety and production build
cmd /c npm --prefix frontend run typecheck
cmd /c npm --prefix frontend run build
```

**Invalidation Conditions**:
- Any test failure in `pytest tests/e2e/ -v`.
- Any unhandled exception resulting in HTTP 500 on corrupted ciphertext, AAD mismatch, or invalid GeoJSON.
- Any regression across the 252 existing unit tests or frontend build failures.
