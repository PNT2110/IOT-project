# SCOPE-04 Baseline Report

Captured: `2026-09-24T04:02:18+07:00`  
Repository: `/home/pnt/IOT`  
Branch: `main`  
HEAD at baseline: `16dc418076b1a53a9d2fc9af482e3a514f0791f7`

## Scope boundary

The direct Owner prompt starts SCOPE-04 repository implementation only. No Pi
mutation, SSH session, network change, listener start, camera frame capture,
recording, PC↔Pi synchronization, firmware work, or SCOPE-05+ work was done.

## Pre-existing evidence used

- SCOPE-02 is owner-accepted in the current packet; historical reports remain
  snapshots.
- SCOPE-03 is owner-accepted with the recorded N4 protocol deviation; it is
  not promoted to a Codex-observed live pass.
- Camera inventory records `/dev/video0` as the external UVC capture node and
  `/dev/video1` as the metadata node.
- Pi identity is local USER/ADMIN with no PC federation or synchronization.

## Planned implementation manifest

| Area | Planned artifact | Evidence class |
|---|---|---|
| Contract | `contracts/v1/SCOPE04_PI_WEB_CONTRACT.md` | `VERIFIED_ON_PC` |
| Local auth/session | `pi5/web/auth.py`, `pi5/web/app.py` | `TESTED_ON_PC_MOCK` |
| Camera adapter | `pi5/web/camera.py` | `TESTED_ON_PC_MOCK`; live capture not run |
| Map cache | `pi5/web/cache.py` | `TESTED_ON_PC_MOCK` |
| Mock telemetry/3D | `pi5/web/telemetry.py`, `pi5/web/models.py` | `TESTED_ON_PC_MOCK` |
| Local web shell | `pi5/web/app.py` | `TESTED_ON_PC_MOCK` |
| Negative/security tests | `tests/scope04/test_pi_web.py` | `TESTED_ON_PC_MOCK` |

## Baseline commands

```text
git rev-parse --show-toplevel -> /home/pnt/IOT
git branch --show-current -> main
git rev-parse HEAD -> 16dc418076b1a53a9d2fc9af482e3a514f0791f7
git diff --check -> exit 0
python --version -> 3.14.7
node --version -> v22.22.1
```

The worktree was already dirty. Existing changes and untracked files were
preserved; no reset, clean, stash, checkout, commit, or push was performed.
