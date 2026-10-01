# Handoff Report — Serial Architecture & USB Migration Survey

## 1. Observation

### 1.1 Serial Configuration Points
Inspection of `backend/app/config.py` lines 16–19, 24:
```python
16:     gps_device: str = os.getenv("GPS_DEVICE", "/dev/serial0")
17:     gps_baud: int = int(os.getenv("GPS_BAUD", "38400"))
18:     esp_device: str = os.getenv("ESP_DEVICE", "auto")
19:     esp_baud: int = int(os.getenv("ESP_BAUD", "115200"))
...
24:     gps_stale_seconds: float = float(os.getenv("GPS_STALE_SECONDS", "5"))
```
Inspection of `backend/.env.example` lines 3–6:
```dotenv
3: GPS_DEVICE=/dev/serial0
4: GPS_BAUD=38400
5: ESP_DEVICE=auto
6: ESP_BAUD=115200
```
Inspection of `deploy/iot-drone.service` lines 11–14:
```ini
11: Group=iot-drone
12: SupplementaryGroups=dialout
13: WorkingDirectory=/home/pi5/iot-drone/backend
14: EnvironmentFile=/etc/iot-drone/drone.env
```

### 1.2 Device Resolvers and Port Selection
Inspection of `backend/app/serial_io.py` lines 175–186:
```python
175: def gps_device() -> str | None:
176:     return settings.gps_device if Path(settings.gps_device).exists() else None
177: 
178: 
179: def esp_device() -> str | None:
180:     if settings.esp_device != "auto":
181:         return settings.esp_device if Path(settings.esp_device).exists() else None
182:     candidates: list[str] = []
183:     for pattern in ("/dev/serial/by-id/*", "/dev/ttyACM*", "/dev/ttyUSB*"):
184:         candidates.extend(sorted(glob.glob(pattern)))
185:     return candidates[0] if candidates else None
```

### 1.3 SerialWorker Lifecycle and Error Handling
Inspection of `backend/app/serial_io.py` lines 151–173:
```python
151:     def _run(self) -> None:
152:         while not self.stop_event.is_set():
153:             device = self.device_resolver()
154:             if not device:
155:                 time.sleep(2)
156:                 continue
157:             try:
158:                 with serial.Serial(device, self.baud, timeout=1) as port:
159:                     self.port = port
160:                     log.info("%s connected to %s", self.name, device)
161:                     while not self.stop_event.is_set():
162:                         raw = port.readline()
163:                         if raw:
164:                             self.line_handler(raw.decode("ascii", errors="replace").strip())
165:             # Closing a POSIX serial port while another thread is blocked in
166:             # readline can surface as TypeError inside pyserial (fd becomes
167:             # None). Treat it as the same expected reconnect/shutdown path.
168:             except (serial.SerialException, OSError, TypeError) as exc:
169:                 log.warning("%s serial unavailable: %s", self.name, exc)
170:             finally:
171:                 self.port = None
172:             time.sleep(2)
```

### 1.4 GPS NMEA Parsing and Ingestion
Inspection of `backend/app/serial_io.py` lines 87–120:
```python
87: def parse_nmea_line(line: str, previous: GpsFix | None = None) -> GpsFix | None:
88:     if not line.startswith("$"):
89:         return None
90:     try:
91:         message = pynmea2.parse(line, check=True)
92:     except (pynmea2.ParseError, ValueError):
93:         return None
...
97:     sentence = getattr(message, "sentence_type", "")
98:     if sentence == "GGA":
...
107:             valid=quality > 0 and bool(message.latitude) and bool(message.longitude),
108:         )
109:     elif sentence == "RMC":
...
116:             valid=status == "A" and bool(message.latitude) and bool(message.longitude),
117:         )
118:     else:
119:         return None
120:     return GpsFix.model_validate(values)
```

### 1.5 ESP32 Telemetry, Command & ACK Protocol
Inspection of `backend/app/serial_io.py` lines 47–82, 198–216:
- `update_esp_line`: Parses JSON frames.
  - `payload.get("type") == "ack"` validates `AckFrame` and sets `self.acks[command_id]`.
  - `payload.get("type") == "telemetry"` extracts `attitude` (`roll`, `pitch`, `yaw`), `armed`, `flight_mode`, and `pid` (`PidAxis`).
- `CommandDispatcher.land(reason)`:
  - Generates `CommandFrame(id=uuid4(), command="LAND", reason=reason)`.
  - Loops 1 to 3 attempts with 500 ms deadline per attempt.
  - Retains the exact same `UUID` across retries for idempotence.
  - Returns `(frame, ack, attempts)`.

### 1.6 Environment & Tool Commands
- Executed `py -0`: returned `-V:3.12 * Python 3.12 (64-bit)`.
- Executed `python -m pytest` with PYTHONPATH pointing to `.venv310/Lib/site-packages`: failed with `ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'` because `.venv310` holds C-extensions built for CPython 3.10, whereas host Windows Python is 3.12.
- Executed `pyserial`'s `serial.tools.list_ports.comports()`: returned `['COM7', 'COM6']`, confirming `pyserial`'s cross-platform port enumeration operates as expected.

