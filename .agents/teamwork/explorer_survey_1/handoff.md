# Firmware & Gateway Tier Survey Report (Handoff)

**Agent Role**: explorer_survey_1 (Firmware & Gateway Explorer)  
**Parent Agent**: 3be5ec9a-8b7d-4356-b0b8-0a206dabba81  
**Timestamp**: 2026-10-03T20:48:00Z  
**Scope**: Firmware Tier (`firmware/`, `tests/firmware/`), Pi 5 Gateway & Local UI Tier (`edge/pi5/`, `tests/scope05/`, `tests/scope07/`)

---

## 1. Observation

### 1.1 Firmware Tier: Altitude Throttle Limiter & Barometer Integration
* **File**: `firmware/FC_can_bang/flight_gate.h` (Lines 59–83):
  ```cpp
  // ---- Gioi han do cao toi da (so voi diem ARM) ----
  #define ALT_LIMIT_FLOOR_US 1100
  #define ALT_LIMIT_STEP_US 0.05f     // moi vong 5 ms -> ha tran ga 10 us / giay
  #define ALT_LIMIT_RELEASE_M 1.0f

  struct AltLimiter {
    bool  active = false;
    float cap_us = 0;
  };

  // Tra ve ga da gioi han. Phi cong luon co the giam ga thap hon tran.
  static inline int altitude_throttle_cap(AltLimiter& s, float rel_alt_m, float max_alt_m, int throttle_us) {
    if (!s.active) {
      if (rel_alt_m <= max_alt_m) return throttle_us;
      s.active = true;
      s.cap_us = (float)throttle_us - 30.0f;
    } else if (rel_alt_m < max_alt_m - ALT_LIMIT_RELEASE_M) {
      s.active = false;
      return throttle_us;
    } else if (rel_alt_m > max_alt_m) {
      s.cap_us -= ALT_LIMIT_STEP_US;   // van con tren tran -> tiep tuc ha tran ga
    }
    if (s.cap_us < ALT_LIMIT_FLOOR_US) s.cap_us = ALT_LIMIT_FLOOR_US;
    return throttle_us > (int)s.cap_us ? (int)s.cap_us : throttle_us;
  }
  ```
* **File**: `firmware/FC_can_bang/Baro.ino` (Lines 18, 101–108):
  `Baro.ino` already samples BMP388 at 50 Hz and calculates vertical speed (`baro_vspeed_mps`) and filtered barometer altitude (`Altitude_barometer`):
  ```cpp
  float baro_temperature_c = NAN;
  float baro_pressure_pa = NAN;
  float baro_vspeed_mps = 0;
  ...
  float alt = 44330.0 * (1.0 - pow(p / baro_ground_pa, 0.1903));
  if (dt > 0 && dt < 1) {
    float v = (alt - baro_prev_alt) / dt;
    baro_vspeed_mps = baro_vspeed_mps * 0.8f + v * 0.2f;
  }
  baro_prev_alt = alt;
  Altitude_barometer = Altitude_barometer * 0.7f + alt * 0.3f;
  ```
* **File**: `firmware/FC_can_bang/MODE.ino` (Lines 8–11):
  ```cpp
  static void apply_altitude_limit() {
    if (!baro_available()) { alt_limiter.active = false; return; }
    throttle_smoot = altitude_throttle_cap(alt_limiter, Altitude_barometer - arm_ground_alt, max_altitude_m, (int)throttle_smoot);
  }
  ```
  `apply_altitude_limit()` calls `altitude_throttle_cap()` with only relative altitude and `throttle_smoot`. `baro_vspeed_mps` is declared globally in `Baro.ino` (compiled together in Arduino IDE build) but completely unused in altitude limiting!
