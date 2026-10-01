# Backend Geofence Implementation & Legacy Data Integration Analysis

**Author:** Explorer 2 (Backend Geofence Researcher)  
**Date:** 2026-09-10  
**Status:** Completed Analysis & Technical Recommendations  
**Working Directory:** `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_r2_2`  
**Project Root:** `c:\Users\pnt21\OneDrive\Máy tính\IOT`  

---

## 1. Executive Summary

This investigation provides a comprehensive analysis of the backend geofence subsystem in the IOT Drone Station project. The study examined the current zone data store (`backend/data/zones.geojson`), the spatial evaluation engine (`backend/app/geofence.py`), vector tile ingestion (`backend/app/zone_sync.py`), FastAPI API endpoints in `backend/app/main.py` (specifically `/api/v1/geofence/zones`, `/api/v1/geofence/sync`, and `/api/v1/preflight`), and the backend test suite (`backend/tests/`).

### Primary Takeaways
1. **Strict Coordinate Ordering**: The backend strictly adheres to the GeoJSON RFC 7946 standard: **`[longitude, latitude]`** (X = longitude, Y = latitude). In `backend/app/geofence.py:46`, the evaluation point is instantiated as `Point(fix.longitude, fix.latitude)`. Shapely evaluates `geometry.covers(point)` assuming polygon coordinates map directly to `(x=lon, y=lat)`. If legacy data has inverted coordinates (`[latitude, longitude]`), the point will never intersect the polygon (~95 degrees apart in coordinate space), and containment/breach detection will completely fail.
2. **Current `zones.geojson` Profile**: The existing file contains **2,745 features** (2,606 Polygons and 139 MultiPolygons) covering Greater Ho Chi Minh City and Con Dao (`lon [106.128, 108.325]`, `lat [8.600, 11.910]`), totaling 8.2 MB. Each feature has properties: `id` (string), `layer_id` (integer: 1 for prohibited, 2 for restricted), `zone_type` (string: "prohibited" or "restricted"), and `source` ("https://cambay.mod.gov.vn"). There are 2,378 prohibited zones and 367 restricted zones.
3. **Property Schema Expectations**: In `geofence.py:53`, the backend checks `properties.get("name", properties.get("rawName", "Vùng kiểm soát"))`. In `App.tsx:153-154`, the frontend relies on `properties.layer_id` (1 = `#ff4655` red for prohibited, 2 = `#ffb23e` amber for restricted). Any integrated legacy data must include `layer_id` (1 or 2) and `name` to ensure both map visualization and telemetry breach alerts render correctly.
4. **Test Suite Decoupling**: Running `python -m pytest -v` in `backend/` passes **78/78 tests** (1 skipped, 1 warning). **Zero tests assert on the count, coordinates, or properties of `backend/data/zones.geojson`**. `test_core.py:25` creates an isolated single-zone fixture in `tmp_path`, and `test_api.py:37` tests RBAC 403 on `/api/v1/geofence/zones`. Modifying or replacing `zones.geojson` will not break any existing test.
5. **Preflight Interlock (Caveat)**: In `main.py:54-63`, `geofence_sync_is_fresh()` checks SQLite table `map_sync` in `drone.sqlite3` for `status='ready'`, `feature_count > 0`, and `fetched_at` within 24 hours. When replacing `zones.geojson` with legacy data, the `map_sync` record must be updated with the new feature count and current timestamp; otherwise `/api/v1/preflight` will report `geofence: false` and prevent drone ARM.

---

## 2. Backend Geofence Architecture & File Mapping

### 2.1 File Map

