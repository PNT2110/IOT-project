# Handoff Report: Frontend Map Visualization & No-Fly Zone Rendering Analysis

**Author:** Explorer 3 (Frontend Map Visualization Researcher)  
**Recipient:** Orchestrator (`parent`, ID: `4778195a-e400-4dc6-9497-5cada5624654`)  
**Date:** 2026-09-10  
**Handoff Type:** Hard (Task Complete)  
**Report File:** `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_r2_3\report.md`  

---

## 1. Observation

1. **Map Component Location & Implementation**:
   - File: `frontend/src/App.tsx:129-177` (`FlightMap` component).
   - Line 145: MapLibre map initialization:
     ```typescript
     mapRef.current = new maplibregl.Map({ container: container.current, style, center: [106.7, 10.78], zoom: 9 })
     ```
   - Center coordinate is `[106.7, 10.78]` in `[longitude, latitude]` format (HCMC). Initial zoom level is `9`.
   - Line 149:
     ```typescript
     const response = await fetch('/api/v1/geofence/zones', { credentials: 'same-origin' })
     if (!response.ok || !mapRef.current) return
     const zones = await response.json()
     mapRef.current.addSource('flight-zones', { type: 'geojson', data: zones })
     ```
   - Lines 153–154:
     ```typescript
     mapRef.current.addLayer({ id: 'flight-zones-fill', type: 'fill', source: 'flight-zones', paint: { 'fill-color': ['match', ['get', 'layer_id'], 1, '#ff4655', 2, '#ffb23e', '#ff4655'], 'fill-opacity': 0.42 } })
     mapRef.current.addLayer({ id: 'flight-zones-line', type: 'line', source: 'flight-zones', paint: { 'line-color': ['match', ['get', 'layer_id'], 1, '#ff6570', 2, '#ffc769', '#ff6570'], 'line-width': 2 } })
     ```

2. **Styling and Color Conventions**:
   - `layer_id == 1` (`prohibited`): Fill `#ff4655`, outline `#ff6570`, outline width `2px`, opacity `0.42`.
   - `layer_id == 2` (`restricted`): Fill `#ffb23e`, outline `#ffc769`, outline width `2px`, opacity `0.42`.
   - Line 174 (Legend):
     ```tsx
     <div className="map-legend"><span className="danger-dot" /> Vùng cấm <span className="warn-dot" /> Vùng hạn chế <span className="drone-dot" /> Drone</div>
     ```
   - In `frontend/src/styles.css:1`:
     `.danger-dot` uses `var(--red)` (`#ff5d68`).
     `.warn-dot` uses `var(--amber)` (`#ffbe55`).
     `.drone-dot` uses `var(--teal)` (`#21d6b5`).

3. **Absence of Interactive Popups / Tooltips**:
   - In `frontend/src/App.tsx:129-177`, there are no event handlers for `click`, `mouseenter`, or `mouseleave` on `flight-zones-fill` or `flight-zones-line`.
   - Clicking or hovering on polygons produces no visual readout or popup showing zone name, zone ID, or flight restrictions.

4. **Frontend Build Toolchain & Clean Build Verification**:
   - Toolchain: Vite 7.3.6, TypeScript 5.9.2, React 19.1.1.
   - Node runtime: Node.js v24.19.0 located at `C:\Users\pnt21\AppData\Local\OpenAI\Codex\runtimes\cua_node\6a86821985684e13\bin\node.exe`.
   - Command executed:
     ```powershell
     $env:PATH = "C:\Users\pnt21\AppData\Local\OpenAI\Codex\runtimes\cua_node\6a86821985684e13\bin;" + $env:PATH
     cmd /c "npm run build"
     ```
   - Verbatim result:
     ```text
     > iot-drone-station-ui@0.1.0 build
     > tsc -b && vite build

     vite v7.3.6 building client environment for production...
     transforming...
     ✓ 2815 modules transformed.
     rendering chunks...
     computing gzip size...
     dist/index.html                     0.55 kB │ gzip:   0.35 kB
     dist/assets/index-D5ahVnzE.css     78.95 kB │ gzip:  12.52 kB
     dist/assets/index-BIFDHDC7.js   2,583.16 kB │ gzip: 715.98 kB
     ✓ built in 21.91s
     ```
   - Clean exit code 0; 0 TypeScript errors, 0 lint/bundling errors.