* **File**: `tests/firmware/test_flight_gate.cpp` (Lines 58–74):
  ```cpp
  AltLimiter limiter;
  CHECK(altitude_throttle_cap(limiter, 50.0f, 120.0f, 1500) == 1500);
  CHECK(!limiter.active);
  CHECK(altitude_throttle_cap(limiter, 120.5f, 120.0f, 1500) == 1470);
  CHECK(limiter.active);
  CHECK(altitude_throttle_cap(limiter, 120.5f, 120.0f, 1400) == 1400);  // pilot may always go lower
  int capped = 1470;
  for (int i = 0; i < 2000; i++) capped = altitude_throttle_cap(limiter, 121.0f, 120.0f, 1600);
  CHECK(capped < 1470 && capped >= 1360 && capped <= 1375);              // 10 us per second at 200 Hz
  for (int i = 0; i < 200000; i++) capped = altitude_throttle_cap(limiter, 121.0f, 120.0f, 1600);
  CHECK(capped == ALT_LIMIT_FLOOR_US);
  CHECK(altitude_throttle_cap(limiter, 119.5f, 120.0f, 1600) == ALT_LIMIT_FLOOR_US);  // still inside the 1 m band
  CHECK(limiter.active);
  CHECK(altitude_throttle_cap(limiter, 118.9f, 120.0f, 1600) == 1600);
  CHECK(!limiter.active);
  ```
* **Firmware Build & Test Execution**:
  - `tests/firmware/test_host_build.py` uses host `g++ -std=c++17 -Wall -Wextra -Werror -I{FIRMWARE}` to compile `test_flight_gate.cpp` and `test_gps_nmea.cpp` and runs the resulting binaries.
  - Ran `pytest tests/firmware/`: Output: `2 passed in 3.51s`.

---

### 1.2 Pi 5 Local UI (`edge/pi5/pi5/web/ui/app.js`)
* **Monolith Structure**:
  - `app.js` has 589 lines in a single file.
  - Line 4: `import * as THREE from "/ui/vendor/three.module.min.js";`
  - Loaded in `index.html` via native ES module: `<script type="module" src="/ui/app.js"></script>`.
  - Core DOM builder: `h(tag, attrs, ...children)` (lines 16–30), HyperScript-like DOM creator without JSX.
  - View sections inside `app.js`:
    - Screen 1 (Wi-Fi scan/connect): `wifiScreen()` (lines 123–163)
    - Screen 2 (Auth/OTP/2FA/Register): `authScreen()` (lines 167–245)
    - Dashboard Tabs: `cameraView()` (lines 249–259), `mapView()` (lines 261–302), `telemetryView()` & `droneModel()` (lines 304–408), `usersView()` (lines 410–434), `firmwareView()` (lines 436–461).
    - Modals: `flightModal()` (line 470), `profileModal()` (line 489), `roleRequestModal()` (line 520).
    - Top Level / State: `dashboard()` (lines 529–570), `boot()` (lines 574–582).

### 1.3 Camera Stream & Bandwidth Control
* **File**: `edge/pi5/pi5/web/ui/app.js` (Lines 249–259):
  ```javascript
  function cameraView() {
    const image = h("img", { class: "camera", alt: "Hình từ webcam USB của Pi", src: `${API}/camera/mjpeg` });
    const note = h("p", { class: "muted" });
    image.addEventListener("error", () => { note.textContent = "Chưa có hình từ webcam USB. Kiểm tra camera đã cắm vào Pi."; });
    cleanup.push(() => { image.src = ""; });
    const live = h("span", { class: "chip live" }, "TRỰC TIẾP");
    image.addEventListener("error", () => { live.hidden = true; });
    image.addEventListener("load", () => { live.hidden = false; });
    return h("section", { class: "card" }, h("div", { class: "row between", style: "margin-bottom:12px" }, h("h2", { style: "margin:0" }, "Camera"),
      h("button", { type: "button", onclick: () => { note.textContent = ""; image.src = `${API}/camera/mjpeg?t=${Date.now()}`; } }, "Tải lại")), h("div", { class: "camera-frame" }, image, live), note);
  }
  ```
