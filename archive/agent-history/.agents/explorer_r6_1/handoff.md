# Handoff Report: Requirement R1 — Camera Stream & Admin Map Investigation

**Author**: Explorer R6-1  
**Date**: 2026-09-14  
**Target Milestone**: Requirement R1 (Camera & Map)  
**Status**: Completed (Investigation & Plan)

---

## 1. Observation

### 1.1 Camera Stream Observations

1. **Backend Dummy Stream**:
   In `/home/pnt/IOT/backend/app/main.py` lines 658–678:
   ```python
   @app.get("/api/v1/camera/stream")
   def camera_stream(_=Depends(session_user)):
       frame = bytes([
           0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01, 0x01, 0x01, 0x00, 0x48,
           ...
           0x00, 0xBF, 0x00, 0xFF, 0xD9
       ])

       def frame_generator():
           while True:
               yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
               time.sleep(0.033)

       return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")
   ```
   The current backend stream is a hardcoded static 1×1 pixel JPEG byte array. It contains zero logic to capture from physical hardware (CSI ribbon or USB UVC) via OpenCV or V4L2.

2. **Missing Dependency in Requirements**:
   In `/home/pnt/IOT/backend/requirements.txt`:
   Lines 1–71 contain `numpy==2.5.3` and `pillow==12.3.0`, but neither `opencv-python` nor `opencv-python-headless` is declared. In the default python environment (`/home/pnt/miniconda3/bin/python3`), running `import cv2` fails with `ModuleNotFoundError: No module named 'cv2'`. In the conda `antidrone` environment (`/home/pnt/miniconda3/envs/antidrone/bin/python3`), OpenCV 5.0.0 is installed.

3. **Linux Service Permissions for `/dev/video*`**:
   In `/home/pnt/IOT/tests/ssh_test_report_remote.json` line 17, remote inspection of the Raspberry Pi 5 reveals:
   ```
   "video_devices": "crw-rw----+ 1 root video 81, 17 Jun 18 07:31 /dev/video0\ncrw-rw----+ 1 root video 81, 18 Jun 18 07:31 /dev/video1..."
   ```
   The video devices `/dev/video0` and `/dev/video1` are owned by `root:video` with mode `0660`.
   In `/home/pnt/IOT/deploy/iot-drone.service` line 12:
   ```ini
   User=iot-drone
   Group=iot-drone
   SupplementaryGroups=dialout
   ```
   And in `/home/pnt/IOT/deploy/install_pi.sh` line 25:
   ```bash
   usermod -a -G dialout iot-drone
   ```
   The `iot-drone` system service user belongs only to `dialout` and is NOT a member of the `video` group. Attempting to open `/dev/video*` from the systemd service without the `video` group will fail with `PermissionError: [Errno 13] Permission denied: '/dev/video0'`.

4. **Frontend `crossOrigin="anonymous"` Cookie Stripping**:
   In `/home/pnt/IOT/frontend/src/CameraTab.tsx` lines 224–234:
   ```tsx
   <img
     ref={imgRef}
     src={streamUrl}
     alt="USB Camera Stream"
     className="live-video-element"
     onLoad={handleImageLoad}
     onError={handleImageError}
     crossOrigin="anonymous"
   />
   ```
   When `crossOrigin="anonymous"` is specified on an `<img>` tag, the browser strips session cookies in cross-origin / proxied dev requests. In `/home/pnt/IOT/backend/app/auth.py` lines 64–70:
   ```python
   def session_user(
       request: Request = None,
       drone_session: Annotated[str | None, Cookie()] = None,
   ):
       row = db.get_session(drone_session)
       if not row:
           raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chưa đăng nhập")
   ```
   Requests lacking the `drone_session` cookie are rejected with HTTP 401 Unauthorized. This triggers `onError` (`handleImageError`), transitioning the tab to the fallback error screen "Không có tín hiệu USB Camera".

