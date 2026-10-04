# Handoff Report: Milestone 4 Challenger 1 (Frontend Empirical Stress & Verifier)

**Challenger**: `challenger_m4_1`  
**Date**: 2026-10-04  
**Working Directory**: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\challenger_m4_1`  
**Parent Conversation ID**: `3be5ec9a-8b7d-4356-b0b8-0a206dabba81`  
**Verdict**: **REJECT**

---

## 1. Observation

### 1.1 Mandatory Verification Command Results

1. **`cmd /c npm --prefix frontend run typecheck`**:
   - Exit code: `0`
   - Output:
     ```text
     > iot-research-pc-foundation-ui@0.1.0 typecheck
     > tsc --noEmit
     ```

2. **`cmd /c npm --prefix frontend run build`**:
   - Exit code: `0`
   - Output:
     ```text
     > iot-research-pc-foundation-ui@0.1.0 build
     > tsc -b && vite build
     vite v7.3.6 building client environment for production...
     ✓ 94 modules transformed.
     dist/index.html                   0.52 kB │ gzip:   0.34 kB
     dist/assets/index-RapmcfLl.css  110.69 kB │ gzip:  30.00 kB
     dist/assets/index-P4tjQe9d.js   711.41 kB │ gzip: 207.92 kB
     ✓ built in 5.19s
     ```

3. **`pytest tests/e2e/test_tier1_feature_coverage.py -k "feature_12 or feature_13 or feature_14 or feature_15 or feature_16 or feature_17" -v`**:
   - Exit code: `1` (**FAILED: 2 failed, 4 passed**)
   - Verbatim failure output:
     ```text
     FAILED tests/e2e/test_tier1_feature_coverage.py::test_feature_14_auto_dismissing_error_banners - AssertionError: Missing frontend/src/components/ErrorBanner.tsx
     FAILED tests/e2e/test_tier1_feature_coverage.py::test_feature_15_pc_frontend_real_time_telemetry_view - AssertionError: Missing TelemetryPanel.tsx in frontend operations
     ================= 2 failed, 4 passed, 12 deselected in 0.26s =================
     ```

### 1.2 Layout & Contract Deficiencies
- `PROJECT.md` § Code Layout (lines 170–174) explicitly mandates:
  ```text
  c:\Users\pnt21\Desktop\IOT\
  └── frontend/src/components/
      ├── ErrorBanner.tsx   (8s auto-dismiss banner with close button)
      └── operations/
          ├── OperationsWorkspace.tsx (Loading states, telemetry view, notifications, exports)
          └── TelemetryPanel.tsx      (Live GPS, altitude, battery display)
  ```
- **Finding 1**: `ErrorBanner.tsx` was placed in `frontend/src/components/common/ErrorBanner.tsx`, violating `PROJECT.md` and failing Tier 1 test `test_feature_14_auto_dismissing_error_banners`.
- **Finding 2**: `TelemetryPanel.tsx` was never created. Worker inlined telemetry markup directly into `frontend/src/components/operations/OperationsWorkspace.tsx` lines 920–1035, violating `PROJECT.md` and failing Tier 1 test `test_feature_15_pc_frontend_real_time_telemetry_view`.

### 1.3 Empirical Stress & Runtime Deficiencies

1. **Telemetry Polling Cascade Loop (Critical Defect)**:
   - File: `frontend/src/components/operations/OperationsWorkspace.tsx` lines 322–362:
     ```ts
     useEffect(() => {
       let active = true;
       const pollTelemetry = async () => {
         try {
           const latest = await getLatestTelemetry();
           if (!active) return;
           if (latest) {
             setTelemetry(latest);
             setLastTelemetryReceived(Date.now()); // <-- Mutates dependency!
             setTelemetryAgeText("< 2s");
           }
         } catch {}
       };
       void pollTelemetry();
       const telemetryInterval = window.setInterval(pollTelemetry, 1000);
       ...
       return () => {
         active = false;
         window.clearInterval(telemetryInterval);
         window.clearInterval(ageTicker);
       };
     }, [lastTelemetryReceived]); // <-- Dependent on state mutated by the effect!
     ```
   - **Empirical Execution Result** (`tests/m4_component_timer_stress.mjs`):
     Calling `setLastTelemetryReceived(Date.now())` on packet arrival triggers a React state update. Because `lastTelemetryReceived` is in the `useEffect` dependency array, React unmounts the previous effect and immediately re-executes it. On re-execution, line 340 runs `void pollTelemetry();` immediately. Under realistic response times (10ms), this fired **32 requests in 500ms (~64 requests/second)** instead of 1 request/second!

2. **ErrorBanner Timer Starvation (Critical Defect)**:
   - File: `frontend/src/components/operations/OperationsWorkspace.tsx` line 738:
     ```tsx
     <ErrorBanner message={error} onDismiss={() => setError(null)} />
     ```
   - File: `frontend/src/components/common/ErrorBanner.tsx` lines 21–27:
     ```ts
     useEffect(() => {
       if (!message) return;
       const timer = window.setTimeout(onDismiss, autoDismissMs);
       return () => {
         window.clearTimeout(timer);
       };
     }, [message, onDismiss, autoDismissMs]);
     ```
   - File: `frontend/src/components/operations/OperationsWorkspace.tsx` lines 344–355:
     ```ts
     const ageTicker = window.setInterval(() => {
       ...
       setTelemetryAgeText(...); // Runs every 500ms!
     }, 500);
     ```
   - **Empirical Execution Result** (`tests/m4_component_timer_stress.mjs`):
     Because `onDismiss` is passed as an anonymous inline function `() => setError(null)` and `ageTicker` calls `setTelemetryAgeText` every 500ms, `OperationsWorkspace` re-renders every 500ms. On each render, a new function reference for `onDismiss` is created. `ErrorBanner`'s `useEffect` sees `onDismiss` changed, clears the existing timer, and schedules a new 8000ms timer. As an empirical consequence, **the error banner NEVER auto-dismisses** while telemetry or age tickers are running!

3. **GpsMap Complete Re-instantiation Thrashing**:
   - File: `frontend/src/components/operations/OperationsWorkspace.tsx` lines 61–82:
     ```ts
     function GpsMap({ lat, lon, label = "Vị trí thiết bị" }: { lat: number; lon: number; label?: string }) {
       const element = useRef<HTMLDivElement | null>(null);
       useEffect(() => {
         if (!element.current) return;
         const map = L.map(element.current, ...).setView([lat, lon], 14);
         ...
         return () => {
           map.remove();
         };
       }, [lat, lon]);
     ```
   - On every coordinate update (1s polling cadence), `map.remove()` completely tears down the Leaflet instance, and `L.map()` re-initializes DOM containers, tile layers, and event listeners from scratch, causing DOM and canvas thrashing instead of smoothly updating `marker.setLatLng([lat, lon])` and `map.panTo([lat, lon])`.

4. **Dark Mode Un-themed `.ghost-button` White Background**:
   - File: `frontend/src/components/account/AccountMenu.tsx` line 160:
     ```tsx
     <button className="ghost-button" type="button" onClick={onClose} disabled={busy}>Hủy</button>
     ```
   - File: `frontend/src/styles.css` line 121:
     ```css
     .ghost-button { border: 1px solid var(--line-strong); background: #fff; color: var(--ink); }
     ```
   - In `frontend/src/experience.css` under `@media (prefers-color-scheme: dark)`, `--ink` is `#e2ecf5` (near white). There is NO override for `.ghost-button`.
   - **Empirical Execution Result** (`tests/m4_contrast_check.py`):
     The cancel button renders with `#fff` background and `#e2ecf5` text. The contrast ratio is **1.19:1**, completely failing WCAG AA (requires 4.5:1) and rendering the text invisible to users.

5. **WCAG 2.1 AA Contrast Failure on `--quiet` Typography**:
   - File: `frontend/src/experience.css` line 769 & 978:
     ```css
     --quiet: #55748f;
     ...
     .metric-sub { color: var(--quiet); }
     ```
   - **Empirical Execution Result** (`tests/m4_contrast_check.py`):
     `.metric-sub` is `<small>` (10–12px) text rendered on `--surface` (`#142130`). Contrast ratio is **3.32:1**, failing the WCAG 2.1 AA requirement of **4.5:1** for body/small text. On `--surface-soft` (`#192a3c`), contrast falls to **2.98:1**, failing even large-text thresholds.

---

## 2. Logic Chain

1. *Observation*: Running `pytest tests/e2e/test_tier1_feature_coverage.py -k "feature_12 or feature_13 or feature_14 or feature_15 or feature_16 or feature_17" -v` produces 2 failures: missing `frontend/src/components/ErrorBanner.tsx` and missing `frontend/src/components/operations/TelemetryPanel.tsx`.
2. *Deduction*: Milestone 4 acceptance criteria state that all new features must adhere to project specifications and pass Tier 1 tests. Because the worker placed files in non-compliant locations and failed to extract `TelemetryPanel.tsx`, the deliverable breaks contract specifications and test automation.
3. *Observation*: `OperationsWorkspace.tsx` lines 322–362 include `lastTelemetryReceived` in the polling `useEffect` dependency array while invoking `setLastTelemetryReceived(Date.now())` inside `pollTelemetry()`.
4. *Deduction*: Mutating the dependency variable inside the effect triggers an immediate cleanup and re-run. In Node simulation (`tests/m4_component_timer_stress.mjs`), this produced an unthrottled burst of 64 requests/sec against the telemetry endpoint, which will overload the server and Pi gateway in production.
5. *Observation*: `OperationsWorkspace.tsx` line 738 passes an inline arrow function `onDismiss={() => setError(null)}` to `ErrorBanner`, and line 344 runs an `ageTicker` every 500ms updating component state.
6. *Deduction*: Re-rendering `OperationsWorkspace` every 500ms instantiates a new `onDismiss` reference, which triggers `ErrorBanner`'s cleanup and restarts the 8-second timer. The banner can never auto-dismiss while telemetry updates are running.
7. *Observation*: `AccountMenu.tsx` uses `.ghost-button` which has `background: #fff` and `color: var(--ink)` (`#e2ecf5` in dark mode) without any dark mode override in `experience.css`.
8. *Deduction*: The calculated contrast ratio is 1.19:1, rendering the button text invisible in dark mode and violating accessibility criteria.

---

## 3. Caveats

1. **Exports Validated**: RFC 7946 GeoJSON and RFC 4180 CSV generation functions were empirically tested with Shapely and Python `csv.reader` across Vietnamese Unicode, quotation marks, commas, and CRLF line breaks, passing all tests.
2. **Build and Typecheck Succeeded**: `npm run typecheck` and `npm run build` both exit with 0 errors. The failures are structural contract discrepancies, lifecycle feedback bugs, and CSS accessibility defects.

---

## 4. Conclusion

**Verdict: REJECT**

Milestone 4 cannot be approved in its current state. The worker must resolve the following concrete items before Milestone 4 can pass:

1. **Fix File Layout & Contracts**:
   - Provide `frontend/src/components/ErrorBanner.tsx` (either moved from `common/` or re-exported from `components/ErrorBanner.tsx`).
   - Extract the telemetry UI from `OperationsWorkspace.tsx` into `frontend/src/components/operations/TelemetryPanel.tsx` matching `PROJECT.md` line 174.
2. **Fix Telemetry Polling Dependency Loop**:
   - In `OperationsWorkspace.tsx`, remove `lastTelemetryReceived` from the polling `useEffect` dependency array (or use a ref for timestamp tracking) so that polling runs strictly on the 1000ms `setInterval`.
3. **Fix ErrorBanner Timer Starvation**:
   - Memoize `onDismiss` with `useCallback` or decouple timer reset in `ErrorBanner.tsx` so that parent re-renders do not reset the auto-dismiss timer unless `message` itself changes.
4. **Fix Leaflet Map Thrashing**:
   - In `GpsMap`, retain the Leaflet map instance and update the marker with `marker.setLatLng([lat, lon])` rather than calling `map.remove()` and re-creating `L.map()` on every coordinate update.
5. **Fix Dark Mode Styling & Contrast**:
   - Add dark mode override for `.ghost-button` in `experience.css` (e.g. `background: var(--surface); color: var(--ink); border-color: var(--line-strong);`).
   - Adjust `--quiet` or `.metric-sub` in dark mode to achieve at least 4.5:1 contrast on `--surface` (e.g. `#8cb3d4` or `var(--muted)`).

---

## 5. Verification Method

To verify these findings:

1. **Run Tier 1 Test Suite**:
   ```powershell
   pytest tests/e2e/test_tier1_feature_coverage.py -k "feature_12 or feature_13 or feature_14 or feature_15 or feature_16 or feature_17" -v
   ```
   *Current Result*: Fails on `test_feature_14` and `test_feature_15`.

2. **Run Empirical Challenger Stress Suite**:
   ```powershell
   pytest tests/test_challenger_m4_empirical.py -v
   ```
   *Current Result*: 6 failed, 2 passed.

3. **Run Component Timer & Polling Stress Test**:
   ```powershell
   node tests/m4_component_timer_stress.mjs
   ```
   *Current Result*: Demonstrates 64 req/sec telemetry cascade loop and ErrorBanner timer starvation.

4. **Run Dark Mode Contrast Audit**:
   ```powershell
   python tests/m4_contrast_check.py
   ```
   *Current Result*: Proves `--quiet` on `--surface` is 3.32:1 (< 4.5:1) and `.ghost-button` in dark mode is 1.19:1.
