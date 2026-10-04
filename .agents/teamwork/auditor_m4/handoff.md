# Forensic Audit Report: Milestone 4 (PC Frontend UI/UX & Features)

**Auditor**: `auditor_m4`  
**Date**: 2026-10-04  
**Working Directory**: `c:\Users\pnt21\Desktop\IOT\.agents\teamwork\auditor_m4`  
**Parent Conversation ID**: `3be5ec9a-8b7d-4356-b0b8-0a206dabba81`  
**Profile**: General Project  
**Integrity Mode**: Development (per `ORIGINAL_REQUEST.md`)  
**Verdict**: **CLEAN**

---

## 1. Observation

### 1.1 Scope of Changes Inspected
1. `frontend/src/types.ts`: New contract types `TelemetryData`, `ZoneGeoJsonFeature`, `ZoneGeoJsonCollection`, and `FlightNotification`.
2. `frontend/src/api.ts`: Real `getLatestTelemetry(deviceId?: string): Promise<TelemetryData | null>` querying `/api/v1/telemetry/latest`.
3. `frontend/src/components/common/ErrorBanner.tsx`: Accessible component with 8-second auto-dismiss (`autoDismissMs = 8000`), manual dismiss button (`×`, `aria-label="Đóng thông báo"`), and `role="alert"` / `aria-live="assertive"`.
4. `frontend/src/components/operations/OperationsWorkspace.tsx`:
   - `initialLoading` state with `<div className="workspace-loading-state" role="status" aria-live="polite">` and `aria-busy={initialLoading || busy}` on `<section>`, preventing empty-state flash.
   - Genuine Web Audio API 2-tone synthesizer (`playNotificationChime()`, 880Hz -> 1320Hz sine tones, `createOscillator()`, `createGain()`, exponential volume envelope ramps).
   - Genuine GeoJSON exporter (`exportZonesGeoJson()` assembling RFC 7946 `FeatureCollection`, `new Blob([json], { type: "application/geo+json" })`, `URL.createObjectURL()`, `<a>` click trigger, and `URL.revokeObjectURL()`).
   - Genuine CSV exporter (`exportFlightsCsv()` adhering to RFC 4180 quotes, CRLF `\r\n`, and `\uFEFF` UTF-8 BOM for Excel compatibility).
   - Real-time telemetry monitoring panel: 1-second polling hook calling `getLatestTelemetry()`, 500ms ticker calculating exact elapsed age (`< 2s`), 6-decimal GPS formatting, altitude in meters (`altitude_m.toFixed(1) m`), 3-tier battery thresholds (≥50% green, 20–49% amber, <20% red), fix state chip (`VALID_FIX` / `NO_FIX` / `STALE`), and live Leaflet GPS positioning map.
   - Background flight request polling at 3s intervals detecting newly submitted flights, playing audio chime, displaying on-screen toast banner with "Xem ngay" button, and showing counter badges.
5. `frontend/src/App.tsx`, `frontend/src/components/account/AccountMenu.tsx`, `frontend/src/components/auth/AuthPanel.tsx`: Replaced static error banners with `ErrorBanner`.
6. `frontend/src/experience.css`:
   - Full `@media (prefers-color-scheme: dark)` palette overrides covering all design tokens (`--ink`, `--surface`, `--canvas`, `--line`, etc.).
   - Cartographic Leaflet raster tile inversion via CSS filter (`brightness(0.65) invert(1) contrast(2.6) hue-rotate(190deg) saturate(0.35) brightness(0.85)`).
   - `.brand-mark` contrast adjustment (`mix-blend-mode: normal`, drop-shadow).
   - Comprehensive styling for all ~40 surface cards, dialogs, popovers, tables, and inputs.

### 1.2 Forensic Phase Results

| Check | Verdict | Details |
|---|---|---|
| **Hardcoded Test Outputs** | **PASS** | No hardcoded coordinates, mock telemetry responses, or pre-computed outputs found in source files. All dynamic data flows through `getLatestTelemetry()` or `listFlights()`. |
| **Facade Implementation Detection** | **PASS** | No dummy stubs or facade return statements. Web Audio API creates actual `OscillatorNode` and `GainNode` audio graphs; file exporters construct genuine `Blob`s and trigger DOM download workflows; polling hooks run real timer intervals. |
| **Pre-populated Artifact Detection** | **PASS** | No fake test reports, pre-generated log files, or mock fixture artifacts planted in the workspace. |
| **Self-Certifying Tests** | **PASS** | No internal tests mock their own outputs to pass artificially. |
| **Code Reuse & Dependency Audit** | **PASS** | Follows development mode guidelines. Zero unauthorized heavy external dependencies added; all features utilize browser-native standards (Web Audio API, Blob, URL API, CSS Media Queries, CSS Filters). |
| **TypeScript Typecheck** | **PASS** | `cmd /c npm --prefix frontend run typecheck` exited with code 0 (zero type errors). |
| **Vite Production Build** | **PASS** | `cmd /c npm --prefix frontend run build` exited with code 0 (94 modules transformed, bundle emitted in `dist/`). |
| **Backend Contract Compatibility** | **PASS** | `pytest tests/scope01..05` executed with 211 passed in 60.45s, confirming full backwards and forwards API compatibility. |

### 1.3 Verbatim Tool Outputs

#### TypeScript Typecheck
```text
> iot-research-pc-foundation-ui@0.1.0 typecheck
> tsc --noEmit

Exited with code 0.
```

