# SCOPE-03 Current Test Report

**STATUS: `PC_MOCK_PASS — LIVE_EVIDENCE_OWNER_ATTESTED_NOT_FULLY_EVIDENCED`**  
**Captured:** 2026-09-24 (Asia/Ho_Chi_Minh)

## Commands executed on PC

| Command | Exit | Result |
|---|---:|---|
| `.venv/bin/pytest -q tests/scope01 tests/scope02 tests/scope03 -W default` | 0 | `31 passed, 1 warning` in 6.89s. Warning is the upstream Starlette/AnyIO deprecation. |
| `git diff --check` | 0 | PASS for the documentation changes in this turn. |

The test run is local/mock evidence only. It does not exercise NetworkManager, systemd, `wlan0`, `ap0`, F450, DHCP/DNS, a real client, a physical console or N4.

## Test coverage boundary

Existing PC tests continue to cover typed mock state, independent reachability signals, validation, bounded retry/recovery and rollback semantics. No fake test was added to claim single-radio hardware capability. Live-lab evidence remains separate and pending authorization.

```text
N1=PASS_PC_MOCK
N2=NOT_TESTED_LIVE
N3=PASS_PC_MOCK / NOT_TESTED_LIVE
N4=OWNER_ATTESTED_SUCCESS_NOT_FULLY_EVIDENCED
N4_PROTOCOL_COMPLIANCE=DEVIATION_RECORDED
N5=DOCUMENTATION_IN_PROGRESS
```
