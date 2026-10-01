# Comprehensive Survey Report: ESP32 Flight Controller & Serial Interface (Drone Station v2)

**Author:** Explorer 1 (Firmware & Serial Interface Specialist)  
**Date:** 2026-09-13  
**Target Repository:** `/home/pnt/IOT/FC_can_bang` & `/home/pnt/IOT/backend`  
**Reference Specification:** `/home/pnt/IOT/prompt-du-an-drone-v2.md` (Sections 1, 2, 4, 10, 11)

---

## 1. Executive Summary

This report presents a thorough, read-only architectural and technical survey of the ESP32 flight controller firmware (`FC_can_bang`), the hardware-in-the-loop serial communication protocol with the Raspberry Pi 5 companion computer, and the operational integration for the Drone Station v2 project.

Key findings:
1. **Firmware Structure Compliance:** The `FC_can_bang` folder contains exactly seven `.ino` files operating as a monolithic Arduino sketch compiled by `arduino-cli`. In accordance with project requirements, the directory and file structure will be **strictly preserved**; all modifications will be internal logic enhancements.
2. **Build Toolchain:** The system possesses a fully functional, local `arduino-cli` (v1.5.1) at `/home/pnt/IOT/bin/arduino-cli`, with ESP32 core 3.3.11 (`esp32:esp32:esp32`) and ArduinoJson 7.4.3. The firmware compiles cleanly into a 4MB merged flash binary ready for bare-metal deployment.
3. **Live Hardware State:** On the target Raspberry Pi 5 (`192.168.1.118`), `/dev/ttyUSB0` is currently occupied by the BZ251 GPS receiver transmitting NMEA at 38400 baud. The ESP32 flight controller will be assigned to a secondary USB-serial interface (e.g. `/dev/ttyUSB1` or `/dev/ttyACM0`) managed dynamically by `UsbPortCoordinator`.
4. **Provisioning Architecture:** The ESP32 WROOM SoftAP and Captive Portal (DNS Server on port 53 + WebServer on port 80) must employ a blue-white aesthetic, handle OS-specific captive-portal probes, hand off Wi-Fi credentials to Pi5 via JSONL over USB serial, display connection status, and shut down AP mode upon successful commissioning.
5. **Fail-Safe ARM Enforcement:** The firmware currently lacks a serial watchdog for the permission state. We propose a robust fail-safe mechanism where ESP32 defaults to `flight_permission = false`, requires continuous heartbeats from Pi5, and enforces a hardware motor kill if permission is revoked or communication is lost for more than 2000 ms.

---

## 2. Complete File Inventory of `FC_can_bang`

The `FC_can_bang` directory (`/home/pnt/IOT/FC_can_bang`) constitutes a multi-file Arduino sketch. In the Arduino build system, all `.ino` files in the sketch directory are concatenated into a single compilation unit, with `FC_can_bang.ino` parsed first, followed by remaining files in alphabetical order.

```
/home/pnt/IOT/FC_can_bang/
├── build/
│   └── esp32.esp32.esp32/
│       ├── FC_can_bang.ino.bin              (963,872 bytes)
│       ├── FC_can_bang.ino.bootloader.bin   (24,992 bytes)
│       ├── FC_can_bang.ino.elf              (13,382,516 bytes)
│       ├── FC_can_bang.ino.map              (13,977,522 bytes)
│       ├── FC_can_bang.ino.merged.bin       (4,194,304 bytes)
│       ├── FC_can_bang.ino.partitions.bin   (3,072 bytes)
│       ├── boot_app0.bin                    (8,192 bytes)
│       ├── build.options.json               (376 bytes)
│       ├── flash_args                       (176 bytes)
│       ├── partitions.csv                   (305 bytes)
│       └── sdkconfig                        (114,491 bytes)
├── ESCino.ino                               (75 lines, 1,775 bytes)
├── FC_can_bang.ino                          (228 lines, 6,886 bytes)
├── ICM20602.ino                             (403 lines, 7,618 bytes)
├── MODE.ino                                 (33 lines, 1,029 bytes)
├── PID.ino                                  (153 lines, 3,892 bytes)
├── Sbus.ino                                 (125 lines, 2,955 bytes)
└── display.ino                              (89 lines, 2,987 bytes)
```

### 2.1 File-by-File Technical Analysis

