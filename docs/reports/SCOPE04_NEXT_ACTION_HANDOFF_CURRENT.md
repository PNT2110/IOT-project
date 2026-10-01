# SCOPE-04 Current Next-Action Handoff

Status: `SCOPE04=PASS`

The final offline-local hard gate is closed by
`SCOPE04_OFFLINE_LOCAL_LIVE_REPORT.md`, and the Owner has accepted the final
packet. SCOPE-04 is closed at the bounded prototype boundary. Do not rerun N4
automatically and do not treat this acceptance as SCOPE-05 authorization.

```text
SCOPE03_N4=DO_NOT_RERUN
SCOPE04_NETWORK_CHANGE=BOUNDED_STA_DOWN_UP_ONLY
SCOPE04_EXTERNAL_BROWSER=OPTIONAL_NOT_RUN
SCOPE04_SYSTEMD=DEFERRED
SCOPE04_OWNER_ACCEPTANCE=ACCEPTED
SCOPE05=BLOCKED_NOT_OPENED
SCOPE05_PLUS=NOT_AUTHORIZED

## Completed SCOPE-04 requirements

See `SCOPE04_FINAL_REPORT_CURRENT.md` and the linked live/offline evidence
reports. The hard gates are accepted as recorded in the current owner packet.

## Optional operational hardening

External browser validation, persistent systemd/autostart, persistent auth
storage and production certificate trust remain optional/deferred.

## Deferred later-scope requirements

PC↔Pi TLS/device identity, protected persistence/retention/legal hold and all
ESP32/GNSS, actuator, firmware, flight-control or public-deployment work remain
outside this handoff.
```
