# Requirements matrix

This matrix translates the requested product scope into verifiable work. It
also separates what is working today from design-only items, so a temporary
public demo is not mistaken for a production Ministry-style system.

| Area | Requested outcome | Current evidence | Status | Next verification |
|---|---|---|---|---|
| PC server | Public API, health, public map zones | FastAPI public runtime, security headers, auth/RBAC, bounded auth rate-limit and quick-tunnel checks | Partial | Replace temporary tunnel with a permanent HTTPS edge and immutable deployment revision |
| Public web | Unauthenticated users see map/zones only | React/Vite shell renders Leaflet/OpenStreetMap, read-only tools, auth modal and an empty production map until zones are published | Partial | Verify owner-created source/zone through the public deployment |
| Zone management | Operator/Admin can create/edit/delete no-fly and restricted zones; Owner controls source provenance | Owner source registration, click-to-draw/edit UI, GeoJSON validation, version guard and audit are implemented | Partial | Run authenticated owner acceptance on the deployed PC |
| Account workflow | Register, email OTP, TOTP/2FA, approval and roles | UI is wired to real SMTP, staged email OTP plus mandatory TOTP login, recovery codes, role-elevation request/review, rate limits and server RBAC | Partial | Bootstrap the first Owner and run a complete production-mail flow |
| Approval workflow | Review flight requests and account elevation | Full internal request form, encrypted sensitive details, simulated state machine and review UI are implemented | Partial | Add authenticated acceptance and keep external-authority adapter separate |
| Pi 5 network | AP/captive portal and outbound PC connection | Edge package is separated, but AP/STA and captive-portal deployment is not wired or live-verified | Partial | Inventory the real Pi image and validate the approved AP/STA profile |
| Pi 5 camera | USB webcam view after login | Authenticated read-only camera status/frame route with mock/V4L2 adapters; live USB device unverified | Partial | Verify camera device, permissions and bounded stream on the Pi |
| Pi 5 dashboard | Map, telemetry, activity, admin and firmware tabs | Active edge dashboard has camera, map cache, telemetry/3D, local flight-request form and locked admin surfaces; optional encrypted SQLite identity/role persistence is implemented, while live device identity and firmware workflow are absent | Partial | Configure persistence on the Pi and validate the dashboard on hardware |
| ESP32 flight controller | Preserve balance controller and add GNSS input | Firmware snapshot is archived; no active firmware tree or flash evidence | Not implemented | Inspect the exact board/pin wiring, add a safe GNSS parser task, bench-test without motors, then record a firmware hash |
| GPS | GPIO16/17, 38400, NMEA/UBX | User-provided hardware facts; not verified on device | Unverified | Read UART on the actual connected hardware and capture parser/quality evidence |
| Telemetry | Barometer, attitude, battery, temperature, GPS and 3D state | No active device telemetry contract/model | Design only | Freeze versioned envelope and add simulator/replay tests before hardware integration |
| Flight safety | Approval gates arm; rejection prevents arm | No active hardware arm path in canonical server | Safety-critical missing | Keep simulation-only until signed command, failsafe and hardware-in-loop evidence exist |
| Firmware update | Manufacturer firmware update tab | No active implementation | Not implemented | Define signed artifact manifest, authorization, rollback and device recovery procedure |
| Tests | Clean reproducible local and deployment checks | Local suite covers the canonical PC internal flight contract, bounded HTTPS PC→Pi map synchronization, Pi local simulator flow, Pi flight-request validation and ARM-blocked boundary, malformed JSON envelope handling, Pi default-account email setup and email/login challenge rate limits, mandatory Pi TOTP login and replay rejection, SMTP login-OTP delivery/rollback, server-enforced terms acknowledgement, request-size and security-header checks, credentialed-CORS wildcard rejection, atomic OTP/recovery-code consumption and monotonic TOTP replay protection, client registration rate limiting, encrypted Pi SQLite identity/role persistence, Pi email-OTP/TOTP registration, SMTP rollback, redacted Admin user listing, auth/camera/read-only/RBAC/CSRF gates, session-bound login OTP regression, public-mode fixture isolation and explicit fake-adapter gating; frontend typecheck/build remain separate checks | Partial | Tie deployment to immutable revision and add authenticated production acceptance |
| Documentation | Easy future updates and handoff | README plus architecture docs 01–14 | Present for Phase A | Keep docs synchronized whenever a contract or deployment changes |

## Explicit boundary for the current phase

The current PC phase is an operational simulation boundary, not a claim that
Pi 5, ESP32/GPS, real external approval, firmware update, or hardware arm
control are complete. Those parts must be implemented and tested in later
phases with dangerous actions disabled by default.
