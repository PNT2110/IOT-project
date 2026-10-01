# SCOPE-02 Policy Amendment — Test report

**STATUS:** `IMPLEMENTED_TESTED_LOCAL_ONLY / PENDING_OWNER_ACCEPTANCE`
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)

## Commands and results

| Command | Exit | Result |
|---|---:|---|
| `.venv/bin/pytest -q tests/scope01 tests/scope02 -W default` | 0 | `22 passed, 0 failed, 1 warning` after amendment tests. |
| `.venv/bin/python -m compileall -q server tests/scope01 tests/scope02` | 0 | PASS. |
| `npm --prefix frontend run typecheck` | 0 | PASS. |
| `npm --prefix frontend run build` | 0 | PASS, Vite `7.3.6`. |
| `.venv/bin/pip check` | 0 | PASS, no broken requirements. |
| `git diff --check` | 0 | PASS. |
| Temporary Alembic `upgrade head → repeat → downgrade 9c4f2d7e6a11 → upgrade head` | 0 | `AMENDMENT_RESTORE_CHECK revision=a71e8c4b2d90 capability_grants=True tables=15`. |

Dependency lockfiles were not changed by this amendment; the prior SCOPE-02 `pip-audit`/npm audit evidence remains applicable and must be rerun before any dependency change.

## Amendment matrix

| Case | Evidence | Result |
|---|---|---|
| Admin without grant denied | `test_admin_requires_owner_grant_and_grant_scope_is_enforced` | PASS |
| Owner grants concrete actions/scope to active Admin | same test, create + idempotent replay | PASS |
| Operator/Admin cannot create grant | same test | PASS |
| Admin activates only verified/MFA-ready pending GUEST | same test | PASS |
| Admin cannot suspend or target out-of-scope account | same test | PASS |
| Admin role approval within grant | `test_granted_admin_can_only_approve_guest_to_admin` | PASS |
| Admin cannot reject/delegate/self-review/Owner elevation | negative route/policy assertions + existing SCOPE-02 tests | PASS |
| Revocation immediately removes capability | grant revoke then mutation denied | PASS |
| Stale grant `If-Match` and idempotency | `test_capability_revoke_is_immediate_and_stale_version_is_safe` | PASS |
| Audit/history transaction | existing history/audit assertions plus grant mutations | PASS |
| Pi identity not mapped to PC reviewer | separate fake Pi contract remains read-only and domain-scoped | PASS |
| SCOPE-01 regression | 13 historical tests | PASS |

## Not run / blocked

No live Pi/SSH/network, real provider, PII sync, public bind or hardware test was run. Browser harness was not rerun after a backend-only capability change in this amendment; existing trusted-browser SCOPE-02 evidence remains valid for the unchanged auth path, while live role-grant browser evidence is `NOT_RUN`. This does not claim the amendment owner-approved.
