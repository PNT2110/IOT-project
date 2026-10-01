# SCOPE-01 — Decisions, conflicts và deviations

**Status:** `BLOCKED_PENDING_OWNER_DECISION`  
**Date:** 2026-09-22

## D-01 — Current repository differs from SCOPE-00 assumptions

| Source | Conflict | Decision for this turn | Impact |
|---|---|---|---|
| `docs/00_PROJECT_OVERVIEW.md`, `03_TECHNOLOGY_DECISIONS.md` | They describe historical backend/frontend code and a dirty worktree with deleted source. Current `HEAD` is docs-only plus `FC_can_bang.zip`; source directories are absent. | Do not restore or infer legacy code. Record actual state in baseline report. | SCOPE-01 cannot extend existing app; a new layout needs explicit confirmation. |

## D-02 — Missing `docs.zip`

The prompt references `docs.zip`, but no such file was found in the repository or attachment search path. The on-disk `docs/` is the only available design source. No core design document was silently replaced.

## D-03 — Missing runtime dependencies

FastAPI, Uvicorn, SQLAlchemy, Argon2 and PyOTP are not importable. Node/npm exist, but no frontend source or package manifest exists. No system/global installation was attempted. Before implementation, the owner must authorize a project-local `.venv`/dependency install and confirm that Python 3.14 is an accepted target, or provide an approved compatible runtime/lockfile.

## D-04 — Layout choice

The proposal is one new PC layout: `server/` for API/domain/persistence/static web integration, `contracts/` for v1 schemas, and `tests/scope01/` for isolated tests. This is not created yet, so no parallel backend has been introduced. A separate `frontend/` tree is not justified until the owner confirms React/Vite dependency setup; a minimal static UI may be served from the approved server layout if that is the selected implementation.

## Decisions required from owner

1. Approve project-local dependency setup (no global install), including Python 3.14 compatibility or an approved alternative runtime.
2. Approve creating the new `server/`, `contracts/` and `tests/scope01/` layout because no source tree exists.
3. Confirm whether SCOPE-01 should implement a static minimal browser UI first or authorize React/TypeScript/Vite dependencies.
4. Confirm whether the existing SCOPE-00 docs are authoritative despite the missing `docs.zip` and their stale repository-state statements.

Until these are resolved, status remains `BLOCKED`; no PASS/production-ready claim is made.

## Continuation resolution — 2026-09-22

The owner approved decisions 1–4 in the continuation prompt. Proceed with one new backend layout under `server/`, React/TypeScript/Vite under `frontend/`, versioned contracts under `contracts/`, and isolated tests under `tests/scope01/`. Use the on-disk `docs/` as design source; do not require the missing `docs.zip`. Keep the historical conflicts recorded above and append implementation deviations rather than rewriting this report.

## Implementation deviations — 2026-09-22

| ID | Decision | Impact |
|---|---|---|
| DEV-01 | The frontend uses a small React SVG demo canvas instead of MapLibre/PMTiles. | Avoids unlicensed/external tiles; pan/zoom is minimal and place search is explicitly deferred. |
| DEV-02 | App startup does not create schema in normal mode; Alembic migration is required. Test app uses `initialize_schema=True` only for isolated temporary DBs. | Prevents silent production schema drift; local run must execute `alembic upgrade head`. |
| DEV-03 | Fake email is an in-memory dev/test sink only. | No real provider integration; browser/manual email flow remains development-only. |
| DEV-04 | `Owner` CLI creates a `PENDING` owner record and does not bypass email verification/MFA. | A complete owner bootstrap requires the approved local flow; account approval remains SCOPE-02. |
| DEV-05 | Browser HTTPS E2E was not run because no trusted local certificate/trust-store change was authorized. | API/test-client evidence is valid; browser secure-cookie behavior remains `BLOCKED/NOT_RUN`. |
| DEV-06 | Frontend `npm audit` initially found a Vite high advisory; Vite was upgraded to `7.3.6`, then audit returned zero vulnerabilities. | Lockfile/build updated; Python dependency audit remains not run. |

## Gate-closure deviations — 2026-09-22T04:28:06+07:00

| ID | Decision | Impact |
|---|---|---|
| DEV-07 | Owner bootstrap now requires an explicit `FAKE_MAIL_OUTBOX` and writes a local test-adapter message; it never prints or bypasses email/TOTP factors. | The local owner path is no longer a dead-end, but this is not real email-provider integration. |
| DEV-08 | Trusted browser E2E uses a one-day CA in a temporary Chrome `HOME/.pki/nssdb` and temporary `certutil`; system trust and personal browser profile are untouched. | Secure-cookie browser evidence is valid for the isolated test profile only. |
| DEV-09 | React auth/dashboard screens were added because the previous UI only exercised the public map and could not meet the browser auth acceptance. | No workflow approval or internal access is granted to `PENDING`. |
| DEV-10 | `httpx2==2.13.0` is pinned for current Starlette TestClient compatibility; the remaining AnyIO alias warning is upstream maintenance debt. | Tests are warning-reduced without a broad dependency upgrade. |
| DEV-11 | No polygon non-overlap rule was invented because the SCOPE-01 contract does not define whether synthetic research layers may overlap. | Overlap policy remains an explicit future domain decision. |