| Component | File Path | Key Class / Function / Endpoint | Role |
|---|---|---|---|
| Zone Data | `backend/data/zones.geojson` | GeoJSON FeatureCollection | 2,745 features, 8,195,328 bytes on disk |
| Spatial Engine | `backend/app/geofence.py` | `GeofenceEngine.load()`, `GeofenceEngine.evaluate()` | Shapely point-in-polygon & Haversine distance |
| Scraper / Sync | `backend/app/zone_sync.py` | `sync_zones()` | Scrapes vector tiles from cambay.mod.gov.vn |
| API Endpoints | `backend/app/main.py:245` | `GET /api/v1/geofence/zones` | Returns JSON of `zones.geojson` to authenticated admin |
| Sync Endpoint | `backend/app/main.py:252` | `POST /api/v1/geofence/sync` | Scrapes cambay tiles and updates DB checksum |
| Preflight Check | `backend/app/main.py:211` | `GET /api/v1/preflight` | Enforces `geofence.data_ready and zone_sync_fresh` |
| Telemetry Loop | `backend/app/main.py:27` | `telemetry_loop()` | Evaluates geofence at 5 Hz (200 ms interval) |
| Safety Loop | `backend/app/main.py:66` | `safety_command_loop()` | Dispatches `LAND("GEOFENCE_BREACH")` on breach |
| Configuration | `backend/app/config.py` | `Settings.zones_path` | Defaults to `Path("./data/zones.geojson")` |
| Database | `backend/app/db.py` | `map_sync` table | Caches sync metadata, checksum, feature count, timestamp |
| Core Tests | `backend/tests/test_core.py` | `test_geofence_inside_outside_warning` | Tests Shapely inside/outside logic using `tmp_path` |
| API Tests | `backend/tests/test_api.py` | `test_role_boundaries_csrf_and_command_lock` | Tests RBAC 403 on `/api/v1/geofence/zones` |

*(Note on Dispatch Path: The user/parent prompt specified `backend/app/services/geofence.py`. In the actual repository layout, there is no `services/` directory; the module is located at `backend/app/geofence.py` directly).*

### 2.2 Call Graph and Data Flow

```
                [FastAPI Startup (main.py:lifespan)]
                               │
                               ▼
                   geofence.load() (geofence.py:30)
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
    backend/data/zones.geojson         shapely.geometry.shape()
                │                             │
                └──────────────┬──────────────┘
                               │
                               ▼
                self.zones = list[tuple[Polygon/MultiPolygon, dict]]
                               │
┌──────────────────────────────┼──────────────────────────────┐
│                              │                              │
▼                              ▼                              ▼
[telemetry_loop() 5 Hz]    [safety_command_loop() 10 Hz]    [GET /api/v1/geofence/zones]
       │                              │                              │
geofence.evaluate(gps)      if status == 'breach':          Reads zones_path
       │                    dispatcher.land('GEOFENCE_BREACH') Returns JSON directly
state.frame.geofence = res
```

---

## 3. Deep Dive: `backend/data/zones.geojson` Structure

### 3.1 Metadata & Feature Collection
```json
{
  "type": "FeatureCollection",
  "metadata": {
    "source": "https://cambay.mod.gov.vn",
    "fetched_at": "2026-09-02T19:34:28.177523+00:00",
    "tile_zoom": 9
  },
  "features": [ ... ]
}
```

### 3.2 Geometry Breakdown
- **Total Features**: 2,745
- **Polygons**: 2,606 (94.93%)
- **MultiPolygons**: 139 (5.07%)
- **Coordinate Bounds**:
  - Longitude: `[106.1279° E, 108.3247° E]`
  - Latitude: `[8.5995° N, 11.9104° N]`

### 3.3 Property Schema
Properties per feature:
- `id` (string): Feature identifier (e.g. `"14129"`, `"14708"`).
- `layer_id` (integer):
  - `1`: Prohibited zone (`"prohibited"`) — **2,378 features**.
  - `2`: Restricted zone (`"restricted"`) — **367 features**.
- `zone_type` (string): Either `"prohibited"` or `"restricted"`.
- `source` (string): `"https://cambay.mod.gov.vn"`.

