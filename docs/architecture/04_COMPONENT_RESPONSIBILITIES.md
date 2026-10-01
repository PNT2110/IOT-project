# Component responsibilities

## PC server domains

| Module | Responsibility | Must not own |
|---|---|---|
| `auth` | registration, terms acceptance, email OTP, TOTP, sessions, recovery | device credentials |
| `accounts` | account status, owner/admin/operator review | frontend-only authorization |
| `zones` | public/internal restricted and limited zones, GeoJSON validation, versioning | map tile rendering |
| `flight` | simulated research/flight request state machine and approval records | direct motor/arming commands |
| `devices` | device identity, capability and heartbeat registry | user passwords |
| `telemetry` | validated versioned ingest, ordering, stale/duplicate handling | PID control |
| `audit` | immutable security/workflow history and correlation IDs | raw secrets |
| `transport` | REST/WSS contracts and retry/idempotency policy | business decisions |

## Web feature areas

`public-map`, `auth`, `zone-editor`, `account-review`, `role-review`,
`flight-review`, `device-status`, `telemetry`, `admin` and `shared-ui`.

The server enforces every permission. The Web application only hides or shows
controls for usability.

## Pi 5 feature areas

`network`, `captive-portal`, `server-client`, `camera`, `telemetry`,
`device-auth`, `cache`, `health` and `firmware-update`.

## ESP32/GPS feature areas

`gnss`, `telemetry-frame`, `stabilization`, `watchdog`, `serial-transport` and
`firmware-version`. ESP32 does not decide account roles, zones, permits or
external approvals.