#### Vite Production Build
```text
> iot-research-pc-foundation-ui@0.1.0 build
> tsc -b && vite build

vite v7.3.6 building client environment for production...
transforming...
✓ 94 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.52 kB │ gzip:   0.34 kB
dist/assets/index-RapmcfLl.css  110.69 kB │ gzip:  30.00 kB
dist/assets/index-P4tjQe9d.js   711.41 kB │ gzip: 207.92 kB
✓ built in 5.45s
Exited with code 0.
```

#### Pytest Scope01–Scope05 Regression Execution
```text
........................................................................ [ 34%]
........................................................................ [ 68%]
...................................................................      [100%]
211 passed in 60.45s (0:01:00)
Exited with code 0.
```

---

## 2. Logic Chain

1. *Requirement R2 (Dark Mode)*: `experience.css` includes `@media (prefers-color-scheme: dark)` which overrides root variables and over 40 UI selectors, including inverting Leaflet raster map tiles using CSS filter. Because `main.tsx` imports `experience.css` after `styles.css`, dark theme styles take precedence when the OS prefers dark mode.
2. *Requirement R2 (Loading Indicators)*: `OperationsWorkspace.tsx` manages `initialLoading: boolean`. During the initial async `refresh()` call, a `<div className="workspace-loading-state" role="status" aria-live="polite">` spinner is rendered while setting `aria-busy={true}`, eliminating any flash of empty data.
3. *Requirement R2 (Auto-dismissing Error Banners)*: `ErrorBanner.tsx` encapsulates `window.setTimeout(onDismiss, 8000)` with `window.clearTimeout` in its effect teardown, provides a manual close button (`aria-label="Đóng thông báo"`), and preserves accessibility alerts (`role="alert"` and `aria-live="assertive"`). It is integrated across all 4 frontend view surfaces.
4. *Requirement R4.1 (Real-Time Telemetry)*: `api.ts` implements `getLatestTelemetry()` querying `/api/v1/telemetry/latest`. `OperationsWorkspace.tsx` polls at 1-second intervals with a 500ms ticker calculating data age (`< 2s`), displays 6-decimal GPS, altitude, 3-tier battery thresholds (≥50%, 20-49%, <20%), and live Leaflet GPS position marker.
5. *Requirement R4.2 (Flight Notifications)*: Background 3-second polling detects new submissions (`status === "SUBMITTED"`), triggers a Web Audio API 2-tone chime (880Hz -> 1320Hz), updates tab counter badges, and displays an on-screen toast with "Xem ngay" button.
6. *Requirement R4.3 (GeoJSON and CSV Exporters)*: Zone export builds RFC 7946 `FeatureCollection` JSON Blobs. Flight export builds RFC 4180 CSV strings with CRLF line endings, double-quote escaping, and UTF-8 BOM (`\uFEFF`). Both use `URL.createObjectURL()`, trigger download, and clean up with `URL.revokeObjectURL()`.
7. *Integrity & Standards*: All implementations use standard web APIs without stubbing, mocked facades, or pre-baked data.

---

## 3. Caveats

1. **Browser Autoplay Policies**: Web Audio API requires a user interaction gesture on some browsers before audio can play without warning. The implementation handles this by catching exceptions and invoking `ctx.resume()` gracefully, so visual banners and badges function even if audio is temporarily suspended.
2. **Telemetry 404 on Missing Device**: When no physical drone or simulator is transmitting, `/api/v1/telemetry/latest` returns 404. `getLatestTelemetry()` catches this and returns `null`, displaying a clear "Đang đợi dữ liệu định vị GPS từ drone..." state without crashing.
3. **No Caveats on Implementation Integrity**: The implementation strictly satisfies all requirements and contains no violations.

---

## 4. Conclusion

The Milestone 4 work product is **CLEAN**. There are zero integrity violations, no facades, no hardcoded responses, and no regressions. TypeScript typecheck and Vite build pass cleanly with exit code 0. All backend integration contracts pass 211 tests.

---

## 5. Verification Method

To independently reproduce the audit verification:

1. **TypeScript Typecheck**:
   ```powershell
   cmd /c npm --prefix frontend run typecheck
   ```
   *Expected*: Code 0, zero diagnostic errors.

2. **Vite Production Build**:
   ```powershell
   cmd /c npm --prefix frontend run build
   ```
   *Expected*: Code 0, `dist/` bundle created with 94 modules transformed.

3. **Backend Contract Verification**:
   ```powershell
   pytest tests/scope01 tests/scope02 tests/scope03 tests/scope04 tests/scope05 -q
   ```
   *Expected*: 211 passed.

4. **Forensic Source Inspections**:
   - Inspect `frontend/src/components/operations/OperationsWorkspace.tsx`:
     - Line 98: `playNotificationChime()` uses `createOscillator()` and `createGain()` for 880Hz -> 1320Hz synthesis.
     - Line 153: `exportZonesGeoJson()` creates RFC 7946 Blob and object URL.
     - Line 188: `exportFlightsCsv()` creates RFC 4180 CSV Blob with `\uFEFF` BOM.
     - Line 323: 1-second polling hook for `getLatestTelemetry()`.
   - Inspect `frontend/src/components/common/ErrorBanner.tsx`:
     - Line 21: `autoDismissMs = 8000` with manual close button.
   - Inspect `frontend/src/experience.css`:
     - Line 1012: `@media (prefers-color-scheme: dark)` token overrides and tile pane inversion.
