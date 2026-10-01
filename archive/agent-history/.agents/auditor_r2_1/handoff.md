# 5-Component Handoff Report: Forensic Integrity Audit (Milestone M1)

**Agent**: Forensic Auditor (`auditor_r2_1`)  
**Target Milestone**: Milestone M1 (Zone Integration & Map Visualization)  
**Recipient**: Parent Agent / Orchestrator (`4778195a-e400-4dc6-9497-5cada5624654`)  
**Date**: 2026-09-10  
**Handoff Type**: Hard (Audit Complete)  
**Report File**: `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\auditor_r2_1\report.md`  

---

## 1. Observation

1. **`backend/data/zones.geojson` Integrity**:
   - File size: Exactly `8,195,328` bytes (~7.82 MB).
   - SHA256 checksum: `a06204a4a2f6b92ebc0e2bfa32b8fe9740987cc209ab9b30f8f461ba857fdc0e`.
   - Feature count: Exactly `2,745` features (2,378 Prohibited with `layer_id=1`, 367 Restricted with `layer_id=2`).
   - Every feature contains properties `id`, `layer_id`, `zone_type`, `source`.
   - Shapely geometry analysis: `2,745` valid geometries (0 invalid). Bounding box: Longitude `[106.1279, 108.3247]`, Latitude `[8.5995, 11.9104]`.
   - Vertex counts vary between 4 and 1,635 vertices per polygon (mean: 71.1 vertices, total coordinates: 195,143).
   - Origin traces to vector tile extraction in `backend/app/zone_sync.py` querying `https://cambay.mod.gov.vn`.

2. **`backend/tests/test_zone_integration.py` Rigor**:
   - File contains 3 test functions (123 lines of code).
   - Tests assert: full 2,745 feature count, property schema compliance across all features, layer breakdown (2378 layer 1, 367 layer 2).
   - Tests evaluate `map_sync` freshness on live DB, and 5 distinct failure boundary cases on an isolated temporary database.
   - Tests run real coordinate evaluation via `GeofenceEngine`: Tan Son Nhat airport (`10.818, 106.652`) -> `breach`, `distance_m == 0`; outside point (`20.0, 105.0`) -> `safe`.
   - AST / Regex search across `backend/tests/` revealed **zero** `assert True` trivial shortcuts.

3. **`backend/data/drone.sqlite3` Synchronization**:
   - Query `SELECT * FROM map_sync WHERE id=1` returns:
     `{'id': 1, 'source_url': 'https://cambay.mod.gov.vn', 'fetched_at': '2026-09-09T19:48:18.889635+00:00', 'checksum': 'a06204a4a2f6b92ebc0e2bfa32b8fe9740987cc209ab9b30f8f461ba857fdc0e', 'feature_count': 2745, 'status': 'ready'}`.
   - Checksum in database matches the computed SHA256 of `backend/data/zones.geojson` byte-for-byte.
   - `geofence_sync_is_fresh()` executes against the database and returns `True`.

4. **`frontend/src/App.tsx` Implementation**:
   - `FlightMap` component (lines 129-250) incorporates real MapLibre GL paint expressions for `flight-zones-fill` and `flight-zones-line` with conditional styling (`#ff4655` red for prohibited, `#ffb23e` amber for restricted).
   - Event listener on `'click'` retrieves feature properties, formats Vietnamese zone type labels ("Vùng cấm bay" / "Vùng hạn chế bay"), displays zone ID, and displays a interactive `maplibregl.Popup`.
   - Event listeners on `'mouseenter'` and `'mouseleave'` dynamically update cursor styling to `'pointer'` and `''`.
   - Cleanup functions are registered in `useEffect` to remove popups and markers upon component unmount.
   - Authenticated backend endpoint `GET /api/v1/geofence/zones` serves the full 2,745 features to the frontend.

5. **Test and Build Toolchain Execution**:
   - `python -m pytest -v tests/test_zone_integration.py` in `backend/`: 3 passed in 1.98s.
   - `python -m pytest -v` in `backend/`: 86 passed, 1 skipped, 1 warning in 31.06s.
   - `npm run build` in `frontend/`: TypeScript compilation and Vite bundling completed with exit code 0 (`✓ built in 17.46s`).

---

## 2. Logic Chain

1. **Authentic Data Foundation**:
   - Direct inspection of `backend/data/zones.geojson` proves that the data is not a mockup or synthetic square. With 195,143 coordinates across 2,745 complex polygons strictly matching Vietnam airspace coordinates (WGS 84 RFC 7946), the dataset is authentic and originates from the Cambay MOD vector tile system.
