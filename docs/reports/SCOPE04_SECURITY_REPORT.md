# SCOPE-04 Security Report

Status: `TESTED_ON_PC_MOCK + BOUNDED_PI_SMOKE`; external browser validation:
`NOT_RUN`.

Implemented controls:

- Pi-local identities do not import or federate with PC users.
- Passwords are Argon2-hashed; raw passwords and MFA values are not placed in
  audit events, responses, or reports.
- Session cookies are `HttpOnly`, `Secure` by default, and `SameSite=Strict`.
- Cookie mutation requires a matching CSRF token. Bearer authentication is
  accepted for testable local API access; it is not a PC federation channel.
- MFA failures are bounded and rate limited.
- Camera status/stream/map/telemetry/3D routes require authentication.
- Camera device path is explicit and `/dev/video1` is not guessed as a capture
  device. No raw device path is exposed through a public listener.
- Camera frames are bounded in memory and never persisted by this package.
- Wildcard/public bind is rejected, and no listener is started automatically.
- No ARM/DISARM, motor, relay, firmware, network mutation, or PC-sync route is
  present.

Security limitations requiring later approval: production secret provisioning,
MFA enrollment UX, persistent session store hardening, Pi service account and
systemd sandboxing, TLS/device identity for any PC↔Pi integration, and privacy
retention/legal-hold policy. These are not claimed as complete here.

## Live Pi verification

```text
SECURE_COOKIE_OVER_AP_HTTPS=PASS
PLAIN_HTTP_AP_AUTH=NOT_USED
NO_WILDCARD_LISTENER=PASS
NO_CONTROL_ROUTE=PASS
NO_PC_SYNC_ROUTE=PASS
NO_FIRMWARE_ROUTE=PASS
NO_NETWORK_MUTATION_ROUTE=PASS
NO_CAMERA_PERSISTENCE=PASS
SECRETS_IN_RUNTIME_LOGS=NOT_OBSERVED
```

The listener observed during smoke was exactly `192.168.4.1:8443`; it was
stopped after the bounded foreground test. A real external F450 browser was
not available to verify browser certificate acceptance, so that gate remains
`NOT_RUN`, not PASS.
