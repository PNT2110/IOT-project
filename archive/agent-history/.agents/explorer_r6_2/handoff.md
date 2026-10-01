# HANDOFF REPORT — Requirements R2 & R3 Investigation
**Author**: Explorer R6-2  
**Date**: 2026-09-14T05:14:00Z  
**Working Directory**: `/home/pnt/IOT/.agents/explorer_r6_2`  
**Scope**: 
1. Serial USB Connection (R2): Dynamic port discovery (`/dev/ttyUSB*`, `/dev/ttyACM*`), auto-reconnection, JSONL resilience, test mocks.
2. Static Manufacturer Firmware Flashing (R3): Removal of custom `.bin` upload from UI & API, enforcement of pre-stored `official.bin`, and fail-safe ARM locking if `official.bin` is missing.

---

## 1. Observation

### 1.1 Serial USB Architecture (R2)
- **Port Discovery Implementation**:
  - Location: `backend/app/serial_io.py:334-363` (`UsbPortCoordinator.find_candidate_ports()`).
  - Candidate discovery enumerates via two methods:
    1. `serial.tools.list_ports.comports()` (cross-platform, scans `/sys/class/tty/` on Linux).
    2. Globbing patterns: `("/dev/ttyUSB*", "/dev/ttyACM*", "/dev/serial/by-path/*", "/dev/serial/by-id/*")`.
  - Symlink normalization is applied via `p_dev.resolve()` at lines 342-345 and 355-358 to avoid duplicate leases of the same physical device.
- **Port Classification & Probing**:
  - Location: `backend/app/serial_io.py:406-483` (`_probe_esp()`) and lines 365-404 (`_probe_gps()`).
  - GPS Probe: Opens port at 38400 baud. Verifies NMEA sentences (`GGA`, `RMC`, `GSA`, `GSV`, `VTG`, `GLL`, `ZDA`) and validates XOR checksums (`is_valid_nmea_checksum` at line 290). Fast-exits if line starts with `{`, `"telemetry"`, or `"rst:"`.
  - ESP32 Probe: Opens port at 115200 baud with DTR/RTS suppression (`dtr=False, rts=False` at lines 248-288). Checks for:
    - JSON telemetry/ack frames: `payload.get("type") in ("telemetry", "ack", "pong")` or keys `("attitude", "pid", "armed", "command")`.
    - ESP-IDF bootloader signatures: `("rst:", "boot:", "configsip:", "SPIWP:", "[I][", "[E][", "[W][", "ESP-IDF", "ESP32", "Drone ESP32")`.
    - Active ping fallback: Transmits `{"type":"ping"}\n` and awaits `pong`/`ack`. In `FC_can_bang/display.ino:103-111`, ESP32 firmware natively replies:
      ```cpp
      StaticJsonDocument<256> pong;
      pong["type"] = "pong";
      pong["firmware"] = "FC_can_bang_v2";
      pong["drone_id"] = drone_mac_id;
      ```
- **Auto-Reconnection & Disconnect Handling**:
  - Location: `backend/app/serial_io.py:633-673` (`SerialWorker._run()`).
  - The worker loop queries `self.device_resolver()` (`esp_device()` -> `coordinator.get_device_for_role("esp")`).
  - When a device is unplugged, `port.readline()` raises `serial.SerialException` or `OSError`.
  - The `finally` block (lines 663-671) executes:
    ```python
    if self.port:
        self.port.close()
    self.port = None
    if coordinator and current_device:
        coordinator.release_device_for_role(self.name, current_device)
    ```
  - This discards the active lease from `coordinator.active_ports` and clears `coordinator.assigned[role]`.
  - The worker waits 2.0s via `self.stop_event.wait(timeout=2.0)`.
  - In the next iteration, `coordinator.get_device_for_role()` triggers `scan_and_assign()`, scanning all candidate ports (`/dev/ttyUSB*`, `/dev/ttyACM*`). As soon as ESP32 is re-inserted (even under a new port name such as `/dev/ttyACM1`), it is re-acquired and communication resumes automatically.
- **JSONL Parsing Resilience**:
  - Location: `backend/app/serial_io.py:144-202` (`TelemetryState.update_esp_line()`).
  - Safe decoding: `raw.decode("utf-8", errors="replace").strip()` prevents UTF-8 decode crashes.
  - JSON parse error protection: `try...except (json.JSONDecodeError, TypeError, ValueError): return`.
  - Type checking: `if not isinstance(payload, dict): return`.
  - Arithmetic protection: `_safe_float()` (lines 72-79) filters `NaN`, `Inf`, and type errors.
  - Altitude validity: `math.isfinite(altitude)`.
  - Try-except wrapping around PID sub-dictionary validations (line 198).
