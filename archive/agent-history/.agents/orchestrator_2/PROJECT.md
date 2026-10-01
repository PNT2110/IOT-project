# Project: Legacy No-Fly Zone Integration

## Architecture
- **Data Source**: Official Cambay MOD vector tiles stored at `backend/data/zones.geojson` (2,745 features: 2,378 Prohibited, 367 Restricted, 195,143 vertices).
- **Backend**:
  - `backend/app/geofence.py`: Ingests `zones.geojson` into Shapely polygons; point-in-polygon and distance checks in WGS 84 `[longitude, latitude]`.
  - `backend/app/main.py`: Exposes `GET /api/v1/geofence/zones` returning GeoJSON FeatureCollection.
  - `backend/data/drone.sqlite3`: Records `map_sync` state for preflight health checks (`geofence_sync_is_fresh`).
- **Frontend**:
  - `frontend/src/App.tsx`: MapLibre GL map component fetching `/api/v1/geofence/zones`.
  - Layers: `flight-zones-fill` (fill opacity 0.42) and `flight-zones-line` (width 2px).
  - Colors: Prohibited (`layer_id: 1` / `zone_type: 'prohibited'`) -> Red (`#ff4655` / `#ff6570`); Restricted (`layer_id: 2` / `zone_type: 'restricted'`) -> Amber (`#ffb23e` / `#ffc769`).
  - Interactive: Click popup displaying Zone Name/ID/Type, cursor pointer on hover.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Legacy Zone Extraction & Verification | Exhaustive scan and validation of legacy zone data (2,745 features, [lng, lat] format) | M0 | ORIGINAL_REQUEST §R1 |
| 2 | Backend GeoJSON & Sync Maintenance | Validate `zones.geojson`, update `map_sync` in `drone.sqlite3` with fresh timestamp | M1 | ORIGINAL_REQUEST §R2 |
| 3 | Frontend MapLibre Zone Visualization | Render prohibited (red) and restricted (amber) zones in `App.tsx` with popups and resilient style | M1 | ORIGINAL_REQUEST §R2 |
| 4 | Verification & Quality Assurance | 100% pytest test suite pass (98 passed), 0-error frontend build, adversarial tests, forensic audit | M1 | ORIGINAL_REQUEST §Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M0 | Survey & Legacy Data Mining | Locate and analyze legacy zone data structure and format | none | DONE |
| M1 | Zone Integration & Map Visualization | Ensure `zones.geojson` integrity, sync `map_sync` metadata, enhance `App.tsx` MapLibre rendering, verify pytest and frontend build | M0 | DONE |

## Interface Contracts
### Backend ↔ Frontend
- Endpoint: `GET /api/v1/geofence/zones`
- Response Payload: GeoJSON `FeatureCollection` (2,745 features, RFC 7946 EPSG:4326)
- Feature Schema:
  ```json
  {
    "type": "Feature",
    "geometry": { "type": "Polygon" | "MultiPolygon", "coordinates": [...] },
    "properties": {
      "id": "14129",
      "layer_id": 1,
      "zone_type": "prohibited",
      "source": "https://cambay.mod.gov.vn"
    }
  }
  ```
- MapLibre Paint Properties:
  - Supports matching on both `layer_id` (`1` or `2`) and `zone_type` (`'prohibited'` or `'restricted'`).
  - Fill color: `#ff4655` for prohibited, `#ffb23e` for restricted.
  - Line color: `#ff6570` for prohibited, `#ffc769` for restricted.
  - Interactive popup on click with Vietnamese labels: "Vùng cấm bay" / "Vùng hạn chế bay" and zone ID.

## Code Layout
- `backend/data/zones.geojson`: Master GeoJSON dataset.
- `backend/data/drone.sqlite3`: Application SQLite database (`map_sync` table).
- `backend/app/geofence.py`: Backend geofence engine (Shapely containment).
- `frontend/src/App.tsx`: React MapLibre visualization component.
- `backend/tests/test_zone_integration.py`: Integration test suite for zone schema and sync.
- `backend/tests/test_geospatial_stress.py`: Geospatial stress testing harness.
- `backend/tests/test_challenger_stress_harness.py`: API and data stress testing harness.
