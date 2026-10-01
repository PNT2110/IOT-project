# Workspace inventory

Date: 2026-09-30
Status: Phase A — read-first baseline

## Active workspace

| Area | Current location | Technology | Current state |
|---|---|---|---|
| PC API | `server/` | FastAPI, SQLAlchemy, SQLite, Alembic | Active canonical runtime |
| PC Web | `frontend/` | React 19, TypeScript, Vite | Public read-only overview; dashboard/auth integration incomplete |
| Contracts | `contracts/v1/` | Markdown contracts | Documentation contracts; no generated SDK/schema package |
| Tests | `tests/scope01`, `tests/scope02` | Pytest | Current PC auth/RBAC/workflow baseline |
| Architecture/docs | `docs/` | Markdown | Historical scopes plus this architecture review |

## Archived material

The active root no longer contains the previous parallel implementations. The
following are retained under `archive/` for traceability and recovery:

- `archive/legacy-backend/backend/`: serial GPS/ESP32 backend and old dashboard;
- `archive/pi5/pi5/`: Pi network, web, camera and mock telemetry code;
- `archive/pi-deploy/`, `archive/pi-scripts/`: deployment helpers;
- `archive/firmware/FC_can_bang.zip`: ESP32/Arduino firmware snapshot;
- `archive/tests/`: SCOPE03–05 tests and other non-PC tests;
- `archive/project-history/`, `archive/agent-history/`: historical reports and agent records.

This is an archive, not a production dependency. No archived module should be
re-enabled by changing a frontend URL or import path without a migration plan.

## Workspace facts and gaps

- The local workspace has no `.git` directory. Changes cannot currently be
  reviewed or rolled back as commits from this checkout.
- The deployment host has a separate Git checkout at `~/IOT` and the clean
  runtime at `~/iot-pc-server`; these are not yet one reproducible release
  pipeline.
- Runtime secrets and SQLite data are outside the source archive on the host,
  which is correct, but backup/restore automation is not yet defined.
- The current public URL is a temporary quick tunnel. It is suitable for
  bounded testing only, not a Ministry/public production service.
