# Handoff Report: Code Review 2 (Milestone 4 - PC Frontend UI/UX & Features)

**Reviewer**: `reviewer_m4_2` (Code Reviewer 2 / Adversarial Critic)  
**Date**: 2026-10-04  
**Working Directory**: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\reviewer_m4_2`  
**Parent Conversation ID**: `3be5ec9a-8b7d-4356-b0b8-0a206dabba81`  
**Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

### 1.1 Typecheck and Build Execution
1. Executed `cmd /c npm --prefix frontend run typecheck`:
   ```text
   > iot-research-pc-foundation-ui@0.1.0 typecheck
   > tsc --noEmit
   Exited with code 0.
   ```
2. Executed `cmd /c npm --prefix frontend run build`:
   ```text
   > iot-research-pc-foundation-ui@0.1.0 build
   > tsc -b && vite build
   vite v7.3.6 building client environment for production...
   ✓ 94 modules transformed.
   dist/index.html                   0.52 kB │ gzip:   0.34 kB
   dist/assets/index-RapmcfLl.css  110.69 kB │ gzip:  30.00 kB
   dist/assets/index-P4tjQe9d.js   711.41 kB │ gzip: 207.92 kB
   ✓ built in 8.56s
   Exited with code 0.
   ```

### 1.2 Automated E2E Feature Test Failures
Executed `pytest tests/e2e/test_tier1_feature_coverage.py -k "feature_12 or feature_13 or feature_14 or feature_15 or feature_16 or feature_17" -v`:
```text
tests/e2e/test_tier1_feature_coverage.py::test_feature_12_pc_frontend_dark_mode PASSED [ 16%]
tests/e2e/test_tier1_feature_coverage.py::test_feature_13_operations_workspace_loading_states PASSED [ 33%]
tests/e2e/test_tier1_feature_coverage.py::test_feature_14_auto_dismissing_error_banners FAILED [ 50%]
tests/e2e/test_tier1_feature_coverage.py::test_feature_15_pc_frontend_real_time_telemetry_view FAILED [ 66%]
tests/e2e/test_tier1_feature_coverage.py::test_feature_16_pc_frontend_flight_request_notifications PASSED [ 83%]
tests/e2e/test_tier1_feature_coverage.py::test_feature_17_pc_frontend_geojson_csv_exporters PASSED [100%]

================================== FAILURES ===================================
________________ test_feature_14_auto_dismissing_error_banners ________________
    banner_file = PROJECT_ROOT / "frontend" / "src" / "components" / "ErrorBanner.tsx"
>   assert banner_file.exists(), "Missing frontend/src/components/ErrorBanner.tsx"
E   AssertionError: Missing frontend/src/components/ErrorBanner.tsx

tests\e2e\test_tier1_feature_coverage.py:388: AssertionError
____________ test_feature_15_pc_frontend_real_time_telemetry_view _____________
    panel_file = PROJECT_ROOT / "frontend" / "src" / "components" / "operations" / "TelemetryPanel.tsx"
>   assert panel_file.exists(), "Missing TelemetryPanel.tsx in frontend operations"
E   AssertionError: Missing TelemetryPanel.tsx in frontend operations

tests\e2e\test_tier1_feature_coverage.py:405: AssertionError
================= 2 failed, 4 passed, 12 deselected in 0.20s ==================
```

### 1.3 Telemetry Polling Effect Dependency Bug
In `frontend/src/components/operations/OperationsWorkspace.tsx`, lines 323–362:
```typescript
  // 1-second interval for real-time telemetry polling
  useEffect(() => {
    let active = true;

    const pollTelemetry = async () => {
      try {
        const latest = await getLatestTelemetry();
        if (!active) return;
        if (latest) {
          setTelemetry(latest);
          setLastTelemetryReceived(Date.now());
          setTelemetryAgeText("< 2s");
        }
      } catch {
        // Telemetry errors handled silently to avoid disrupting workspace
      }
    };

    void pollTelemetry();
    const telemetryInterval = window.setInterval(pollTelemetry, 1000);

    // Age updater ticker every 500ms
    const ageTicker = window.setInterval(() => {
      if (!lastTelemetryReceived) {
        setTelemetryAgeText("—");
        return;
      }
      const elapsedSeconds = (Date.now() - lastTelemetryReceived) / 1000;
      if (elapsedSeconds < 2) {
        setTelemetryAgeText("< 2s");
      } else {
        setTelemetryAgeText(`${Math.round(elapsedSeconds)}s trước`);
      }
    }, 500);

    return () => {
      active = false;
      window.clearInterval(telemetryInterval);
      window.clearInterval(ageTicker);
    };
  }, [lastTelemetryReceived]);
