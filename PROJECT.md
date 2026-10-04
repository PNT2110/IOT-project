# Project: IoT Drone Zone Management System (F450 PNT PVD)

## Architecture
The system consists of a 3-tier distributed architecture:
1. **ESP32 Flight Controller Firmware (`firmware/`)**:
   - C++ flight controller running FreeRTOS/Arduino framework on ESP32.
   - Altitude control with barometer (BMP388) integration and flight gate limiting.
   - NMEA GPS processing, failsafe, and USB/Serial telemetry telemetry output.
2. **Raspberry Pi 5 Gateway & Local Web Interface (`edge/pi5/`)**:
   - FastAPI gateway handling USB communications with ESP32 flight controller.
   - MJPEG camera streaming (`camera.py`) from USB camera.
   - Offline AP mode web portal (`192.168.4.1`) written in modular Vanilla JS (ES modules).
   - Encrypted telemetry forwarding and local OTA firmware management.
3. **PC Central Server & Operations Frontend (`server/` and `frontend/`)**:
   - FastAPI backend with SQLite/PostgreSQL, SQLAlchemy ORM, cryptographic sealed envelopes (AES-256-GCM), Argon2-cffi auth, and TOTP MFA.
   - React 19 + TypeScript frontend with Leaflet/Geoman mapping, dark mode design system, real-time telemetry display, operator alerts, and GeoJSON/CSV exports.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Altitude Throttle Dynamic Floor | Replace hardcoded 1100 µs floor in `flight_gate.h` with dynamic floor factoring in entry throttle and `Baro.ino` vertical speed dampening | M1 | Bug 1 / ORIGINAL_REQUEST |
