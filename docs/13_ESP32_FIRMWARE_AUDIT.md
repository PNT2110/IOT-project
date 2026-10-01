# SCOPE-00 — ESP32 firmware audit (read-only)

**Input:** `FC_can_bang.zip` at repository root; archive SHA-256 recorded in [00_PROJECT_OVERVIEW.md](00_PROJECT_OVERVIEW.md). No files were extracted/modified by SCOPE-00.

## Inventory from archive

| File | Observed content | Confidence |
|---|---|---|
| `FC_can_bang/FC_can_bang.ino` | setup ICM20602, SBUS, motor; loop reads IMU/SBUS, maps arm/mode, angle mode/no-fly, writes ESC output; 5 ms loop wait; calls display. | `VERIFIED_FROM_SOURCE` |
| `FC_can_bang/ICM20602.ino` | SPI at 1 MHz, CS GPIO5, register config, accel/gyro reads, calibration loop, 1D Kalman; names function `ICM20620_danhthuc` despite file/device label ICM20602. | `VERIFIED_FROM_SOURCE` |
| `FC_can_bang/Sbus.ino` | `HardwareSerial(2)`, 100000, `SERIAL_8E2`, RX GPIO35, TX -1, inversion true; 16 channels; timeout 200 ms. | `VERIFIED_FROM_SOURCE` |
| `FC_can_bang/ESCino.ino` | ESC GPIO27/26/25/33, LEDC channels 0–3, frequency 391, resolution 11; motor writes exist. | `VERIFIED_FROM_SOURCE` |
| `FC_can_bang/MODE.ino` | angle mode PID mixing, no_fly sets ESC values 800 and status_arm 0. | `VERIFIED_FROM_SOURCE` |
| `FC_can_bang/PID.ino` | angle/rate PID, fixed `0.005` dt, integral/derivative state. | `VERIFIED_FROM_SOURCE` |
| `FC_can_bang/display.ino` | debug `Serial.print` statements are commented out; no structured telemetry encoder. | `VERIFIED_FROM_SOURCE` |

## Verified pin/protocol table

| Resource | Evidence | Risk |
|---|---|---|
| SPI CS | GPIO5 | May conflict with board wiring; actual SPI pins not explicit. |
| SBUS | UART2; RX GPIO35; inverted; 100000 8E2; no TX | GPIO16/17 not used by this source for SBUS, but board/other code must be verified. |
| ESC | GPIO27, 26, 25, 33 | Firmware has actuator output; therefore no physical test under SCOPE-00. |
| Arm switch | `sbus_ch[5]`, threshold 1800; throttle channel index 3 < 1050 | Behavior is source-observed, not safety-certified. |
| Mode switch | `sbus_ch[6]` near 990 selects angle mode | Only angle/no-fly branch visible. |
| Loop | `while (micros()-LoopTimer < 5000)` | Actual jitter/overrun unmeasured. |
| GNSS | No GNSS identifier/parser/configuration in archive | `BLOCKED` for integration claims. |

## Findings and non-findings

- The archive does not contain NMEA/UBX parser, GNSS UART setup, I²C GNSS code, JSONL telemetry, or server protocol.
- `Serial.begin(115200)` is called in IMU setup and is the only observed debug serial setup; board USB/console mapping is not identified.
- No `platformio.ini`, Arduino board selection, library manifest or exact ESP32 variant is in archive.
- The source contains active motor output code and arm state logic. This report must not be read as approval to power, arm, flash or test motors.
- User-reported GPIO16/17, 38400 baud, NMEA 4.x/UBX, 1–10 Hz are **not verified by archive**.

## Safe follow-up (SCOPE-05 only after approval)

1. Identify board/module/datasheet and verify electrical levels/power.
2. Build a passive/read-only test plan with motors/propellers physically isolated as required by safety procedure.
3. Capture serial input without sending GNSS configuration writes; validate checksums and timestamp/fix semantics.
4. Add synthetic parser fixtures before any hardware read.
5. Review loop timing/SBUS timeout/ESC state transitions with a safety reviewer.

No command sequence for motors, ARM/DISARM, flashing or persistent GNSS configuration belongs in SCOPE-00.
