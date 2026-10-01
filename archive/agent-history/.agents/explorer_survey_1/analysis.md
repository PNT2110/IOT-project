# Comprehensive Serial Architecture Survey & USB Serial Migration Analysis

## Executive Summary
This document provides a technical survey of the serial communication architecture for the Drone Station project running on Raspberry Pi 5. It details the existing GPS reader service, ESP32 handler, baud rates, serial workers, and error/reconnection routines. It identifies all concrete code points and architecture changes required to migrate the GPS receiver (BZ251) from the hardware UART (`/dev/serial0`) to a USB serial adapter (CH340) operating at 38,400 baud while preparing for concurrent ESP32 USB serial communication.

---

## 1. Serial Connection Architecture & Lifecycle

### 1.1 Configuration Sources
Serial connection settings are defined centrally in `backend/app/config.py` via an immutable `Settings` dataclass:
- **`backend/app/config.py` (lines 16–19, 24)**:
  ```python
  gps_device: str = os.getenv("GPS_DEVICE", "/dev/serial0")
  gps_baud: int = int(os.getenv("GPS_BAUD", "38400"))
  esp_device: str = os.getenv("ESP_DEVICE", "auto")
  esp_baud: int = int(os.getenv("ESP_BAUD", "115200"))
  gps_stale_seconds: float = float(os.getenv("GPS_STALE_SECONDS", "5"))
  ```
- **`backend/.env.example` (lines 3–6, 11)**:
  ```dotenv
  GPS_DEVICE=/dev/serial0
  GPS_BAUD=38400
  ESP_DEVICE=auto
  ESP_BAUD=115200
  GPS_STALE_SECONDS=5
  ```
- **`deploy/iot-drone.service` (line 14)**:
  `EnvironmentFile=/etc/iot-drone/drone.env`
  During deployment (`deploy/install_pi.sh` lines 37–39), `/etc/iot-drone/drone.env` is initialized from `backend/.env.example`.

### 1.2 Threading Model & Worker Lifecycle
Serial communications are managed by background threads encapsulated in the `SerialWorker` class in `backend/app/serial_io.py` (lines 123–173):
- **Class Structure**:
  - `SerialWorker(name: str, device_resolver: Callable[[], str | None], baud: int, line_handler: Callable[[str], None])`
  - Instantiated as two module-level singletons:
    - `gps_worker = SerialWorker("gps", gps_device, settings.gps_baud, _handle_gps)` (`serial_io.py:194`)
    - `esp_worker = SerialWorker("esp", esp_device, settings.esp_baud, state.update_esp_line)` (`serial_io.py:195`)
- **FastAPI Lifespan Hook (`backend/app/main.py:95–116`)**:
  - `gps_worker.start()` and `esp_worker.start()` are triggered during application startup inside `@asynccontextmanager async def lifespan(app: FastAPI)` (lines 100–101).
  - Background daemon threads `serial-gps` and `serial-esp` run continuously until application shutdown.
  - On application teardown, `gps_worker.stop()` and `esp_worker.stop()` set `stop_event`, close the underlying `serial.Serial` port, and join the threads with a 2-second timeout (lines 113–114, 137–143).

### 1.3 Telemetry State Management
`TelemetryState` (`backend/app/serial_io.py:24–83`) coordinates concurrent access across worker threads and asyncio coroutines:
- Protected by an internal `threading.Lock` (`self._lock`).
- Maintains `self.frame = TelemetryFrame()`, `self.raw_esp = deque(maxlen=200)`, `self.acks = dict[str, AckFrame]`, `last_gps_monotonic = 0.0`, and `last_esp_monotonic = 0.0`.
- Method `snapshot()` generates a deep copy of `TelemetryFrame` with freshness calculations:
  - `gps_connected = now - self.last_gps_monotonic < settings.gps_stale_seconds`
  - `esp_connected = now - self.last_esp_monotonic < settings.gps_stale_seconds`
  - `gps.stale = not frame.gps_connected`
- Dispatched to frontend clients over WebSocket `/ws/telemetry` at 5 Hz (200 ms interval) via `backend/app/main.py:290–303`.

