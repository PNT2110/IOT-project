# SCOPE-01 — Baseline report

**Status:** `BLOCKED_BEFORE_P1`  
**Captured:** 2026-09-22  
**Scope:** PC local-only foundation; no Pi, firmware, public network or real authority integration.

## Repository and worktree

| Item | Evidence |
|---|---|
| Working directory | `/home/pnt/IOT` |
| Repository root | `/home/pnt/IOT` (`git rev-parse --show-toplevel`) |
| Branch | `main` |
| HEAD | `16dc418076b1a53a9d2fc9af482e3a514f0791f7` |
| HEAD tree | `.agents/`, `.gitignore`, `FC_can_bang.zip`, `docs/`; no `backend/`, `frontend/`, `server/`, `contracts/` or `tests/` source tree. |
| Worktree status at baseline | `docs/05_SYSTEM_ARCHITECTURE.md` modified; new/untracked SCOPE-00 docs `10–12`, `15–20`, Codex rules/prompt and `docs/scopes/`. No non-doc source change was made by SCOPE-01. |
| Write permission | Repository root and `docs/` writable. |
| Archive | `FC_can_bang.zip`, SHA-256 `95809c58d61bb20c12a9541719ad90ec4afc8dab74597a20517486174849771f`; read-only. |
| docs.zip | Not found under `/home/pnt/IOT` or `/home/pnt/.codex/attachments`; pasted prompt is the only available copy. |

## Runtime/dependency inventory

| Component | Observed | Consequence |
|---|---|---|
| OS/kernel | Linux x86_64, kernel `7.0.0-31-generic` | `VERIFIED_FROM_SOURCE` for this PC only. |
| Python | `3.14.7` | Available; framework compatibility must be verified before install. |
| Node/npm | Node `v22.22.1`, npm `9.2.0` | Available; no frontend source/package manifest exists on disk. |
| FastAPI/Uvicorn | Missing | Cannot run the selected API stack. |
| SQLAlchemy | Missing | Cannot use the proposed ORM without project-local dependency setup. |
| Argon2/PyOTP | Missing | Cannot safely claim password/MFA implementation. |
| Pydantic/cryptography/pytest/httpx | Available (`2.13.4`, `50.0.0`, `9.1.1`, `0.28.1`) | Insufficient alone to satisfy SCOPE-01 auth/API target. |
| Listening ports | `0.0.0.0:7070`, SSH `:22`, DNS `:53`, CUPS `127.0.0.1:631` | No port chosen; future server must bind loopback only and avoid 7070. |

No global installation, virtualenv creation, dependency download or server start was performed.

## Existing/missing/dirty/conflicting inventory

| Path/group | Disk | Git/HEAD | Action |
|---|---|---|---|
| `docs/` | Exists | Exists | Read-only for baseline; reports created here. |
| `FC_can_bang.zip` | Exists | Exists | Read-only; out of scope. |
| `backend/`, `frontend/`, `tests/` | Missing | Not in current HEAD | Do not restore from historical assumptions. |
| `server/`, `contracts/` | Missing | Missing | Candidate create paths after blocker resolution. |
| `deploy/`, Pi/firmware source | Missing | Missing | Forbidden in SCOPE-01. |
| Existing docs changes | Present | Dirty/untracked as above | Preserve; no overwrite/reset/restore/stash. |

## Proposed manifest if unblocked

| Action | Planned paths | Gate |
|---|---|---|
| `CREATE` | `server/`, `contracts/`, `tests/scope01/`, `.env.example` in approved layout, project-local ignore entries, SCOPE-01 reports | Requires stack/layout approval and project-local dependency authorization. |
| `MODIFY` | Only newly-created SCOPE-01 files and explicitly approved docs/report files | Never modify dirty existing source/docs without decision. |
| `READ ONLY` | `docs/**/*.md`, `FC_can_bang.zip`, Git metadata, runtime inventory | No secrets/hardware. |
| `FORBIDDEN` | `backend/`, `frontend/` historical restoration, `FC_can_bang.zip`, Pi/SSH/network/firmware/deploy, public bind/tunnel | Always outside this scope or conflict-protected. |

## Local-only execution plan

When dependencies and layout are approved, the server will bind explicitly to `127.0.0.1` (and optionally `::1` only after testing), use CORS allowlist for loopback UI origin, and never bind `0.0.0.0`. Port `7070` is occupied; select an unused loopback port at runtime/configuration and record the actual value. Browser E2E requires local HTTPS with a trusted development certificate; until that exists, API/unit tests may run with a test client but browser secure-cookie E2E is `BLOCKED`, not PASS.

## P0 gate result

`BLOCKED`: the repository has no application source/layout to extend, and required FastAPI/Uvicorn/SQLAlchemy/Argon2/PyOTP dependencies are absent. The safe next action is owner approval to create a project-local virtual environment and install pinned dependencies, plus confirmation of the new `server/` + frontend layout. No code was written while this gate is unresolved.

## Continuation addendum — 2026-09-22

The owner approved all four unlock decisions in the continuation prompt: project-local `.venv` and npm dependencies, new `server/`/`contracts/`/`tests/scope01/` layout, React/TypeScript/Vite, and the on-disk `docs/` as current design source. Recheck confirms the same repository `/home/pnt/IOT`, branch `main`, HEAD `16dc418076b1a53a9d2fc9af482e3a514f0791f7`, missing target paths, Python `3.14.7`, Node `v22.22.1`, npm `9.2.0`, and occupied `0.0.0.0:7070`. The optional continuation prompt file is absent. The previous P0 snapshot is preserved; this addendum authorizes P1 work under the approved manifest.

Dependency resolution subsequently succeeded in `.venv` on Python 3.14.7. The final frontend lockfile/build uses Vite `7.3.6` after an initial audit finding; production npm audit is now clean. The server was smoke-tested on `127.0.0.1:8765`; no public bind or port-forward was used.