Example Feature:
```json
{
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [
      [
        [106.74144744873047, 10.50249657168559],
        [106.74144744873047, 10.498952055273376],
        [106.73990249633789, 10.498952055273376],
        [106.74144744873047, 10.50249657168559]
      ]
    ]
  },
  "properties": {
    "id": "14129",
    "layer_id": 1,
    "zone_type": "prohibited",
    "source": "https://cambay.mod.gov.vn"
  }
}
```

*(Note: Features in `zones.geojson` do not currently have `name`, `min_altitude`, or `max_altitude` properties).*

---

## 4. Coordinate System, Parsing & Spatial Evaluation Logic

### 4.1 Coordinate Order: Longitude First `[lon, lat]`
- **RFC 7946 Standard**: Mandates `[longitude, latitude]`.
- **Shapely Ingestion (`geofence.py:38`)**:
  ```python
  self.zones.append((shape(geometry), feature.get("properties", {})))
  ```
  Shapely treats `coord[0]` as X and `coord[1]` as Y.
- **Evaluation Point (`geofence.py:46`)**:
  ```python
  point = Point(fix.longitude, fix.latitude)
  ```
  Constructs Point with `x = fix.longitude` and `y = fix.latitude`.
- **Point-in-Polygon Check**:
  `geometry.covers(point)` compares `x` with `x` (lon) and `y` with `y` (lat).
- **Inverted Coordinate Failure Mode**:
  If legacy data is `[latitude, longitude]`, Shapely assigns `x = lat (~10.8)` and `y = lon (~106.6)`. GPS coordinates produce `point.x = 106.6` and `point.y = 10.8`. Containment checks will never trigger (`False`), and distance calculations will report ~15,000 km, entirely breaking safety interlocks.

### 4.2 Point-in-Polygon Algorithm & Performance
- `GeofenceEngine.evaluate()` iterates linearly over `self.zones`:
  1. Calls `geometry.covers(point)`. If `True`, returns `status="breach"`, `distance_m=0`.
  2. If outside all zones: computes `nearest_points(point, geometry)[1]` and Haversine distance in meters.
  3. If minimum distance <= `settings.geofence_warning_m` (100 m), returns `status="warning"`.
  4. Otherwise, returns `status="safe"`.
- **Benchmark Timing on Current 2,745 Zones**:
  - Load 2,745 zones: **476.6 ms**.
  - Breach evaluation (Tan Son Nhat airport): **55.8 ms** (early exit).
  - Outside evaluation (all 2,745 polygons tested): **110.8 ms**.
  - *Legacy Data Advantage*: If legacy data has fewer zones (e.g. 5–50 zones), evaluation takes `< 1.0 ms`, eliminating CPU latency in `telemetry_loop()` (runs at 5 Hz / 200 ms).

---

## 5. Backend Test Suite Analysis

### 5.1 Test Execution Results
- Command: `python -m pytest -v` in `backend/` (Python 3.12).
- Results: **78 passed, 1 skipped, 1 warning in 21.55s** (100% Green).

### 5.2 Zone-Related Test Assertions
1. `backend/tests/test_core.py::test_geofence_inside_outside_warning` (lines 25–51):
   - Creates a synthetic isolated GeoJSON in pytest fixture `tmp_path`:
     `coordinates: [[[106.6, 10.7], [106.8, 10.7], [106.8, 10.9], [106.6, 10.9], [106.6, 10.7]]]`
     `properties: {"id": "zone-1", "name": "Vùng thử"}`
   - Asserts `inside.status == "breach"` and `outside.status == "safe"`.
   - **Does NOT depend on `backend/data/zones.geojson`**.
2. `backend/tests/test_api.py::test_role_boundaries_csrf_and_command_lock` (line 37):
   - Asserts `client.get("/api/v1/geofence/zones").status_code == 403` for viewer role.
   - **Does NOT inspect payload body**.
3. `backend/tests/test_core.py::test_command_times_out_after_three_attempts`:
   - Checks dispatcher handling `"GEOFENCE_BREACH"` reason.

**Conclusion**: Zero pytest tests depend on the data in `backend/data/zones.geojson`. Replacing or augmenting `zones.geojson` will not cause test regressions.