---

## 2. GPS Data Ingestion, Parsing, and Error Handling

### 2.1 Port & Baud Rate Configuration
- **Current Device**: `/dev/serial0` (configured in `config.py:16` and `.env.example:3`).
  On the Raspberry Pi 5, `/dev/serial0` points to `/dev/ttyAMA10` on physical GPIO 14/15 (pin 8 TX, pin 10 RX).
- **Resolver**: `gps_device()` in `serial_io.py:175–176`:
  ```python
  def gps_device() -> str | None:
      return settings.gps_device if Path(settings.gps_device).exists() else None
  ```
  Note: This resolver only checks `Path(settings.gps_device).exists()`. It does not perform discovery or probe alternative paths if `/dev/serial0` is dead or absent.
- **Configured Baud Rate**: `38400` baud (`settings.gps_baud`), with 8 data bits, no parity, 1 stop bit (8N1), timeout = 1.0 s.

### 2.2 Parser Implementation
NMEA parsing is implemented in `parse_nmea_line` (`backend/app/serial_io.py:87–120`):
- Uses `pynmea2` (`pynmea2.parse(line, check=True)`).
- **Filter**: Rejects any line not starting with `$` (`line.startswith("$")`).
- **Checksum Validation**: Enforced via `check=True`. Any checksum mismatch or parsing exception (`pynmea2.ParseError`, `ValueError`) causes immediate rejection (`return None`).
- **Supported Sentences**:
  1. **`GGA` (Global Positioning System Fix Data)**:
     - Extracts `latitude`, `longitude`, `altitude_m`, `satellites` (`num_sats`), `hdop` (`horizontal_dil`), and `fix_quality` (`gps_qual`).
     - Validation condition: `valid = quality > 0 and bool(message.latitude) and bool(message.longitude)`.
  2. **`RMC` (Recommended Minimum Specific GPS/Transit Data)**:
     - Extracts `speed_mps` (`spd_over_grnd * 0.514444` converting knots to m/s), `course_deg` (`true_course`), and status (`status == "A"` for active fix).
     - Preserves previous latitude/longitude if omitted.
     - Validation condition: `valid = status == "A" and bool(message.latitude) and bool(message.longitude)`.
  3. **Other Sentences** (`GSA`, `GSV`, `VTG`, etc.): Currently discarded.
- **Model Output**: Returns an updated `GpsFix` instance with `timestamp = datetime.now(timezone.utc)`, `raw = line`, and `stale = False`.

### 2.3 Error and Reconnect Handling
- **Worker Read Loop (`serial_io.py:151–173`)**:
  - Catches `(serial.SerialException, OSError, TypeError)`.
  - The `TypeError` exception specifically handles a known PySerial quirk where closing a POSIX file descriptor while another thread is blocked in `readline()` results in internal `fd` becoming `None`.
  - On disconnection or port failure:
    - Logs warning: `"%s serial unavailable: %s"`.
    - Resets `self.port = None` in `finally`.
    - Sleeps for 2.0 seconds (`time.sleep(2)`).
    - Retries `self.device_resolver()` on the next loop iteration.
- **Staleness & Safety Interlock**:
  - If no valid GPS sentence is received within `settings.gps_stale_seconds` (5.0 seconds), `TelemetryState.snapshot()` marks `gps_connected=False` and `frame.gps.stale=True`.
  - In `backend/app/main.py:66–93` (`safety_command_loop`): If the drone is armed (`frame.armed == True`) and real commands are enabled, losing GPS fix for >= 5.0 seconds automatically triggers `command_dispatcher.land("GPS_LOST")`.

---

## 3. ESP32 Serial Communication Architecture & Protocol

### 3.1 Device Resolution & Current Discovery
- **Resolver**: `esp_device()` in `backend/app/serial_io.py:179–185`:
  ```python
  def esp_device() -> str | None:
      if settings.esp_device != "auto":
          return settings.esp_device if Path(settings.esp_device).exists() else None
      candidates: list[str] = []
      for pattern in ("/dev/serial/by-id/*", "/dev/ttyACM*", "/dev/ttyUSB*"):
          candidates.extend(sorted(glob.glob(pattern)))
      return candidates[0] if candidates else None
  ```
