# Simulation architecture

Simulation is the safe integration path before Pi/ESP32 hardware.

```text
Simulated GPS/telemetry
          ↓
TelemetrySource adapter
          ↓
PC validation + session store
          ↓
REST/WSS API
          ↓
Web map, status and research-session UI
```

The same high-level interface should later accept `PiSource` and
`ReplaySource`. A simulator must generate timestamped latitude/longitude,
altitude, speed, heading, device health and heartbeat data, including stale,
duplicate, out-of-order and reconnect cases. It must never simulate or enable
real arming/motor authority.