| File | Purpose & Architecture | Key Variables & Peripherals | Issues & Required v2 Enhancements |
|---|---|---|---|
| `FC_can_bang.ino` | **Primary Sketch & Main Loop**<br>Contains `setup()` and `loop()`. Manages Wi-Fi AP provisioning, captive portal routing, main 200Hz loop execution, and master arming logic. | `DNSServer dnsServer;`<br>`WebServer webServer;`<br>`flight_permission` (bool)<br>`status_arm` (int)<br>`LoopTimer` (micros) | 1. AP SSID is currently hardcoded (`DRONE-123456`). Must dynamically incorporate ESP32 MAC suffix.<br>2. Captive portal webserver handling is called directly in the 200Hz loop (`webServer.handleClient()`), which introduces loop jitter during client connections. Needs non-blocking handling or dual-core separation.<br>3. Does not persist provisioning state or shut down AP when configured. |
| `display.ino` | **USB Serial Interface & Telemetry**<br>Communicates with Pi5 over hardware UART0 (115200 baud). Deserializes JSONL commands and emits 5Hz telemetry frames. | `Serial` (UART0)<br>`last_telemetry` (millis)<br>`pi5_status`, `pi5_ip`, `pi5_url` | 1. Uses blocking `Serial.readStringUntil('\n')` which can stall the 200Hz flight loop if data is incomplete.<br>2. Hardcodes PID telemetry values rather than referencing live variables from `PID.ino`.<br>3. Lacks handler for `pid_set` / `pid_get` commands.<br>4. Telemetry omits LiDAR altitude required by v2 spec. |
| `ICM20602.ino` | **IMU Driver & State Estimation**<br>Interfaces with InvenSense ICM-20602 via SPI. Performs 2000-sample gyro calibration, computes angular rates, and runs 1D Kalman filters for Roll and Pitch. | SPI bus (VSPI):<br>SCK=18, MISO=19, MOSI=23, CS=5.<br>`KalmanAngleRoll`, `KalmanAnglePitch` | 1. Calibration loop in `setup_icm20602()` runs in a blocking `while(1)` without timeout. If the physical sensor is detached or unresponsive, ESP32 hangs permanently, preventing serial boot communication with Pi5.<br>2. Needs timeout/mock fallback when running bench tests without sensor. |
| `ESCino.ino` | **Motor PWM Actuation**<br>Generates 391Hz 11-bit PWM pulses using ESP32 LEDC peripheral for 4 brushless ESCs. | LEDC peripheral.<br>Pins: M1=27, M2=26, M3=25, M4=33.<br>Values: 800 (1000µs idle) to 1600 (2000µs full). | 1. Uses ESP32 Core 3.x API (`ledcAttach`).<br>2. Fully functional; motor safety kill is cleanly tied to `status_arm`. |
| `MODE.ino` | **Flight Modes & Mixer**<br>Calculates angle stabilization PID and maps desired rates to Quad-X motor mixing matrix. | `angle_mode()`, `no_fly()`, `limit_value(900, 1600)` | 1. Quad-X mixer correctly maps roll, pitch, and yaw inputs to 4 motors.<br>2. `no_fly()` cleanly commands 800 to all ESCs and sets `status_arm = 0`. |
| `PID.ino` | **Cascaded PID Controller**<br>Implements dual-loop PID: outer angle loop (`PID_Angle`, 10Hz/200Hz) and inner rate loop (`PID_Rate`, 200Hz). Includes anti-windup clamping. | `PAngleRoll`, `PRateRoll`, `IRateRoll`, `DRateRoll`, etc. | 1. PID gains are currently static variables; they are not updated when Pi5 requests tuning.<br>2. Must expose getter/setter functions for live PID tuning from Pi5. |
| `Sbus.ino` | **RC Receiver Driver (SBUS)**<br>Reads Futaba SBUS 25-byte inverted frames at 100,000 baud 8E2 on UART2 (GPIO 35). | `HardwareSerial Serial_sbus(2);`<br>Pin RX=35.<br>`sbus_ch[1..16]` | 1. Channels correctly mapped: Ch1=Roll, Ch2=Pitch, Ch3=Throttle, Ch4=Yaw, Ch5=Arm/Disarm, Ch6=Flight Mode.<br>2. 200ms signal-loss failsafe correctly triggers `no_fly()`. |

---

## 3. Build & Flash Toolchain Details

