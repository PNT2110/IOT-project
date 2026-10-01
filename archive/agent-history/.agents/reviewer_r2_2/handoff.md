# Handoff Report: Reviewer 2 (Frontend & Map Reviewer)

**Reviewer**: Reviewer 2 (`reviewer_r2_2` — Frontend & Map Reviewer / Adversarial Critic)  
**Recipient**: Orchestrator (`parent`, ID: `4778195a-e400-4dc6-9497-5cada5624654`)  
**Date**: 2026-09-10  
**Handoff Type**: Hard (Review Complete)  
**Report File**: `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\reviewer_r2_2\report.md`  
**Verdict**: **APPROVE**

---

## 1. Observation

1. **MapLibre Paint Expressions (`frontend/src/App.tsx:158-205`)**:
   - `flight-zones-fill` layer defines:
     - Color matching condition: matches `layer_id == 2`, string `'2'`, or `zone_type == 'restricted'` to `#ffb23e`; matches `layer_id == 1`, string `'1'`, or `zone_type == 'prohibited'` to `#ff4655`; fallback `#ff4655`.
     - `fill-opacity: 0.42`.
   - `flight-zones-line` layer defines:
     - Color matching condition: restricted to `#ffc769`; prohibited to `#ff6570`; fallback `#ff6570`.
     - `line-width: 2`.

2. **Interactive Popups & Hover Cursor (`frontend/src/App.tsx:207-244`)**:
   - Attached click listener on `'flight-zones-fill'` opening a `maplibregl.Popup` with Vietnamese labels:
     - `zoneTypeVi = isRestricted ? 'Vùng hạn chế bay' : 'Vùng cấm bay'`
     - Color badge matching zone type (`#ffb23e` or `#ff4655`).
     - Identifier: `<div><strong>Mã vùng (ID):</strong> ${zoneId}</div>`.
     - Name container: rendered when `props.name` is present.
   - Attached `mouseenter` and `mouseleave` listeners setting canvas cursor to `'pointer'` and `''`.
   - Single-instance popup management via `popupRef.current?.remove()`.

3. **Lifecycle Cleanup (`frontend/src/App.tsx:248-254`)**:
   - The effect cleanup callback explicitly calls:
     ```typescript
     popupRef.current?.remove()
     markerRef.current?.remove()
     mapRef.current?.remove()
     mapRef.current = null
     maplibregl.removeProtocol('pmtiles')
     ```
   - Prevents memory leaks and WebGL context leakage on unmount.

4. **MapLibre Stylesheet Import (`frontend/src/main.tsx:3`)**:
   - Verbatim line 3: `import 'maplibre-gl/dist/maplibre-gl.css'`.
   - Ensures standard MapLibre GL popup, navigation controls, and compass stylesheets are bundled into the CSS output.

5. **Frontend Build Toolchain Verification**:
   - Executed:
     ```powershell
     $env:PATH = "C:\Users\pnt21\AppData\Local\OpenAI\Codex\runtimes\cua_node\6a86821985684e13\bin;" + $env:PATH
     cd "c:\Users\pnt21\OneDrive\Máy tính\IOT\frontend"
     cmd /c "npm run build"
     ```
   - Build output:
     ```
     > iot-drone-station-ui@0.1.0 build
     > tsc -b && vite build

     vite v7.3.6 building client environment for production...
     transforming...
     ✓ 2815 modules transformed.
     rendering chunks...
     computing gzip size...
     dist/index.html                     0.55 kB │ gzip:   0.35 kB
     dist/assets/index-D5ahVnzE.css     78.95 kB │ gzip:  12.52 kB
     dist/assets/index-Dl-BWI13.js   2,584.97 kB │ gzip: 716.53 kB
     ✓ built in 17.06s
     ```
   - Exit code: `0`. Zero TypeScript diagnostic errors, zero bundler errors.

6. **Integrity Audit**:
   - Zero hardcoded mock responses in `App.tsx`.
   - Data is dynamically retrieved from `/api/v1/geofence/zones`.
   - Zero facade layers or bypassed features.

---

## 2. Logic Chain

1. **Visual Fidelity Compliance**:
   - Observation 1 demonstrates that `flight-zones-fill` and `flight-zones-line` strictly utilize the required colors: Prohibited fill `#ff4655`, Prohibited line `#ff6570`, Restricted fill `#ffb23e`, Restricted line `#ffc769`, and fill opacity `0.42`.
   - By matching against both integer `layer_id` and string variants as well as `zone_type`, the implementation guarantees correct visualization regardless of whether the source is parsed JSON or vector tiles.
2. **Operator Ergonomics & UX**:
   - Observation 2 confirms that clicking on any zone provides immediate, clear Vietnamese situational awareness ("Vùng cấm bay" / "Vùng hạn chế bay") alongside the numeric Zone ID.
   - The hover pointer cursor provides standard web map feedback to the pilot/operator that polygons are interactive.
3. **Application Stability & Memory Safety**:
   - Observations 2, 3, and 4 confirm that popups and map instances are cleaned up when unmounted or re-rendered, avoiding orphan DOM nodes and WebGL context accumulation.
4. **Production Readiness**:
   - Observation 5 establishes that the complete TypeScript codebase compiles under strict project compiler settings, and Vite successfully produces production bundles.
   - Observation 6 confirms full engineering integrity.

---

## 3. Caveats

1. **HTML Interpolation Hardening**:
   - In `App.tsx`, `popup.setHTML()` uses template literals with `props.name` and `props.id`. Because these come from the authoritative system dataset `zones.geojson`, this is safe in the current architecture. If user-generated GeoJSON is ever accepted in the future, standard DOM construction or sanitization should be added.
2. **Offline Tile Pack Dependency**:
   - The map container activates when `status.map_ready` is true (requiring `backend/data/maps/hcm.pmtiles`). In environments lacking the offline PMTiles file, the dashboard gracefully displays the placeholder (`Đang chờ map pack TPHCM`) until mounted.

---

## 4. Conclusion

**Verdict**: **APPROVE**

The frontend changes in `frontend/src/App.tsx`, `frontend/src/styles.css`, and `frontend/src/main.tsx` fully satisfy all requirements:
- Prohibited and restricted zones are correctly and distinctively styled.
- Interactive popups display accurate Vietnamese labels and Zone IDs.
- Hover pointer cursors and lifecycle cleanup operate cleanly.
- Frontend build succeeds with exit code 0.
- No integrity violations or blocking flaws exist.

---

## 5. Verification Method

To independently reproduce and verify this review:

1. **Verify Frontend Build & TypeScript Check**:
   ```powershell
   $env:PATH = "C:\Users\pnt21\AppData\Local\OpenAI\Codex\runtimes\cua_node\6a86821985684e13\bin;" + $env:PATH
   cd "c:\Users\pnt21\OneDrive\Máy tính\IOT\frontend"
   cmd /c "npm run build"
   ```
   *Expected Result*: Exits with code 0, 0 TypeScript errors, `dist/` generated.

2. **Inspect Layer Definitions in `App.tsx`**:
   Verify lines 158-205 in `frontend/src/App.tsx` for fill colors (`#ff4655`, `#ffb23e`), line colors (`#ff6570`, `#ffc769`), and opacity `0.42`.

3. **Inspect Popup & Cursor Handlers in `App.tsx`**:
   Verify lines 207-244 in `frontend/src/App.tsx` for `flight-zones-fill` click, `mouseenter`, `mouseleave`, and cleanup hooks.
