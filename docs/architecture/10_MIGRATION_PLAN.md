# Migration plan

## Phase A — inventory and baseline (current)

Create architecture reports, record active/archive boundaries and run tests
without changing production behavior. Rollback: delete only the reports.

## Phase B — contracts and module boundaries

Add versioned JSON schemas and adapters for PC-Web, Pi-PC and ESP32-Pi. Keep
legacy implementations behind explicit adapters. Acceptance: contract tests
cover valid, stale, duplicate and unauthorized messages.

## Phase C — PC public gateway hardening

Add production mail abstraction, rate limiting, origin policy, secure session
configuration, structured redacted logs, backup/restore and named HTTPS edge.
Acceptance: security tests and a documented rollback procedure pass.

## Phase D — PC Web product

Implement map rendering, public read-only zones, authenticated zone editor,
account review, role review and simulated flight approval UI. Acceptance:
permissions are enforced by API tests and browser tests.

## Phase E — simulation/realtime

Add `TelemetrySource`, session lifecycle, validated telemetry persistence and
WSS. Acceptance: complete simulator → server → Web path without hardware.

## Phase F — Pi 5 integration

Restore only the needed Pi modules under a new `edge/pi5/` boundary; implement
AP/captive portal, outbound PC client, camera read-only stream and cache.
Acceptance: offline/reconnect behavior and camera privacy controls pass.

## Phase G — ESP32/GNSS integration

Create a firmware build manifest and add GPS parsing/telemetry around the
existing stabilization firmware. Verify GPIO16/17, 38400 baud, NMEA and UBX
on hardware before flashing. Acceptance: GPS loss, checksum errors, stale
fixes and watchdog behavior are safe and observable.

## Phase H/I — end-to-end and public hardening

Run bounded end-to-end tests, review authorization and only then move from
temporary tunnel to named HTTPS infrastructure. Never treat a quick tunnel as
production deployment.
