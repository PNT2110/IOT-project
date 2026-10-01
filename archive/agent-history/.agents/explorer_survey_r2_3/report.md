# Research Report: Frontend Map Visualization & No-Fly Zone Rendering

**Author:** Explorer 3 (Frontend Map Visualization Researcher)  
**Date:** 2026-09-10  
**Target:** Drone Station UI (`frontend/src/App.tsx`, `frontend/src/styles.css`, MapLibre GL)  
**Project Root:** `c:\Users\pnt21\OneDrive\Máy tính\IOT`  

---

## Executive Summary

This investigation analyzed the frontend map architecture of the IOT Drone Station project, specifically examining:
1. The MapLibre GL and PMTiles integration in `frontend/src/App.tsx`.
2. How no-fly zones (cấm bay) and restricted flight zones (hạn chế bay) are fetched from `/api/v1/geofence/zones` and styled.
3. The legacy visualization specifications, color conventions, layer IDs, and coordinate handling.
4. The frontend build environment, TypeScript strictness, and bundler requirements.
5. Concrete code recommendations to ensure seamless, visually faithful rendering of no-fly zone data matching the original design.

---

## 1. Frontend Architecture & Component Inspection

### 1.1 Source Directory Layout (`frontend/src/`)
The frontend is a modern React 19 + TypeScript single-page dashboard bundled with Vite 7:
- `frontend/src/main.tsx` (13 lines): Application entry point. Mounts `<App />` inside React `StrictMode`. Imports `maplibre-gl/dist/maplibre-gl.css` and `./styles.css`.
- `frontend/src/App.tsx` (270 lines): Central monolithic dashboard component containing:
  - `Login`: Authentication form (username, password, 6-digit TOTP).
  - `StatusPill`: Reusable connection status indicator (online/offline).
  - `CameraPanel`: Live WebRTC video feed container.
  - `UserView`: Read-only view for `role === 'user'`.
  - `DroneModel`: 3D drone orientation visualizer using `@react-three/fiber` and `@react-three/drei`.
  - `FlightMap`: MapLibre GL viewer rendering the vector basemap and geofence polygons.
  - `AdminView`: Full monitoring dashboard (FlightMap, Attitude 3D, Camera, PID Recharts AreaChart, ESP Serial Monitor, Preflight checks, telemetry metrics).
  - `DashboardErrorBoundary`: Graceful error boundary protecting the dashboard from crashing.
  - `App`: Main controller handling session authentication state.
- `frontend/src/api.ts` (26 lines): Type-safe REST client for auth, status, camera, and serial endpoints.
- `frontend/src/types.ts` (46 lines): TypeScript interfaces for `UserSession`, `Telemetry`, and `SystemStatus`.
- `frontend/src/styles.css` (8,969 bytes): Cyber/industrial dark theme palette (`#050a0d` background, `#21d6b5` teal accent, `#ff5d68` danger red, `#ffbe55` warning amber).

---

## 2. MapLibre GL Initialization & Zone Layer Styling

### 2.1 Map Initialization Lifecycle (`FlightMap` in `App.tsx:129-160`)
```typescript
function FlightMap({ status, telemetry }: { status: SystemStatus; telemetry: Telemetry | null }) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const markerRef = useRef<maplibregl.Marker | null>(null)

  useEffect(() => {
    if (!container.current || mapRef.current || !status.map_ready) return
    const protocol = new Protocol()
    maplibregl.addProtocol('pmtiles', protocol.tile)
    const style: StyleSpecification = {
      version: 8,
      glyphs: '/map-assets/fonts/{fontstack}/{range}.pbf',
      sprite: `${location.origin}/map-assets/sprites/v4/light`,
      sources: { protomaps: { type: 'vector', url: 'pmtiles:///api/v1/map-pack/file', attribution: '© OpenStreetMap · Protomaps' } },
      layers: layers('protomaps', namedFlavor('dark'), { lang: 'vi' }) as StyleSpecification['layers'],
    }
    mapRef.current = new maplibregl.Map({ container: container.current, style, center: [106.7, 10.78], zoom: 9 })
    mapRef.current.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right')
    ...
```

