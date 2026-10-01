# SCOPE-05 UART / Pin Ownership Report

Evidence source: actual files in `FC_can_bang.zip`, read-only. No board wiring
or physical interface was accessed.

| Interface | UART/peripheral | RX pin | TX pin | baud | mode | source | status |
|---|---|---:|---:|---:|---|---|---|
| SBUS | `HardwareSerial(2)` | GPIO35 | `-1` (disabled) | 100000 | `SERIAL_8E2`, inverted | `FC_can_bang/Sbus.ino` | `VERIFIED_FROM_SOURCE` |
| GNSS | unknown | unknown | unknown | unknown | unknown | no GNSS source evidence | `BLOCKED` |

The source proves SBUS ownership of UART2 as coded, not physical board wiring.
It does not prove that GPIO16/GPIO17 are GNSS pins, nor that the board exposes
the assumed UART route. GNSS ownership, electrical levels, common ground and
conflict resolution remain blocked pending exact board/datasheet/wiring proof.

No serial device was opened and no serial write/transmit API exists in the
repository-only parser preparation.