### 3.1 Host Development & Compilation Environment
- **Arduino CLI Binary:** `/home/pnt/IOT/bin/arduino-cli` (v1.5.1, Commit `01f3d4f2b`)
- **ESP32 Core:** Arduino-ESP32 v3.3.11 located at `/home/pnt/.arduino15/packages/esp32/hardware/esp32/3.3.11`
- **Target FQBN:** `esp32:esp32:esp32`
- **Required Libraries:**
  - `ArduinoJson` (v7.4.3) located at `/home/pnt/Arduino/libraries/ArduinoJson`
  - Core libraries provided by ESP32 SDK: `WiFi`, `WebServer`, `DNSServer`, `SPI`, `HardwareSerial`
- **Memory Footprint (Current Build):**
  - Flash: `963,731 bytes` (73% of 1,310,720 byte app partition)
  - RAM: `48,148 bytes` (14% of 327,680 byte dynamic memory)

### 3.2 Compilation Command
```bash
/home/pnt/IOT/bin/arduino-cli compile \
  --fqbn esp32:esp32:esp32 \
  --build-property "compiler.optimization_flags=-Os" \
  /home/pnt/IOT/FC_can_bang \
  --output-dir /home/pnt/IOT/FC_can_bang/build/esp32.esp32.esp32
```

### 3.3 Flashing Toolchain & Memory Layout
The build produces both individual component binaries and a merged 4MB image:
- **`FC_can_bang.ino.bootloader.bin`** -> Flash Offset: `0x1000`
- **`FC_can_bang.ino.partitions.bin`** -> Flash Offset: `0x8000`
- **`boot_app0.bin`** -> Flash Offset: `0xe000`
- **`FC_can_bang.ino.bin`** -> Flash Offset: `0x10000`
- **`FC_can_bang.ino.merged.bin`** -> Flash Offset: `0x0000` (Single combined image)

**Flashing Tool:** `esptool` (v5.4.0) located on Pi5 at `/opt/iot-drone/venv/bin/esptool`.

**Flashing Commands:**
1. Single merged binary (recommended for Pi5 bare-metal update):
   ```bash
   /opt/iot-drone/venv/bin/esptool --chip esp32 --port /dev/ttyUSB1 --baud 921600 write-flash 0x0 /home/pi5/FC_can_bang.ino.merged.bin
   ```
2. Segmented binary flashing:
   ```bash
   /opt/iot-drone/venv/bin/esptool --chip esp32 --port /dev/ttyUSB1 --baud 921600 \
     --before default-reset --after hard-reset write-flash -z \
     --flash-mode dio --flash-freq 80m --flash-size 4MB \
     0x1000 FC_can_bang.ino.bootloader.bin \
     0x8000 FC_can_bang.ino.partitions.bin \
     0xe000 boot_app0.bin \
     0x10000 FC_can_bang.ino.bin
   ```

---

## 4. Proposed Wi-Fi Provisioning Architecture

```
+------------------+         +---------------------+         +---------------------+
|   User Phone     |         |   ESP32 (WROOM)     |         |  Raspberry Pi 5     |
+------------------+         +---------------------+         +---------------------+
        |                               |                               |
        | 1. Scan QR Code               |                               |
        |    SSID: DRONE-A1B2           |                               |
        |------------------------------>|                               |
        | 2. Connect to SoftAP          |                               |
        |    (192.168.4.1)              |                               |
        |------------------------------>|                               |
        |                               |                               |
        | 3. Captive Portal Triggered   |                               |
        |    (DNS Redirect to 192.168.4.1)                              |
        |<------------------------------|                               |
        | 4. User selects Home Wi-Fi    |                               |
        |    & enters Password          |                               |
        |------------------------------>|                               |
        |                               | 5. USB Serial (JSONL)         |
        |                               |    {"type": "wifi_setup",     |
        |                               |     "ssid": "...", "pass":..} |
        |                               |------------------------------>|
        |                               |                               | 6. nmcli connects
        |                               |                               |    to Home Wi-Fi
        |                               | 7. USB Serial (JSONL)         |
        |                               |    {"type": "wifi_status",    |
        |                               |     "status": "connected",    |
        |                               |     "ip": "192.168.1.118",    |
        |                               |     "url": "https://pi5.local"|
        |                               |<------------------------------|
        | 8. Portal displays Success:   |                               |
        |    - IP & URL of Pi5          |                               |
        |    - Drone ID                 |                               |
        |    - Default Credentials      |                               |
        |<------------------------------|                               |
        |                               | 9. Disable SoftAP & WebServer |
        |                               |    (Transition to Normal FC)  |
```

