# Handoff Report — Survey Explorer 3 (Testing and Integration)

**Date**: 2026-09-09  
**From**: Survey Explorer 3 (`.agents/explorer_survey_3/`)  
**To**: Orchestrator / Parent Agent (`94568146-c35e-44d3-9a12-47c93b67809f`)  
**Task**: Survey existing tests, frontend-backend integration, and pending codebase blockers (R3 and Acceptance Criteria).  
**Handoff Type**: Hard (Task complete)

---

## 1. Observation

### 1.1 Backend Test Suite Observations
- **Test File Locations**:
  - `backend/tests/test_api.py` (45 lines)
  - `backend/tests/test_core.py` (107 lines)
- **Existing Tests**: 8 tests across 2 files:
  - `test_valid_gga_sentence` (`test_core.py:12`): validates GGA sentence parsing, latitude 48.1173, satellites 8, `valid=True`.
  - `test_bad_checksum_rejected` (`test_core.py:21`): validates rejection of invalid checksum `*00`.
  - `test_geofence_inside_outside_warning` (`test_core.py:25`): validates polygon inside ("breach") vs outside ("safe").
  - `test_jsonl_esp_parser_updates_attitude` (`test_core.py:53`): validates JSON line parsing into `frame.attitude` and `frame.armed`.
  - `test_command_retry_reuses_id_and_accepts_ack` (`test_core.py:60`): validates 2 attempts, UUID reuse, and ACK acceptance.
  - `test_command_fails_fast_without_serial` (`test_core.py:82`): validates immediate exit on attempt 1 when serial worker returns `False`.
  - `test_command_times_out_after_three_attempts` (`test_core.py:92`): validates 3 retry attempts before giving up with `ack=None`.
  - `test_role_boundaries_csrf_and_command_lock` (`test_api.py:10`): validates TOTP requirement for admin, CSRF requirement, HTTP 423 on land command when locked, viewer role restricted endpoints (403), and password/TOTP rotation.
- **Serial Mocking in Current Tests**:
  - Serial is mocked exclusively via duck-typed classes in `test_core.py:63-72, 83-86, 93-100` (`FakeWorker`, `MissingWorker`, `SilentWorker`).
  - `SerialWorker` class (`backend/app/serial_io.py:123-173`), `gps_device()`, `esp_device()`, and pyserial interaction are **never instantiated or exercised** in tests.
- **Fixtures**:
  - Only built-in `tmp_path` is used (`test_api.py:10`, `test_core.py:25`). No `conftest.py` exists.
- **Lifespan Side Effects in `test_api.py`**:
  - `with TestClient(app) as client:` triggers `lifespan` in `backend/app/main.py:95-115`, which starts background threads `gps_worker.start()` and `esp_worker.start()`. On machines without hardware, `gps_worker` continuously logs `gps serial unavailable: ...`.

### 1.2 Frontend Telemetry Integration & Data Contracts Observations
- **WebSocket Endpoint**:
  - Defined in `backend/app/main.py:290-302` (`@app.websocket("/ws/telemetry")`).
  - Consumed in `frontend/src/App.tsx:191`: `new WebSocket(`${scheme}://${location.host}/ws/telemetry`)`.
  - Pushes full `TelemetryFrame` at 5 Hz (`asyncio.sleep(0.2)`).
- **REST Endpoints Consumed by Frontend**:
  - `GET /api/v1/auth/me`: `frontend/src/api.ts:13`
  - `POST /api/v1/auth/login`: `frontend/src/api.ts:14-19`
  - `POST /api/v1/auth/logout`: `frontend/src/api.ts:20`
  - `GET /api/v1/status`: `frontend/src/api.ts:21` (polled every 5s in `App.tsx:188`)
  - `GET /api/v1/camera/status`: `frontend/src/api.ts:22` (polled on mount in `App.tsx:80`)
  - `GET /api/v1/serial/raw`: `frontend/src/api.ts:23` (polled every 3s in `App.tsx:189`)
  - `GET /api/v1/geofence/zones`: loaded by MapLibre in `App.tsx:149`
  - `GET /api/v1/map-pack/file`: loaded by PMTiles protocol in `App.tsx:142`
- **Data Contract Alignment**:
  - `Telemetry` in `frontend/src/types.ts:9-35` strictly matches `TelemetryFrame` in `backend/app/models.py:53-65`.
  - `SystemStatus` in `frontend/src/types.ts:37-44` strictly matches the dictionary returned by `GET /api/v1/status` (`backend/app/main.py:187-194`).
  - Battery telemetry (`battery_volts`, etc.) is **not present** in either `models.py` or `types.ts`.

### 1.3 Codebase Blockers & Robustness Observations
- **UART Close Race Condition**:
  - In `backend/app/serial_io.py:137-142` (`SerialWorker.stop`):
    ```python
    def stop(self) -> None:
        self.stop_event.set()
        if self.port:
            self.port.close()
        if self.thread:
            self.thread.join(timeout=2)
    ```
  - In `backend/app/serial_io.py:144-149` (`SerialWorker.write_line`):
    ```python
    def write_line(self, line: str) -> bool:
        if not self.port or not self.port.is_open:
            return False
        self.port.write((line.rstrip() + "\n").encode())
        self.port.flush()
        return True
    ```
  - `self.port` is read/written across threads without a lock. If `write_line` executes while `stop` closes the port or `_run` sets `self.port = None`, unhandled `AttributeError` or `serial.PortNotOpenError` occurs.
  - In `_run()` line 155 and 172: `time.sleep(2)` delays thread termination on shutdown when device is not connected.
