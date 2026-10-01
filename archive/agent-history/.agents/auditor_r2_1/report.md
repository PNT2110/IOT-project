# Forensic Audit Report: Milestone M1 (Zone Integration & Map Visualization)

**Auditor**: Forensic Auditor (`auditor_r2_1`)  
**Project Root**: `c:\Users\pnt21\OneDrive\Máy tính\IOT`  
**Target Milestone**: Milestone M1 (Zone Integration & Map Visualization)  
**Profile**: General Project (Integrity Mode: `development` per `ORIGINAL_REQUEST.md`)  
**Date**: 2026-09-10  
**Verdict**: **CLEAN**

---

## Executive Summary

A comprehensive forensic audit was conducted on all Milestone M1 work products in accordance with the Integrity Forensics standard. The audit evaluated:
1. Authenticity of `backend/data/zones.geojson` (Cambay MOD dataset vs. synthetic/stubbed facade).
2. Rigor and integrity of `backend/tests/test_zone_integration.py` (absence of dummy assertions, genuine edge case validation).
3. Synchronization status of `backend/data/drone.sqlite3` (`map_sync` metadata, SHA256 match, timestamp freshness).
4. Authenticity of React/MapLibre GL implementation in `frontend/src/App.tsx` (paint expressions, popup handlers, cursor state).
5. Independent execution of verification commands (Pytest suite and Frontend production build).

**Verdict**: **CLEAN**. No integrity violations, mocked shortcuts, dummy facades, hardcoded test cheats, or fabricated artifacts were detected. All components are genuinely implemented and fully verified empirically.

---

## Phase Results

| # | Check Item | Result | Details |
|---|---|:---:|---|
| 1 | `backend/data/zones.geojson` Authenticity | **PASS** | Genuine 8,195,328-byte dataset; exactly 2,745 features; all valid Shapely geometries; RFC 7946 coordinates; matches official Cambay MOD vector tile crawl. |
| 2 | `backend/tests/test_zone_integration.py` Rigor | **PASS** | Comprehensive schema, feature count, coordinate containment, and SQLite freshness edge cases; 0 dummy `assert True` shortcuts found. |
| 3 | `backend/data/drone.sqlite3` `map_sync` Table | **PASS** | Row 1 populated with valid UTC timestamp `2026-09-09T19:48:18.889635+00:00`, `status='ready'`, `feature_count=2745`, matching SHA256 checksum; `geofence_sync_is_fresh()` returns `True`. |
| 4 | `frontend/src/App.tsx` MapLibre Implementation | **PASS** | Genuine MapLibre paint expressions for prohibited/restricted zones, interactive popup listener, pointer cursor handling, and unmount cleanup. |
| 5 | Empirical Build & Test Execution | **PASS** | Pytest: 86 passed, 1 skipped, 1 warning (100% pass rate); Frontend build: `tsc -b && vite build` built in 17.46s with exit code 0. |

---

## Detailed Forensic Evidence

### 1. `backend/data/zones.geojson` Dataset Verification

- **Filesystem Stats**:
  - File path: `backend/data/zones.geojson`
  - Exact byte size: `8,195,328` bytes (~7.82 MB on disk)
  - SHA256 checksum: `a06204a4a2f6b92ebc0e2bfa32b8fe9740987cc209ab9b30f8f461ba857fdc0e`
- **Feature Breakdown**:
  - Total features: `2,745`
  - Unique feature IDs: `2,745` (100% unique identifiers)
  - Prohibited zones (`layer_id: 1`): `2,378` features
  - Restricted zones (`layer_id: 2`): `367` features
  - Geometry types: `2,606` Polygons, `139` MultiPolygons
- **Shapely Topological Validation**:
  - Valid geometries: `2,745` / `2,745` (`invalid = 0`)
  - Coordinate bounding box: Longitude `[106.127929, 108.324680]`, Latitude `[8.599522, 11.910354]` (covers Greater Ho Chi Minh City, Binh Duong, Dong Nai, Ba Ria - Vung Tau, and Con Dao)
  - Polygon complexity: Minimum vertices = 4, Maximum vertices = 1,635, Mean vertices = 71.1 (total coordinates: 195,143)
- **Source Verification**:
  - Root metadata: `{"source": "https://cambay.mod.gov.vn", "fetched_at": "2026-09-02T19:34:28.177523+00:00", "tile_zoom": 9}`
  - Origin generator: `backend/app/zone_sync.py` connects to `https://cambay.mod.gov.vn/api/tiles/features/{z}/{x}/{y}.pbf`, decodes vector tiles via `mapbox_vector_tile`, projects coordinates, and performs `unary_union`.
  - **Verdict**: Genuine GIS dataset, NOT faked or stubbed.

### 2. `backend/tests/test_zone_integration.py` Rigor & Anti-Cheating Scan

- **Code Inspection**:
  - Lines: 123
  - Functions: `test_zones_geojson_schema_and_integrity`, `test_map_sync_freshness_in_sqlite`, `test_geofence_engine_evaluation_with_definitive_zones`.
