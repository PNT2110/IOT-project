# Comprehensive Survey & Analysis Report
**Role**: Survey Explorer 3 (Testing & Integration Explorer)  
**Target Project**: IOT Drone Station (Raspberry Pi 5)  
**Date**: 2026-09-09  

---

## Executive Summary

This report delivers a thorough survey of the backend test suite, frontend telemetry contracts, pending codebase blockers, and a proposed acceptance test plan for the IOT Drone Station. 

Key takeaways:
1. **Backend Tests**: Currently 8 unit tests in `backend/tests/test_api.py` (1 test) and `test_core.py` (7 tests) pass on deployment. However, serial communication is only tested with simplistic mock duck-types (`FakeWorker`, `MissingWorker`, `SilentWorker`). There is **zero test coverage** for `SerialWorker` lifecycle, thread safety, port resolution, baud rate configuration, or pyserial exception handling.
2. **Frontend Telemetry Contracts**: The frontend (`frontend/src/`) strictly relies on WebSocket `/ws/telemetry` (5 Hz) and REST endpoints (`/api/v1/status`, `/api/v1/serial/raw`, `/api/v1/camera/status`, `/api/v1/geofence/zones`, `/api/v1/map-pack/file`). The TypeScript interfaces (`Telemetry`, `SystemStatus`) match the Pydantic models (`TelemetryFrame`, `SystemStatus`) exactly. Crucially, battery telemetry is not yet part of the active schema. Any backend refactoring must preserve this JSON schema with 100% fidelity.
3. **Software Blockers**:
   - **UART Close Race Condition / Thread Safety**: In `SerialWorker`, `self.port` is shared across threads without synchronization locks; `write_line` can throw `AttributeError` or `SerialException` if called while the worker is disconnecting or stopping. Furthermore, `time.sleep(2)` delays thread termination on shutdown.
   - **R1 & R2 USB Migration & Port Collision**: GPS is migrating from `/dev/serial0` (UART GPIO) to USB-to-TTL at **38400 baud**. Both GPS and ESP32 may use identical CH340 adapters (`1a86:7523`), resulting in unpredictable USB port assignment (`/dev/ttyUSB0` vs `/dev/ttyUSB1`). A content-aware, collision-free device routing architecture is mandatory.
   - **Safety Rules**: `ENABLE_REAL_FLIGHT_COMMANDS=false` is rigorously fail-closed (HTTP 423 on land command, preflight fail, auto-land suppressed).
4. **Acceptance Test Plan**: A cross-platform `MockSerial` architecture for `pytest` that simulates 38400 baud NMEA streams, 115200 baud ESP32 JSON streams, port contention, dynamic unplugs, and port swapping while maintaining 100% pass rate on all 8 existing tests.

---

## 1. Backend Test Suite Review (`backend/tests/`)

### 1.1 Test Suite Inventory and Execution
- **Location**: `backend/tests/`
- **Files**:
  - `backend/tests/test_api.py` (45 lines)
  - `backend/tests/test_core.py` (107 lines)
- **Framework**: `pytest==8.4.1` (specified in `backend/requirements.txt`).
- **Execution Mechanism**:
  - Asynchronous tests invoke `asyncio.run(...)` directly inside test functions (e.g. `test_core.py:75, 87, 102`) rather than using `pytest-asyncio`.
  - API tests use Starlette's `TestClient(app)` as a context manager (`test_api.py:17`).

### 1.2 Catalog of Existing Tests (All 8 Tests)