### 4.1 SSID & QR Code Format
- **SSID Generation:** `DRONE-<CHIP_MAC_SUFFIX>` (e.g. `DRONE-3A8F` using the last two bytes of `ESP.getEfuseMac()`).
- **QR Code Content:** Standard Wi-Fi pairing payload:
  ```
  WIFI:S:DRONE-3A8F;T:nopass;;
  ```
- **Fallback URL:** `http://192.168.4.1`

### 4.2 Captive Portal Engine & Multi-Platform Probing
When client devices connect to the SoftAP, their OS sends detection HTTP requests. The ESP32 DNS server redirects all DNS queries (`*` -> `192.168.4.1`), and `WebServer` handles standard probing endpoints:
- **Android:** `/generate_204`, `/gen_204` -> HTTP 302 Redirect to `/`
- **Apple iOS/macOS:** `/hotspot-detect.html` -> Serves portal HTML
- **Windows:** `/ncsi.txt`, `/connecttest.txt` -> HTTP 302 Redirect to `/`
- **Catch-All:** `webServer.onNotFound(...)` -> HTTP 302 Redirect to `http://192.168.4.1/`

### 4.3 Blue-White Design System
The captive portal HTML/CSS embedded in ESP32 flash complies strictly with the v2 Blue-White theme:
- **Background:** Clean ice blue `#f0f4f8`
- **Surface / Card:** Pure white `#ffffff` with subtle elevation `box-shadow: 0 4px 16px rgba(2, 132, 199, 0.08)` and `border-radius: 12px`
- **Primary Accent:** Sky Blue / Tech Navy `#0284c7` and `#0369a1`
- **Typography:** System sans-serif (`-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`)
- **Input Fields:** `#f8fafc` background with border `#cbd5e1`, focusing to `#0284c7`

### 4.4 Provisioning State Machine
1. **Unconfigured State (`NVS: provisioned = 0`):**
   - Starts SoftAP + DNS Server + WebServer on Core 0.
   - Scans Wi-Fi networks in background and caches results.
2. **Handoff State:**
   - On `/connect` submission, serializes `{"type": "wifi_setup", "ssid": "...", "password": "..."}` over Serial.
   - Portal client transitions to polling `GET /status` every 1.5 seconds.
3. **Commissioned State:**
   - Pi5 replies over Serial with `{"type": "wifi_status", "status": "connected", ...}`.
   - Portal displays Pi5 credentials and IP/URL.
   - ESP32 sets `provisioned = 1` in NVS.
   - After a 45-second user grace period (or on explicit serial ACK), ESP32 terminates SoftAP and stops WebServer to dedicate full CPU bandwidth to flight stabilization.
4. **Re-Provisioning Trigger:**
   - If Pi5 sends `{"type": "command", "command": "RESET_WIFI"}` or a physical failsafe button is pressed, ESP32 clears NVS and restarts AP mode.

---

## 5. Serial JSONL Protocol Specification (115200 Baud)

Physical layer: UART0 over USB (Micro-USB / Type-C on ESP32 connected to Pi5 USB-3.0 port).  
Framing: ASCII/UTF-8 JSON terminated by `\n` (`0x0A`).  
Baud rate: `115200` bps, 8 data bits, no parity, 1 stop bit (8N1). Flow control disabled.

### 5.1 Messages: ESP32 -> Raspberry Pi 5

#### 1. Wi-Fi Credentials Transfer (`wifi_setup`)
Sent immediately when user submits credentials in the captive portal.
```json
{
  "type": "wifi_setup",
  "ssid": "HomeNetwork_5G",
  "password": "CorrectHorseBatteryStaple"
}
```

#### 2. Periodic Telemetry (`telemetry`) — 5Hz (every 200 ms)
Delivers attitude, motor/arm state, LiDAR altitude, and live PID states.
```json
{
  "type": "telemetry",
  "armed": false,
  "flight_mode": "STABILIZE",
  "attitude": {
    "roll": 1.42,
    "pitch": -0.85,
    "yaw": 182.40
  },
  "altitude": 1.75,
  "lidar_altitude": 1.75,
  "pid": {
    "roll": {
      "kp": 0.40,
      "ki": 0.40,
      "kd": 0.02,
      "setpoint": 0.0,
      "measured": 1.42,
      "output": -0.56
    },
    "pitch": {
      "kp": 0.40,
      "ki": 0.40,
      "kd": 0.02,
      "setpoint": 0.0,
      "measured": -0.85,
      "output": 0.34
    },
    "yaw": {
      "kp": 1.00,
      "ki": 10.00,
      "kd": 0.00,
      "setpoint": 180.0,
      "measured": 182.4,
      "output": -2.40
    }
  }
}
```

