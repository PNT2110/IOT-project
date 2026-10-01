# Communication contracts

## Existing vs target

| Link | Target transport | Evidence status |
|---|---|---|
| Browser → PC | HTTPS REST | **Observed in code:** canonical API routes are implemented; **partial:** Web UI only consumes health/public zones |
| Browser → PC realtime | WSS | **Not implemented in canonical tree:** old implementation is archived |
| Pi → PC | outbound HTTPS/WSS | **Not present in active tree:** only mock fake-Pi read endpoints exist |
| Pi → ESP32/GPS | serial/UART | **Not present in active tree:** serial/GPS abstractions exist only in archive |
| PC → external authority | HTTPS signed request/webhook | **Proposed target only:** use a simulated adapter first |

The labels above are deliberate: “observed in code” means verified from the
current source tree, “not present” means no active implementation was found,
and “proposed target only” means architecture guidance, not a working feature.

## Versioned device envelope

All future device messages should include a stable envelope similar to:

```json
{
  "version": 1,
  "device_id": "device-id",
  "timestamp": "2026-01-01T00:00:00Z",
  "sequence": 123,
  "type": "telemetry.gnss",
  "payload": {}
}
```

The contract must define producer, consumer, authentication, payload schema,
retry/backoff, duplicate/out-of-order behavior and stale thresholds. Do not
change every legacy format in one rewrite; introduce adapters at the boundary.

## GPS facts to preserve for the next hardware scope

- GPS UART is reported on GPIO16/17 (RX/TX).
- Baud rate is 38400 bps.
- Expected protocols are NMEA 0183 v4.0/v4.1 and optionally UBX.
- Pin ownership and electrical level still require a physical verification on
  the connected Pi/ESP32 before writing firmware or flashing anything.