| # | Test Function | File & Lines | Target Component | Verifications Performed |
|---|---|---|---|---|
| 1 | `test_valid_gga_sentence` | `test_core.py:12-19` | `parse_nmea_line` | Parses valid `$GPGGA` sentence; asserts `fix.valid == True`, `latitude == 48.1173`, `satellites == 8`. |
| 2 | `test_bad_checksum_rejected` | `test_core.py:21-23` | `parse_nmea_line` | Submits `$GPGGA` with invalid checksum `*00`; asserts parser returns `None`. |
| 3 | `test_geofence_inside_outside_warning` | `test_core.py:25-51` | `GeofenceEngine` | Writes temporary GeoJSON polygon; asserts `evaluate()` returns status `"breach"` inside coordinates and `"safe"` outside. |
| 4 | `test_jsonl_esp_parser_updates_attitude` | `test_core.py:53-58` | `state.update_esp_line` | Feeds JSON `{"type":"telemetry","attitude":{"roll":1,"pitch":2,"yaw":3},"armed":true}`; asserts `frame.attitude.roll == 1`, `frame.armed == True`. |
| 5 | `test_command_retry_reuses_id_and_accepts_ack` | `test_core.py:60-80` | `CommandDispatcher.land` | Simulates worker responding with ACK on attempt 2; asserts attempt count is 2, UUID is preserved across retries, ACK is accepted. |
| 6 | `test_command_fails_fast_without_serial` | `test_core.py:82-90` | `CommandDispatcher.land` | Worker `write_line` returns `False`; asserts immediate exit on attempt 1, `ack is None`. |
| 7 | `test_command_times_out_after_three_attempts` | `test_core.py:92-107` | `CommandDispatcher.land` | Worker `write_line` succeeds but yields no ACK; asserts 3 attempts made, `ack is None`, all attempts reuse same command UUID. |
| 8 | `test_role_boundaries_csrf_and_command_lock` | `test_api.py:10-45` | FastAPI endpoints, DB, Auth | Admin login with TOTP; CSRF token validation; `POST /api/v1/commands/land` blocked with HTTP 423; CSRF required for logout; Viewer login without TOTP; Viewer permitted on `/camera/status` (200) but forbidden (403) on `/status`, `/telemetry/latest`, `/geofence/zones`; Password and TOTP rotation. |

### 1.3 Fixtures and State Isolation
1. **Built-in Fixture Only**: Only standard `tmp_path: Path` is used (`test_core.py:25`, `test_api.py:10`).
2. **Missing `conftest.py`**: No shared test setup or teardown exists.
3. **Shared State Pollution Risks**:
   - `test_api.py` modifies the singleton `db.path`:
     ```python
     db.path = tmp_path / "test.sqlite3"
     db.initialize()
     ```
   - `test_core.py:54` updates the global singleton `state`:
     ```python
     state.update_esp_line('{"type":"telemetry",...}')
     ```
     This leaks mutated attitude state across test runs unless explicitly reset.
   - `TestClient(app)` in `test_api.py:17` invokes the full `lifespan` context in `backend/app/main.py:95-115`:
     - Calls `gps_worker.start()` and `esp_worker.start()`.
     - Spawns background loops: `telemetry_loop`, `recorder_loop`, `safety_command_loop`, `simulated_telemetry`.
     - When running without hardware (or on Windows), `gps_worker` attempts to open `/dev/serial0` and logs `gps serial unavailable: ...` in the background.

### 1.4 How Serial Devices are Currently Mocked
In `test_core.py`, serial communication is mocked exclusively via lightweight in-test duck typing:
```python
class FakeWorker:
    def __init__(self):
        self.lines = []
    def write_line(self, line):
        self.lines.append(line)
        if len(self.lines) == 2:
            command_id = json.loads(line)["id"]
            telemetry.update_esp_line(json.dumps({"version": 1, "type": "ack", "command_id": command_id, "accepted": True}))
        return True

class MissingWorker:
    def write_line(self, _line):
        return False

class SilentWorker:
    def __init__(self):
        self.lines = []
    def write_line(self, line):
        self.lines.append(line)
        return True
```
**Critical Gaps in Current Test Suite**:
- `SerialWorker` itself is **completely untested**: `start()`, `stop()`, `_run()`, `self.port` management, and exception handling are never exercised.
- `gps_device()` and `esp_device()` resolver logic is untested.
- Baud rate configuration (38400 for GPS, 115200 for ESP) is never verified.
- Concurrency, serial disconnects, reconnection loops, and port conflicts are never verified.

---

## 2. Frontend Telemetry Integration & Data Contracts

### 2.1 Communication Channels & Protocols