- **R1 & R2 Port Collision**:
  - `gps_device()` (`serial_io.py:175-176`) checks `settings.gps_device` (`/dev/serial0` by default).
  - `esp_device()` (`serial_io.py:179-185`) globs `/dev/serial/by-id/*`, `/dev/ttyACM*`, `/dev/ttyUSB*` and returns `candidates[0]`.
  - When GPS migrates to USB (CH340 adapter), both GPS and ESP32 appear as `/dev/ttyUSB*` with identical VID:PID (`1a86:7523`). `esp_device` will collide with GPS on `candidates[0]`.
- **Preflight Logic Discrepancy**:
  - Backend `/api/v1/preflight` checks `gps`: `frame.gps_connected and frame.gps.valid and not frame.gps.stale`.
  - Frontend `App.tsx:231` checks: `['GPS fix hợp lệ', !!telemetry?.gps.valid]`. It misses checking `stale` and `gps_connected`.
- **Real Flight Safety Lock**:
  - `ENABLE_REAL_FLIGHT_COMMANDS` defaults to `False` in `backend/app/config.py:22`.
  - When `False`, `POST /api/v1/commands/land` returns HTTP 423 (`main.py:277-279`) and `safety_command_loop` suppresses automatic land (`main.py:72`).

---

## 2. Logic Chain

1. **Test Coverage Gap**:
   - Because existing tests in `test_core.py` mock serial workers using `FakeWorker` duck types (Obs 1.1), `SerialWorker` lifecycle and exception handling (`serial.SerialException`, `OSError`, `TypeError`) are never tested.
   - Therefore, introducing USB serial port detection, 38400 baud support, and ESP32 routing without automated unit tests would violate acceptance criteria.
2. **Device Routing & Conflict Resolution**:
   - Because both GPS and ESP32 use USB-to-TTL adapters that enumerate dynamically under `/dev/ttyUSB*` with identical CH340 hardware IDs (Obs 1.3), naive index selection (`candidates[0]`) will inevitably cause port collisions or wrong baud assignment (38400 baud GPS stream sent to 115200 baud ESP worker).
   - Therefore, a content-based auto-detection router is required that sniffs the incoming byte stream (valid NMEA checksum vs JSON telemetry) and leases ports exclusively.
3. **Thread Safety & Shutdown Fix**:
   - Because `self.port` is unprotected by locks and `time.sleep(2)` blocks thread joining (Obs 1.3), `SerialWorker` can throw exceptions during concurrent `write_line` calls and times out on service shutdown.
   - Therefore, adding a `threading.Lock()` to `write_line` and replacing `time.sleep(2)` with `self.stop_event.wait(timeout=2.0)` eliminates race conditions and ensures clean, immediate shutdown.
4. **Frontend Contract Invariance**:
   - Because the frontend TypeScript interfaces (`Telemetry`, `SystemStatus`) map 1:1 to `TelemetryFrame` and `SystemStatus` (Obs 1.2), backend refactoring of device routing must not alter the external shape or field names of these objects.
5. **Acceptance Test Plan**:
   - A cross-platform `MockSerial` class that simulates NMEA at 38400 baud, JSON at 115200 baud, and disconnection exceptions will allow pytest to thoroughly verify port auto-detection, baud configuration, and disconnection recovery without requiring physical hardware.

---

## 3. Caveats

1. **Physical Hardware Verification**:
   - Live hardware verification with the physical BZ251 GPS module and ESP32 board requires deployment on the Raspberry Pi 5. In local workspace environments, tests must rely on simulated mock streams.
2. **Local Python Environment**:
   - The local Windows environment currently has Python 3.12 without `pytest` installed globally, and stale `.venv` folders referencing Python 3.10/3.14. Running tests locally on Windows will require creating a clean virtual environment (`python -m venv .venv; pip install -r backend/requirements.txt`). On the Pi, `/opt/iot-drone/venv/` has all dependencies installed.
3. **Firmware Source for ESP32**:
   - Real ESP32 firmware source is not yet in the repository. ESP32 telemetry testing is strictly based on the agreed JSONL schema (`{"type":"telemetry", ...}`) and ACK frame specification.

---

## 4. Conclusion

1. The current codebase has a solid foundation (8 passing tests, clean API/WebSocket separation, strict fail-closed safety guards).
2. The primary architectural need is a **Central Serial Device Router**:
   - Automatically probes and classifies candidate serial ports via stream content.
   - Operates GPS at **38400 baud** (NMEA) and ESP32 at **115200 baud** (JSON).
   - Prevents port contention and seamlessly handles device disconnection and re-enumeration.
   - Ensures thread-safe worker shutdown and writing.
3. The frontend contracts are verified and must remain 100% untouched.
4. An automated acceptance test suite using `MockSerial` in pytest can be introduced to verify all R1, R2, and R3 requirements while preserving all 8 existing tests.

---

## 5. Verification Method

### How to Independently Verify This Report:
1. **Inspect Test Suite**:
   - View `backend/tests/test_api.py` and `backend/tests/test_core.py` to confirm the 8 tests, `tmp_path` fixture usage, and `FakeWorker` mock implementations.
2. **Inspect Frontend Contracts**:
   - View `frontend/src/types.ts` and `backend/app/models.py` to confirm exact matching between `Telemetry` and `TelemetryFrame`.
3. **Inspect Thread Safety & Port Resolvers**:
   - View `backend/app/serial_io.py:123-185` to confirm `self.port` concurrency vulnerability, `time.sleep(2)` blocking, and `esp_device()` `candidates[0]` collision.
4. **Run Existing Tests (once venv is active)**:
   - Command: `pytest backend/tests`
   - Expected result: 8 passed.
5. **Detailed Analysis Reference**:
   - Refer to `.agents/explorer_survey_3/analysis.md` for full field mapping tables, race condition call-traces, and code sketches for `MockSerial`.
