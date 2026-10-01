# SCOPE-05 Readiness Report

Assessment date: `2026-09-26` (Asia/Ho_Chi_Minh)

## Boundary

This is a repository/archive-only readiness assessment. No ESP32, GNSS,
serial interface or powered hardware was accessed. No firmware was edited or
flashed, no GNSS configuration was written, and no motor, ESC, propeller,
ARM/DISARM or actuator operation was performed.

## Readiness status

```text
SCOPE04_ACCEPTED=OWNER_PROVIDED
SCOPE05_HARDWARE_CAPTURE=BLOCKED
SCOPE05=BLOCKED_NOT_OPENED
```

SCOPE-04 acceptance is recorded in
`SCOPE04_OWNER_ACCEPTANCE_PACKET_CURRENT.md`. SCOPE-05 is not opened because
the exact hardware identity, wiring/electrical evidence and safe bench
prerequisites are not available in the current repository evidence.

## Prerequisite matrix

| Prerequisite | Evidence | Status | Smallest resolution |
|---|---|---|---|
| SCOPE-04 accepted | Current owner acceptance packet and direct Owner decision in this conversation | `OWNER_PROVIDED` | None; already recorded |
| ESP32 exact board/model | `FC_can_bang.zip` source tree has no board selection, platform manifest or exact variant; `docs/00_PROJECT_OVERVIEW.md` records the gap | `MISSING` | Provide exact board/module identifier from the physical unit or authoritative documentation |
| GNSS exact model | Archive has no GNSS identifier/parser/configuration; no model evidence in repo | `MISSING` | Provide exact GNSS module/part identifier |
| Datasheet | No board/GNSS-specific datasheet supplied in current evidence | `MISSING` | Provide the exact model datasheet |
| Source/archive | `FC_can_bang.zip`, SHA-256 `95809c58d61bb20c12a9541719ad90ec4afc8dab74597a20517486174849771f`; read-only listing contains seven `.ino` files under `FC_can_bang/` | `VERIFIED` | None for archive inventory; do not replace it with another archive |
| Wiring | `docs/14_HARDWARE_INTERFACE.md` explicitly marks GNSS wiring as blocked; no current wiring diagram/photo/pin ownership proof | `MISSING` | Provide a redacted wiring/pin/ground/power diagram |
| UART ownership/conflict | Archive verifies SBUS on `HardwareSerial(2)`, RX GPIO35, TX disabled, 100000 `SERIAL_8E2`, inverted; archive has no GNSS UART | `BLOCKED` | Reconcile exact board wiring and GNSS UART ownership from source plus datasheet |
| Safe bench | No current bench/power procedure evidence | `MISSING` | Document bench power limits and passive-capture conditions |
| Propeller/actuator isolation | Archive contains ESC outputs on GPIO27/26/25/33 and arm-state logic; physical isolation is not evidenced | `BLOCKED` | Owner documents physical propeller removal/actuator isolation before any capture |
| Supervisor | No current named supervisor evidence | `MISSING` | Name the responsible supervisor |
| Stop authority | No current named stop authority or immediate power-cut procedure evidence | `MISSING` | Name stop authority and document immediate unplug/power-cut method |

Only the allowed status vocabulary is used above. `OWNER_PROVIDED` describes
the current SCOPE-04 acceptance; it is not hardware verification.

## Claim/source/evidence matrix

| Claim | Source | Evidence class | Status |
|---|---|---|---|
| ESP32 exact model | `FC_can_bang.zip` has no board selection or exact variant | `VERIFIED_FROM_SOURCE` for the absence; no identity proof | `MISSING` |
| GNSS exact model | Archive source and `docs/13_ESP32_FIRMWARE_AUDIT.md` contain no GNSS identifier | `VERIFIED_FROM_SOURCE` for the absence | `MISSING` |
| GNSS voltage/logical interface | No exact GNSS datasheet or wiring evidence | `NOT_EVIDENCED` | `MISSING` |
| ESP32 UART RX/TX pins | `FC_can_bang/Sbus.ino`: UART2 RX GPIO35, TX `-1`, inverted, 100000 `SERIAL_8E2` | `VERIFIED_FROM_SOURCE` for SBUS only | `BLOCKED` for GNSS ownership |
| GNSS baud | No GNSS UART setup in archive | `VERIFIED_FROM_SOURCE` for the absence | `BLOCKED` |
| NMEA support | No NMEA parser/configuration in archive; prior descriptive notes are not current hardware proof | `VERIFIED_FROM_SOURCE` for the absence | `BLOCKED` |
| UBX support | No UBX parser/configuration in archive; prior descriptive notes are not current hardware proof | `VERIFIED_FROM_SOURCE` for the absence | `BLOCKED` |
| Update rate | No GNSS source, datasheet or capture | `NOT_EVIDENCED` | `BLOCKED` |
| SBUS/UART conflict | SBUS UART2 ownership is source-verified, but GNSS connection is unknown | `VERIFIED_FROM_SOURCE` plus missing wiring evidence | `BLOCKED` |

The repository's historical GPIO16/GPIO17, approximately 38400 baud, NMEA/UBX
and 1–10 Hz notes remain unverified and are not used as hardware truth.

## Archive read-only inventory

The archive was hashed and listed without extraction or modification. It
contains:

- `FC_can_bang/FC_can_bang.ino`
- `FC_can_bang/ICM20602.ino`
- `FC_can_bang/Sbus.ino`
- `FC_can_bang/ESCino.ino`
- `FC_can_bang/MODE.ino`
- `FC_can_bang/PID.ino`
- `FC_can_bang/display.ino`

The source shows active IMU/SBUS/ESC control paths. It has no GNSS parser,
NMEA/UBX handling, JSONL telemetry, server protocol, `platformio.ini`, board
selection or library manifest. This is why archive presence does not make
model-specific telemetry ready.

## Safety gate

`SCOPE05_HARDWARE_CAPTURE=BLOCKED`. Repository/source audit and synthetic
fixture preparation may be considered later, but model-specific parser or
live capture remains blocked until the missing identity, wiring and safety
facts are supplied and separately authorized.
