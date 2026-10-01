# SCOPE-05 Read-only Telemetry Contract v1

Status: `REPOSITORY_PREPARATION_ONLY`; hardware compatibility:
`BLOCKED_NOT_OPENED`.

The preparation adapter consumes supplied NMEA/UBX bytes only. It has no serial
device dependency, no write/configuration operation and no command field. The
current implementation is synthetic/model-agnostic scaffolding; it does not
claim that the unknown physical GNSS module supports NMEA or UBX.

## Envelope

```json
{
  "source": "SYNTHETIC:nmea",
  "source_type": "SYNTHETIC",
  "parser": "nmea-gga",
  "schema_version": "scope05.telemetry.v1",
  "capture_timestamp": "2026-09-26T00:00:00Z",
  "sample_timestamp": "2026-09-26T00:00:00Z",
  "sequence": 1,
  "stale": false,
  "fix_state": "VALID_FIX",
  "availability": "AVAILABLE",
  "latitude": 10.0,
  "longitude": 106.0,
  "altitude_m": 12.3,
  "hdop": 0.9,
  "accuracy_m": null,
  "error_code": null
}
```

Fixture coordinates are synthetic and are not a physical position. Unknown
fields remain `null`/`UNAVAILABLE`; they are never replaced with zero or a
guess.

## States

`VALID_FIX`, `NO_FIX`, `STALE`, `TIMEOUT`, `BAD_CHECKSUM`, `MALFORMED`,
`SEQUENCE_GAP`, `UNAVAILABLE` and `UNSUPPORTED_MESSAGE` are explicit states.

Future passive hardware capture must use `source_type=PASSIVE_HARDWARE_CAPTURE`
only after separate hardware authorization. No `arm`, `disarm`, motor, ESC,
actuator, flight or serial-write field is part of this contract.