- **Existing Serial Test Suite Verification**:
  - Command: `PYTHONPATH=backend /home/pnt/miniconda3/envs/antidrone/bin/python -m pytest -v backend/tests/test_serial_autodetect.py`
  - Result: `19 passed in 6.36s`. Covers baud isolation, XOR checksum validation, noise prefix rejection, DTR/RTS flag suppression, dynamic unplug, and dual-port concurrency.
  - Command: `/home/pnt/miniconda3/envs/antidrone/bin/python -m unittest tests/test_scenario_03_serial_jsonl.py`
  - Result: `Ran 1 test in 0.051s. OK`. Verifies resilience against corrupted lines (`CORRUPTED_NON_JSON_DATA_LINE\n`).

---

### 1.2 Static Manufacturer Firmware Flashing (R3)
- **Current Custom File Upload Locations**:
  - **Frontend UI**: `frontend/src/FirmwareTab.tsx`
    - Lines 60-70: `handleFileChange` listens on `<input type="file" accept=".bin" id="fw-file-input">`.
    - Lines 72-89: `handleDrop` accepts dragged `.bin` files.
    - Lines 91-96: `handleFlash` blocks execution if `!selectedFile`:
      ```typescript
      if (!selectedFile) {
        setToast({ type: 'error', message: 'Vui lòng chọn file firmware (.bin) trước khi nạp' })
        return
      }
      ```
    - Lines 309-382: Entire upload dropzone UI rendered (`<div className="firmware-upload-section">`), prompting users to upload custom files.
  - **Frontend API Client**: `frontend/src/api.ts`
    - Lines 150-159: `uploadFirmware(file: File)` uploads custom file to `/api/v1/firmware/upload`.
    - Lines 161-176: `flashFirmware(file: File | null)` sends `FormData` containing custom `file` to `/api/v1/firmware/flash`.
  - **Backend API Endpoints**: `backend/app/main.py`
    - Lines 951-1004: `@app.post("/api/v1/firmware/upload")` accepts raw bytes from multipart form or JSON `content_hex`, storing it via `save_firmware_binary()`.
    - Lines 1011-1041: `@app.post("/api/v1/firmware/flash")` accepts custom `file` or JSON payload, saving it prior to flashing.
  - **Backend Firmware Logic**: `backend/app/firmware.py`
    - Lines 189-231: `save_firmware_binary()` stores arbitrary user uploads in `data/firmware/`.
    - Lines 274-320: `execute_flash_firmware(filename)` defaults to the most recently modified `.bin` file in `data/firmware/`.
- **Pre-Stored Official Firmware Availability**:
  - Existing compiled merged binary in workspace: `/home/pnt/IOT/build/FC_can_bang.ino.merged.bin` (size: ~1.4MB, verified valid ESP32 merged binary).
  - Target production path on Pi5: `/opt/drone-web-ui/firmware/official.bin`.
- **ARM Gatekeeper & Fail-Safe Logic**:
  - `backend/app/main.py:99-102`: `require_firmware_flashed()` blocks flight controls with `HTTP 423 Locked`.
  - `backend/app/main.py:1070-1077`: `arm_command()` Check 1 asserts `is_firmware_flashed()`.
  - `backend/app/main.py:237-295`: `arm_safety_monitor_loop()` continuously checks `if not is_firmware_flashed(): _revoke_arm_safety("FIRMWARE_NOT_FLASHED")`.
- **Observed Unit Test Regression in `backend/app/firmware.py`**:
  - Command: `PYTHONPATH=backend /home/pnt/miniconda3/envs/antidrone/bin/python -m pytest -v backend/tests/test_firmware_and_arm.py`
  - Verbatim Error:
    ```
    line = await asyncio.wait_for(proc.stdout.readline(), timeout=120)
    ...
    decoded = line.decode('utf-8', errors='replace')
    if "Erasing flash" in decoded:
    TypeError: argument of type 'coroutine' is not iterable
    backend/app/firmware.py:376: TypeError
    ```
  - Cause: When `proc` is mocked via `AsyncMock()`, `proc.stdout.readline` returns an `AsyncMock` object instead of bytes, causing `line.decode()` to return an unawaited coroutine.

---

## 2. Logic Chain

