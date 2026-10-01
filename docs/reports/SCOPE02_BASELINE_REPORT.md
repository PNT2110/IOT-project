# SCOPE-02 — Baseline report

**Status:** `P0_COMPLETE_BEFORE_P1`
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)
**Scope:** PC-local simulated workflow/API, account review, audit/history and read-only fake Pi adapter. No Pi, firmware, hardware, public bind, real provider or legal authority integration.

## Repository and worktree

| Item | Evidence |
|---|---|
| Working directory / repository root | `/home/pnt/IOT` |
| Branch / HEAD | `main` / `16dc418076b1a53a9d2fc9af482e3a514f0791f7` |
| Worktree | Dirty. Existing SCOPE-00/SCOPE-01 modifications and untracked source/docs are preserved; no reset, clean, checkout, stash, commit or push performed. |
| Existing diff | `git diff --stat` reports only tracked changes in `.gitignore` and `docs/05_SYSTEM_ARCHITECTURE.md`; the rest of the approved SCOPE-01 layout is untracked. |
| Firmware/archive boundary | `FC_can_bang.zip` and any firmware/hardware evidence remain read-only and out of scope. |
| Previous scope gate | `docs/reports/SCOPE01_GATE_CLOSURE_REPORT.md` records mandatory SCOPE-01 local-only PASS; its historical reports/addenda are preserved. |

## Runtime and local-state inventory

| Component | Observed | Consequence |
|---|---|---|
| Python | `3.14.7`; project `.venv` available | Use existing project-local environment only. |
| Node/npm | `v22.22.1` / `9.2.0` | Existing frontend toolchain may be regression-tested. |
| Server dependencies | Pinned in `server/requirements.lock`; `pip check` was PASS in SCOPE-01 evidence | Do not widen dependency scope without need. |
| Frontend lock | `frontend/package-lock.json`; SCOPE-01 typecheck/build/audit PASS | Extend existing UI only. |
| Listening ports at baseline | No listener found on `8765`, `5173` or `8000` | Any smoke process must bind explicitly to `127.0.0.1` and be torn down. |
| Database artifacts | No `*.db`, `*.sqlite` or `*.sqlite3` file found in the repository tree | Use temporary DBs for tests; do not create tracked runtime data. |
| External services | None contacted | Fake mail and fake Pi client only; offline behavior must be explicit. |

## Current implementation manifest

| Area | Current paths | SCOPE-02 action |
|---|---|---|
| Backend/API | `server/app/{api,config,db,geo,mail,main,models,schemas,security,services}.py` | Extend with workflow domain, RBAC and read-only adapter. |
| Persistence | `server/migrations/versions/380891b589d3_initial.py` | Add forward migration with constraints/indexes and downgrade for temp restore testing. |
| CLI | `server/cli.py` | Preserve SCOPE-01 bootstrap behavior; no self-approval or factor bypass. |
| Contracts | `contracts/v1/README.md` | Append versioned SCOPE-02 DTO/error/state rules. |
| Frontend | `frontend/src/{App,api,styles}.tsx/css/ts` | Add backend-authoritative role/review/workflow tabs without map-provider expansion. |
| Regression tests | `tests/scope01/` | Preserve and rerun; add `tests/scope02/` only. |
| Reports | `docs/reports/SCOPE02_*.md` | This P0 report is written before implementation; remaining reports are append-only deliverables. |

## Safety and scope lock

- Every simulated request/status/result must carry `simulated: true`, source/provenance and the exact label `SIMULATED — NOT A FLIGHT PERMIT`.
- No route, field, event, schema or UI action is allowed to introduce actuator/control semantics, including the prohibited control vocabulary from the SCOPE-02 prompt.
- Account approval is backend-authoritative. The safe policy selected for implementation is least privilege: `OWNER` reviews account status and role elevations; no self-approval, no normal registration/elevation to `OWNER`, no operator account review.
- The first bootstrap Owner remains a local operational gate: SCOPE-01 only creates `OWNER/PENDING` and completes email/MFA; SCOPE-02 will not add HTTP self-activation. Any local activation procedure must be explicit, operator-confirmed and audited.
- Pi-facing functionality is a versioned fake/read-only status/map adapter. It will not contact Pi, SSH, hardware, firmware, GNSS, webcam, ESP32 or external map/authority services.

## P0 result and implementation gate

`P0_COMPLETE_BEFORE_P1`: prerequisites, current source, SCOPE-01 reports, tool versions, local bind/database state and safety boundaries were rechecked. P1 may proceed within the manifest above. The next stop condition is any attempt to create a control path, leak secrets/extra PII, weaken object authorization, or require an external service.