- **Baud Rate**: 115,200 baud (`settings.esp_baud`).
- **Vulnerability / Limitation**:
  - `esp_device()` blindly glob-matches `/dev/serial/by-id/*`, `/dev/ttyACM*`, and `/dev/ttyUSB*`, taking `candidates[0]`.
  - When GPS is migrated to a USB-to-TTL adapter, it appears as `/dev/ttyUSB0` or `/dev/serial/by-id/...`.
  - If `esp_device()` is set to `"auto"`, it will greedily claim the first USB device (`candidates[0]`), which could be the GPS adapter! This leads to port collisions or cross-wiring workers to the wrong devices.

### 3.2 Communication Protocol
ESP32 communication uses a line-delimited JSON (JSONL) protocol:
1. **Telemetry Stream (ESP -> Pi)**:
   - Example line: `{"type":"telemetry","attitude":{"roll":1.2,"pitch":-0.5,"yaw":45.0},"armed":true,"flight_mode":"STABILIZE","pid":{"roll":{"kp":1.2,"output":0.5}}}`
   - Parsed in `state.update_esp_line(line)` (`serial_io.py:47–78`).
   - Appends raw line to `self.raw_esp` ring buffer (viewable on dashboard terminal panel `/api/v1/serial/raw`).
   - Updates `frame.attitude`, `frame.armed`, `frame.flight_mode`, and `frame.pid` (roll, pitch, yaw).
2. **Command & ACK Stream (Bi-directional)**:
   - Pi -> ESP: `CommandFrame` (`models.py:67–74`):
     ```json
     {"version":1,"type":"command","id":"<UUID4>","command":"LAND","reason":"GEOFENCE_BREACH","timestamp":"..."}
     ```
   - ESP -> Pi: `AckFrame` (`models.py:76–83`):
     ```json
     {"version":1,"type":"ack","command_id":"<UUID4>","accepted":true,"message":null,"timestamp":"..."}
     ```
   - `CommandDispatcher.land(reason)` (`serial_io.py:198–216`):
     - Transmits up to 3 times with a 500 ms deadline per attempt.
     - Crucially maintains idempotency: preserves the identical `UUID` across retries.
     - Awaits ACK matching `command_id` stored in `state.acks`.
3. **Simulator Fallback**:
   - `simulated_telemetry()` in `serial_io.py:221–241` runs an asyncio background loop.
   - If `state.snapshot().esp_connected` is False, it synthesizes smooth sinusoidal roll, pitch, yaw attitude and PID curves with `flight_mode="SIMULATOR"`, keeping the 3D dashboard functional during offline development.
4. **Safety Interlock**:
   - `settings.enable_real_flight_commands` defaults to `False`.
   - Real `LAND` commands via `/api/v1/commands/land` are rejected with HTTP 423 until prop-off test milestones are met.

---

## 4. Requirements & Concrete Code Points for GPS USB Migration

### 4.1 The Core Architectural Challenge: Port Disambiguation
When migrating GPS from `/dev/serial0` (GPIO UART) to USB serial:
- Both the GPS (BZ251 via CH340) and the ESP32 (via onboard USB or external USB-TTL) will be USB serial devices on the Raspberry Pi 5.
- On Linux, both adapters typically register under `/dev/ttyUSB0` and `/dev/ttyUSB1` (or `/dev/ttyACM0` for native ESP32 USB).
- If both devices use CH340 chips:
  - Both share the same USB VID:PID (`1a86:7523`).
  - Standard CH340 chips lack unique serial numbers (`iSerial` descriptor is blank or identical).
  - Consequently, `/dev/serial/by-id/` either produces a single symlink (overwriting each other) or index suffixes (`...-port0`).
  - The numbering `/dev/ttyUSB0` vs `/dev/ttyUSB1` is non-deterministic across reboots, depends on plug order, and changes if USB hubs enumerate differently.