The frontend (`frontend/src/`) communicates with the backend via two channels:
1. **WebSocket Stream (`/ws/telemetry`)**:
   - Connected in `AdminView` (`App.tsx:191`):
     ```typescript
     const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
     const ws = new WebSocket(`${scheme}://${location.host}/ws/telemetry`)
     ```
   - Pushed by backend at 5 Hz (every 0.2s) in `main.py:298-300`.
   - Requires valid `admin` session cookie (closes with code 4403 if unauthenticated or viewer).
   - Payload is full snapshot of `TelemetryFrame`.
2. **REST Endpoints**:
   - `GET /api/v1/auth/me`: Verifies active session (`UserSession`).
   - `POST /api/v1/auth/login`: Authenticates user (`LoginRequest` -> `UserSession`).
   - `POST /api/v1/auth/logout`: Invalidates session (requires CSRF token).
   - `GET /api/v1/status`: Polled every 5s (`SystemStatus`).
   - `GET /api/v1/serial/raw`: Polled every 3s (`{ lines: string[] }`).
   - `GET /api/v1/camera/status`: Polled on mount (`CameraStatus`).
   - `GET /api/v1/geofence/zones`: Fetched on MapLibre initialization (`FeatureCollection`).
   - `GET /api/v1/map-pack/file`: Static PMTiles served with HTTP Range header support (`206 Partial Content`).

### 2.2 Data Contract Cross-Verification

Below is the field-by-field verification between Backend models (`backend/app/models.py`) and Frontend types (`frontend/src/types.ts`):

#### Telemetry Frame Contract
| Field Path | Backend Type (`models.py`) | Frontend Type (`types.ts`) | UI Component / Rendering (`App.tsx`) | Status |
|---|---|---|---|---|
| `timestamp` | `datetime` (ISO 8601 string) | `string` | Stored in state | Compatible |
| `gps.latitude` | `float \| None` | `number \| null` | Map marker (`FlightMap:163`), Footer (`App.tsx:234`) | Compatible |
| `gps.longitude` | `float \| None` | `number \| null` | Map marker (`FlightMap:164`), Footer (`App.tsx:234`) | Compatible |
| `gps.altitude_m` | `float \| None` | `number \| null` | Metric card `ĐỘ CAO` (`App.tsx:203`) | Compatible |
| `gps.speed_mps` | `float \| None` | `number \| null` | Metric card `TỐC ĐỘ` (`App.tsx:204`) | Compatible |
| `gps.satellites` | `int \| None` | `number \| null` | Metric card `VỆ TINH` (`App.tsx:205`) | Compatible |
| `gps.course_deg` | `float \| None` | `number \| null` | Defined in `Telemetry` type | Compatible |
| `gps.hdop` | `float \| None` | `number \| null` | Footer `HDOP` (`App.tsx:234`) | Compatible |
| `gps.fix_quality`| `int` (default 0) | `number` | Defined in `Telemetry` type | Compatible |
| `gps.valid` | `bool` (default False) | `boolean` | Preflight check `GPS fix hợp lệ` (`App.tsx:231`) | Compatible |
| `gps.stale` | `bool` (default True) | `boolean` | Defined in `Telemetry` type | Compatible |
| `attitude.roll` | `float` (degrees) | `number` | 3D drone mesh rotation & readout (`App.tsx:105, 124`) | Compatible |
| `attitude.pitch`| `float` (degrees) | `number` | 3D drone mesh rotation & readout (`App.tsx:105, 124`) | Compatible |
| `attitude.yaw` | `float` (degrees) | `number` | 3D drone mesh rotation & readout (`App.tsx:105, 124`) | Compatible |
| `pid.roll.output` | `float \| None` | `number \| null` | PID AreaChart 5 Hz rolling graph (`App.tsx:195, 228`) | Compatible |
| `pid.pitch.output`| `float \| None` | `number \| null` | PID AreaChart 5 Hz rolling graph (`App.tsx:195, 228`) | Compatible |
| `pid.yaw.output` | `float \| None` | `number \| null` | PID AreaChart 5 Hz rolling graph (`App.tsx:195, 228`) | Compatible |
| `pid[axis].*` | `kp, ki, kd, setpoint, measured` | `number \| null` | Defined in `types.ts` | Compatible |
| `armed` | `bool` | `boolean` | Defined in `types.ts` | Compatible |
| `flight_mode` | `str` | `string` | Metric card `CHẾ ĐỘ` (`App.tsx:206`) | Compatible |
| `esp_connected` | `bool` | `boolean` | Topbar status pill (`App.tsx:213`), 3D badge `LIVE`/`SIM` | Compatible |
| `gps_connected` | `bool` | `boolean` | Topbar status pill (`App.tsx:213`) | Compatible |
| `geofence.status`| `"unknown"\|"safe"\|"warning"\|"breach"` | string union | Metric card `VÙNG BAY` (`App.tsx:221`) | Compatible |
| `geofence.zone_name`| `str \| None` | `string \| null` | Defined in `types.ts` | Compatible |
| `geofence.distance_m`| `float \| None` | `number \| null` | Defined in `types.ts` | Compatible |
| `geofence.data_ready`| `bool` | `boolean` | Preflight & Topbar status pill | Compatible |

#### System Status Contract (`GET /api/v1/status`)
| Field | Backend (`main.py:187-194`) | Frontend (`types.ts:37-44`) | Usage in `App.tsx` | Status |
|---|---|---|---|---|
| `gps_connected` | `bool` | `boolean` | Topbar `GPS` pill (`App.tsx:213`) | Compatible |
| `esp_connected` | `bool` | `boolean` | Topbar `ESP` pill, 3D `LIVE`/`SIM` badge | Compatible |
| `geofence_ready`| `bool` | `boolean` | Topbar `GEOFENCE` pill (`App.tsx:213`) | Compatible |
| `map_ready` | `bool` | `boolean` | Map loaded or placeholder display (`App.tsx:172`) | Compatible |
| `real_commands_enabled`| `bool` | `boolean` | Safety banner `SAFE MODE` (`App.tsx:217`) | Compatible |
| `raw_esp_lines` | `int` | `number` | Serial monitor panel header count (`App.tsx:229`) | Compatible |

### 2.3 Clarification on Battery Telemetry
- Observation: Neither `backend/app/models.py` nor `frontend/src/types.ts` currently contains battery fields (`voltage`, `current`, `percentage`).
- Rule: If battery fields are introduced later from ESP32 telemetry, they must be added as optional fields (`battery_volts: float | None = None`) to preserve 100% backward compatibility with current frontend builds.

---

## 3. Pending Software Blockers & Robustness Analysis

### 3.1 UART Close Race Condition & Thread Safety in `SerialWorker`

#### Current Implementation (`serial_io.py:123-173`):
```python
class SerialWorker:
    def __init__(self, name: str, device_resolver: Callable[[], str | None], baud: int, line_handler: Callable[[str], None]):
        ...
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.port: serial.Serial | None = None

    def stop(self) -> None:
        self.stop_event.set()
        if self.port:
            self.port.close()
        if self.thread:
            self.thread.join(timeout=2)

    def write_line(self, line: str) -> bool:
        if not self.port or not self.port.is_open:
            return False
        self.port.write((line.rstrip() + "\n").encode())
        self.port.flush()
        return True

    def _run(self) -> None:
        while not self.stop_event.is_set():
            device = self.device_resolver()
            if not device:
                time.sleep(2)
                continue
            try:
                with serial.Serial(device, self.baud, timeout=1) as port:
                    self.port = port
                    while not self.stop_event.is_set():
                        raw = port.readline()
                        if raw:
                            self.line_handler(raw.decode("ascii", errors="replace").strip())
            except (serial.SerialException, OSError, TypeError) as exc:
                log.warning("%s serial unavailable: %s", self.name, exc)
            finally:
                self.port = None
            time.sleep(2)