---

## 6. Preflight & Database Freshness Interlock Analysis

In `backend/app/main.py:54-63`:
```python
def geofence_sync_is_fresh() -> bool:
    with db.connect() as conn:
        row = conn.execute("SELECT fetched_at,feature_count,status FROM map_sync WHERE id=1").fetchone()
    if not row or row["status"] != "ready" or int(row["feature_count"]) <= 0 or not row["fetched_at"]:
        return False
    try:
        fetched_at = datetime.fromisoformat(row["fetched_at"])
    except ValueError:
        return False
    return datetime.now(timezone.utc) - fetched_at.astimezone(timezone.utc) <= timedelta(hours=24)
```

In `GET /api/v1/preflight`:
```python
"geofence": frame.geofence.data_ready and zone_sync_fresh,
"geofence_sync_fresh": zone_sync_fresh,
```

**Crucial Operational Consideration**:
- `map_sync` in `drone.sqlite3` records the sync status.
- Currently, `fetched_at = 2026-09-02T19:34:28.177523+00:00` (> 24 hours old).
- On 2026-09-10, `geofence_sync_is_fresh()` returns `False`.
- When legacy data is written to `zones.geojson`, an SQL statement must update `map_sync` with the new feature count and current timestamp so that preflight passes.

---

## 7. Frontend MapLibre Styling (`App.tsx`)

In `frontend/src/App.tsx:147-158`:
```typescript
const response = await fetch('/api/v1/geofence/zones', { credentials: 'same-origin' })
const zones = await response.json()
mapRef.current.addSource('flight-zones', { type: 'geojson', data: zones })
mapRef.current.addLayer({
  id: 'flight-zones-fill',
  type: 'fill',
  source: 'flight-zones',
  paint: {
    'fill-color': ['match', ['get', 'layer_id'], 1, '#ff4655', 2, '#ffb23e', '#ff4655'],
    'fill-opacity': 0.42
  }
})
mapRef.current.addLayer({
  id: 'flight-zones-line',
  type: 'line',
  source: 'flight-zones',
  paint: {
    'line-color': ['match', ['get', 'layer_id'], 1, '#ff6570', 2, '#ffc769', '#ff6570'],
    'line-width': 2
  }
})
```

- Prohibited zones (`layer_id = 1`): Red fill (`#ff4655`), red border (`#ff6570`).
- Restricted zones (`layer_id = 2`): Orange fill (`#ffb23e`), amber border (`#ffc769`).
- Default fallback: Red (`#ff4655`).

---

## 8. Concrete Recommendations for Legacy Data Integration

1. **Coordinate Conversion**:
   - Ensure all coordinates are `[longitude, latitude]`.
   - Ensure each linear ring is closed (`ring[0] == ring[-1]`).
2. **Property Schema Mapping**:
   - `id`: unique string (e.g. `"legacy-1"` or original ID).
   - `name`: string in Vietnamese (e.g. `"Sân bay Tân Sơn Nhất"`).
   - `layer_id`: integer `1` for Prohibited, `2` for Restricted.
   - `zone_type`: string `"prohibited"` or `"restricted"`.
   - `source`: `"legacy"`.
3. **Database Preflight Sync**:
   - Execute an SQL update on `backend/data/drone.sqlite3`:
     ```sql
     UPDATE map_sync SET
         source_url='legacy',
         fetched_at='<CURRENT_UTC_ISO>',
         checksum='<SHA256_OF_GEOJSON>',
         feature_count=<NEW_COUNT>,
         status='ready'
     WHERE id=1;
     ```
4. **Backend Endpoint**:
   - `GET /api/v1/geofence/zones` requires no code modification; it reads `settings.zones_path` directly.
5. **Regression Unit Test**:
   - Add a test in `backend/tests/test_core.py` verifying that `backend/data/zones.geojson` loads with valid geometries, valid layer_ids (1 or 2), and valid zone_types.