* **File**: `edge/pi5/pi5/web/camera.py`:
  - `MjpegStreamer` (lines 102–185) runs `v4l2-ctl` capture process.
  - Line 132: `if time.monotonic() - self._last_consumer > self._idle_seconds: break` (capture process automatically shuts down when all consumers disconnect!).
  - In browsers, an `<img>` element pointing to an MJPEG endpoint maintains an open HTTP connection downloading continuous multipart JPEG frames.
  - There is currently NO pause/resume button, only a "Tải lại" (Reload) button. Setting `image.src = ""` or placeholder stops frame downloads and drops the connection, while reassigning `image.src = `${API}/camera/mjpeg?t=${Date.now()}` resumes the stream.

### 1.4 OTA Firmware Update Flow & Endpoints
* **Current Backend Implementation**:
  - `edge/pi5/pi5/web/firmware.py`: Contains `FirmwareReadiness` and `FirmwareUpdater`.
  - `FirmwareUpdater` currently requires a GitHub repository (`PI_FW_GITHUB_REPO`) and calls GitHub releases API (`_release()`) to fetch `FC_can_bang.bin` and `.sha256`.
  - `edge/pi5/pi5/web/extra_routes.py` (Lines 192–234):
    - `GET /api/pi/v1/firmware/latest`
    - `POST /api/pi/v1/firmware/flash` (body: `{"version": "..."}`)
    - `GET /api/pi/v1/firmware/jobs/{job_id}`
  - `edge/pi5/pi5/web/app.py` (Line 570):
    - `GET /api/pi/v1/firmware/status` (calls `firmware_readiness.read()`)
* **Missing Direct Upload Flow**:
  - In field operations, client mobile/laptop connects directly to Pi's AP (`192.168.4.1`), which often has NO internet connection (upstream disconnected).
  - The backend lacks an endpoint to upload a local `.bin` file directly from the operator's browser (`POST /api/pi/v1/firmware/upload`).
  - The UI (`firmwareView()`, lines 436–461) only offers a button to flash from GitHub release; it has NO file input to select and upload a `.bin` file.

### 1.5 Test Suite Survey (`tests/scope05/`, `tests/scope07/`, `tests/scope04/`)
* **Test results**:
  - `tests/firmware/`: 2 passed (test_host_build.py compiling test_flight_gate.cpp and test_gps_nmea.cpp).
  - `tests/scope07/test_firmware_update.py`: 7 passed.
  - `tests/scope05/`: 34 passed, 1 failed:
    `test_pi_asgi_entrypoint_uses_esp_usb_boundary_without_opening_a_device` failed with:
    `ModuleNotFoundError: No module named 'fastapi'` because `pi5.web.asgi` imports `edge/pi5/pi5/web/app.py` which requires `fastapi`.
  - The system Python has no virtual environment active and `fastapi` is not installed globally. Pip dry-run verified network wheel installation works for `edge/pi5/pi5/requirements-scope04.lock`.

---

## 2. Logic Chain

### 2.1 Firmware Dynamics: Why 1100 µs Causes Free-Fall on F450
1. Observation 1.1 shows ESC PWM throttle range is 1000 µs (idle/stop) to 2000 µs (full throttle).
2. For an F450 drone (~1.2–1.6 kg with 3S/4S LiPo and payload), hover throttle ($T_{hover}$) is typically between 1400 µs and 1500 µs (~40%–50% thrust).
3. The current implementation in `flight_gate.h` line 81 hard-clamps:
   `if (s.cap_us < ALT_LIMIT_FLOOR_US) s.cap_us = ALT_LIMIT_FLOOR_US;` where `ALT_LIMIT_FLOOR_US = 1100`.
4. 1100 µs provides only ~10% motor output, which is far below hover thrust. The drone enters free fall.
5. In free fall, downward vertical velocity accelerates until `rel_alt_m < max_alt_m - 1.0f`. By then, high downward momentum and motor spin-up latency cause severe altitude undershoot or ground impact.
6. Observation 1.1 shows `Baro.ino` measures `baro_vspeed_mps` (vertical velocity in m/s).
7. If the dynamic floor is calculated using:
   - A base floor tied to the entry throttle ($T_{latch} - \Delta_{margin}$, e.g. $T_{latch} - 150\ \mu s$) OR
   - Vertical descent rate dampening: when descending at $\ge 0.5\ \text{m/s}$ (`vspeed_mps <= -0.5f`), the throttle floor halts further descent throttle reduction, preventing uncontrolled descent while still gently restoring altitude below the ceiling.
8. To preserve backward compatibility and allow `test_flight_gate.cpp` line 69 (`CHECK(capped == ALT_LIMIT_FLOOR_US)`) to pass, `altitude_throttle_cap()` can retain default arguments or an overloaded signature where default / fallback floor is `ALT_LIMIT_FLOOR_US` (1100), but when dynamic state parameters (such as `vspeed_mps` or `floor_us`) are supplied by `MODE.ino` via `Baro.ino`, it dynamically enforces the safe floor.

### 2.2 Pi UI Modernization Strategy
1. Observation 1.2 shows `index.html` loads `app.js` as an ES module (`<script type="module" src="/ui/app.js"></script>`).
2. Browsers natively support `import` and `export` across ES modules without requiring Webpack, Vite, or Node build tools.
3. `app.js` can be refactored into focused ES modules within `edge/pi5/pi5/web/ui/`:
   - `core/dom.js`: `h()`, `banner()`, `field()`, `form()`, `modal()`, `closeModal()`
   - `core/api.js`: `API`, `cookie()`, `api()`, `clearScreen()`, `every()`
   - `views/wifi.js`: `wifiScreen()`
   - `views/auth.js`: `authScreen()`, `showTerms()`, `termsCheck()`
   - `views/camera.js`: `cameraView()` with Pause/Resume toggle
   - `views/map.js`: `mapView()`
   - `views/telemetry.js`: `telemetryView()`, `droneModel()`
   - `views/users.js`: `usersView()`
   - `views/firmware.js`: `firmwareView()` with OTA `.bin` file upload and flash status
   - `views/flight.js`: `flightModal()`, `profileModal()`, `roleRequestModal()`, `refreshFlight()`
   - `app.js`: Main controller: initializes tabs, resize observer, and `boot()`.
4. This retains 100% of the UI design, CSS class names (`.card`, `.chip`, `.banner`, `.tabs`), and accessibility attributes while removing the 589-line monolithic structure.

### 2.3 Camera Pause/Resume Mechanism
1. Observation 1.3 shows `app.js` embeds an `<img>` tag requesting `/api/pi/v1/camera/mjpeg`.
2. Setting `image.src = ""` physically closes the browser HTTP connection.
3. Observation 1.3 shows `edge/pi5/pi5/web/camera.py` lines 132–134 shuts down `v4l2-ctl` after `_idle_seconds` (10s) when consumers disconnect.
4. Pausing in the UI immediately stops MJPEG data stream over Wi-Fi/4G, saving mobile bandwidth.
5. Resuming with `image.src = `${API}/camera/mjpeg?t=${Date.now()}` re-establishes the stream cleanly.
6. A UI toggle button (`Tạm dừng` / `Tiếp tục`) with visual status chip (`TRỰC TIẾP` / `TẠM DỪNG`) meets R3 without requiring backend architectural changes.