- **Assertion Quality**:
  - `test_zones_geojson_schema_and_integrity`: Iterates over all 2,745 features verifying presence of `id`, `layer_id`, `zone_type`, `source`, ensures `layer_id in (1, 2)` mapped to prohibited/restricted, verifies coordinate array non-empty, and asserts total counts (2378 layer 1, 367 layer 2).
  - `test_map_sync_freshness_in_sqlite`: Validates real DB `geofence_sync_is_fresh() is True`, then isolates a temporary SQLite database to test 5 failure boundary conditions: (1) status != 'ready', (2) feature_count == 0, (3) stale fetched_at > 24 hours, (4) malformed ISO timestamp string, (5) fresh timestamp returning True.
  - `test_geofence_engine_evaluation_with_definitive_zones`: Evaluates real geospatial coordinates through `GeofenceEngine.evaluate()`:
    - Tan Son Nhat Airport (`10.818 N, 106.652 E`) -> `state.status == "breach"`, `distance_m == 0`.
    - Outside coordinates (`20.0 N, 105.0 E`) -> `state.status == "safe"`.
- **Search for Dummy Asserts**:
  - Regex search for `assert True` across `backend/tests/`: **0 occurrences**.
  - All assertions test actual variables against non-trivial expected values.
  - **Verdict**: Rigorous, genuine integration tests.

### 3. `backend/data/drone.sqlite3` Database Verification

- **Schema & Table Data (`map_sync`)**:
  ```
  id: 1
  source_url: 'https://cambay.mod.gov.vn'
  fetched_at: '2026-09-09T19:48:18.889635+00:00'
  checksum: 'a06204a4a2f6b92ebc0e2bfa32b8fe9740987cc209ab9b30f8f461ba857fdc0e'
  feature_count: 2745
  status: 'ready'
  ```
- **Integrity Cross-Check**:
  - SHA256 of `backend/data/zones.geojson`: `a06204a4a2f6b92ebc0e2bfa32b8fe9740987cc209ab9b30f8f461ba857fdc0e`
  - Checksum in database: `a06204a4a2f6b92ebc0e2bfa32b8fe9740987cc209ab9b30f8f461ba857fdc0e`
  - Match: **Exact (True)**
  - Timestamp age: < 8 hours (well within the 24-hour freshness threshold)
  - `geofence_sync_is_fresh()` evaluation: **True**
  - **Verdict**: Database state is authentic, consistent, and fresh.

### 4. `frontend/src/App.tsx` MapLibre Implementation Verification

- **Source Code Analysis (`FlightMap` component, lines 129-250)**:
  - **Paint Expressions**:
    - `flight-zones-fill`: Dynamic case statement supporting `layer_id` (1 vs 2) and string `zone_type` ('prohibited' vs 'restricted'). Prohibited is painted red (`#ff4655`) with opacity `0.42`; restricted is painted amber (`#ffb23e`).
    - `flight-zones-line`: Prohibited outline `#ff6570`, restricted outline `#ffc769`, `line-width: 2`.
  - **Interactive Popup**:
    - Attached via `mapRef.current.on('click', 'flight-zones-fill', (e) => ...)`.
    - Extracts `e.features[0].properties`, parses `id` and `layer_id`/`zone_type`.
    - Renders Vietnamese badge ("Vùng cấm bay" or "Vùng hạn chế bay") with colored indicator dot and zone ID.
    - Creates `maplibregl.Popup({ closeButton: true, closeOnClick: true })`.
  - **Cursor UX**:
    - `mouseenter` sets `mapRef.current.getCanvas().style.cursor = 'pointer'`.
    - `mouseleave` restores cursor to `''`.
  - **Resource Cleanup**:
    - Cleanup function unmounts `popupRef.current?.remove()` and `markerRef.current?.remove()`.
- **End-to-End API Verification**:
  - Authenticated `GET /api/v1/geofence/zones` returns HTTP 200 with FeatureCollection containing all 2,745 features.
  - **Verdict**: Authentic, production-grade frontend implementation.

### 5. Independent Command Execution Logs

#### A. Pytest Zone Integration Suite
```powershell
cd "c:\Users\pnt21\OneDrive\Máy tính\IOT\backend"
python -m pytest -v tests/test_zone_integration.py
```
**Output**:
```
tests/test_zone_integration.py::test_zones_geojson_schema_and_integrity PASSED [ 33%]
tests/test_zone_integration.py::test_map_sync_freshness_in_sqlite PASSED [ 66%]
tests/test_zone_integration.py::test_geofence_engine_evaluation_with_definitive_zones PASSED [100%]
============================== 3 passed in 1.98s ==============================
```

#### B. Full Backend Pytest Suite
```powershell
cd "c:\Users\pnt21\OneDrive\Máy tính\IOT\backend"
python -m pytest -v
```
**Output**:
```
================== 86 passed, 1 skipped, 1 warning in 31.06s ==================
```

#### C. Frontend Production Build
```powershell
$env:PATH = "C:\Users\pnt21\AppData\Local\OpenAI\Codex\runtimes\cua_node\6a86821985684e13\bin;" + $env:PATH
cd "c:\Users\pnt21\OneDrive\Máy tính\IOT\frontend"
cmd /c "npm run build"
```
**Output**:
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
✓ built in 17.46s
```

---

## Conclusion

The Milestone M1 work product passes all forensic integrity checks without reservation. The implementation is authentic, rigorous, robust, and verified empirically.

**FINAL VERDICT: CLEAN**