```

#### Vulnerabilities Identified:
1. **Unsynchronized `self.port` Read/Write Race**:
   `self.port` is updated in `_run()` (`self.port = port`, then `finally: self.port = None`), while `write_line()` reads `self.port` from FastAPI's event loop thread.
   If `stop()` closes the port or `_run()` exits right between `if not self.port or not self.port.is_open:` and `self.port.write(...)`, `write_line()` will raise `AttributeError: 'NoneType' object has no attribute 'write'` or `serial.PortNotOpenError`.
2. **Uninterruptible `time.sleep(2)`**:
   When no device is plugged in or during reconnect delay, `_run()` calls `time.sleep(2)`. If `stop()` is called during this sleep, `stop()` blocks on `self.thread.join(timeout=2)` and frequently times out!
   *Solution*: Replace `time.sleep(2)` with `self.stop_event.wait(timeout=2.0)`. This wakes immediately when `stop()` sets `self.stop_event`.
3. **Missing Lock for Serial Write**:
   Concurrent calls to `write_line()` can interleave bytes on the serial wire. `write_line` must acquire a dedicated `threading.Lock()`.

---

### 3.2 R1 & R2: USB Migration & Port Collision Analysis

#### The Problem:
- **R1 (USB Migration for GPS)**: GPS BZ251 is moving from GPIO UART (`/dev/serial0`) to a USB-to-TTL adapter (e.g. CH340) at **38400 baud**.
- **R2 (Concurrent USB Device Handling)**: ESP32 is also connected via USB-to-TTL (often also CH340) at **115200 baud**.
- **The Collision Risk**:
  Currently, `esp_device()` does:
  ```python
  candidates: list[str] = []
  for pattern in ("/dev/serial/by-id/*", "/dev/ttyACM*", "/dev/ttyUSB*"):
      candidates.extend(sorted(glob.glob(pattern)))
  return candidates[0] if candidates else None
  ```
  If both devices use CH340 adapters:
  1. Both devices share the same USB VID:PID (`1a86:7523`). Their `/dev/serial/by-id/` entries often have identical ID strings or collide.
  2. Linux assigns `/dev/ttyUSB0` and `/dev/ttyUSB1` based purely on kernel enumeration order (which USB port was plugged first or responded first upon reboot).
  3. If `esp_device()` blindly picks `candidates[0]`, it may grab the GPS port!
  4. If GPS worker and ESP worker target the same port or swapped ports:
     - GPS worker at 38400 baud listening to ESP32: receives gibberish or nothing.
     - ESP worker at 115200 baud listening to GPS: receives corrupted NMEA, fails JSON decoding.
     - Or both workers attempt to open the same `/dev/ttyUSB0`, triggering `serial.SerialException: Device or resource busy`.

#### Architectural Requirement for Port Auto-Detection & Routing:
A unified **Serial Device Router / Manager** is needed:
1. **Baud Rate Strategy**:
   - GPS worker requires **38400 baud**.
   - ESP32 worker requires **115200 baud**.
2. **Content-Based Probing / Classification**:
   - Available serial ports (`/dev/ttyUSB*`, `/dev/ttyACM*`, `/dev/serial/by-id/*`, or `COM*` on Windows via `serial.tools.list_ports`) are identified.
   - Ports explicitly pinned via config (`GPS_DEVICE=/dev/...`, `ESP_DEVICE=/dev/...`) are respected if configured to an explicit path.
   - For auto-detection (`auto`):
     - Probe Candidate Port:
       - Open briefly at 38400 baud. If valid NMEA sentence starting with `$` (`$GP...`, `$GN...`) with valid checksum is received within ~1.0s -> Classified as **GPS**.
       - Open briefly at 115200 baud. If valid JSON telemetry line (`{"type":"telemetry"...}`) or ESP-IDF log text is received -> Classified as **ESP32**.
3. **Collision Prevention**:
   - A port assigned to GPS cannot be assigned to ESP, and vice versa.
4. **Dynamic Re-enumeration / Disconnection Recovery**:
   - When a USB device is unplugged and re-plugged, it may shift from `/dev/ttyUSB0` to `/dev/ttyUSB1`.
   - The router must detect disconnection, release the port assignment, re-scan candidate ports, and re-bind.

---

### 3.3 Error Handling, Stale Data Timeouts, Preflight Checks

1. **Stale Data Timeout Mechanics**:
   - In `TelemetryState.snapshot()` (`serial_io.py:37-39`):
     ```python
     now = time.monotonic()
     frame.gps_connected = now - self.last_gps_monotonic < settings.gps_stale_seconds
     frame.esp_connected = now - self.last_esp_monotonic < settings.gps_stale_seconds
     frame.gps.stale = not frame.gps_connected
     ```
   - In `safety_command_loop()` (`main.py:77-85`):
     ```python
     if frame.gps_connected and frame.gps.valid and not frame.gps.stale:
         gps_lost_since = None
     elif gps_lost_since is None:
         gps_lost_since = now
     ...
     elif gps_lost_since is not None and now - gps_lost_since >= settings.gps_stale_seconds:
         reason = "GPS_LOST"
     ```
   - Notice: `gps_lost_since` is only set after `gps_connected` becomes `False` (which takes `settings.gps_stale_seconds` = 5s), and then it waits *another* `gps_stale_seconds` (5s) before triggering `GPS_LOST`. Total time to trigger: 10s. This double-delay should be noted or streamlined in backend documentation.

2. **Preflight Check Discrepancy (Backend vs Frontend)**:
   - Backend `/api/v1/preflight` evaluates:
     - `gps`: `frame.gps_connected and frame.gps.valid and not frame.gps.stale`
     - `esp`: `frame.esp_connected`
     - `geofence`: `frame.geofence.data_ready and zone_sync_fresh`
     - `map`: `settings.map_path.exists()`
     - `firmware_commands`: `settings.enable_real_flight_commands`
   - Frontend `App.tsx:231` currently checks:
     `['GPS fix hợp lệ', !!telemetry?.gps.valid]`
     It does not check `!telemetry?.gps.stale` or `telemetry?.gps_connected`! If GPS gets a fix and is then unplugged, `telemetry.gps.valid` stays `true` while `stale` is `true`.
   - Recommendation: Update frontend preflight to check `!!telemetry?.gps.valid && !telemetry?.gps.stale && telemetry?.gps_connected`.

---

### 3.4 Real Flight Command Safety Rules (`ENABLE_REAL_FLIGHT_COMMANDS=false`)

- **Security Posture**: Fail-closed by default (`backend/app/config.py:22`).
- **Guarantees**:
  1. `POST /api/v1/commands/land` unconditionally rejects requests with HTTP 423 (Locked) and logs audit entry `land_blocked`.
  2. `safety_command_loop()` will never issue automated `LAND` frames to serial if `enable_real_flight_commands` is `False`.
  3. Preflight check `firmware_commands` evaluates to `False`, rendering preflight unready.
  4. Frontend displays sticky `SAFE MODE` banner (`App.tsx:217`).
- **Project Condition from PROJECT_STATUS.md**:
  Commands remain locked until ESP32 firmware source is provided, JSONL/ACK protocol is verified, and 20 propeller-removed tests succeed.

---

## 4. Acceptance Test Plan for Pytest

### 4.1 Mock Serial Architecture (`MockSerial`)

To enable fast, deterministic, cross-platform testing on both Windows and Linux without physical hardware or OS virtual serial drivers:

```python
import queue
import threading
from typing import Optional

class MockSerial:
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.is_open = True
        self._lock = threading.Lock()
        self._inbound_queue: queue.Queue[bytes] = queue.Queue()
        self.outbound_data: list[bytes] = []
        self._disconnect_on_read = False

    def feed_line(self, line: str) -> None:
        """Helper to inject incoming bytes (NMEA or JSON)."""
        self._inbound_queue.put((line.rstrip() + "\r\n").encode("ascii"))

    def readline(self) -> bytes:
        if not self.is_open:
            raise serial.SerialException("Port is closed")
        if self._disconnect_on_read:
            self.is_open = False
            raise serial.SerialException("Device disconnected")
        try:
            return self._inbound_queue.get(timeout=self.timeout)
        except queue.Empty:
            return b""

    def write(self, data: bytes) -> int:
        with self._lock:
            if not self.is_open:
                raise serial.SerialException("Port is closed")
            self.outbound_data.append(data)
            return len(data)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        with self._lock:
            self.is_open = False
```

---

### 4.2 Detailed Test Suites

#### Test Suite A: Port Auto-Detection with Simulated Streams
1. **`test_auto_detect_gps_at_38400`**:
   - Configure a mock port `"/dev/ttyUSB0"` streaming valid NMEA sentences (`$GPGGA,...*47`) at 38400 baud.
   - Run router detection.
   - Assert: Port `"/dev/ttyUSB0"` is assigned to GPS worker. `gps_worker.baud == 38400`.
2. **`test_auto_detect_esp32_at_115200`**:
   - Configure mock port `"/dev/ttyUSB1"` streaming JSON telemetry (`{"type":"telemetry","attitude":{"roll":10.0}}`) at 115200 baud.
   - Run router detection.
   - Assert: Port `"/dev/ttyUSB1"` is assigned to ESP worker. `esp_worker.baud == 115200`.
3. **`test_auto_detect_swapped_ports`**:
   - Case 1: `/dev/ttyUSB0` = GPS, `/dev/ttyUSB1` = ESP32.
     - Assert: GPS gets `ttyUSB0`, ESP gets `ttyUSB1`.
   - Case 2: `/dev/ttyUSB0` = ESP32, `/dev/ttyUSB1` = GPS (ports swapped on reboot).
     - Assert: GPS gets `ttyUSB1`, ESP gets `ttyUSB0`. No misrouting!
4. **`test_no_port_contention`**:
   - Both workers active simultaneously.
   - Assert: Neither worker ever attempts to open or lock the other's port.

#### Test Suite B: Baud Rate Verification
1. **`test_gps_baud_rate_strict_38400`**:
   - Verify `gps_worker` configures `baudrate == 38400`.
   - Send mock GPS NMEA at 38400 -> Parsed cleanly.
   - If probed at 115200 -> Data rejected or checksum fails -> Classified as non-matching.
2. **`test_esp_baud_rate_strict_115200`**:
   - Verify `esp_worker` configures `baudrate == 115200`.

#### Test Suite C: Concurrent Device Routing & Disconnection Recovery
1. **`test_gps_disconnection_and_reconnection`**:
   - GPS worker connected and receiving NMEA. `snapshot().gps_connected == True`.
   - Trigger mock disconnection (`_disconnect_on_read = True`).
   - Assert worker catches exception, marks `self.port = None`.
   - After `gps_stale_seconds`, assert `frame.gps_connected == False`, `frame.gps.stale == True`.
   - Simulate device re-plugged as `/dev/ttyUSB2` with NMEA stream.
   - Assert worker/router rediscovers port, reconnects, and `frame.gps_connected` becomes `True`.
2. **`test_esp_disconnection_and_fallback_to_simulation`**:
   - ESP worker connected and receiving attitude. Live attitude reflected in state.
   - Trigger mock disconnect.
   - Assert `frame.esp_connected` drops to `False`.
   - Assert simulated telemetry takes over smoothly without crashing.
   - Reconnect mock ESP; assert live attitude resumes.
3. **`test_worker_thread_safety_rapid_stop_start`**:
   - Repeatedly start and stop `SerialWorker` 20 times in rapid succession.
   - Concurrently trigger `write_line()`.
   - Assert: No unhandled exceptions (`AttributeError`, `TypeError`, `PortNotOpenError`), all threads join cleanly within timeout.

#### Test Suite D: Preserving Existing Backend Test Suite
- Run all existing 8 tests:
  - `backend/tests/test_api.py::test_role_boundaries_csrf_and_command_lock`
  - `backend/tests/test_core.py::test_valid_gga_sentence`
  - `backend/tests/test_core.py::test_bad_checksum_rejected`
  - `backend/tests/test_core.py::test_geofence_inside_outside_warning`
  - `backend/tests/test_core.py::test_jsonl_esp_parser_updates_attitude`
  - `backend/tests/test_core.py::test_command_retry_reuses_id_and_accepts_ack`
  - `backend/tests/test_core.py::test_command_fails_fast_without_serial`
  - `backend/tests/test_core.py::test_command_times_out_after_three_attempts`
- Assert 100% pass rate with zero regression.

---

## 5. Summary Matrix & Actionable Recommendations for Implementation

| Task / Requirement | Current Code State | Proposed Implementation Path | Risk / Complexity |
|---|---|---|---|
| **R1: GPS 38400 USB** | Hardcoded to `/dev/serial0` (UART GPIO) | Set default `GPS_DEVICE=auto` or `/dev/ttyUSB*`; auto-detect NMEA stream at 38400 baud. | Low |
| **R2: Dual USB Handling** | `candidates[0]` in `esp_device()` collides with GPS CH340 | Central `SerialRouter` with content sniffing (NMEA vs JSON) and exclusive port leasing. | Medium |
| **Thread Safety** | Unsynchronized `self.port` access; `time.sleep(2)` delays stop | Add `threading.Lock` for `write_line` & port transitions; replace `time.sleep(2)` with `stop_event.wait(2.0)`. | Low |
| **Frontend Compatibility** | Matches 100% | Preserve exact JSON keys in `TelemetryFrame` and `SystemStatus`. | Zero regression risk |
| **Safety Lock** | Fail-closed (`ENABLE_REAL_FLIGHT_COMMANDS=false`) | Retain locked default; ensure tests explicitly mock this guard. | Zero safety risk |
| **Pytest Suite** | 8 tests passing; 0 tests for `SerialWorker` | Add `test_serial_router.py` using `MockSerial` covering all auto-detect, baud, and disconnect scenarios. | Low |