### 4.2 Required Code Modifications
| File Path | Lines | Current Code / Behavior | Required Changes |
|-----------|-------|-------------------------|------------------|
| `backend/app/config.py` | 16–19 | `gps_device: str = os.getenv("GPS_DEVICE", "/dev/serial0")`<br>`gps_baud: int = int(os.getenv("GPS_BAUD", "38400"))`<br>`esp_device: str = os.getenv("ESP_DEVICE", "auto")` | Support `gps_device: str = os.getenv("GPS_DEVICE", "auto")` or explicit device path.<br>Keep `gps_baud` default `38400`.<br>Add auto-detection and exclusive port allocation logic. |
| `backend/.env.example` | 3–6 | `GPS_DEVICE=/dev/serial0`<br>`GPS_BAUD=38400`<br>`ESP_DEVICE=auto`<br>`ESP_BAUD=115200` | Update default `GPS_DEVICE=auto` (or documented USB path `/dev/serial/by-path/...` or `/dev/ttyUSB0`). Clarify dual USB setup in comments. |
| `backend/app/serial_io.py` | 175–186 | `gps_device()` checks only `Path(settings.gps_device).exists()`.<br>`esp_device()` grabs `candidates[0]` from glob search. | Implement coordinated port resolution:<br>1. **Exclusive reservation**: GPS and ESP must never open the same port.<br>2. **Auto-detection**: If `auto`, scan available ports (`/dev/ttyUSB*`, `/dev/ttyACM*`, Windows `COM*`). Probe or distinguish GPS (NMEA stream `$GP...`/`$GN...` at 38400) vs ESP (JSONL/text at 115200).<br>3. **Explicit override support**: Allow `GPS_DEVICE` and `ESP_DEVICE` to specify `/dev/serial/by-path/...` for 100% deterministic physical port binding. |
| `scripts/test_gps_uart.py` | 13–17 | Defaults to `--device /dev/serial0` and scans multiple bauds. | Create or update test script (e.g. `scripts/test_gps_usb.py` or enhanced `test_gps_uart.py`) supporting `--device /dev/ttyUSB0` or auto-scanning USB ports with default baud 38400. |
| `deploy/iot-drone.service` | 11–12 | `SupplementaryGroups=dialout` | Retain `dialout` group. On Debian/Raspberry Pi OS, `/dev/ttyUSB*` devices are owned by `root:dialout` (mode 0660). |
| `backend/tests/test_core.py` | N/A | Existing tests cover NMEA parsing and ACK frames, but lack automated tests for USB port resolver and concurrent port disambiguation. | Add automated pytest tests verifying port discovery, conflict avoidance (exclusive assignment), and content-based stream discrimination. |

### 4.3 Recommended Disambiguation Strategies
Three complementary techniques should be adopted:
1. **Physical Port Binding via `/dev/serial/by-path/`**:
   - Linux creates symlinks in `/dev/serial/by-path/` matching the physical USB port hierarchy (e.g. `platform-xhci-hcd.0-usb-0:1.1:1.0-port0`).
   - If user plugs GPS into USB port 1 (top blue) and ESP into USB port 2 (bottom blue), paths remain completely stable across reboots regardless of device insertion order.
2. **Content-Based Auto-Detection (Sniffing)**:
   - When configured as `"auto"`, the port resolver or an initialization probe briefly opens candidate ports:
     - Probe at 38,400 baud: If bytes matching NMEA sentences (`$GP`, `$GN`, `$BD`) arrive within 1.0–2.0 s, the port is assigned to `gps_worker`.
     - Probe at 115,200 baud: If valid JSON (`{"type":...}`) or ESP log strings arrive, the port is assigned to `esp_worker`.
3. **Mutual Exclusion Lock**:
   - The device resolver must enforce that `gps_device()` and `esp_device()` cannot resolve to the same device path. If GPS is assigned to `/dev/ttyUSB0`, ESP auto-detection must exclude `/dev/ttyUSB0` from its candidate pool.

---

## 5. Hardware Constraints, Environment Nuances & Verification

