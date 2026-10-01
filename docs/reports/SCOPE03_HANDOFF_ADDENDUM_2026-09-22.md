# SCOPE-03 — Evidence Handoff Addendum

**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)  
**Purpose:** Record only findings from this handoff; this is not a replacement for the existing SCOPE-03 FINAL or TEST report.

## New PC findings

| Evidence class | Finding |
|---|---|
| `VERIFIED_ON_PC` | SCOPE-02 amendment baseline, decisions, implementation, test and final reports exist; source, migration and tests were located directly. |
| `VERIFIED_ON_PC` | Rebaseline confirmed `main` at `16dc418076b1a53a9d2fc9af482e3a514f0791f7`; dirty/untracked worktree was preserved. |
| `TESTED_ON_PC_MOCK` | `.venv/bin/pytest -q tests/scope01 tests/scope02 -W default` exited `0`: 22 passed, 1 upstream deprecation warning. Compileall, pip check and diff check also exited `0`. |
| `TESTED_ON_PC_MOCK` | Temporary SQLite migration cycle upgraded to `a71e8c4b2d90`, downgraded to `9c4f2d7e6a11`, then restored to `a71e8c4b2d90`; `capability_grants` lifecycle passed. |
| `EVIDENCE_INCOMPLETE` | Owner acceptance remains unrecorded. The role-review response still says `OWNER_ONLY_REVIEW` at `server/app/api.py:659-663`, while enforcement permits a capability-granted Admin; this requires a separate SCOPE-02 corrective decision. |
| `BLOCKED` | Pi identity, current OS/interface/subnet facts, read-only authorization and independent recovery path remain unverified. |
| `NOT_RUN` | Gate N4 — AP remains reachable when STA fails on the real Pi — was not run and remains blocked. |

## State and stop boundary

`SCOPE03_STATUS=PARTIAL_PC_MOCK_PENDING_LIVE` remains unchanged, but this addendum is new evidence and does not claim that the old reports were rerun. `NO_NEW_EXECUTION` is **not** applicable: new PC-only verification was performed. There was no new live execution.

The required access request is [SCOPE03_PI_READ_ONLY_ACCESS_REQUEST.md](SCOPE03_PI_READ_ONLY_ACCESS_REQUEST.md). The amendment review is [SCOPE02_AMENDMENT_ACCEPTANCE_REVIEW.md](SCOPE02_AMENDMENT_ACCEPTANCE_REVIEW.md).

No SCOPE-04/05/06 work was opened. No Pi/SSH/network command, credential handling, real AP/STA change or public deployment occurred.
