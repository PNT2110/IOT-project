# CODEX — SCOPE-05 ESP32 Telemetry Preparation

## Status

```text
SCOPE05_REPOSITORY_PREPARATION=PASS
SCOPE05=BLOCKED_NOT_OPENED
SCOPE05_HARDWARE_CAPTURE=BLOCKED
PREPARATION_ONLY=COMPLETE
```

The Owner authorized this repository-only preparation. It does not authorize
hardware access, passive capture or opening the full SCOPE-05 gate.

## Allowed preparation

- Read-only inventory and hash of the existing `FC_can_bang.zip` archive.
- Read-only source audit of board hints, UART/SBUS ownership and actuator paths.
- Synthetic NMEA and UBX fixtures only after the exact protocol/model boundary
  is established.
- Typed `NO_FIX`, checksum-failure, timeout and sequence-gap parser fixtures.
- Reconciliation of the exact board/GNSS datasheet with a redacted wiring and
  pin-ownership record.
- A passive-capture plan and a safety checklist for later review.

## Required entry evidence before model-specific work

- Exact ESP32 board/module and exact GNSS model.
- Authoritative datasheets and electrical-level/power evidence.
- Verified wiring, RX/TX direction and UART ownership, including SBUS
  conflict review.
- Safe bench power arrangement, physical propeller/actuator isolation,
  named supervisor, named stop authority and immediate power-cut method.
- Separate Owner authorization for any passive hardware capture.

## Prohibited

Do not edit or flash firmware, change persistent GNSS configuration, transmit
serial configuration to hardware, send motor/ESC commands, ARM/DISARM, run a
flight test, alter actuator behavior, or open SCOPE-06 or later. Do not infer
board/GNSS identity from GPIO16/GPIO17, approximate baud, NMEA/UBX or update
rate notes without current source, datasheet and wiring evidence.

No secrets, private keys, credentials, raw unnecessary identifiers or
unredacted hardware logs belong in the preparation artifacts.
