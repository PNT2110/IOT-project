# SCOPE-01 — PC Server Foundation

## 1. Mục tiêu

Local-only PC foundation: auth/RBAC, simulated map data, versioned API, audit and tests.

## 2. Preconditions/status

Owner approval of SCOPE-00; actual OS/runtime/repo status checked; clean working plan that preserves dirty changes; no public bind. `BLOCKED` if any missing.

## 3. In/out

In: FastAPI/React baseline, SQLite migrations, fake email, Guest/Pending/Admin/Owner policy, public/internal zone fixture. Out: Pi, real email/legal source, public deploy, workflow approval, actuator/firmware.

## 4. Dependencies

`01`, `03`, `05`, `08–11`, `CODEX_IMPLEMENTATION_RULES`; approved runtime and test runner.

## 5. Applied decisions

ADR-001–005; SQLite local and PostGIS gate; no SSO; GeoJSON WGS84.

## 6. Files

Create only approved server/contracts/tests files after inventory. Do not modify `FC_can_bang.zip`, firmware, Pi/deploy scripts or unrelated dirty files.

## 7. Tasks

1. Inspect status/runtime and record plan. 2. Create migrations/entities. 3. Implement auth/session/RBAC with fake email. 4. Implement map public/internal filtering and provenance. 5. Implement error envelope/audit. 6. Add tests and local run instructions.

## 8. Contracts/errors

Use `09_API_CONTRACTS.md`; return safe 401/403/404/409/422/429 errors; idempotency and `If-Match` for mutations.

## 9. Security/privacy

Argon2id, MFA staging, CSRF, rate limits, cookie flags, no secrets in logs, simulated labels.

## 10. Tests

Unit/contract/integration; unauthorized object access, duplicate keys, stale/invalid GeoJSON, fake email unavailable, secret scan.

## 11. Acceptance

Local bind only; Guest sees public fixture only; Admin mutation audited; tests reproducible; no actuator field/path; all reports classify outcomes.

## 12. Evidence

Commands, versions, test output, migration checksum, redacted screenshots/logs.

## 13. Rollback

Stop services, restore pre-scope files by manifest or revert only own changes with approval; preserve reports/evidence.

## 14. DoD/gate

Owner approves local foundation and opens SCOPE-02; otherwise `BLOCKED`.
