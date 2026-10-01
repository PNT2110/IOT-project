# SCOPE-05 Entry Owner Decision Packet

## Current state

```text
SCOPE05_REPOSITORY_PREPARATION=PASS
SCOPE05=BLOCKED_NOT_OPENED
SCOPE05_HARDWARE_CAPTURE=BLOCKED
```

The Owner separately authorized repository-only preparation. That preparation,
including the archive audit and synthetic parser tests, is complete. SCOPE-04
acceptance and this preparation authorization do not authorize SCOPE-05
hardware work. The current canonical assessment is
`SCOPE05_READINESS_REPORT_CURRENT.md`.

## Only missing Owner inputs

Provide or approve the following facts/decisions without sending secrets:

1. Exact ESP32 board/module identifier.
2. Exact GNSS module/part identifier and its authoritative datasheet.
3. Redacted wiring/pin-ownership record: GNSS power/ground, logic level,
   GNSS RX/TX direction, ESP32 pins and SBUS/UART ownership.
4. Safe bench record: power arrangement, props removed or physically isolated,
   actuator/ESC path disabled or isolated, named supervisor, named stop
   authority and immediate unplug/power-cut method.
5. A separate authorization for any passive/read-only hardware capture.

Until these inputs are evidenced and separately authorized, retain
`SCOPE05=BLOCKED_NOT_OPENED`. No firmware edit/flash, persistent GNSS config,
serial write, motor/ESC command, ARM/DISARM or flight test is permitted.