### 5.1 WCH CH340 USB-to-TTL Adapter Nuances
- **Chip Characteristics**:
  - USB VID: `0x1a86` (QinHeng Electronics), PID: `0x7523` (CH340 serial converter).
  - Linux Kernel Module: `ch341.ko` (built into Raspberry Pi OS / Debian 13).
- **Serial Number Absence**:
  - Low-cost CH340 dongles lack a unique serial number in their USB descriptor.
  - `/dev/serial/by-id/` will typically produce `usb-1a86_USB_Serial-if00-port0`. If two dongles are connected, one will overwrite the symlink or udev will append non-deterministic indices.
- **Baud Rate Accuracy**:
  - CH340 supports standard bauds: 9600, 19200, 38400, 57600, 115200, 230400, 460800.
  - At 38,400 baud, CH340 crystal frequency (typically 12 MHz) achieves exact integer division (divisor = 312.5 or fractional generator), giving < 0.16% baud rate error, which is well within UART tolerances (< 2.5%).
- **Logic Voltage**:
  - CH340 adapters usually offer a 3.3V / 5V jumper.
  - The BZ251 module uses 3.3V CMOS UART logic. Setting the CH340 VCC jumper to 3.3V or ensuring RX/TX is 3.3V tolerant is essential to prevent module damage.

### 5.2 Raspberry Pi 5 Hardware Architecture
- **Peripherals & USB Controller**:
  - The Pi 5 routes all USB 2.0 and USB 3.0 ports through the custom Raspberry Pi RP1 southbridge chip.
  - Port allocation:
    - 2x USB 3.0 Type-A ports (blue)
    - 2x USB 2.0 Type-A ports (black)
  - Unlike GPIO UART (`/dev/ttyAMA10` on physical pins 8 and 10), USB serial communication is isolated from Pi GPIO pinmux settings and not subject to conflicts with Bluetooth (`/dev/ttyAMA0`).
- **Device Node Naming**:
  - USB serial converters dynamically allocate nodes: `/dev/ttyUSB0`, `/dev/ttyUSB1` ...
  - Native USB microcontroller devices (e.g. ESP32-S3 USB CDC) register as `/dev/ttyACM0`, `/dev/ttyACM1` ...

### 5.3 Cross-Platform & Mock Testing Considerations
- **Development Environment (Windows)**:
  - Windows names serial ports `COM1`, `COM2`, `COM6`, `COM7`, etc.
  - Linux paths like `/dev/serial0` and `/dev/ttyUSB0` do not exist on Windows.
  - `glob.glob('/dev/tty*')` returns an empty list on Windows.
  - Using `serial.tools.list_ports.comports()` provides cross-platform enumeration, returning `COMx` on Windows and `/dev/ttyUSBx` on Linux.
- **Automated Mock Testing with Pytest**:
  - Unit tests in CI/development must not depend on physical USB ports or OS-specific hardware nodes.
  - Mocking strategies:
    1. Mock `serial.tools.list_ports.comports()` returning synthetic port descriptors with custom VID/PID, port paths, and descriptions.
    2. Mock `serial.Serial` using an in-memory buffer or `unittest.mock.MagicMock` returning pre-recorded NMEA sentences (`$GNGGA...`, `$GNRMC...`) and JSON telemetry lines.
    3. Test port assignment conflicts, ensuring when two USB ports are present, GPS binds to the 38,400 baud NMEA port and ESP binds to the 115,200 baud JSON port.

---

## 6. Synthesis and Roadmap

1. **Phase 1 (Configuration & Port Disambiguation)**:
   - Enhance `config.py` to allow `GPS_DEVICE=auto`.
   - Update `serial_io.py` resolvers to use mutual exclusion and stream/content detection.
2. **Phase 2 (Unit & Mock Testing)**:
   - Add automated pytest test cases in `backend/tests/test_serial.py` verifying USB discovery, mutual exclusion, and concurrent GPS + ESP stream assignment.
3. **Phase 3 (Hardware Verification on Pi 5)**:
   - Deploy to `/home/pi5/iot-drone`.
   - Connect BZ251 via CH340 at 38,400 baud.
   - Verify live NMEA parsing and telemetry update on dashboard.
