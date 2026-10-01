# SCOPE-05 Passive Capture Plan

Status: planning only; `SCOPE05_HARDWARE_CAPTURE=BLOCKED`.

This plan cannot be executed until the exact hardware facts are evidenced and
a separate Owner authorization is supplied. Any future capture must be RX/read
only where technically possible and must not configure the GNSS persistently.

## Required pre-capture evidence

- Exact ESP32 board/module and exact GNSS model.
- Board/GNSS datasheets, supply and logic-level compatibility.
- Redacted wiring showing GNSS TX → ESP RX, GNSS RX ← ESP TX if connected,
  common ground, power and UART ownership.
- Safe bench power arrangement and limits.
- Props removed or physically isolated.
- ESC/motor actuation path disabled or physically isolated.
- Named supervisor, named stop authority and immediate unplug/power-cut method.
- Separate Owner authorization for passive hardware capture.

## Capture boundary

```text
SERIAL_READ=allowed only after separate authorization
SERIAL_WRITE=FORBIDDEN
PERSISTENT_GNSS_CONFIGURATION=FORBIDDEN
FIRMWARE_EDIT_OR_FLASH=FORBIDDEN
MOTOR_ESC_ARM_DISARM_FLIGHT=FORBIDDEN
```

Capture output must be redacted, timestamped, provenance-labelled and retained
only under an approved policy. Synthetic parser fixtures are not live hardware
evidence.

The current DFM screenshots and procurement record do not satisfy any missing
physical wiring or actuator-isolation prerequisite. No capture authorization
request is eligible yet.