Key Observations:
1. **Offline PMTiles Basemap**: Uses `pmtiles` custom protocol registering `/api/v1/map-pack/file` as vector tiles. Fonts are served from `/map-assets/fonts/{fontstack}/{range}.pbf` and sprites from `/map-assets/sprites/v4/light`.
2. **Language & Theme**: Protomaps dark flavor with Vietnamese language labels (`lang: 'vi'`).
3. **Map Center & Bounds**: Initial center is fixed at `[106.7, 10.78]` (Ho Chi Minh City coordinates in `[longitude, latitude]` format), with initial zoom level `9`.
4. **Cleanup**: Proper cleanup unregistering `pmtiles` protocol and disposing markers/map instances on unmount.

### 2.2 Zone Fetching & Layer Styling (`App.tsx:147-158`)
```typescript
    mapRef.current.on('load', async () => {
      try {
        const response = await fetch('/api/v1/geofence/zones', { credentials: 'same-origin' })
        if (!response.ok || !mapRef.current) return
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
      } catch {
        // Preflight sẽ báo dữ liệu chưa sẵn sàng.
      }
    })
```

### 2.3 Visual Styling Specifications
| Layer Property | Layer 1: Prohibited (Cấm bay) | Layer 2: Restricted (Hạn chế bay) | Default / Fallback |
|---|---|---|---|
| **Fill Color** | `#ff4655` (Crimson Red) | `#ffb23e` (Amber / Orange) | `#ff4655` |
| **Fill Opacity**| `0.42` (semi-transparent) | `0.42` (semi-transparent) | `0.42` |
| **Outline Color**| `#ff6570` (Bright Red) | `#ffc769` (Bright Amber) | `#ff6570` |
| **Outline Width**| `2px` | `2px` | `2px` |
| **Legend Dot** | `.danger-dot` (`#ff5d68`) | `.warn-dot` (`#ffbe55`) | — |
| **Drone Marker** | `#21d6b5` (Teal dot) | — | — |

---

## 3. Historical / Legacy Data Context & Comparison

### 3.1 Historical Background
- According to `WORKLOG.md:44` and `PROJECT_STATUS.md:70-75`:
  - The geofence dataset is synchronized from the official Ministry of National Defence portal `cambay.mod.gov.vn`.
  - 2,745 zones exist in the Greater HCMC area (including HCMC, Binh Duong, Ba Ria - Vung Tau, and Con Dao).
  - Layer classification:
    - **Layer 1 (`layer_id = 1`)**: Vùng cấm bay (`zone_type = 'prohibited'`) — 2,378 zones.
    - **Layer 2 (`layer_id = 2`)**: Vùng hạn chế bay (`zone_type = 'restricted'`) — 367 zones.
- Coordinate order in GeoJSON: `[longitude, latitude]` (RFC 7946).
  - Longitudes range: `106.1279°E` to `108.3247°E`.
  - Latitudes range: `8.5995°N` to `11.9104°N`.
