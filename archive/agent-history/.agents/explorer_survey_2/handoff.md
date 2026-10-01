# Handoff Report: Survey 2 — Concurrent USB Device Handling & Auto-Detection (R2)

**Agent:** Survey Explorer 2 (USB Auto-Detect Explorer)  
**Parent Conversation ID:** `94568146-c35e-44d3-9a12-47c93b67809f`  
**Handoff Type:** Hard (Survey Task Complete)  
**Primary Artifact:** `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_2\analysis.md`

---

## 1. Observation

1. **Static Configuration in `backend/app/config.py:16-19`**:
   ```python
   gps_device: str = os.getenv("GPS_DEVICE", "/dev/serial0")
   gps_baud: int = int(os.getenv("GPS_BAUD", "38400"))
   esp_device: str = os.getenv("ESP_DEVICE", "auto")
   esp_baud: int = int(os.getenv("ESP_BAUD", "115200"))
   ```
   The default GPS device is hardcoded to `/dev/serial0` (hardware GPIO UART), which is documented in `PROJECT_STATUS.md:54` as receiving 0 bytes at all baud rates.

2. **Greedy First-Match Port Resolution in `backend/app/serial_io.py:179-185`**:
   ```python
   def esp_device() -> str | None:
       if settings.esp_device != "auto":
           return settings.esp_device if Path(settings.esp_device).exists() else None
       candidates: list[str] = []
       for pattern in ("/dev/serial/by-id/*", "/dev/ttyACM*", "/dev/ttyUSB*"):
           candidates.extend(sorted(glob.glob(pattern)))
       return candidates[0] if candidates else None
   ```
   `esp_device()` globs `/dev/ttyUSB*` and blindly returns `candidates[0]`. When GPS is plugged into USB, `esp_device()` steals the GPS port (e.g. `/dev/ttyUSB0`), attempts to parse NMEA bytes as JSON, fails, and locks the port away from the GPS worker.

3. **Serial Worker Architecture in `backend/app/serial_io.py:123-173`**:
   - `SerialWorker` runs in a daemon thread (`serial-{name}`) and executes a loop resolving `device = self.device_resolver()`.
   - On connection failure, it catches `(serial.SerialException, OSError, TypeError)`.
   - `SerialWorker` currently does not coordinate with other workers to prevent dual access to the same port.

4. **NMEA Checksum Parsing in `backend/app/serial_io.py:87-93`**:
   ```python
   def parse_nmea_line(line: str, previous: GpsFix | None = None) -> GpsFix | None:
       if not line.startswith("$"):
           return None
       try:
           message = pynmea2.parse(line, check=True)
       except (pynmea2.ParseError, ValueError):
           return None
   ```
   `pynmea2.parse(..., check=True)` validates the 8-bit XOR checksum against the trailing `*XX` hex code.

5. **Hardware USB Descriptor Ambiguity in Linux**:
   - WCH CH340G / CH340C chips (VID `0x1A86`, PID `0x7523`) lack a unique USB serial number descriptor (`iSerialNumber` is 0 or dummy `"0001"`).
   - `/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0` collides when two CH340 adapters are connected simultaneously.
   - Linux `/dev/ttyUSB0` and `/dev/ttyUSB1` enumeration order is non-deterministic across boots and hotplugs.

6. **ESP32 Auto-Reset Circuit Hazard**:
   ESP32 development boards connect USB bridge `DTR` and `RTS` pins to `EN` (reset) and `GPIO0` (boot mode). Standard serial port openings without explicit `dtr=False, rts=False` toggle `EN` low, causing an immediate hardware reset of the ESP32.

7. **Test Environment Differences**:
   The development workspace is on Windows 11 (`.venv310` uv trampoline pointed to missing CPython 3.10; system Python is 3.12.5), while the deployment target is Debian 13 arm64 (Python 3.13.5). POSIX `pty` does not exist on Windows, necessitating duck-typed `MockSerial`.

---

## 2. Logic Chain