#### 3. Command Acknowledgment (`ack`)
Emitted in response to any discrete command frame received from Pi5.
```json
{
  "version": 1,
  "type": "ack",
  "command_id": "c8a45e90-8438-4e5a-8b9a-7c98e1f0e210",
  "accepted": true,
  "message": "PID parameters updated successfully"
}
```

#### 4. Active Probe Response (`pong`)
Emitted when Pi5 probes the port during USB autodetect.
```json
{
  "type": "pong",
  "firmware": "FC_can_bang_v2",
  "drone_id": "DRONE-3A8F"
}
```

---

### 5.2 Messages: Raspberry Pi 5 -> ESP32

#### 1. Wi-Fi Status Handoff (`wifi_status`)
Transmitted by Pi5 after `nmcli` successfully joins the Wi-Fi network and obtains a valid IP.
```json
{
  "type": "wifi_status",
  "status": "connected",
  "ip": "192.168.1.118",
  "url": "https://pi5.local",
  "drone_id": "DRONE-3A8F",
  "default_account": "admin / 123456"
}
```

#### 2. Flight Permission & ARM Lock State (`permission`)
Transmitted continuously by Pi5 (every 1000 ms) and immediately upon MOD authorization changes.
```json
{
  "type": "permission",
  "granted": true,
  "expires_in_s": 3540
}
```
*When authorization is revoked or expired:*
```json
{
  "type": "permission",
  "granted": false,
  "reason": "FLIGHT_WINDOW_EXPIRED"
}
```

#### 3. Critical Flight Commands (`command`)
Used for immediate emergency actions:
```json
{
  "version": 1,
  "type": "command",
  "id": "c8a45e90-8438-4e5a-8b9a-7c98e1f0e210",
  "command": "LAND",
  "reason": "GEOFENCE_BREACH"
}
```
*Or emergency hardware ARM lock:*
```json
{
  "version": 1,
  "type": "command",
  "id": "5f3a2b1c-99d0-42e1-a7b8-61d0f5c4e321",
  "command": "LOCK_ARM",
  "reason": "MOD_REJECTED"
}
```

#### 4. PID Tuning Command (`pid_set`)
Transmitted when an authorized admin tunes PID values from Tab 3.
```json
{
  "version": 1,
  "type": "pid_set",
  "id": "8b7e21a0-44e2-4917-b08e-324f9c118e9a",
  "axis": "roll",
  "kp": 0.42,
  "ki": 0.38,
  "kd": 0.025
}
```

#### 5. Port Probe (`ping`)
Emitted by `UsbPortCoordinator` during port identification.
```json
{
  "type": "ping"
}
```

---

## 6. Fail-Safe ARM Locking Mechanism on ESP32

```
                       [ SBUS RC Transmitter ]
                                  |
                                  | Ch5 > 1800 (Arm Switch)
                                  v
+-----------------------------------------------------------------+
| ESP32 Flight Controller Firmware                                |
|                                                                 |
|   1. switch_arm_disarm = (sbus_ch[5] > 1800 && sbus_ch[3] < 1050) |
|                                                                 |
|   2. FAILSAFE GATE:                                             |
|      bool allow_arm = flight_permission &&                      |
|                       (millis() - last_permission_time < 2000) &&|
|                       sbus_status_valid;                        |
|                                                                 |
|   3. if (!allow_arm) {                                          |
|          status_arm = 0;                                        |
|          reset_status_flight(); // Clear I-terms                |
|          no_fly();              // Force ESCs to 800 (Idle/Kill)|
|      } else {                                                   |
|          status_arm = switch_arm_disarm;                        |
|      }                                                          |
+-----------------------------------------------------------------+
                                  |
             +--------------------+--------------------+
             | (allow_arm == false)                    | (allow_arm == true)
             v                                         v
   [ ESC Output: 800 ]                       [ Angle Mode Active ]
   Motors Locked / Off                       PID Controls ESCs (900-1600)
```

### 6.1 Architectural Rules
1. **Deny-by-Default:** On boot, `flight_permission` initializes to `false`. Under no circumstances can the drone arm until Pi5 explicitly sends `"granted": true`.
2. **Communication Watchdog:** If serial communication from Pi5 ceases for more than `2000 ms`, ESP32 automatically flips `flight_permission = false`. This guarantees that if Pi5 freezes, panics, reboots, or loses USB connectivity, the drone disarms immediately.
3. **Disarm Throttle Check:** In conformance with RC safety rules, arming is only permitted if SBUS throttle (Channel 3) is at minimum (< 1050 ticks).
4. **Mid-Flight Disarm / Breach Action:** If permission is revoked while airborne (`status_arm == 1`), ESP32 immediately engages `no_fly()` or controlled descend mode, zeroes PID integral accumulators (`reset_status_flight()`), and logs a security disarm event.

