# Project: Drone Station USB Serial Migration & Concurrent Device Handling

## Architecture
- **Hardware Integration**: Raspberry Pi 5 connecting to BZ251 GPS module and ESP32 flight controller via USB-to-TTL serial adapters (CH340).
- **Core Problem**: CH340 adapters share identical USB VID:PID (`1a86:7523`) and lack unique serial numbers, making `/dev/serial/by-id/` non-unique and dynamic kernel enumeration (`/dev/ttyUSB0`, `/dev/ttyUSB1`) unstable.
- **Solution Component**: `UsbPortCoordinator` (Central Serial Router) in `backend/app/serial_io.py`.
  - Content-based stream sniffing: GPS detected via NMEA sentences starting with `$` and verified 8-bit XOR checksum at 38,400 baud. ESP32 detected via JSONL format (`{"type":...}`) or boot/ping frames at 115,200 baud.
  - Hardware Reset Protection: Port open handles enforce `dtr=False, rts=False` to prevent ESP32 auto-reset circuit assertion.
  - Mutual Exclusion: Dynamic leasing ensures workers never collide or seize each other's ports.
  - Thread Safety: Dedicated lock protecting `write_line` and responsive stop event (`stop_event.wait(timeout=2.0)`) instead of `time.sleep(2)`.
- **Dual Track Organization**:
  - **E2E Testing Track**: Autonomous test suite (`test_serial_autodetect.py`, `test_serial_worker.py`) using cross-platform duck-typed `MockSerialPort` and monkeypatched `comports()`.
  - **Implementation Track**: 
    - M1: USB Serial Migration & Auto-Detection Engine (`serial_io.py`, `config.py`)
    - M2: Concurrent Stream Dispatcher & Backend Integration (`main.py`, `models.py`)
    - M3: Codebase Improvements & Blocker Resolution (thread safety, shutdown, logging)
    - M4 (Final Milestone): 100% E2E test pass + Adversarial Hardening (Challenger stress testing)

## Feature Inventory
Every feature from the Survey phase is mapped to an assigned milestone:
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | GPS 38400 Baud USB Serial | Read GPS NMEA from USB serial at 38400 baud instead of /dev/serial0 | M1 | ORIGINAL_REQUEST R1 |
| 2 | Content-Based Port Auto-Detection | Identify GPS via valid NMEA XOR checksum at 38400 baud vs ESP32 at 115200 baud | M1 | ORIGINAL_REQUEST R2 |
| 3 | ESP32 Auto-Reset Protection | Enforce `dtr=False, rts=False` on all serial port open calls | M1 | Survey Explorer 2 |
| 4 | Thread-Safe Port Leasing | Central `UsbPortCoordinator` leasing ports exclusively to prevent worker races | M1 | Survey Explorer 1, 2 |
| 5 | Config & Fallback Handling | `GPS_DEVICE=auto`, physical path override (`/dev/serial/by-path/...`), graceful fallback | M2 | Survey Explorer 1 |
| 6 | Lifespan & Worker Lifecycle | Asynchronous coordinator startup and clean worker shutdown | M2 | Survey Explorer 2, 3 |
| 7 | SerialWorker Thread Safety | Thread lock on `write_line` and replace `time.sleep(2)` with `stop_event.wait()` | M3 | Survey Explorer 3 |
| 8 | Frontend Integration Integrity | Guarantee 100% contract compatibility for `/ws/telemetry` and REST endpoints | M3 | Survey Explorer 3 |
| 9 | Opaque-Box E2E Test Suite | Comprehensive pytest test suite (Tiers 1-4) with simulated dual USB ports | E2E-TEST | Acceptance Criteria |
| 10 | Regression & Existing Tests Pass | All 8 existing backend tests pass with zero regressions | M4 | Acceptance Criteria |
| 11 | Adversarial Stress Hardening | Challenger tests for hotplugging, race conditions, and corrupted bytes | M4 | Project Pattern Tier 5 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E-TEST | E2E Testing Suite | Requirements-driven mock serial test harness & test cases (Tiers 1-4) | none | PLANNED |
| M1 | USB Serial & Auto-Detect Engine | Central coordinator, content-based stream sniffer, DTR/RTS protection | none | PLANNED |
| M2 | Concurrent Stream Dispatcher | Wire coordinator to gps_worker and esp_worker, config updates | M1 | PLANNED |
| M3 | Codebase Improvements & Blockers | SerialWorker thread safety, responsive shutdown, documentation | M2 | PLANNED |
| M4 | Final Verification & Hardening | 100% test pass on full suite (existing + new), Tier 5 adversarial stress tests | E2E-TEST, M3 | PLANNED |

## Interface Contracts
### UsbPortCoordinator ↔ SerialWorker (gps_worker / esp_worker)
- `coordinator.get_device_for_role(role: str) -> str | None`: Thread-safe retrieval of leased device path.
- `coordinator.release_device_for_role(role: str, device: str) -> None`: Called on disconnect/SerialException to release lease.
- `coordinator.scan_and_assign() -> dict[str, str]`: Probes unleased candidate ports, assigns roles, returns mapping.
- Probing constraints:
  - GPS probe: 38,400 baud, 8N1, `timeout=1.0s`, `dtr=False, rts=False`. Validated via `pynmea2.parse(line, check=True)` on lines starting with `$`.
  - ESP32 probe: 115,200 baud, 8N1, `timeout=1.0s`, `dtr=False, rts=False`. Validated via JSON parse with `type` in `("telemetry", "ack", "pong")` or ESP bootloader message.

### Backend ↔ Frontend
- WebSocket `/ws/telemetry` (5 Hz): Emits `TelemetryFrame` JSON with fields:
  `timestamp`, `gps` (lat, lon, alt, speed, heading, satellites, fix_quality, valid, stale), `attitude` (roll, pitch, yaw), `armed`, `flight_mode`, `pid`, `gps_connected`, `esp_connected`.
- REST `/api/v1/status`: Returns JSON with `armed`, `flight_mode`, `gps_connected`, `esp_connected`, `failsafe_triggered`.
- REST `/api/v1/serial/raw`: Returns JSON with recent log lines for GPS and ESP.

## Code Layout
- `backend/app/config.py`: Central settings (`GPS_DEVICE`, `GPS_BAUD`, `ESP_DEVICE`, `ESP_BAUD`).
- `backend/app/serial_io.py`: `UsbPortCoordinator`, `SerialWorker`, `parse_nmea_line`, `update_esp_line`, `CommandDispatcher`.
- `backend/app/main.py`: FastAPI lifespan, WebSocket endpoint, REST endpoints.
- `backend/tests/test_core.py`: Existing parser and dispatcher unit tests.
- `backend/tests/test_api.py`: Existing role/CSRF/status API tests.
- `backend/tests/test_serial_autodetect.py`: New E2E and mock test suite for USB auto-detection and concurrency.
- `backend/tests/conftest.py`: Shared mock serial fixtures and duck-typed port helpers.