2. **True System Synchronization**:
   - The database record in `map_sync` matches the file's SHA256 checksum exactly, has a fresh timestamp, and status `'ready'`. This allows `geofence_sync_is_fresh()` to return `True`, satisfying the drone station preflight health checks without bypassing security checks.
3. **Rigorous Integration Testing**:
   - The integration test suite (`test_zone_integration.py`) comprehensively checks feature counts, attribute presence, coordinate validity, SQLite query failure modes, and geofence breach/safe states. Zero cheat patterns or dummy facades exist.
4. **Authentic UI Visualization**:
   - `App.tsx` does not use static image stubs or dummy components; it uses standard MapLibre GL GeoJSON layers, vector styling expressions, interactive event handlers, and cleans up memory on unmount.
5. **No Regressions**:
   - All 86 backend tests and the complete frontend production build succeed cleanly.

---

## 3. Caveats

1. **Execution Directory for Backend Pytest**:
   - The backend configuration relies on `settings.data_dir`, which defaults to `./data`. When executing pytest or backend scripts from the project root (`c:\Users\pnt21\OneDrive\Máy tính\IOT`), `DRONE_DATA_DIR` should be set to `backend/data` (or commands should be executed directly with working directory `backend/`).
2. **Offline PMTiles Dependency for Map Display**:
   - `FlightMap` mounts when `status.map_ready` is true (i.e. when `backend/data/maps/hcm.pmtiles` exists). If the base offline vector tile pack is absent in development, the dashboard renders the fallback placeholder while zone data and geofence evaluation remain fully functional.

---

## 4. Conclusion

**VERDICT: CLEAN**

Milestone M1 (Zone Integration & Map Visualization) demonstrates total integrity:
- `backend/data/zones.geojson` is authentic and complete (2,745 features, 8.2 MB).
- `backend/tests/test_zone_integration.py` is rigorous and free of shortcuts or dummy facades.
- `backend/data/drone.sqlite3` `map_sync` table is properly updated and fresh.
- `frontend/src/App.tsx` has genuine MapLibre styling and interactive popup handlers.
- Both the backend pytest suite (86 passed) and frontend build (`npm run build`) pass cleanly.

---

## 5. Verification Method

To independently reproduce and verify this audit:

1. **Verify Zones GeoJSON & Geometry**:
   ```powershell
   cd "c:\Users\pnt21\OneDrive\Máy tính\IOT"
   python -c "import json; d=json.load(open('backend/data/zones.geojson', 'r', encoding='utf-8')); print('Features:', len(d['features']))"
   # Output: Features: 2745
   ```

2. **Verify SHA256 & SQLite Synchronization**:
   ```powershell
   cd "c:\Users\pnt21\OneDrive\Máy tính\IOT\backend"
   python -c "import hashlib, sqlite3; h=hashlib.sha256(open('data/zones.geojson', 'rb').read()).hexdigest(); cur=sqlite3.connect('data/drone.sqlite3').cursor(); cur.execute('SELECT checksum, status, feature_count FROM map_sync WHERE id=1'); r=cur.fetchone(); print('Checksum match:', h == r[0], '| Status:', r[1], '| Count:', r[2])"
   # Output: Checksum match: True | Status: ready | Count: 2745
   ```

3. **Verify Preflight Geofence Freshness**:
   ```powershell
   cd "c:\Users\pnt21\OneDrive\Máy tính\IOT\backend"
   python -c "from app.main import geofence_sync_is_fresh; print('Fresh:', geofence_sync_is_fresh())"
   # Output: Fresh: True
   ```

4. **Execute Pytest Integration & Full Suite**:
   ```powershell
   cd "c:\Users\pnt21\OneDrive\Máy tính\IOT\backend"
   python -m pytest -v tests/test_zone_integration.py
   python -m pytest -v
   # Output: 86 passed, 1 skipped, 1 warning
   ```

5. **Execute Frontend Production Build**:
   ```powershell
   $env:PATH = "C:\Users\pnt21\AppData\Local\OpenAI\Codex\runtimes\cua_node\6a86821985684e13\bin;" + $env:PATH
   cd "c:\Users\pnt21\OneDrive\Máy tính\IOT\frontend"
   cmd /c "npm run build"
   # Output: built in ~17s, exit code 0
   ```