1. **From Obs 1 & 2**: When GPS (BZ251 on CH340) is connected via USB, Linux assigns it a node such as `/dev/ttyUSB0`. If ESP32 is connected simultaneously, Linux assigns `/dev/ttyUSB1`. `esp_device()` immediately selects `/dev/ttyUSB0` (GPS) because it takes `candidates[0]`. Consequently, the ESP worker occupies the GPS port at 115,200 baud, while the GPS worker is stuck polling `/dev/serial0`.
2. **From Obs 5**: Hardware identifiers (VID/PID `0x1A86:0x7523`, `/dev/serial/by-id/`) cannot distinguish the two devices because both use CH340 without unique serial numbers. Physical paths (`/dev/serial/by-path/`) are vulnerable to user cable swapping. Therefore, identification **must be content-based**.
3. **From Obs 4**: GPS BZ251 streams unsolicited NMEA sentences at 38,400 baud. Verifying that an incoming line starts with `$` and has a mathematically valid XOR checksum (`*XX`) confirms a GPS device with zero false positives.
4. **From Obs 2 & Obs 6**: Opening candidate ports with standard default settings risks asserting `DTR`/`RTS`, triggering the ESP32 auto-reset circuit. To probe safely without rebooting a running flight controller, all probe handles must open with `dtr=False, rts=False`.
5. **From Obs 3**: If `gps_worker` and `esp_worker` independently probe ports, they will race, causing `serial.SerialException` (port busy). Therefore, a centralized `UsbPortCoordinator` must manage candidate discovery, probing, and role assignment.
6. **From Obs 7**: Tests must execute identically on Windows and Linux without physical hardware. POSIX `pty` is non-portable. A duck-typed `MockSerialPort` monkeypatched into `serial.Serial` and `serial.tools.list_ports.comports` provides 100% portable, sub-second unit test verification.

---

## 3. Caveats

- **UBX Binary Stream**: If the BZ251 is explicitly configured in u-center to emit *pure UBX binary* (suppressing NMEA), the ASCII NMEA check would not match. However, factory default BZ251 modules emit NMEA (or mixed NMEA+UBX), which is fully supported.
- **Silent ESP32 Firmware**: If future ESP32 firmware is purely reactive (never sends telemetry or boot logs until queried), passive probing at 115,200 baud would time out. The architecture addresses this by adding an active fallback ping (`{"type":"ping"}\n`) at Stage 2b.
- **Physical Baud Rate**: Assumes GPS operates at 38,400 baud (per user requirement R1) and ESP32 operates at 115,200 baud. If a user customizes baud rates, they can be configured via `GPS_BAUD` and `ESP_BAUD` environment variables.

---

## 4. Conclusion

A **Content-Based Auto-Detection Architecture** centered on a thread-safe `UsbPortCoordinator` is the optimal, robust solution for Requirement R2:
1. **Probe Sequence**: Probes unassigned ports at 38,400 baud for up to 1.0s (NMEA checksum validation); if not matched, probes at 115,200 baud for up to 1.0s (JSONL / ESP boot validation).
2. **Hardware Protection**: Enforces `dtr=False, rts=False` on all port open operations to eliminate the ESP32 auto-reset hazard.
3. **Concurrency Control**: A single coordinator owns port assignment, completely preventing worker collisions and greedy port-stealing.
4. **Lifecycle & Hotplug**: Seamlessly releases disconnected ports on `SerialException` and rebinds devices upon reinsertion without server restart.
5. **Cross-Platform Pytest Suite**: Implements `MockSerialPort` and monkeypatched `list_ports.comports()` to verify port disambiguation, inverted enumeration, checksum rejection, and hotplug recovery across both Windows and Linux.

---

## 5. Verification Method

### 5.1 Verification Commands
Once implemented, the auto-detect and simulation architecture can be verified with:
```bash
# Run the automated USB auto-detect test suite
pytest backend/tests/test_serial_autodetect.py -v

# Run the complete backend test suite to ensure zero regressions
pytest backend/tests -v
```

### 5.2 Artifacts to Inspect
- `c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents\explorer_survey_2\analysis.md` (detailed architectural survey and specifications).
- `backend/app/serial_io.py` (review proposed `UsbPortCoordinator` integration).
- `backend/app/config.py` (review `gps_device="auto"` migration).

### 5.3 Invalidation Conditions
This architecture is invalidated if:
1. A GPS module is flashed with pure proprietary binary that never emits NMEA 0183 sentences.
2. ESP32 firmware operates at 38,400 baud and intentionally outputs NMEA `$GNGGA` formatted lines with valid checksums (a deliberate spoofing case).
