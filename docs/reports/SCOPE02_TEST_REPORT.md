# SCOPE-02 — Test report

**STATUS:** `PASS` cho local-only SCOPE-02; các phần ngoài scope là `NOT_RUN/DEFERRED_BY_SCOPE`.
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)

## Automated results

| Command | Exit | Result / evidence |
|---|---:|---|
| `.venv/bin/pytest -q tests/scope02 -W default` | 0 | `6 passed, 1 warning`; account/RBAC, role elevation, state machine, stale/IDOR, history, fake Pi. |
| `.venv/bin/pytest -q tests/scope01 -W default` | 0 | `13 passed, 1 warning`; SCOPE-01 auth/MFA/map/RBAC regression. |
| `.venv/bin/pytest -q tests/scope01 tests/scope02 -W default` | 0 | `19 passed, 1 warning`; combined regression. |
| `.venv/bin/python -m compileall -q server tests/scope01 tests/scope02` | 0 | Python source compiles. |
| `npm --prefix frontend run typecheck` | 0 | TypeScript check PASS. |
| `npm --prefix frontend run build` | 0 | Vite `7.3.6` production build PASS. |
| `.venv/bin/pip check` | 0 | `No broken requirements found.` |
| `.venv/bin/pip-audit -r server/requirements.lock --format columns` | 0 | `No known vulnerabilities found`. |
| `npm --prefix frontend audit --omit=dev --audit-level=high` | 0 | `found 0 vulnerabilities`. |
| `git diff --check` | 0 | Whitespace check PASS. |
| Trusted browser harness `SCOPE01_CERTUTIL=… SCOPE01_CHROME=/usr/bin/google-chrome .venv/bin/python tests/scope01/browser_e2e.py` | 0 | `PASS`; screenshot `/tmp/scope01-browser-e2e-ynx60nu0/scope01-authenticated-dashboard.png`; isolated CA/NSS profile, no certificate bypass. |

## Migration/restore evidence

On a temporary SQLite database: `alembic upgrade head` → repeat upgrade no-op → `downgrade 380891b589d3` → `upgrade head`. Verification printed `RESTORE_CHECK revision=9c4f2d7e6a11 tables=14`. No repository DB artifact was created and no user database was downgraded.

## Coverage matrix

| Requirement | Evidence | Result |
|---|---|---|
| Guest/PENDING blocked from internal workflow | SCOPE-01 pending regression; SCOPE-02 pending role test | PASS |
| Owner bootstrap does not bypass email/MFA | SCOPE-01 owner bootstrap test; CLI procedure remains pending until explicit local operation | PASS / operational gate documented |
| Admin rights and Operator boundary | `test_account_review_policy_status_version_and_session_revoke` | PASS |
| Self-review/self-elevation protection | account, role and flight negative assertions | PASS |
| Suspend/reject session revocation | target session gets `401`, DB `revoked_at` set | PASS |
| Valid/invalid workflow transitions | full happy path plus stale review | PASS |
| Concurrent/stale reviewer | second review with old version returns `409` | PASS |
| Idempotent duplicate and key reuse mismatch | create/replay returns same object; changed body returns `409` | PASS |
| Atomic audit/history and redaction | counts match mutations; history excludes secret/hash indicators | PASS |
| IDOR/object scope | other user gets `404`; fake Pi status is caller-scoped | PASS |
| Synthetic geometry/time validation | Pydantic timezone/order and existing GeoJSON validator | PASS |
| Fake Pi read-only/offline | identity header, map/status GET, `UNSYNCED`/`stale`; OpenAPI route inventory | PASS |
| No external provider | no network client/provider added; offline path is local response | PASS |
| Loopback/no leaked secret | browser runner and static scans; no private key or literal secret assignment | PASS |

## Warning and not-run classification

The one test warning is upstream Starlette use of the deprecated AnyIO `BlockingPortal` alias; it did not alter results. No Pi/SSH/webcam/GNSS/ESP32/firmware/hardware test, real email/OTP provider, official map/authority API, public bind, load benchmark, PostGIS concurrency test or production TLS test was run; each is outside SCOPE-02 and not represented as PASS.
