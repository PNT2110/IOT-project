# SCOPE-01 — Test report

**STATUS:** `NOT_RUN` / `BLOCKED`  
**Reason:** no application source or selected dependency environment exists; running a test command would not test SCOPE-01.

## Baseline checks performed

| Check | Result | Evidence |
|---|---|---|
| Repository root/branch/HEAD | `PASS` | `/home/pnt/IOT`, `main`, `16dc418…` in baseline report. |
| Write permission | `PASS` | Root and `docs/` writable. |
| Python/Node presence | `PASS` | Python 3.14.7; Node 22.22.1; npm 9.2.0. |
| FastAPI/Uvicorn/SQLAlchemy | `BLOCKED` | Imports unavailable. |
| Argon2/PyOTP | `BLOCKED` | Imports unavailable; auth cannot be claimed safe. |
| Source tree | `BLOCKED` | No `backend/`, `frontend/`, `server/`, `contracts/`, `tests/` on disk. |
| Server test | `NOT_RUN` | No server exists; no process started. |
| Browser E2E | `BLOCKED` | No UI and no local HTTPS setup. |

## Required rerun after unblock

Run only in project-local environment with loopback binding: migration clean/upgrade/restore tests; auth fake-mail/MFA/session/CSRF/rate-limit tests; RBAC/IDOR matrix; GeoJSON validation/public DTO isolation; audit/version conflicts; secret scan; API contract/OpenAPI checks; browser E2E with trusted local HTTPS. Record exact commands, exit codes and counts. `SKIPPED`/`NOT_RUN` must not become `PASS`.

## Continuation execution evidence — 2026-09-22

| Command/check | Result |
|---|---|
| `.venv/bin/python -m compileall -q server tests/scope01` | `PASS` |
| `.venv/bin/pytest -q tests/scope01` | `PASS` — 8 passed; 2 dependency deprecation warnings from Starlette/TestClient. |
| Alembic clean `upgrade head` | `PASS` — revision `380891b589d3`. |
| Alembic repeated `upgrade head` | `PASS` — idempotent no-op. |
| Alembic `downgrade base` then `upgrade head` on temp DB | `PASS` — schema recreated. |
| Copy/restore temp DB backup and verify schema | `PASS` — revision `380891b589d3` restored. |
| `npm --prefix frontend run typecheck` | `PASS`. |
| `npm --prefix frontend run build` | `PASS` — Vite `7.3.6`. |
| `npm --prefix frontend audit --omit=dev --audit-level=high` | `PASS` — 0 vulnerabilities after Vite upgrade. |
| Uvicorn smoke on `127.0.0.1:8765` + `/api/v1/health` | `PASS`; response `local_only=true`, request ID present. |
| Uvicorn `/api/v1/public/zones` | `PASS`; one public synthetic fixture and explicit simulated label. |
| Loopback/listening inspection | `PASS`; app listened on `127.0.0.1:8765`, not `0.0.0.0`. |
| Browser E2E with trusted local HTTPS | `BLOCKED/NOT_RUN`; no certificate/trust-store change was authorized. |
| Python dependency vulnerability audit | `NOT_RUN`; `pip-audit` is not installed in the project environment. |

No test used Pi, ESP32, GNSS, webcam, external email, public Internet binding or real airspace data.

## Gate-closure execution addendum — 2026-09-22T04:28:06+07:00

| Command/check | Result |
|---|---|
| `.venv/bin/pytest -q tests/scope01 -W default` | `PASS` — 13 passed, 1 upstream AnyIO deprecation warning |
| `.venv/bin/python -m compileall -q server tests/scope01` | `PASS` |
| `pip-audit 2.10.1 -r server/requirements.lock` | `PASS` — no known vulnerabilities |
| `npm audit --audit-level=high` | `PASS` — 0 vulnerabilities including dev dependencies |
| `npm audit --omit=dev --audit-level=high` | `PASS` — 0 production vulnerabilities |
| Trusted Chrome HTTPS E2E | `PASS` — exit `0`, isolated CA/NSS test home, no certificate bypass; screenshot retained under `/tmp/scope01-browser-e2e-qlpvqx66/` |
| Owner bootstrap API path | `PASS` — CLI pending owner → fake verification mail → TOTP → authenticated `OWNER/PENDING` session |
| CSRF/OTP/TOTP/session/RBAC negative tests | `PASS` — expanded test suite |
| Alembic upgrade/repeat/downgrade/restore | `PASS` — restored revision `380891b589d3` on temp DB |
| Frontend typecheck/build | `PASS` — Vite `7.3.6` |
| Loopback smoke | `PASS` — health/public zones; `127.0.0.1:8765` only; clean teardown |
| Route/control/secret/diff scans | `PASS` |

The only remaining warning is upstream Starlette `1.6.0` use of the deprecated AnyIO `BlockingPortal` alias. It does not alter the application behavior tested here and is recorded as dependency maintenance debt.