| 2 | Non-Blocking Email Sending | Wrap synchronous `SmtpEmailSender.send_code()` in `asyncio.to_thread()` in `server/app/mail.py` while preserving backwards compatibility | M1 | Bug 2 / ORIGINAL_REQUEST |
| 3 | Email Normalization | Implement RFC/provider-compliant email normalization in `server/app/security.py` (Gmail dot-stripping, `+tag` removal) | M1 | Bug 3 / ORIGINAL_REQUEST |
| 4 | Telemetry Ingestion Endpoint | Add authenticated/sealed envelope endpoint `POST /api/v1/device/telemetry` in `server/app/routers/device.py` | M2 | R4.1 / ORIGINAL_REQUEST |
| 5 | Telemetry Streaming/Query Endpoint | Add `GET /api/v1/telemetry/latest` (and SSE) in `server/app/routers/` delivering updates within 2 seconds | M2 | R4.1 / ORIGINAL_REQUEST |
| 6 | Flight Request Notification Endpoint | Add `GET /api/v1/flight-requests/notifications` for PC operators to query pending requests | M2 | R4.2 / ORIGINAL_REQUEST |
| 7 | Zone GeoJSON Export Endpoint | Add RFC 7946 compliant GeoJSON export endpoint `GET /api/v1/zones/export/geojson` | M2 | R4.3 / ORIGINAL_REQUEST |
| 8 | Flight History CSV Export Endpoint | Add RFC 4180 compliant CSV export endpoint `GET /api/v1/flight-requests/export/csv` | M2 | R4.3 / ORIGINAL_REQUEST |
| 9 | Pi 5 Local UI ES Module Modularization | Refactor monolithic `edge/pi5/pi5/web/ui/app.js` (589 lines) into structured ES modules (`core/`, `views/`) preserving design and behaviour | M3 | R3 / ORIGINAL_REQUEST |
| 10 | Pi Camera Stream Pause/Resume | Add bandwidth-saving pause/resume toggle to Pi camera view physically disconnecting MJPEG stream | M3 | R3 / ORIGINAL_REQUEST |
| 11 | Pi Local OTA Firmware Upload & Status | Add `POST /api/pi/v1/firmware/upload` and UI `.bin` upload & flashing status display on Pi local interface | M3 | R4.4 / ORIGINAL_REQUEST |
| 12 | PC Frontend Dark Mode | Implement `@media (prefers-color-scheme: dark)` token overrides, dark card backgrounds, inverted map tiles, and brand logo contrast in `experience.css` | M4 | R2 / ORIGINAL_REQUEST |
| 13 | OperationsWorkspace Loading States | Add initial loading skeletons and spinners during data fetch, tied to `aria-busy` in `OperationsWorkspace.tsx` | M4 | R2 / ORIGINAL_REQUEST |
| 14 | Auto-Dismissing Error Banners | Introduce 8-second auto-dismiss timer with manual dismiss button (`×`) and `role="alert"` preservation across PC frontend | M4 | R2 / ORIGINAL_REQUEST |
| 15 | PC Frontend Real-Time Telemetry View | Create telemetry panel in PC frontend displaying GPS position, altitude, and battery percentage with ≤2s update latency | M4 | R4.1 / ORIGINAL_REQUEST |
| 16 | PC Frontend Flight Request Notifications | Display real-time badge on flight requests tab, interactive toasts, and audio chime when new requests arrive | M4 | R4.2 / ORIGINAL_REQUEST |
| 17 | PC Frontend GeoJSON & CSV Exporters | Add export buttons for Zone GeoJSON and Flight history CSV triggers with browser download handling | M4 | R4.3 / ORIGINAL_REQUEST |
| 18 | E2E Opaque-Box Test Suite | Comprehensive 4-tier E2E opaque-box test suite covering all features and boundary cases | M_E2E | R5 / ORIGINAL_REQUEST |
| 19 | 100% E2E Verification & Adversarial Hardening | Pass 100% of E2E tests followed by white-box adversarial testing and forensic audit clean pass | M5 | Acceptance Criteria |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Core Bug Fixes across Tiers | Bug 1 (`flight_gate.h`), Bug 2 (`mail.py`), Bug 3 (`security.py`), unit tests in `tests/firmware/` and `tests/scope01/` | none | DONE |
| M2 | Server Backend APIs & Features | Ingestion & query telemetry APIs, flight notifications API, GeoJSON & CSV export APIs, backend pytest suites | none | DONE |
| M3 | Pi 5 Gateway & Local UI Modernization | Modular UI refactor (`core/`, `views/`), camera stream pause/resume, local OTA `.bin` upload endpoint & UI | none | DONE |
| M4 | PC Frontend UI/UX & Features | Dark mode, loading skeletons, 8s auto-dismiss error banners, telemetry view, flight notifications, export buttons, strict typecheck | M2 | DONE |
| M_E2E | E2E Testing Track | Requirement-driven opaque-box test infrastructure and Tier 1–4 test cases, publishing `TEST_READY.md` | none (parallel track) | DONE |
| M5 | Final Milestone: E2E Pass & Adversarial Hardening | Phase 1: 100% E2E test pass (Tiers 1-4); Phase 2: Tier 5 adversarial coverage hardening (77/77 E2E passed, 252 regression passed, CLEAN audit) | M1, M2, M3, M4, M_E2E | DONE |

---

## Interface Contracts

### 1. Firmware: Altitude Limiter (`firmware/FC_can_bang/flight_gate.h`)
```cpp
#define ALT_LIMIT_DEFAULT_FLOOR_US 1100
#define ALT_LIMIT_MARGIN_US 150.0f
#define ALT_LIMIT_STEP_US 0.05f
#define ALT_LIMIT_RELEASE_M 1.0f

struct AltLimiter {
  bool  active = false;
  float cap_us = 0;
  float floor_us = ALT_LIMIT_DEFAULT_FLOOR_US;
};

// Signature supporting both default fallback (backward compatibility) and dynamic state
static inline int altitude_throttle_cap(
    AltLimiter& s,
    float rel_alt_m,
    float max_alt_m,
    int throttle_us,
    float vspeed_mps = 0.0f,
    float min_floor_us = 0.0f
);
```