```

### 1.4 Web Audio API Chime Resource Leak and Autoplay Rejection
In `frontend/src/components/operations/OperationsWorkspace.tsx`, lines 98–135:
```typescript
function playNotificationChime() {
  try {
    const AudioCtx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    if (ctx.state === "suspended") {
      void ctx.resume();
    }
...
```
1. `new AudioCtx()` is created on each new notification without ever calling `ctx.close()`.
2. `void ctx.resume();` does not catch rejected promises returned when the browser blocks audio before user interaction.

### 1.5 Export Functions and Accessibility
1. GeoJSON export (`exportZonesGeoJson` in `OperationsWorkspace.tsx` lines 153–183):
   - Uses `Blob` with `type: "application/geo+json;charset=utf-8"`.
   - Structures output as RFC 7946 `FeatureCollection`.
   - Cleans up DOM anchor and revokes object URL via `URL.revokeObjectURL(url)`.
2. CSV export (`exportFlightsCsv` in `OperationsWorkspace.tsx` lines 188–233):
   - Prepends UTF-8 BOM `\uFEFF`.
   - Joins lines with RFC 4180 CRLF (`\r\n`).
   - Uses RFC 4180 escaping `escapeCsv` (doubles quotes `""`, quotes fields containing `,`, `"`, `\r`, `\n`).
   - Sets MIME type `text/csv;charset=utf-8`.
3. Accessibility attributes:
   - `ErrorBanner.tsx`: `role="alert"`, `aria-live="assertive"`, dismiss button `aria-label="Đóng thông báo"`.
   - `OperationsWorkspace.tsx`: `aria-busy={initialLoading || busy}`, loading spinner `role="status"` and `aria-live="polite"`.
   - Flight notification banner: `role="status"`, `aria-live="polite"`, close button `aria-label="Đóng thông báo"`.
   - Badges: `aria-label` detailing count; map `role="img"` with coordinate labels.

---

## 2. Logic Chain

1. *Observation 1.2*: `pytest tests/e2e/test_tier1_feature_coverage.py -k "feature_12 or feature_13 or feature_14 or feature_15 or feature_16 or feature_17"` failed with 2 errors:
   - `test_feature_14_auto_dismissing_error_banners` failed because `frontend/src/components/ErrorBanner.tsx` does not exist (the worker created `frontend/src/components/common/ErrorBanner.tsx` without an export from `frontend/src/components/ErrorBanner.tsx`).
   - `test_feature_15_pc_frontend_real_time_telemetry_view` failed because `frontend/src/components/operations/TelemetryPanel.tsx` does not exist (the worker embedded all telemetry code inside `OperationsWorkspace.tsx` rather than extracting the component).
   *Deduction*: Contractual feature deliverables required by the automated test suite are missing or improperly located.

2. *Observation 1.3*: In `OperationsWorkspace.tsx`, `lastTelemetryReceived` is included in the dependency array of the `useEffect` that updates `lastTelemetryReceived`.
   *Deduction*: Every time telemetry data is successfully received, `setLastTelemetryReceived(Date.now())` triggers a re-render. Because `lastTelemetryReceived` changed, React tears down the effect and runs it again immediately. The effect body starts with `void pollTelemetry();`, which immediately issues another fetch to `/api/v1/telemetry/latest`. This creates a tight infinite request flood (polling dozens of times per second) whenever telemetry is active, defeating the intended 1-second interval, overloading the server, and causing timer teardown churn.

3. *Observation 1.4*: In `playNotificationChime()`, `new AudioCtx()` is created on each notification without calling `ctx.close()`. Browsers (Chrome, Edge, Safari) limit the maximum number of concurrent AudioContext instances per tab (typically 6). After 6 notifications, audio creation throws an error and permanently fails. Furthermore, `ctx.resume()` returns a Promise that rejects when the browser's autoplay policy denies unprompted audio, resulting in an unhandled promise rejection in the browser console.
   *Deduction*: The audio chime leaks audio contexts and lacks proper Promise rejection handling.

4. *Observation 1.1, 1.5*: TypeScript typecheck and Vite build pass cleanly with 0 errors. Dark mode token overrides, cartographic tile inversion, RFC 7946 GeoJSON export, RFC 4180 CSV export with UTF-8 BOM, and accessibility attributes are correctly implemented.
   *Deduction*: The core visual, formatting, and accessibility logic is sound, but the missing component files, infinite request storm, and AudioContext leak require resolution before approval.

---

## 3. Caveats

- The backend E2E tests in `tests/e2e/test_tier3_cross_feature.py` and `tests/e2e/test_tier4_scenarios.py` failed due to missing backend columns/fixtures (`NOT NULL constraint failed: simulated_flight_requests.scheduled_start_at`), which is part of the Milestone 2 backend scope rather than Milestone 4 frontend scope. The M4 review is strictly scoped to M4 PC Frontend deliverables.
- No other caveats.

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

The PC Frontend work shows high visual quality, solid dark mode styling, and proper RFC data export formatting, but contains two blocking test failures and two architectural/runtime defects:

1. **[Critical - Integrity/Contract] Missing Deliverable Files**:
   - `test_feature_14_auto_dismissing_error_banners` fails: Create or re-export `ErrorBanner.tsx` at `frontend/src/components/ErrorBanner.tsx`.
   - `test_feature_15_pc_frontend_real_time_telemetry_view` fails: Extract the telemetry view from `OperationsWorkspace.tsx` into `frontend/src/components/operations/TelemetryPanel.tsx` and import it into `OperationsWorkspace.tsx`.

2. **[Critical - Runtime Defect] Infinite Request Storm in Telemetry Polling**:
   - In `OperationsWorkspace.tsx` (lines 323–362), remove `lastTelemetryReceived` from the effect's dependency array (use a ref `lastTelemetryReceivedRef = useRef<number | null>(null)` or separate the age ticker). Ensure the telemetry interval effect has dependencies `[]` or depends only on active tab, maintaining an exact 1-second cadence without immediate re-triggering.

3. **[Major - Resource Leak] AudioContext Exhaustion & Autoplay Promise Handling**:
   - In `playNotificationChime()`, close the `AudioContext` after playback (e.g. `setTimeout(() => void ctx.close(), 1000)` or use a persistent lazily-initialized singleton).
   - Add `.catch(() => {})` to `ctx.resume()` (e.g. `void ctx.resume().catch(() => {})`) to avoid unhandled promise rejections when autoplay is blocked.

---

## 5. Verification Method

To verify the required fixes:

1. **Run M4 E2E Feature Test Suite**:
   ```powershell
   pytest tests/e2e/test_tier1_feature_coverage.py -k "feature_12 or feature_13 or feature_14 or feature_15 or feature_16 or feature_17" -v
   ```
   *Expected Output*: All 6 tests must pass (`6 passed, 12 deselected, 0 failed`).

2. **TypeScript Compilation & Build**:
   ```powershell
   cmd /c npm --prefix frontend run typecheck
   cmd /c npm --prefix frontend run build
   ```
   *Expected Output*: Exit code 0 for both commands.

3. **Runtime Polling Cadence Verification**:
   - Open browser developer tools Network tab while on the PC Frontend workspace with active telemetry data.
   - Verify that requests to `/api/v1/telemetry/latest` fire strictly once per second (1000ms), and do not fire in a rapid continuous loop.
