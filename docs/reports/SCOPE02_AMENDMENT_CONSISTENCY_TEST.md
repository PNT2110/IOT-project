# SCOPE-02 Amendment Consistency — Test Report

**STATUS: `PASS_PC_LOCAL_ONLY_PENDING_OWNER_ACCEPTANCE`**  
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)  
**Implementation:** [SCOPE02_AMENDMENT_CONSISTENCY_IMPLEMENTATION.md](SCOPE02_AMENDMENT_CONSISTENCY_IMPLEMENTATION.md)

## Commands and results from this corrective turn

| Command | Exit | Result |
|---|---:|---|
| `.venv/bin/pytest -q tests/scope02 -W default` | 0 | `11 passed, 1 warning` |
| `.venv/bin/pytest -q tests/scope01 tests/scope02 tests/scope03 -W default` | 0 | `31 passed, 1 warning` |
| `.venv/bin/python -m compileall -q server pi5 tests/scope01 tests/scope02 tests/scope03` | 0 | PASS |
| `npm --prefix frontend run typecheck` | 0 | PASS |
| `npm --prefix frontend run build` | 0 | PASS; Vite `7.3.6`, 30 modules transformed |
| `.venv/bin/pip check` | 0 | PASS; no broken requirements |
| `.venv/bin/pip-audit -r server/requirements.lock --format columns` | 0 | PASS; no known vulnerabilities found |
| `npm --prefix frontend audit --omit=dev --audit-level=high` | 0 | PASS; 0 vulnerabilities |
| `git diff --check` | 0 | PASS |
| Temporary SQLite Alembic cycle: `upgrade head → inspect → downgrade 9c4f2d7e6a11 → inspect → upgrade head → inspect` | 0 | PASS; `capability_grants` created, removed, then restored at `a71e8c4b2d90` |

The only warning is the upstream Starlette/AnyIO `BlockingPortal` deprecation from `.venv/lib/python3.14/site-packages/starlette/testclient.py:53`; it is not a SCOPE-02 failure.

## Corrective coverage

| Case | Test/evidence | Result |
|---|---|---|
| Admin without grant cannot account-approve or role-review | `test_admin_requires_owner_grant_and_grant_scope_is_enforced`; `test_review_responses_expose_effective_scope_and_not_owner_only` | PASS; mutation/review denied and metadata reports `NONE` |
| Owner response and granted Admin response are policy-consistent | `test_review_responses_expose_effective_scope_and_not_owner_only` | PASS; both use `OWNER_OR_GRANTED_ADMIN_SCOPED` with distinct scopes |
| Account list/detail expose effective scope | same test | PASS |
| Delegated Admin role list filters ineligible target | `test_granted_admin_can_only_approve_guest_to_admin` | PASS; operator target is not listed and decision is 403 |
| Admin approval action is exact and approval-only | same test | PASS |
| Self-review and explicit Owner elevation blocked without side effect | `test_role_self_review_and_owner_elevation_are_rejected_without_side_effect` | PASS; 403/422 and request remains pending |
| Admin/operator cannot create grants; Owner grant/revoke is immediate | `test_admin_requires_owner_grant_and_grant_scope_is_enforced` | PASS |
| Audit/history for grant revoke | same test | PASS; rows present after the mutation |
| Stale `If-Match`, idempotency and session revocation | amendment and SCOPE-02 regression tests | PASS |
| SCOPE-01/02/03 regression and no actuator route | combined suite, compile and existing contract tests | PASS |

No Pi/SSH/console, live network, public bind, external probe, hardware, PII exchange or real provider was used.
