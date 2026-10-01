# SCOPE-00 — Test strategy

## Test layers

1. Unit: schema validation, state transitions, RBAC predicates, provenance and stale computation.
2. Contract: OpenAPI/JSON fixtures, error envelopes, version/units/sequence behavior.
3. Integration: SQLite migration/rollback, fake email, fake NetworkManager, fake camera, synthetic serial frames.
4. E2E local: browser Guest/Pending/Admin workflows and offline transitions.
5. Hardware later: passive read-only inventory/capture only after safety approval; never substitute synthetic PASS for hardware evidence.
6. Security: OWASP-aligned auth/session/CSRF/IDOR/rate-limit/secrets/log tests; dependency audit before public gate.

## Negative/boundary cases

- expired/replayed OTP/TOTP/recovery code; rate limit and session fixation;
- stale map/cache, invalid CRS/order, missing provenance, unauthorized object id;
- duplicate idempotency key with changed body;
- `external_wifi_connected=true` while Internet/server false;
- email offline, PC offline, GNSS `NO_FIX`, malformed frame/checksum, sequence gap;
- unknown telemetry fields, impossible units/range, oversized payload;
- simulated approval cannot expose or serialize actuator command fields.

## Evidence

Record command, environment, fixture hash, timestamp, result, log path and redaction status. Reports use `PASS`, `FAIL`, `NOT_RUN`, `BLOCKED`; “not run” is never silently converted to pass.
