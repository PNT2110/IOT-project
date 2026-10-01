# SCOPE-02 — Implementation report

**STATUS:** `IMPLEMENTED_LOCAL_ONLY`
**Repository:** `/home/pnt/IOT` · branch `main` · HEAD baseline `16dc418076b1a53a9d2fc9af482e3a514f0791f7`
**Boundary:** PC local only; no Pi/SSH/firmware/hardware/public network/external provider.

## Task → file → result

| Task | Files | Result |
|---|---|---|
| S02-P0 baseline | `docs/reports/SCOPE02_BASELINE_REPORT.md` | Current branch/HEAD/dirty state/runtime/DB/ports/source manifest recorded before code changes. |
| S02-P1 domain schema | `server/app/models.py`, `server/app/schemas.py` | Account version, role elevation, simulated flight request, idempotency and workflow history entities; enum/check/FK/index constraints. |
| S02-P1 migration | `server/migrations/versions/9c4f2d7e6a11_scope02_workflow.py` | Forward Alembic revision from `380891b589d3`; downgrade supports temporary restore test. |
| S02-P2 account review | `server/app/api.py`, `server/app/services.py` | Paginated owner/admin read, owner-only status mutation, valid transitions, `If-Match`, no self-review, session revocation and atomic audit/history. |
| S02-P2 role elevation | `server/app/api.py`, `server/app/services.py` | Own request, duplicate-open prevention, owner-only decision, no Owner target, replay/key-reuse/version guards, audit/history. |
| S02-P2 simulated workflow | `server/app/api.py`, `server/app/services.py` | `DRAFT → SUBMITTED → UNDER_REVIEW → NEEDS_INFORMATION/REJECTED/APPROVED_SIMULATED`; resubmit path, object ownership, edit/version/idempotency and mandatory simulated label. |
| S02-P2 bootstrap gate | `server/cli.py` | Explicit local `activate-bootstrap-owner` procedure requiring confirmation, existing password and current TOTP; no HTTP self-activation. |
| S02-P2 fake Pi API | `server/app/api.py` | `GET /api/v1/pi/v1/map` and `/status`, active-session + fake-client identity, object scope, offline/stale response, no write route. |
| S02-P3 contracts/docs | `contracts/v1/README.md`, `docs/09_API_CONTRACTS.md`, `docs/10_AUTHENTICATION_RBAC.md`, `server/README.md`, reports | v1 envelope/state/RBAC/offline/rollback policy documented; no legal or external-provider claim. |
| S02-P3 UI | `frontend/src/api.ts`, `frontend/src/App.tsx`, `frontend/src/styles.css` | Role-sensitive account/role/workflow tabs, authoritative error display, offline unsynced text, persistent simulated banner; no new map tiles/search. |
| S02-P4 tests | `tests/scope02/`, adjusted `tests/scope01/test_health_and_contracts.py` | Six focused tests plus 13 SCOPE-01 regression tests; read-only Pi routes are now the approved SCOPE-02 contract. |

## Data and transaction guarantees

Mutation routes add `AuditEvent` and `WorkflowHistory` in the same SQLAlchemy transaction as the state change. Idempotency records store only a SHA-256 digest and redacted response DTO; secrets, hashes, OTP/TOTP data and full request bodies are not returned or logged. History responses are object-authorized and marked redacted.

## Rollback

For a local rollback, stop local services, preserve the reports/evidence, restore a verified temporary DB snapshot or run the SCOPE-02 Alembic downgrade on a copy, and revert only SCOPE-02 paths after owner approval. No destructive rollback command was run. The migration downgrade was tested on a temporary database, not on user data.

## Known limits

- SQLite remains a local prototype store; production concurrency/PostgreSQL/PostGIS are not claimed.
- Fake mail remains fake; Pi API remains a fake client contract; no external service was contacted.
- TOTP failure limiting remains process-local from SCOPE-01.
- Account retention, legal hold, and expanded UX policy remain owner decisions before later integration/deployment scopes.