5. **Frontend FPS Watchdog Misconception**:
   In `/home/pnt/IOT/frontend/src/CameraTab.tsx` lines 65–77 & 79–97:
   ```tsx
   // Watchdog: if no frame arrives for 2s, report FPS 0 (stream stalled)
   useEffect(() => {
     const watchdog = setInterval(() => {
       if (performance.now() - lastFrameRef.current > 2000) {
         setFps(0)
         frameTimes.current = []
       }
     }, 2000)
     return () => clearInterval(watchdog)
   }, [])

   const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
     ...
     // Measure real FPS from frame load intervals (MJPEG fires load per frame)
     const now = performance.now()
     lastFrameRef.current = now
   ```
   In modern browsers (Chromium, WebKit, Gecko), the DOM `load` event on an `<img>` displaying a `multipart/x-mixed-replace` stream fires only once on initial payload arrival, NOT on every individual multipart boundary. As a result, `lastFrameRef.current` is never updated after the first frame; within 2000ms, the watchdog interval always fires and forces `fps` to `0`, misleading the user into thinking the stream has frozen.

---

### 1.2 Admin Map Observations

1. **Hardcoded Dependency on Absent Offline PMTiles**:
   In `/home/pnt/IOT/backend/app/main.py` lines 681–688:
   ```python
   @app.get("/api/v1/status")
   def system_status(_=Depends(require_admin)):
       frame = state.snapshot()
       return {
           ...
           "map_ready": settings.map_path.exists(),
           ...
       }
   ```
   In `/home/pnt/IOT/backend/app/config.py` line 44–45:
   ```python
   @property
   def map_path(self) -> Path:
       return self.data_dir / "maps" / "hcm.pmtiles"
   ```
   Running `ls -la /home/pnt/IOT/backend/data/` shows `maps/` does not exist. Generating `hcm.pmtiles` and `map-assets` requires running `/home/pnt/IOT/scripts/download_hcm_map.sh`, which downloads 8 GB of data from external repositories. Without this file on disk, `settings.map_path.exists()` is always `False`, and `/api/v1/status` returns `"map_ready": false`.

2. **Frontend Dom Exclusion Gate**:
   In `/home/pnt/IOT/frontend/src/MapTab.tsx` lines 89–91 & 415–424:
   ```tsx
   useEffect(() => {
     if (!container.current || mapRef.current || !status.map_ready || !config) return
     ...
   ```
   ```tsx
   {status.map_ready ? (
     <div ref={container} className="maplibre-element" />
   ) : (
     <div className="map-empty-state">
       <MapIcon size={40} className="text-muted" />
       <h4>Đang tải dữ liệu PMTiles Offline</h4>
       <p>Vui lòng đợi hệ thống khởi tạo bản đồ không phận...</p>
     </div>
   )}
   ```
   Because `status.map_ready` is `False`, the map DOM container `<div ref={container} className="maplibre-element" />` is never rendered. Instead, a static placeholder message is displayed indefinitely.

3. **Style Specification 404 Cascades**:
   In `/home/pnt/IOT/frontend/src/MapTab.tsx` lines 110–134:
   ```tsx
   const style: StyleSpecification = {
     version: 8,
     glyphs: '/map-assets/fonts/{fontstack}/{range}.pbf',
     sprite: `${location.origin}/map-assets/sprites/v4/light`,
     sources: {
       protomaps: {
         type: 'vector',
         url: 'pmtiles:///api/v1/map-pack/file',
         attribution: '© OpenStreetMap · Protomaps',
       },
       ...
   ```
   Even if `status.map_ready` is bypassed:
   - `/api/v1/map-pack/file` returns 404 (`settings.map_path.exists()` is false).
   - `/map-assets/fonts/...` returns 404 (directory does not exist).
   - `/map-assets/sprites/...` returns 404 (directory does not exist).
   MapLibre GL encounters multiple critical resource fetch errors and either fails during style parsing or leaves a blank white canvas.