- In previous microcontroller UI (`web_ui.h` in ESP32 firmware):
  - Leaflet OSM was used with simple drone/home point markers.
  - In the Pi 5 Drone Station architecture, MapLibre GL with vector PMTiles offline basemap is used, rendering polygons with Red (#ff4655) and Amber (#ffb23e).

### 3.2 Key Gaps in Current Frontend Implementation
1. **Lack of Interaction / Popups**:
   Currently, clicking or hovering over a zone displays no information. Users cannot see the zone's name, designation, rules, or altitude restrictions.
2. **Brittle Property Expression in MapLibre Style**:
   The style expression `['match', ['get', 'layer_id'], 1, '#ff4655', 2, '#ffb23e', '#ff4655']` expects an integer `1` or `2`. If properties have `zone_type: 'restricted'`, or `layer_id: "2"` (string), it falls back to red.
3. **Map Initialization Gated on `status.map_ready`**:
   `FlightMap` returns an empty container if `!status.map_ready`. If the offline PMTiles file is not loaded yet, no map or zones are visible.
4. **Static Viewport**:
   The map center is fixed at `[106.7, 10.78]` without auto-centering on the zone bounding box or following drone telemetry when active.

---

## 4. Frontend Build Requirements & Verification

### 4.1 Build Toolchain & Environment
- **Node Runtime**: Node.js v24.19.0 (located at `C:\Users\pnt21\AppData\Local\OpenAI\Codex\runtimes\cua_node\6a86821985684e13\bin\node.exe`).
- **Package Manager**: npm 11.17.0.
- **Compiler**: TypeScript `tsc -b` (tsconfig.json target ES2022).
- **Bundler**: Vite 7.3.6.

### 4.2 Build Verification Command & Result
Command executed:
```powershell
$env:PATH = "C:\Users\pnt21\AppData\Local\OpenAI\Codex\runtimes\cua_node\6a86821985684e13\bin;" + $env:PATH
cmd /c "npm run build"
```
Output:
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
**Status: PASSED (0 errors, 0 warnings).**

---

## 5. Concrete Recommendations for `frontend/src/App.tsx`

To guarantee 100% visual fidelity, robustness against legacy data variations, and superior user experience:

### 5.1 Robust Property Fallbacks for Zone Styling
Replace the strict integer `layer_id` match with an expression supporting `layer_id` (numeric or string) and `zone_type`:
```typescript
const fillColorExpression: maplibregl.ExpressionSpecification = [
  'match',
  ['coalesce', ['get', 'zone_type'], ['to-string', ['get', 'layer_id']]],
  'restricted', '#ffb23e',
  '2', '#ffb23e',
  '#ff4655' // default: prohibited / 1
]

const lineColorExpression: maplibregl.ExpressionSpecification = [
  'match',
  ['coalesce', ['get', 'zone_type'], ['to-string', ['get', 'layer_id']]],
  'restricted', '#ffc769',
  '2', '#ffc769',
  '#ff6570' // default: prohibited / 1
]
```

### 5.2 Interactive Tooltips / Popups on Zone Click
Implement interactive inspection so operators can click any no-fly zone and see details:
```typescript
const popupRef = useRef<maplibregl.Popup | null>(null)

// In map.on('load'):
mapRef.current.on('click', 'flight-zones-fill', (e) => {
  if (!e.features || !e.features[0] || !mapRef.current) return
  const f = e.features[0]
  const p = f.properties || {}
  const isProhibited = p.layer_id === 1 || p.layer_id === '1' || p.zone_type === 'prohibited'
  const zoneName = p.name || p.rawName || (isProhibited ? 'Vùng cấm bay' : 'Vùng hạn chế bay')
  const zoneType = isProhibited ? 'CẤM BAY (PROHIBITED)' : 'HẠN CHẾ BAY (RESTRICTED)'
  const color = isProhibited ? '#ff4655' : '#ffb23e'

  const content = `
    <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; padding: 4px; color: #e8f6f5;">
      <div style="font-weight: 700; font-size: 12px; margin-bottom: 4px; color: ${color};">${zoneName}</div>
      <div style="margin-bottom: 2px; color: #8fa6ad;">Phân loại: <strong style="color: ${color};">${zoneType}</strong></div>
      ${p.id ? `<div style="color: #8fa6ad;">Mã vùng: ${p.id}</div>` : ''}
      ${p.max_altitude ? `<div style="color: #8fa6ad;">Trần bay: ${p.max_altitude} m</div>` : ''}
    </div>
  `

  if (popupRef.current) popupRef.current.remove()
  popupRef.current = new maplibregl.Popup({ className: 'drone-map-popup' })
    .setLngLat(e.lngLat)
    .setHTML(content)
    .addTo(mapRef.current)
})

mapRef.current.on('mouseenter', 'flight-zones-fill', () => {
  if (mapRef.current) mapRef.current.getCanvas().style.cursor = 'pointer'
})

mapRef.current.on('mouseleave', 'flight-zones-fill', () => {
  if (mapRef.current) mapRef.current.getCanvas().style.cursor = ''
})
```

### 5.3 Popup Styling in `frontend/src/styles.css`
Add styling for `.drone-map-popup` to match the industrial dark UI:
```css
.drone-map-popup .maplibregl-popup-content {
  background: #081116f0;
  border: 1px solid var(--line);
  border-radius: 6px;
  box-shadow: 0 12px 32px #000a;
  backdrop-filter: blur(8px);
  padding: 8px 10px;
}
.drone-map-popup .maplibregl-popup-tip {
  border-top-color: #081116f0;
}
```

### 5.4 Coordinate Safety
MapLibre GL requires `[longitude, latitude]`. The backend must ensure all coordinates are `[lon, lat]`. The frontend should maintain this convention so polygon vertices and drone markers align with zero offset.
