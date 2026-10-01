# SCOPE-04 Pi Web Contract v1

Status: `PC_REPO_IMPLEMENTED`; live Pi deployment: `NOT_RUN`.

This is a Pi-local, mostly read-only contract. The identity domain is separate from
the PC server. `source=MOCK` is explicit for mock telemetry. Missing values
are `null` and rendered as `UNAVAILABLE`; they are never generated from
random animation or inferred device state.

Implemented read-only routes:

```text
GET  /health
POST /api/pi/v1/auth/challenge
POST /api/pi/v1/auth/email/setup
POST /api/pi/v1/auth/email/verify
POST /api/pi/v1/auth/login
POST /api/pi/v1/auth/register
POST /api/pi/v1/auth/verify-email
POST /api/pi/v1/auth/mfa/enroll    (enrollment bearer token)
POST /api/pi/v1/auth/mfa/confirm   (enrollment bearer token)
GET  /api/pi/v1/auth/me
POST /api/pi/v1/auth/logout          (CSRF protected)
GET  /api/pi/v1/camera/status        (authenticated)
GET  /api/pi/v1/camera/stream        (authenticated, one bounded local frame)
GET  /api/pi/v1/map/cache            (authenticated)
POST /api/pi/v1/map/sync             (authenticated ADMIN + CSRF; optional HTTPS PC public-map fetch)
GET  /api/pi/v1/telemetry            (authenticated)
GET  /api/pi/v1/3d                   (authenticated)
GET  /api/pi/v1/flight-requests     (authenticated; own requests only)
POST /api/pi/v1/flight-requests      (authenticated + CSRF; local recording only)
POST /api/pi/v1/role-requests       (authenticated, CSRF protected)
GET  /api/pi/v1/role-requests       (authenticated ADMIN only)
GET  /api/pi/v1/admin/users         (authenticated ADMIN only, redacted)
POST /api/pi/v1/role-requests/{id}/decision (authenticated ADMIN + CSRF)
```

The login challenge, email setup and registration requests require
`terms_accepted: true`; the Pi web server enforces this before issuing an OTP
challenge or creating an account. The provisioned default account may start
without an email, but its first login is blocked until the authenticated
`auth/email/setup` then `auth/email/verify` flow configures and verifies a
unique email address. A configured SMTP sender delivers the login, email-setup
and registration OTP; the login then requires a second TOTP/2FA code before a
session is issued. Email OTP and TOTP challenges are single-use; in-memory
codes are test-only. When both
`PI_AUTH_DB_PATH` and `PI_DATA_KEY` are configured, identity and role-request
state persists locally and TOTP secrets are stored with authenticated
encryption.

There are deliberately no ARM, DISARM, motor, relay, firmware or public-bind
routes in this contract. The optional map sync is read-only, HTTPS-only and
ADMIN/CSRF protected; it only refreshes the Pi cache. Camera default is `/dev/video0`;
`/dev/video1` is rejected by the adapter because the inventory identifies it
as the metadata node. The PC simulator's camera tab additionally offers an
explicit browser-only `getUserMedia` preview of the laptop webcam. That preview
is local to the browser, is not a camera API source, and is not uploaded to the
Pi simulator; real Pi camera acceptance still requires the V4L2 adapter and
USB device.

The flight-request routes are a local UI/API boundary for validation and test
only. They return `PENDING_PC_REVIEW`,
`PC_AUTHORITY_ADAPTER_NOT_CONFIGURED`, `NOT_A_GOVERNMENT_PERMIT` and
`arm_state=BLOCKED`. They do not contact an external authority, issue a legal
permit, or create an ARM command. A future PC adapter must be designed and
reviewed separately before any production integration.

The Pi web boundary rejects request bodies larger than the configured
`max_request_bytes` limit (1 MiB by default) and emits same-origin isolation
headers (`Cross-Origin-Resource-Policy`, `Cross-Origin-Opener-Policy` and
`X-Permitted-Cross-Domain-Policies`). These controls are part of the local
simulator contract and must be preserved by a production reverse proxy.
### Firmware safety boundary

The Pi web contract exposes firmware status as read-only UI only. Firmware update remains unavailable until the deployment provides a signed artifact, device identity verification, and rollback evidence. No API route may arm, flash, or otherwise write firmware to an ESP32 in the current scope.
