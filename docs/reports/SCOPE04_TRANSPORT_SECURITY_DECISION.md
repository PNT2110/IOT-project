# SCOPE-04 Transport Security Decision

Captured: `2026-09-25T21:18:56+07:00` (Asia/Ho_Chi_Minh)

## Decision

```text
TRANSPORT_OPTION= A — local HTTPS on the approved AP address
AP_BIND_ADDRESS=192.168.4.1
AP_PORT=8443
COOKIE_SECURE=true
HTTP_PLAIN_AP_AUTH=NOT_USED
```

The repository implementation keeps secure cookies enabled by default. It is
not being weakened to make plain HTTP browser authentication pass.

## Observed preflight

- `openssl` exists on the Pi: OpenSSL 3.5.7.
- No listener was present on ports 8080 or 8443.
- The AP address is `192.168.4.1/24` and `f450-ap.service` is active.
- The approved deployment permits a Pi-local self-signed test certificate,
  with its private key remaining on the Pi and no trust-store change.

## Limits

The deployment may create a Pi-local certificate/key and bind the app to
`192.168.4.1:8443`. A real external F450 client/browser is not assumed by
this decision; if it is unavailable during smoke, the AP browser gate remains
`NOT_RUN` or `BLOCKED_TRANSPORT_DECISION`. No plain-HTTP AP auth PASS may be
claimed.