---

## 2. Logic Chain

1. **Premise 1 (Current Configuration & Code)**:
   `backend/app/config.py:16` defaults `gps_device` to `/dev/serial0`. `serial_io.py:176` checks `Path(settings.gps_device).exists()`. If `/dev/serial0` is dead or disabled, `gps_device()` returns `None`.
2. **Premise 2 (ESP Auto-detection Behavior)**:
   `serial_io.py:182–185` searches `("/dev/serial/by-id/*", "/dev/ttyACM*", "/dev/ttyUSB*")` and returns `candidates[0]`.
3. **Premise 3 (USB Migration Collision Risk)**:
   When GPS is migrated from `/dev/serial0` to a CH340 USB adapter, it registers as `/dev/ttyUSB0` (or similar).
   Because `esp_device()` scans `/dev/ttyUSB*` and selects `candidates[0]`, `esp_worker` will greedily claim the GPS adapter at 115,200 baud unless disambiguation is implemented.
4. **Premise 4 (Hardware Descriptor Limitations)**:
   CH340 USB-TTL adapters typically share identical USB Vendor/Product IDs (`1a86:7523`) and omit unique serial numbers (`iSerial`). As a result:
   - `/dev/serial/by-id/` symlinks will collide or overwrite each other.
   - Kernel dynamic assignments (`/dev/ttyUSB0` vs `/dev/ttyUSB1`) vary based on plug order and boot timing.
5. **Deduction & Architectural Requirement**:
   To migrate GPS to USB serial at 38,400 baud while supporting concurrent ESP32 USB communication:
   - The device resolution system MUST enforce mutual exclusion (the two workers can never open the same port).
   - The device resolution system MUST support content-based stream discrimination (sniffing for NMEA `$` sentences at 38,400 baud vs JSON `{` frames at 115,200 baud).
   - Configuration MUST allow deterministic physical port overrides via `/dev/serial/by-path/...`.

---

## 3. Caveats

1. **Hardware In-Loop**: We did not perform physical hardware tests on the Raspberry Pi 5 because this investigation is conducted from the workspace environment. Physical validation of CH340 enumeration and BZ251 NMEA output requires testing on the Pi 5 target.
2. **Logic Voltage Safety**: BZ251 GPS modules operate with 3.3V CMOS UART logic. Connecting a 5V TTL adapter directly can damage the BZ251 receiver. Verification of the CH340 adapter's 3.3V jumper setting is assumed for hardware deployment.
3. **Read-Only Scope**: In accordance with the Explorer role, no modifications were made to `backend/app/` source files or deploy scripts during this survey.

---

## 4. Conclusion

The existing serial subsystem is well-modularized inside `backend/app/serial_io.py`, but its device discovery logic is fragile when both GPS and ESP32 reside on USB.
- **GPS Configuration**: Needs `GPS_DEVICE` in `config.py` to support `auto` and resolve USB ports at 38,400 baud.
- **Mutual Exclusion**: A coordinated resolver must be introduced in `serial_io.py` so that `gps_worker` and `esp_worker` never compete for or cross-bind to the same device node.
- **Stream Auto-Detection**: A content sniffer distinguishes GPS (ASCII NMEA starting with `$GP`/`$GN`) at 38,400 baud from ESP32 (JSONL/text) at 115,200 baud.
- **Testing**: A dedicated test module (`backend/tests/test_serial.py`) with mock ports must be added to verify concurrent USB assignment and error recovery.

---

## 5. Verification Method

### 5.1 Independent Code Verification
Inspect the following files to verify the claims made in this report:
- `backend/app/config.py`: lines 16–19 (baud rate defaults and device paths).
- `backend/app/serial_io.py`: lines 87–120 (NMEA parser), lines 151–173 (worker loop), lines 175–186 (resolvers).
- `backend/app/models.py`: lines 53–83 (`TelemetryFrame`, `CommandFrame`, `AckFrame`).
- `backend/tests/test_core.py`: lines 12–23 (NMEA parser tests), lines 60–80 (ACK dispatcher tests).

### 5.2 Test Commands (Target & Local)
1. **Target Environment (Raspberry Pi 5 / Debian 13)**:
   ```bash
   cd /home/pi5/iot-drone/backend
   /opt/iot-drone/venv/bin/pytest
   ```
   All existing tests must pass (`8 passed`).
2. **USB Serial Scan Script Verification**:
   ```bash
   python3 scripts/test_gps_uart.py --device /dev/ttyUSB0 --seconds 3
   ```
3. **Automated Unit Tests for New USB Resolver**:
   Run the pytest suite to verify that synthetic ports with NMEA and JSON data are correctly matched to GPS and ESP workers respectively without conflict.

### 5.3 Invalidation Conditions
This survey report would be invalidated if:
1. The BZ251 module does not output NMEA 0183 sentences at 38,400 baud.
2. The ESP32 and GPS use dedicated, immutable hardware ports where concurrent USB collision cannot occur.
3. Systemd or Linux permissions prevent user `iot-drone` from accessing `/dev/ttyUSB*` despite membership in the `dialout` group.
