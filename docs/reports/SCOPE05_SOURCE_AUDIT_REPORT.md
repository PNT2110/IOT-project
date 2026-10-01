# SCOPE-05 Source Audit Report

Assessment: repository/archive-only preparation, `2026-09-26`.

## Archive integrity

```text
ARCHIVE=FC_can_bang.zip
SHA256=95809c58d61bb20c12a9541719ad90ec4afc8dab74597a20517486174849771f
ARCHIVE_ACCESS=VERIFIED
ARCHIVE_MODIFIED=no
```

The archive was hashed and listed read-only. No extraction, overwrite,
repackaging or firmware edit occurred.

## Member inventory

| Member | Read-only finding |
|---|---|
| `FC_can_bang/FC_can_bang.ino` | Main loop reads IMU/SBUS, evaluates arm/mode state and calls motor control |
| `FC_can_bang/ICM20602.ino` | SPI IMU access; CS GPIO5, 1 MHz in source |
| `FC_can_bang/Sbus.ino` | `HardwareSerial(2)`, SBUS RX GPIO35, TX `-1`, 100000 `SERIAL_8E2`, inverted |
| `FC_can_bang/ESCino.ino` | ESC output pins GPIO27/26/25/33 |
| `FC_can_bang/MODE.ino` | Angle/no-fly control branches |
| `FC_can_bang/PID.ino` | PID state and mixing |
| `FC_can_bang/display.ino` | Display/debug helper; no structured telemetry protocol |

## Build and identity evidence

| Item | Evidence | Status |
|---|---|---|
| Build system | No `platformio.ini`, Arduino board selection or build manifest in archive | `MISSING` |
| Library manifest | No library manifest in archive | `MISSING` |
| Exact ESP32 board/model | No exact variant or module identifier in source | `MISSING` |
| ICM20602 interface | SPI, CS GPIO5 and register access in source | `VERIFIED_FROM_SOURCE` |
| SBUS interface | UART2 / GPIO35 / 100000 / 8E2 / inverted in source | `VERIFIED_FROM_SOURCE` |
| ESC ownership | GPIO27/26/25/33 output code in source | `VERIFIED_FROM_SOURCE` |
| Arm/control logic | arm state and `control_motor` path in source | `VERIFIED_FROM_SOURCE` |
| GNSS | No identifier, parser, UART setup or configuration | `MISSING` / `BLOCKED` |
| Telemetry | No NMEA, UBX, JSONL or server protocol | `MISSING` / `BLOCKED` |

The archive contains active actuator-related code. This is source evidence
only and is not permission for powered hardware, motor/ESC, ARM/DISARM or
flight activity.