4. **Content Security Policy (CSP) Network Wall**:
   In `/home/pnt/IOT/backend/app/main.py` lines 329–339:
   ```python
   @app.middleware("http")
   async def security_headers(request: Request, call_next):
       response = await call_next(request)
       ...
       response.headers["Content-Security-Policy"] = (
           "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
           "script-src 'self'; connect-src 'self' ws: wss:; worker-src 'self' blob:; media-src 'self' blob:"
       )
   ```
   The CSP header restricts `connect-src` to `'self' ws: wss:` and `img-src` to `'self' data: blob:`. If frontend MapLibre GL attempts to fetch tiles from standard public OpenStreetMap servers (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`), the browser's CSP engine blocks all tile HTTP requests, resulting in a blank white canvas.

5. **Map Container Resizing in Tabbed Navigation**:
   In `/home/pnt/IOT/frontend/src/Tabs.tsx`, switching to the Map tab mounts `<MapTab>`. When container sizing or layout stabilizes after render, without calling `map.resize()`, WebGL canvases often retain a 0×0 or distorted viewport until window resizing occurs.

---

## 2. Logic Chain

### 2.1 Camera Stream Logic Chain
1. **Observation 1.1.1** demonstrates that `/api/v1/camera/stream` currently only yields a synthetic 1×1 pixel byte array and has no connection to OpenCV, V4L2, or camera hardware.
2. **Observation 1.1.2 & 1.1.3** demonstrate that `iot-drone` lacks membership in the `video` group and `opencv-python-headless` is not tracked in `requirements.txt`. Even if capture code were introduced, opening `/dev/video0` under systemd would fail with `EACCES (Permission denied)`.
3. Furthermore, on Linux, V4L2 capture devices cannot be opened simultaneously by multiple `open()` handles in read/write capture mode. If each client request creates a `cv2.VideoCapture(0)` instance, concurrent requests from multiple tabs or users cause `EBUSY (Device or resource busy)` and crash the stream.
4. **Observation 1.1.4** shows that frontend `crossOrigin="anonymous"` prevents sending auth cookies on cross-origin requests, triggering HTTP 401 from `session_user` and switching `CameraTab` to the offline fallback screen.
5. **Observation 1.1.5** shows that the FPS counter in `CameraTab` resets to 0 after 2 seconds due to an invalid assumption that DOM `load` events fire for every boundary in a multipart stream.
6. **Conclusion for Camera**: A thread-safe, singleton `CameraManager` service must be implemented in the backend. It will open `/dev/video*` (or CSI via OpenCV/V4L2) once, continuously grab frames into a shared buffer, and gracefully fall back to synthetic frames if hardware is missing. The frontend must remove `crossOrigin="anonymous"`, adjust FPS calculation to use backend status metrics, and query a dedicated snapshot endpoint. System permissions and package dependencies must be updated accordingly.

### 2.2 Admin Map Logic Chain
1. **Observation 1.2.1 & 1.2.2** demonstrate that `status.map_ready` is false because `hcm.pmtiles` does not exist on disk. `MapTab.tsx` explicitly checks `status.map_ready` and refuses to render the `<div ref={container} />` element, instead displaying an empty state.
2. **Observation 1.2.3** shows that the current MapLibre style is tightly coupled to Protomaps vector tiles, local fonts, and local sprites. All three fail with 404 because neither the PMTiles file nor the `/map-assets` directory is bundled with the codebase.
3. **Observation 1.2.4** shows that even if MapLibre is configured to use public OpenStreetMap tiles (`https://tile.openstreetmap.org`), the strict backend CSP header (`connect-src 'self' ws: wss:; img-src 'self' data: blob:;`) blocks tile requests at the browser network layer, causing a blank white canvas.
4. **Observation 1.2.5** shows that when transitioning to tabbed Map views, MapLibre must invoke `map.resize()` once the DOM container dimensions are resolved.
5. **Conclusion for Map**:
   - The backend CSP must permit `https://*.tile.openstreetmap.org` (or provide a local backend tile proxy).
   - `status.map_ready` must return `true` (since public OSM tiles are always available).
   - `MapTab.tsx` must remove the `status.map_ready` DOM exclusion gate and replace the vector Protomaps style with a standard, self-contained raster OpenStreetMap basemap (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`).
   - The satellite raster layer and all GeoJSON vector layers (prohibited zones, restricted zones, dynamic 1km approved flight zone, and live drone GPS marker) must be layered over the OSM basemap.
   - `map.resize()` must be invoked upon map load and container resize.

---

## 3. Caveats

1. **Hardware Presence vs Simulation**:
   In automated testing environments (CI/CD or bench test runners), a physical USB or CSI camera is not plugged into the runner. The backend camera capture service must feature an automatic, seamless fallback to a synthetic test pattern (with valid JPEG SOI `0xFFD8` / EOI `0xFFD9` markers) so that unit tests (`test_scenario_07_camera.py`, `test_api.py`) and developer previews pass with 100% reliability.
2. **Raspberry Pi 5 CSI Camera Specifics**:
   On Raspberry Pi 5 running Raspberry Pi OS Bookworm (kernel 6.x), CSI cameras are controlled via `rp1-cfe` and libcamera. When accessed via OpenCV `cv2.VideoCapture`, the system can capture either via V4L2 node `/dev/video0` (if `v4l2loopback` or driver compatibility mode is present) or via a GStreamer pipeline (`libcamerasrc`). Standard USB UVC webcams operate directly via `cv2.VideoCapture(index, cv2.CAP_V4L2)`. The implementation must probe V4L2 device nodes sequentially.
3. **Offline Map Caching**:
   Public OpenStreetMap tiles require an active internet connection on the client browser. To support completely air-gapped field operations without downloading the 8GB Protomaps dataset, the backend can optionally cache OSM tiles locally or proxy them.

---

## 4. Conclusion & Implementation Plan

### 4.1 Changes Required for Camera Stream

#### A. Backend Camera Manager (`backend/app/camera.py`)
Create a new singleton `CameraService` class:
- **Device auto-detection**: Scans `/dev/video0`, `/dev/video2`, etc. Probes with `cv2.VideoCapture(index, cv2.CAP_V4L2)`.
- **Configuration**: Sets MJPG FOURCC, resolution (1280×720 default, fallback to 640×480), and target FPS (30).
- **Background Frame Worker**: A dedicated daemon thread reads frames from OpenCV, encodes them to JPEG via `cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])`, and writes to an atomic memory buffer (`latest_frame: bytes`).
- **Synthetic Fallback**: If no device can be opened, generates an animated test pattern with drone station telemetry overlay, timestamp, crosshairs, and valid JPEG SOI/EOI markers.
- **Auto-reconnect**: If frame acquisition fails repeatedly (e.g. USB camera unplugged), closes the handle and enters a periodic re-probe loop every 2 seconds.

```python
# Proposed backend/app/camera.py structure:
import cv2
import threading
import time
import glob
from typing import Optional, Tuple