### 2. Server Backend: Telemetry Ingestion & Query
- **Ingestion**: `POST /api/v1/device/telemetry`
  - Headers: `X-Device-Id: PI_DEVICE_ID`, `X-Timestamp: ...`
  - Body: `DeviceEnvelope` (AES-256-GCM ciphertext)
  - Decrypted payload:
    ```json
    {
      "device_id": "pi-device-01",
      "seq": 101,
      "observed_at": "2026-10-03T20:50:00Z",
      "latitude": 21.0285,
      "longitude": 105.8544,
      "altitude_m": 42.5,
      "battery_pct": 92.0,
      "voltage_v": 11.9,
      "fix_state": "FIX",
      "stale": false
    }
    ```
- **Query**: `GET /api/v1/telemetry/latest?device_id=...`
  - Response: `200 OK` with JSON telemetry object above.

### 3. Server Backend: Flight Request Notifications
- **Query**: `GET /api/v1/flight-requests/notifications`
  - Response:
    ```json
    {
      "pending_count": 3,
      "latest_request_id": "uuid-...",
      "latest_submitted_at": "2026-10-03T20:45:00Z"
    }
    ```

### 4. Server Backend: Exports
- **Zone GeoJSON**: `GET /api/v1/zones/export/geojson`
  - Content-Type: `application/geo+json`
  - Header: `Content-Disposition: attachment; filename="zones.geojson"`
  - Body: RFC 7946 FeatureCollection of active zones.
- **Flight History CSV**: `GET /api/v1/flight-requests/export/csv`
  - Content-Type: `text/csv; charset=utf-8`
  - Header: `Content-Disposition: attachment; filename="flight_history.csv"`
  - Body: RFC 4180 CSV with decrypted flight request data.

### 5. Pi 5 Gateway: Local OTA Upload
- `POST /api/pi/v1/firmware/upload`
  - Accepts multipart/form-data with `.bin` file.
  - Verifies magic byte `0xe9`, max size 4MB, drone disarmed.
  - Returns `{"job_id": "...", "status": "QUEUED" | "FLASHING" | "COMPLETED" | "FAILED"}`.

---

## Code Layout
```
c:\Users\pnt21\Desktop\IOT\
├── firmware/
│   └── FC_can_bang/
│       ├── flight_gate.h         (Limiter dynamic floor)
│       ├── Baro.ino              (BMP388 barometer & vspeed)
│       └── MODE.ino              (apply_altitude_limit integration)
├── server/
│   └── app/
│       ├── mail.py               (Async SmtpEmailSender)
│       ├── security.py           (Email normalization)
│       ├── models.py             (Data models)
│       ├── schemas.py            (Pydantic schemas)
│       └── routers/
│           ├── auth.py
│           ├── device.py         (Telemetry ingestion)
│           ├── zones.py          (GeoJSON export)
│           ├── flights.py        (CSV export & notifications)
│           └── telemetry.py      (Telemetry query / stream)
├── edge/pi5/pi5/
│   └── web/
│       ├── app.py
│       ├── extra_routes.py       (OTA upload endpoint)
│       ├── camera.py             (Camera capture & idle disconnect)
│       └── ui/
│           ├── index.html        (ES module entry)
│           ├── app.js            (Controller)
│           ├── core/             (dom.js, api.js)
│           └── views/            (wifi, auth, camera, map, telemetry, users, firmware, flight)
├── frontend/
│   └── src/
│       ├── styles.css            (Base styles)
│       ├── experience.css        (Dark mode tokens & component dark overrides)
│       ├── api.ts                (Telemetry, notifications, export API clients)
│       ├── types.ts              (Telemetry and notification types)
│       └── components/
│           ├── ErrorBanner.tsx   (8s auto-dismiss banner with close button)
│           └── operations/
│               ├── OperationsWorkspace.tsx (Loading states, telemetry view, notifications, exports)
│               └── TelemetryPanel.tsx      (Live GPS, altitude, battery display)
└── tests/
    ├── e2e/                      (E2E Testing Track test harness & cases)
    ├── firmware/                 (Firmware unit tests)
    └── scope01/ - scope07/       (Tier regression tests)
```
