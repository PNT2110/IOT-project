# SCOPE-01 — Final report

## Status

`PARTIAL`

P1–P4 implementation and local/API/build tests completed in the approved new layout. The remaining important gate is browser E2E over trusted local HTTPS; it is explicitly `BLOCKED/NOT_RUN`, so this is not production-ready and not a full SCOPE-01 PASS.

## Traceability

| Requirement group | Implementation | Test | Status |
|---|---|---|---|
| Auth/RBAC/MFA | `server/app/api.py`, `security.py`, models | 8 pytest tests; browser E2E blocked | `PARTIAL` |
| Public/internal demo map | `server/app/geo.py`, zone routes, React UI | public isolation/RBAC/geometry tests | `PASS` for API/UI build |
| SQLite migrations/audit | `server/migrations/`, SQLAlchemy models | Alembic upgrade/downgrade/restore checks | `PASS` |
| Local-only API/UI | `server/app/main.py`, `frontend/` | loopback Uvicorn smoke, typecheck/build | `PASS` |
| No actuator path | route/OpenAPI scan and source boundary | test asserts no Pi/ARM/DISARM route | `PASS` |

## Rollback

Rollback is limited to files created by this continuation: remove the new `server/`, `frontend/`, `contracts/`, `tests/scope01/`, root README/config and generated local runtime artifacts after owner review. Existing docs, archive and unrelated files were preserved. No commit or push was made by this attempt.

## Remaining blockers

- Trusted local HTTPS/browser E2E has not run; secure-cookie behavior is not claimed browser-verified.
- Python dependency vulnerability audit was not run because `pip-audit` was not installed; npm production audit is clean.
- Two Starlette/TestClient deprecation warnings remain; they do not fail tests but should be reviewed before hardening.

## Next gate

`WAIT FOR OWNER ACCEPTANCE; DO NOT START SCOPE-02.`

## Gate-closure continuation addendum — 2026-09-22T04:28:06+07:00

The prior `PARTIAL` header is historical and remains unchanged. The continuation closed the two previously missing gates: trusted local HTTPS browser E2E and Python dependency audit. It also added the browser auth/dashboard path, Owner bootstrap fake-mail outbox path, TOTP limiter, persisted OTP-attempt limiting, logout CSRF enforcement and regression tests.

Current mandatory SCOPE-01 result: `PASS`.

Evidence and exact commands are consolidated in [SCOPE01_GATE_CLOSURE_REPORT.md](SCOPE01_GATE_CLOSURE_REPORT.md). The result is still local-only and does not approve account workflow, Pi integration, firmware, real airspace data or public deployment. SCOPE-02 remains locked pending owner acceptance.
