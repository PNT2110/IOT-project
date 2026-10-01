# Test baseline

Date: 2026-09-30

Revision identity: this workspace has no local Git repository. The deployment
checks below were run against the deployed source snapshot, but a commit hash
or generated source manifest was not captured. Treat them as deployment
evidence, not as a reproducible release baseline, until the source and remote
artifact are tied to an immutable revision.

| Check | Environment | Result |
|---|---|---|
| `python -m compileall -q server` | Local Windows workspace | PASS |
| `python -m pytest -q tests` | Local Windows workspace | NOT AVAILABLE: local environment lacks FastAPI dependency |
| `npm --prefix frontend run typecheck` | Local Windows workspace | NOT AVAILABLE: local `tsc` dependency is absent |
| `pytest -q tests` | Deployment host virtualenv | PASS: 24 passed, 1 warning |
| `npm --prefix frontend run typecheck` | Deployment host | PASS |
| `npm --prefix frontend run build` | Deployment host | PASS |
| public `/api/v1/health` | Deployment quick tunnel | PASS: HTTP 200 |
| public Web dashboard | Deployment quick tunnel | PASS: HTML 200, API status online, one demo zone displayed |

The local missing dependencies are an environment/reproducibility gap, not a
new code regression. A future release must pin and install both Python and
Node dependencies from a clean checkout before claiming a green baseline.