```
[Observation 1.1: UsbPortCoordinator globbing & probe]
       │
       ▼
(Inference 1: Discovery already supports both /dev/ttyUSB* and /dev/ttyACM*.
             No hardcoded ports exist when configured with "auto".
             Dynamic scanning safely arbitrates GPS vs ESP32 without conflicts.)
       │
       ▼
[Observation 1.1: SerialWorker finally block & get_device_for_role]
       │
       ▼
(Inference 2: Disconnect triggers SerialException, cleanly releasing the lease.
             Subsequent iterations invoke scan_and_assign(), enabling auto-reconnect.)
       │
       ▼
[Observation 1.2: FirmwareTab dropzone + main.py /firmware/upload & /flash]
       │
       ▼
(Inference 3: User file upload is exposed in UI, API client, and backend routes.
             This directly conflicts with R3 requiring static official firmware.)
       │
       ▼
[Observation 1.2: build/FC_can_bang.ino.merged.bin & /opt/drone-web-ui/firmware/official.bin]
       │
       ▼
(Inference 4: Static official firmware path must be standardized with fallback:
             1. /opt/drone-web-ui/firmware/official.bin (Pi5 target)
             2. settings.data_dir / "firmware" / "official.bin"
             3. PROJECT_ROOT / "build" / "FC_can_bang.ino.merged.bin")
       │
       ▼
[Observation 1.2: require_firmware_flashed & arm_safety_monitor_loop]
       │
       ▼
(Inference 5: Existing 4 gatekeepers only check if firmware is flashed (flag file/db).
             If official.bin is missing from disk, system currently lacks an upfront
             gatekeeper. Adding Gatekeeper 0 ("official_firmware_present") fulfills R3.)
```

---

## 3. Caveats

1. **Hardware Bench Testing**: Physical flashing via `esptool` over real USB serial can only execute when physically attached to the Raspberry Pi 5 hardware. Unit tests and mock harnesses rely on `AsyncMock` or PTY emulation.
2. **Backward Compatibility of Upload Endpoint**: If third-party automated scripts call `POST /api/v1/firmware/upload`, returning `403 Forbidden` with a descriptive message (`"Custom firmware upload is disabled; official manufacturer firmware is enforced."`) is preferred over a silent `404 Not Found`.
3. **Firmware Merged Binary**: ESP32 flashing at `0x0` requires a merged binary containing the bootloader, partition table, boot_app0, and application code. The repository's `build/FC_can_bang.ino.merged.bin` satisfies this requirement.

---

## 4. Conclusion & Implementation Plan

### 4.1 Requirement R2 Assessment
- **Status**: **Fully Architectural Compliant**.
- Dynamic scanning across `/dev/ttyUSB*` and `/dev/ttyACM*`, automatic ESP32 detection (passive inspection + active ping `{"type":"ping"}` / `{"type":"pong"}`), auto-reconnect via `coordinator.release_device_for_role()`, and JSONL resilience are fully implemented.
- The existing 19 tests in `test_serial_autodetect.py` and Scenario 3 test pass.

### 4.2 Requirement R3 Implementation Blueprint (for Implementers)

#### Step 1: Configuration (`backend/app/config.py`)
Add official firmware path configuration:
```python
# In Settings dataclass:
official_firmware_path: Path = Path(os.getenv("OFFICIAL_FIRMWARE_PATH", "/opt/drone-web-ui/firmware/official.bin"))
```

#### Step 2: Firmware Helper (`backend/app/firmware.py`)
1. **Define Official Firmware Resolver**:
   ```python
   OFFICIAL_TARGET_PATH = Path("/opt/drone-web-ui/firmware/official.bin")
   REPO_FALLBACK_PATH = Path("/home/pnt/IOT/build/FC_can_bang.ino.merged.bin")

   def get_official_firmware_path() -> Optional[Path]:
       """Resolve official firmware path with fallback order."""
       if settings.official_firmware_path.exists() and settings.official_firmware_path.is_file():
           return settings.official_firmware_path
       if OFFICIAL_TARGET_PATH.exists() and OFFICIAL_TARGET_PATH.is_file():
           return OFFICIAL_TARGET_PATH
       local_official = get_firmware_dir() / "official.bin"
       if local_official.exists() and local_official.is_file():
           return local_official
       if REPO_FALLBACK_PATH.exists() and REPO_FALLBACK_PATH.is_file():
           return REPO_FALLBACK_PATH
       return None

   def is_official_firmware_available() -> bool:
       fw = get_official_firmware_path()
       return bool(fw and fw.exists() and fw.stat().st_size > 0)
   ```
2. **Update `get_firmware_status()`**:
   Include `official_firmware_present: bool`, `official_firmware_path: str`, and warning if missing.
3. **Update `execute_flash_firmware()`**:
   Remove parameter `filename: Optional[str]`. Always resolve `target_file = get_official_firmware_path()`. If `not target_file`: raise `HTTPException(404, "Không tìm thấy tệp firmware chính thức (official.bin)")`.