### 2.4 OTA Firmware Management Design
1. Observation 1.4 reveals that `FirmwareUpdater` currently only supports downloading from a configured GitHub repository.
2. In typical flight operations where the Pi operates as an offline AP (`192.168.4.1`), operators need to upload a locally compiled `.bin` file (`firmware/build/FC_can_bang.bin`).
3. Adding a `POST /api/pi/v1/firmware/upload` endpoint:
   - Accepts binary payload or multipart form data.
   - Verifies ESP32 header magic byte (`0xe9`) and file size ($\le 4\ \text{MB}$).
   - Verifies the drone is `DISARMED`.
   - Computes SHA-256 and writes to `PI_FW_WORKDIR / "FC_can_bang.bin"`.
   - Flashes via `esptool` pausing `esp_link` during flashing (reusing `FirmwareUpdater.flash` logic).
4. In `views/firmware.js`:
   - Adds a file input `<input type="file" accept=".bin">` with upload progress and status alert.

---

## 3. Caveats

1. **Hardware Validation vs Host Simulation**:
   - Firmware host unit tests (`test_flight_gate.cpp`) run pure C++ logic without hardware registers or ESP32 RTOS FreeRTOS primitives. Physical aerodynamic validation on real F450 frame requires flight test bench.
2. **FastAPI Dependency in Global Environment**:
   - Running `pytest tests/scope05/test_esp_usb.py` currently requires installing `requirements-scope04.lock` into the Python environment. In read-only investigation mode, packages were not installed.
3. **Browser Compatibility for ES Modules**:
   - ES modules require HTTP/HTTPS serving (already handled by FastAPI `app.mount("/ui", StaticFiles(...))`). Opening `index.html` directly via `file://` protocol in a browser would trigger CORS security errors, which is normal for modern web apps.