---

## 7. Technical Constraints, Dependencies & Failure Modes

### 7.1 Constraints
- **Preserve Directory & File Names:** Under no condition should new `.ino` or `.cpp` files be introduced to `FC_can_bang`. All v2 features (watchdogs, non-blocking serial, PID tuning, captive portal enhancements) must be written inside the existing 7 files.
- **Dual-Core Partitioning:** The flight stabilization loop requires deterministic timing at 200 Hz (5000 µs period). The captive portal web server and DNS server must not block or introduce timing jitter to Core 1.
- **Single Exclusive Port Lease:** Only one process can bind to the ESP32 USB serial port at any given time. Before firmware flashing via `esptool`, Pi5 backend must cleanly release the serial port (`coordinator.release_device_for_role("esp")` and `esp_worker.stop()`).

### 7.2 Hardware Abstractions & Dependencies
- **IMU:** ICM-20602 on SPI CS 5. Gyro ±2000 dps, Accel ±16g.
- **RC:** Futaba SBUS on UART2 (GPIO 35).
- **ESCs:** LEDC PWM on GPIOs 27, 26, 25, 33 at 391 Hz.
- **USB-UART:** CH340 / CP2102 connecting ESP32 UART0 (GPIO 1 & 3) to Pi5 USB.

### 7.3 Identified Failure Modes & Mitigations

| Failure Mode | Impact | Root Cause | Proposed Mitigation |
|---|---|---|---|
| **IMU Calibration Hang** | ESP32 completely hangs on boot; fails to respond to serial commands. | `setup_icm20602()` runs `while(1)` until calibration diff < 20. If sensor is absent or noisy, it loops infinitely. | Add a 3-second calibration timeout. If sensor not responding (`WHO_AM_I != 0x12`), flag sensor error and proceed to serial loop in SAFE/BENCH mode. |
| **Serial Read Lockup** | 200Hz loop freezes for 1000ms. | `Serial.readStringUntil('\n')` blocks until timeout if newline is delayed. | Replace with non-blocking character accumulator: read available bytes into buffer, trigger parse only when `\n` is encountered. |
| **USB Port Collision (GPS vs ESP32)** | Pi5 connects GPS worker to ESP32 or flashes GPS instead of ESP32. | Both devices use CH340 USB-Serial adapters (`1a86:7523`). | `UsbPortCoordinator` must enforce content-based probing: 38400 baud NMEA checksum for GPS, 115200 baud JSON ping/telemetry for ESP32. |
| **Pi5 Crash Mid-Flight** | Drone continues flying in uncontrolled or unmonitored state. | ESP32 preserves last received `flight_permission = true`. | Serial watchdog timer: automatically revoke permission if no heartbeat is received within 2000 ms. |
| **DTR/RTS Reset Spikes** | ESP32 resets unexpectedly when Pi5 opens serial port. | Linux serial drivers toggle DTR/RTS upon port open, pulling ESP32 EN pin LOW via CH340 auto-reset circuit. | Configure `open_serial_port()` with `dtr=False, rts=False` before opening and re-assert immediately after open. |

---

## 8. Implementation Roadmap for Firmware Rewrite

When transitioning to the implementation phase, the firmware files will be updated in place:

1. **`FC_can_bang.ino`**:
   - Add MAC-based dynamic SSID generation (`DRONE-XXXX`).
   - Implement persistent provisioning state using ESP32 `Preferences` (NVS).
   - Implement non-blocking captive portal handlers and automatic AP shutdown.
   - Implement 2000ms serial permission watchdog in `loop()`.
2. **`display.ino`**:
   - Replace blocking `readStringUntil` with non-blocking line parser.
   - Implement `pid_set` and `pid_get` handlers with ACK responses.
   - Add `lidar_altitude` to telemetry payload.
   - Connect telemetry PID fields directly to live global PID variables.
3. **`PID.ino`**:
   - Expose thread-safe getters and setters: `set_pid_rate_roll(kp, ki, kd)`, `get_pid_rate_roll(...)`, etc.
4. **`ICM20602.ino`**:
   - Add 3-second timeout to gyro calibration loop and WHO_AM_I validation.
