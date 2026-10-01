# SCOPE-00 — Database design

## Storage decision

SCOPE-01 local-only: SQLite, foreign keys, migrations, audit table and deterministic fixtures. Geometry is validated GeoJSON with canonical WGS84 coordinates. Before multi-user/public deployment, benchmark and migrate to PostgreSQL/PostGIS; do not infer SQLite concurrency or spatial accuracy from unrun tests.

## Logical entities

| Entity | Key fields | Privacy/retention |
|---|---|---|
| `user_account` | id, email_normalized, display_name, status, role, verified_at | PII; retention policy pending. |
| `credential` | user_id, password_hash, totp_secret_encrypted, version | never expose secrets; encrypted/hashed as applicable. |
| `recovery_code` | user_id, code_hash, used_at | one-time hash only. |
| `session` | id/hash, user_id, created/last_seen/expires, MFA level | revoke on password/MFA change. |
| `zone` | id, visibility, geometry, source_id, effective_at, version, status | public/internal separation. |
| `zone_source` | id, publisher, URL, license, retrieved_at, checksum | provenance, no assumed legal authority. |
| `flight_request` | idempotency_key, applicant, itinerary, status, simulated flag | PII; every transition audited. |
| `telemetry_sample` | device_id, seq, observed_at, received_at, fields, stale | minimize; raw retention pending. |
| `audit_event` | actor, action, object, outcome, request_id, redacted metadata | append-only; no secret payload. |
| `device_identity` | device_id, cert/key reference, status, rotated_at | PC↔Pi only; no default shared key. |

## Invariants

- Every zone has `source_id`, `version`, `visibility`, `retrieved_at`; `legal_status` is never inferred from `visibility`.
- Every workflow transition requires current state, actor policy, reason and audit event.
- Every telemetry field has units/availability; missing is `UNAVAILABLE`, not zero.
- A `flight_request` may reach only `SIMULATED_APPROVED`/`SIMULATED_REJECTED`, never an actuator state.
- Store timestamps in UTC; include timezone at API boundary.

## Migration/backup

Migration is forward-only with tested rollback snapshot. Backup must include schema version and checksum; restore test is required before SCOPE-08. Deletion/cleanup must use an explicit retention manifest and never delete evidence/source data implicitly.