---

## 4. Conclusion & Recommendations

### 4.1 Firmware Limiter Fix Recommendation
In `firmware/FC_can_bang/flight_gate.h`:
1. Store latch throttle in `AltLimiter`:
   ```cpp
   struct AltLimiter {
     bool  active = false;
     float cap_us = 0;
     float latch_throttle_us = 0;
   };
   ```
2. Implement dynamic floor calculation:
   ```cpp
   // Dynamic floor calculation:
   // - Never falls below safe hover boundary (e.g., latch_throttle_us - 120 us)
   // - Dampens descent if vertical speed is downward (vspeed_mps < -0.4 m/s)
   // - Fallback to min_floor_us (default ALT_LIMIT_FLOOR_US = 1100) when dynamic parameters are omitted.
   static inline int calculate_dynamic_floor(float latch_throttle, float vspeed_mps, int fallback_floor = ALT_LIMIT_FLOOR_US) {
     if (latch_throttle <= 1150) return fallback_floor;
     int safe_floor = (int)latch_throttle - 120;
     if (safe_floor < 1300) safe_floor = 1300; // F450 minimum controllable descent floor
     if (vspeed_mps < -0.4f) {
       // Drone descending: increase floor to prevent sinking too fast
       safe_floor += (int)((-vspeed_mps - 0.4f) * 100.0f);
     }
     if (safe_floor > (int)latch_throttle - 20) safe_floor = (int)latch_throttle - 20;
     return safe_floor;
   }
   ```
3. Update `altitude_throttle_cap()` with optional `vspeed_mps` and dynamic floor parameters so existing calls in `test_flight_gate.cpp` remain valid, while `MODE.ino` passes `baro_vspeed_mps`.

### 4.2 Pi Local UI Modularization Recommendation
Decompose `edge/pi5/pi5/web/ui/app.js` into clean ES modules under `edge/pi5/pi5/web/ui/`:
```
edge/pi5/pi5/web/ui/
├── core/
│   ├── api.js
│   └── dom.js
├── views/
│   ├── auth.js
│   ├── camera.js      <-- contains pause/resume toggle
│   ├── firmware.js    <-- contains .bin upload & flash
│   ├── flight.js
│   ├── map.js
│   ├── telemetry.js
│   ├── users.js
│   └── wifi.js
├── app.css
├── app.js             <-- lightweight orchestrator (<60 lines)
└── index.html
```

### 4.3 Camera Pause/Resume Recommendation
In `views/camera.js`:
Add state `let streaming = true;` and a button next to `Tải lại`:
- When clicking `Tạm dừng`: `streaming = false`, `image.src = ""`, button text changes to `Tiếp tục`, chip changes to `TẠM DỪNG`.
- When clicking `Tiếp tục`: `streaming = true`, `image.src = `${API}/camera/mjpeg?t=${Date.now()}`, button text changes to `Tạm dừng`, chip changes to `TRỰC TIẾP`.

### 4.4 OTA Firmware Upload Recommendation
1. Add `POST /api/pi/v1/firmware/upload` in `edge/pi5/pi5/web/extra_routes.py` (or `app.py`).
2. Add `upload_and_flash(image: bytes)` in `edge/pi5/pi5/web/firmware.py`.
3. Add a file selection and upload UI in `views/firmware.js`.

---

## 5. Verification Method

### 5.1 Firmware Tests
1. Run host compilation unit test:
   `pytest tests/firmware/test_host_build.py`
2. Direct compilation with g++:
   `g++ -std=c++17 -Wall -Wextra -Werror -Ifirmware/FC_can_bang tests/firmware/test_flight_gate.cpp -o test_flight_gate.exe`
   `./test_flight_gate.exe`
   Expected: `flight_gate: all checks passed`

### 5.2 Pi 5 Backend & Scope Tests
1. Install Pi requirements:
   `pip install -r edge/pi5/pi5/requirements-scope04.lock`
2. Run Pi unit tests:
   `pytest tests/scope05/`
   `pytest tests/scope07/`
   `pytest tests/scope04/test_pi_features.py`
3. Verify modularized UI files load in browser without console errors by running FastAPI server:
   `uvicorn pi5.web.asgi:app --host 127.0.0.1 --port 8080`