class CameraService:
    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._latest_jpeg: bytes = self._generate_fallback_frame()
        self._last_frame_time = 0.0
        self.device_name = "Synthetic / Standby"
        self.resolution = "1280x720"
        self.fps = 30.0
        self.is_hardware = False
        ...
```

#### B. Backend API Routes (`backend/app/main.py`)
1. In lifespan startup: Start `camera_service.start()`; on shutdown, `camera_service.stop()`.
2. Update `GET /api/v1/camera/status`:
   Return current hardware/synthetic status, resolution, device name, and real FPS.
3. Update `GET /api/v1/camera/stream`:
   Support authentication via cookie or query parameter `?token=...`.
   Stream multipart frames from `camera_service.get_latest_jpeg()`.
   Add response headers: `Cache-Control: no-cache, no-store, must-revalidate`, `Pragma: no-cache`.
4. Add `GET /api/v1/camera/snapshot`:
   Return a single JPEG frame with `Content-Type: image/jpeg` for instant snapshot downloads.

#### C. Backend Dependencies & Deployment
1. `backend/requirements.txt`: Add `opencv-python-headless>=4.8.0`.
2. `deploy/iot-drone.service`: Set `SupplementaryGroups=dialout video`.
3. `deploy/install_pi.sh`: Set `usermod -a -G dialout,video iot-drone`.

#### D. Frontend Camera Tab (`frontend/src/CameraTab.tsx`)
1. Remove `crossOrigin="anonymous"` from `<img ... />` to preserve session cookies across reverse proxies and dev ports.
2. Remove the broken DOM `onLoad` frame watchdog. Instead, obtain FPS and resolution directly from `api.cameraStatus()`.
3. Update snapshot feature to fetch directly from `/api/v1/camera/snapshot` or use the current image handle without canvas security errors.

---

### 4.2 Changes Required for Admin Map

#### A. Backend Security Headers & Status (`backend/app/main.py`)
1. Update Content-Security-Policy (CSP) middleware in `security_headers`:
   ```python
   response.headers["Content-Security-Policy"] = (
       "default-src 'self'; "
       "img-src 'self' data: blob: https://*.tile.openstreetmap.org https://tile.openstreetmap.org; "
       "style-src 'self' 'unsafe-inline'; "
       "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
       "connect-src 'self' ws: wss: https://*.tile.openstreetmap.org https://tile.openstreetmap.org; "
       "worker-src 'self' blob:; "
       "media-src 'self' blob:"
   )
   ```
2. Update `/api/v1/status`:
   Set `"map_ready": True` unconditionally so the frontend UI is never blocked from rendering maps.
3. Optional backend tile proxy `/api/v1/map/osm/{z}/{x}/{y}.png` for cached / offline network reliability.

#### B. Frontend MapTab (`frontend/src/MapTab.tsx`)
1. Remove the `!status.map_ready` check in `useEffect` and JSX. Always render `<div ref={container} className="maplibre-element" />`.
2. Replace the vector Protomaps basemap configuration with a standard raster OpenStreetMap style:
   ```typescript
   const style: StyleSpecification = {
     version: 8,
     sources: {
       'osm-tiles': {
         type: 'raster',
         tiles: [
           'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
         ],
         tileSize: 256,
         attribution: '© OpenStreetMap contributors',
         maxzoom: 19,
       },
       ...(config?.satellite.available
         ? {
             satellite: {
               type: 'raster' as const,
               tiles: ['/api/v1/map/satellite/{z}/{x}/{y}'],
               tileSize: 256,
               minzoom: config.satellite.min_zoom,
               maxzoom: config.satellite.max_zoom,
               attribution: config.satellite.attribution ?? '',
             },
           }
         : {}),
     },
     layers: [
       {
         id: 'osm-tiles-layer',
         type: 'raster',
         source: 'osm-tiles',
         minzoom: 0,
         maxzoom: 19,
         layout: {
           visibility: modeRef.current === 'street' ? 'visible' : 'none',
         },
       },
       ...(config?.satellite.available
         ? [
             {
               id: 'satellite-basemap',
               type: 'raster' as const,
               source: 'satellite',
               layout: {
                 visibility: modeRef.current === 'satellite' ? 'visible' as const : 'none' as const,
               },
             },
           ]
         : []),
     ],
   }
   ```
3. Retain existing GeoJSON layers (`flight-zones-fill`, `flight-zones-line`, `authorized-flight-zone-fill`, `authorized-flight-zone-line`, and `maplibregl.Marker` for Drone GPS).
4. Add container resize handling:
   ```typescript
   map.on('load', () => {
     map.resize()
     ...
   })
   ```
   Add a `ResizeObserver` on `container.current` to call `mapRef.current?.resize()` when tabs switch or layout changes.

---

## 5. Verification Method

### 5.1 Automated Unit & Integration Tests
Run the pytest suite to verify backend status and streaming endpoints:
```bash
cd /home/pnt/IOT/backend
PYTHONPATH=. /home/pnt/miniconda3/envs/antidrone/bin/pytest tests/test_api.py tests/test_m2_auth_and_wifi.py -v
```
Run Scenario 7 camera verification test:
```bash
cd /home/pnt/IOT
python3 tests/test_scenario_07_camera.py
```
Expected output:
- `GET /api/v1/camera/status` returns HTTP 200 with `available: true`.
- `GET /api/v1/camera/stream` returns HTTP 200 with `Content-Type: multipart/x-mixed-replace; boundary=frame` and contains valid JPEG markers (`0xFFD8`).
- `GET /api/v1/status` returns `"map_ready": true`.

### 5.2 Frontend Build & Style Check
Run frontend TypeScript typecheck and Vite build:
```bash
cd /home/pnt/IOT/frontend
npm run build
```
Verify that `dist/index.html` and assets build cleanly with no syntax or type errors.

### 5.3 Manual Browser Verification
1. **Camera Tab**:
   - Log in to the web interface at `http://localhost:8000` (or `http://192.168.1.118`).
   - Navigate to the **Camera** tab.
   - Confirm video displays immediately without dropping to the fallback error screen.
   - Confirm FPS indicator displays a positive rate (e.g. 30 FPS).
   - Click "Chụp ảnh" (Snapshot) and verify that the JPEG image downloads successfully.
2. **Admin Map Tab**:
   - Navigate to the **Map** tab.
   - Confirm the OpenStreetMap basemap tiles render cleanly across the viewport (no blank white screen).
   - Confirm no-fly zone polygons (red prohibited and amber restricted) are drawn on the map.
   - Toggle between "Bản đồ Light" and "Vệ tinh" modes.
   - Resize browser window and verify that the map tiles adjust without blank artifacts.

### 5.4 Invalidation Conditions
- If CSP blocks tile loading in browser console (`Refused to connect to 'https://tile.openstreetmap.org...'`), CSP headers in `security_headers` middleware must be updated to include the tile domain.
- If `/dev/video0` is present on the Pi5 but `cap.isOpened()` returns `False`, verify user group membership (`groups iot-drone`) and ensure `SupplementaryGroups=dialout video` is active in systemd.