5. **Historical Context from Project Status & Worklog**:
   - `WORKLOG.md:44`: "Đồng bộ 2.745 vùng cấm/hạn chế từ vector tile chính thức của `cambay.mod.gov.vn`; lớp 1 là cấm bay, lớp 2 là hạn chế bay."
   - `backend/data/zones.geojson` contains 2,745 features (2,378 `prohibited` with `layer_id=1`, 367 `restricted` with `layer_id=2`).
   - The original/intended visualization design is strictly: Layer 1 = Red (#ff4655) and Layer 2 = Amber (#ffb23e).

---

## 2. Logic Chain

1. **Layer ID vs Property Name Sensitivity**:
   - From Observation 1, the MapLibre paint style strictly checks `['get', 'layer_id']` expecting integer `1` or `2`.
   - If legacy or converted GeoJSON provides properties with `zone_type: 'prohibited'` / `'restricted'` or string numbers (`layer_id: "1"`), the strict match fails and defaults to red `#ff4655`.
   - Therefore, the style expression should be reinforced with `coalesce` or `to-string` to support both `zone_type` and `layer_id` without breaking backwards compatibility.

2. **Coordinate Standard Adherence**:
   - From Observation 1, MapLibre GL constructs map projections using `[longitude, latitude]`.
   - If GeoJSON coordinates are inverted (`[latitude, longitude]`), the polygons will render off the coast of East Africa (~10°E, 106°N), disappearing completely from the Vietnam map view.
   - Therefore, GeoJSON data must strictly maintain `[longitude, latitude]` ordering.

3. **Operator Interaction Needs**:
   - From Observation 3, there is currently no popup or tooltip when clicking or hovering on no-fly zones.
   - For an operational drone ground station, the pilot must be able to click a zone to inspect its name, type, and identifier.
   - Adding a lightweight MapLibre `Popup` on `'click'` and cursor styling on `'mouseenter'`/`'mouseleave'` fulfills this requirement without altering existing DOM layout.

4. **Build Integrity**:
   - From Observation 4, `npm run build` succeeds cleanly in 21.91s with TypeScript strict checks enabled.
   - Any modifications to `frontend/src/App.tsx` must preserve strict TypeScript typing (e.g. MapLibre event handler signatures) so that future CI builds never break.

---

## 3. Caveats

1. **Map Ready Precondition**: `FlightMap` requires `status.map_ready` to be `true` to instantiate MapLibre; otherwise it displays an offline placeholder (`Đang chờ map pack TPHCM`). If testing in an environment where PMTiles are not yet downloaded, `status.map_ready` will be false.
2. **WebGL Context in Headless Testing**: MapLibre GL requires WebGL support. Headless Node.js environments (like Jest/JSDOM) cannot render MapLibre canvas without WebGL mocks. Manual browser inspection or Playwright with GPU flags is required for full visual verification.

---

## 4. Conclusion

1. The current frontend map visualization in `frontend/src/App.tsx` correctly renders `prohibited` zones in red (`#ff4655`) and `restricted` zones in amber (`#ffb23e`) with `0.42` opacity and `2px` border lines.
2. To ensure the no-fly zone data renders identically to the original and handles any property structure variations, `frontend/src/App.tsx` should be updated to:
   - Enhance the paint expressions to gracefully handle both `zone_type` ('prohibited' / 'restricted') and `layer_id` (1 / 2, numeric or string).
   - Add interactive `maplibregl.Popup` on zone click displaying zone name, type badge, and ID.
   - Set pointer cursor on `'mouseenter'` and revert on `'mouseleave'`.
3. The frontend build environment compiles cleanly via `npm run build` (`tsc -b && vite build`) on Node v24.19.0 with 0 errors.

---

## 5. Verification Method

To independently verify the frontend map build and visualization:

1. **Verify Frontend Build**:
   ```powershell
   $env:PATH = "C:\Users\pnt21\AppData\Local\OpenAI\Codex\runtimes\cua_node\6a86821985684e13\bin;" + $env:PATH
   cd "c:\Users\pnt21\OneDrive\Máy tính\IOT\frontend"
   cmd /c "npm run build"
   ```
   *Expected Result*: Exits with code 0, `✓ built in ~22s`, output in `frontend/dist/`.

2. **Verify MapLibre Styling Code**:
   Inspect lines 145–158 of `frontend/src/App.tsx` using `view_file` to confirm layer IDs, paint match rules, and fill/line colors.

3. **Verify API Endpoint Connectivity**:
   ```powershell
   python -c "import json; from app.config import settings; print('Zones exist:', settings.zones_path.exists()); print('Feature count:', len(json.loads(settings.zones_path.read_text(encoding='utf-8'))['features']))"
   ```
   *Expected Result*: `Zones exist: True`, `Feature count: 2745`.
