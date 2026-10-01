# SCOPE-03 — Baseline report

**STATUS:** `N0A_PENDING / PC_MOCK_ALLOWED`
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)
**Scope:** mock-first Pi network design/state/adapters on PC. No live Pi access or network mutation.

## Current repository and runtime

| Item | Evidence / status |
|---|---|
| Root / branch / HEAD | `/home/pnt/IOT` / `main` / `16dc418076b1a53a9d2fc9af482e3a514f0791f7` |
| Worktree | Dirty/untracked SCOPE-00/01/02/amendment files preserved; no reset, clean, stash, forced checkout, commit or push. |
| SCOPE-02 amendment | `SCOPE02_POLICY_AMENDMENT_FINAL_REPORT.md` exists and says `PASS_REPORTED_PENDING_OWNER_ACCEPTANCE`; `SCOPE02_AMENDMENT_ACCEPTANCE=PENDING`. Mock work is independent and does not exchange data with PC API. |
| Python/Node/npm | Python `3.14.7`; Node `v22.22.1`; npm `9.2.0`; project `.venv` exists. |
| Local services | No listener on scoped ports `8765`, `5173`, `8000`. No server was started for this P0. |
| DB artifacts | No `*.db`, `*.sqlite`, `*.sqlite3` under repository. Mock scope uses no database. |
| Pi inventory | `PI_READ_ONLY_INVENTORY=BLOCKED`: no device/address/username authorization was supplied. |
| Live authorization | `LIVE_NETWORK_AUTHORIZATION=NOT_GRANTED`; no SSH, console, sudo, reboot or network change permitted. |

## Source/design evidence

Read and compared: `docs/scopes/SCOPE03_PI_NETWORK.md`, `docs/12_NETWORK_ARCHITECTURE.md`, `docs/05_SYSTEM_ARCHITECTURE.md`, SCOPE-03 preparation report/prompt, SCOPE-02 workflow and amendment reports, `docs/CODEX_IMPLEMENTATION_RULES.md`, contracts and current worktree status. Existing design requires onboard AP + USB STA separation, three independent reachability signals, manual recovery URL, typed adapters, no arbitrary shell/sudo and mock-first tests. `192.168.4.1/24`, interface names, SSID, country/channel, chipset and driver remain unverified proposals.

## SCOPE-03 mock manifest

| Classification | Paths | Action |
|---|---|---|
| `CREATE` | `pi5/network/` | Pure Python typed models, validation, mock adapters, state machine and contract serializer; no OS/network calls. |
| `CREATE` | `tests/scope03/` | Offline unit/contract/failure-injection tests only. |
| `CREATE` | `docs/reports/SCOPE03_DECISIONS_AND_DEVIATIONS.md`, `SCOPE03_IMPLEMENTATION_REPORT.md`, `SCOPE03_TEST_REPORT.md`, `SCOPE03_FINAL_REPORT.md` | Evidence and handoff reports. |
| `CREATE` | `docs/reports/SCOPE03_LIVE_CHANGE_REQUEST.md`, `SCOPE03_RECOVERY_RUNBOOK.md` | Planning documents only; each marked `NOT AUTHORIZED — DO NOT EXECUTE`. |
| `READ_ONLY` | Existing SCOPE-00/01/02 docs, SCOPE-03 prompt/scope, `FC_can_bang.zip`, PC SCOPE-02 source | Preserve; no unrelated edits. |
| `FORBIDDEN` | Pi/SSH/sudo, host Wi-Fi, AP/STA/DHCP/DNS/firewall/route, real credentials, PC↔Pi exchange, SCOPE-04/05/06 | Not authorized in this turn. |

## Safety invariants for mock implementation

- Mock status is labeled `TESTED_ON_PC_MOCK` and never claims Pi hardware evidence.
- `X-Fake-Pi-Client` from SCOPE-02 is not imported or reused as a device identity.
- No secret value is stored in profile metadata, serialized status, logs or fixtures; validation accepts an input and retains only `credential_present`.
- The mock cannot apply profiles, invoke subprocesses, call NetworkManager, alter routes or start a watchdog/root helper.
- AP continuity is a simulated invariant only. Real N4 evidence remains `BLOCKED/NOT_RUN`.

## P0 result

`N0A_PENDING / PC_MOCK_ALLOWED`: the requested PC mock work can proceed safely. N0B/N4 remain blocked until the owner separately authorizes read-only Pi access/live testing and supplies a verified independent recovery path.