4. **Fix Line 376 Mock Compatibility Bug**:
   Ensure `line` and `decoded` handle non-bytes or string representations safely:
   ```python
   if isinstance(line, (bytes, bytearray)):
       decoded = line.decode('utf-8', errors='replace')
   else:
       decoded = str(line)
   ```

#### Step 3: Backend Endpoints & ARM Fail-Safe (`backend/app/main.py`)
1. **Disable `/api/v1/firmware/upload`**:
   ```python
   @app.post("/api/v1/firmware/upload")
   async def upload_firmware(user=Depends(require_admin)):
       raise HTTPException(
           status_code=status.HTTP_403_FORBIDDEN,
           detail="Tính năng tải lên firmware tùy chỉnh đã bị vô hiệu hóa. Hệ thống chỉ hỗ trợ nạp firmware chính thức từ nhà sản xuất.",
       )
   ```
2. **Update `/api/v1/firmware/flash`**:
   Remove `UploadFile` and JSON body inputs. Directly invoke `execute_flash_firmware(username=user["username"])`.
3. **Add Gatekeeper 0 to ARM Gatekeepers**:
   - In `require_firmware_flashed()`:
     ```python
     if not is_official_firmware_available():
         raise HTTPException(
             status_code=status.HTTP_423_LOCKED,
             detail="Cảnh báo an toàn: Tệp firmware chính thức (official.bin) không tồn tại. Toàn bộ tính năng bay bị khóa.",
         )
     ```
   - In `arm_command()`: Check `if not is_official_firmware_available()` before checking `is_firmware_flashed()`.
   - In `arm_safety_monitor_loop()`: Check `if not is_official_firmware_available(): _revoke_arm_safety("OFFICIAL_FIRMWARE_MISSING")`.

#### Step 4: Frontend UI (`frontend/src/FirmwareTab.tsx`)
1. **Remove Custom File Upload Elements**:
   - Delete `selectedFile`, `fileSha256`, `handleFileChange`, `handleDrop`.
   - Remove `<input type="file" ...>` and `<div className="dropzone-box">`.
2. **Render Static Official Firmware Card**:
   - Display:
     - **Tệp Firmware chuẩn**: `/opt/drone-web-ui/firmware/official.bin`
     - **Trạng thái tệp**: `Sẵn sàng` (Xanh) hoặc `Không tìm thấy file!` (Đỏ).
     - **Phiên bản & SHA256**: Hiển thị thông tin chính thức.
3. **Update "Nạp Firmware" Button**:
   - Directly triggers `handleFlash()` without prompting for file selection.
   - Disabled if `isFlashing` or if `!fwStatus.official_firmware_present`.
4. **Display Warning Banner**:
   - If `!fwStatus.official_firmware_present`, show banner:
     `"CẢNH BÁO NGUY HIỂM: Không tìm thấy tệp firmware chính thức (official.bin). Khóa toàn bộ tính năng ARM!"`

---

## 5. Verification Method

To independently verify these conclusions and validate the implementation when performed:

1. **Verify Serial USB Connection (R2)**:
   ```bash
   PYTHONPATH=backend /home/pnt/miniconda3/envs/antidrone/bin/python -m pytest -v backend/tests/test_serial_autodetect.py
   /home/pnt/miniconda3/envs/antidrone/bin/python -m unittest tests/test_scenario_03_serial_jsonl.py
   ```
   *Expected*: All tests pass.

2. **Verify Static Flashing & ARM Lockout (R3)**:
   ```bash
   # 1. Run unit tests for firmware and ARM
   PYTHONPATH=backend /home/pnt/miniconda3/envs/antidrone/bin/python -m pytest -v backend/tests/test_firmware_and_arm.py
   
   # 2. Run Scenario 6 (Pre-flash mandatory lock)
   /home/pnt/miniconda3/envs/antidrone/bin/python -m unittest tests/test_scenario_06_mandatory_firmware.py
   
   # 3. Run all 16 SSH test runner scenarios in bench mode
   /home/pnt/miniconda3/envs/antidrone/bin/python tests/ssh_test_runner.py --mode bench
   ```

3. **Verify Invalidating Conditions**:
   - If `POST /api/v1/firmware/upload` is invoked, it must return `403 Forbidden`.
   - If `/opt/drone-web-ui/firmware/official.bin` (and fallback) is removed or renamed, `POST /api/v1/commands/arm` must return `HTTP 423 Locked`, and `GET /api/v1/firmware/status` must report `official_firmware_present = False`.
   - Clicking "Nạp Firmware" in the frontend must immediately start flashing `official.bin` without opening a file dialogue.
