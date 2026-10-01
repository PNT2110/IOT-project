# SCOPE-03 — Test report

**STATUS:** `PARTIAL — PC MOCK TESTED`
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)

## Commands

| Command | Exit | Result |
|---|---:|---|
| `.venv/bin/pytest -q tests/scope01 tests/scope02 tests/scope03 -W default` | 0 | `29 passed, 0 failed, 1 warning`; SCOPE-03 adds 7 mock tests. |
| `.venv/bin/python -m compileall -q server pi5 tests/scope01 tests/scope02 tests/scope03` | 0 | PASS. |
| `npm --prefix frontend run typecheck` | 0 | PASS. |
| `npm --prefix frontend run build` | 0 | PASS, Vite `7.3.6`. |
| `.venv/bin/pip check` | 0 | PASS. |
| `.venv/bin/pip-audit -r server/requirements.lock --format columns` | 0 | `No known vulnerabilities found`. |
| `npm --prefix frontend audit --omit=dev --audit-level=high` | 0 | `0 vulnerabilities`. |
| `git diff --check` | 0 | PASS. |

No new dependency or lockfile change was made.

## PC mock matrix

| Case | Result |
|---|---|
| Unknown/unverified interface cannot receive STA proposal | PASS |
| SSID empty/too long/control input | PASS |
| Credential length/control validation | PASS |
| Injection-shaped credential never becomes shell/command | PASS; proposal command list remains empty and apply is disabled |
| `external_wifi_connected` independent of Internet/PC | PASS |
| Internet DOWN while PC UP | PASS |
| STA failure keeps simulated AP_UP | PASS |
| Bounded retry and cancellation semantics | PASS |
| Profile version conflict and repeated rollback | PASS |
| Restart restores AP_UP/STA_DISCONNECTED and unknown probes | PASS |
| Redacted versioned contract and mock evidence class | PASS |

## Gate evidence

| Gate | Status | Evidence |
|---|---|---|
| N0A | `PASS_PC_MOCK / PENDING_OWNER_AMENDMENT` | SCOPE-02 amendment report exists and is tested, but owner acceptance remains pending; mock does not exchange data. |
| N0B | `BLOCKED/NOT_RUN` | No read-only Pi authorization, device facts or independent recovery evidence. |
| N1 | `PASS_PC_MOCK` | Typed adapters, validation, state machine, no apply path, 7 tests. |
| N2 | `DESIGN_READY / PC_MOCK` | Contract/runbook specify AP/STA, manual URL, unknown subnet; no Pi config applied. |
| N3 | `PASS_PC_MOCK` | Three independent signals, timestamps/source/stale/timeout/error; no live probes. |
| N4 | `BLOCKED/NOT_RUN` | No Pi/client lab/live authorization; AP continuity is simulated only. |
| N5 | `PARTIAL/PENDING_OWNER` | Reports and rollback artifacts complete; owner handoff pending; no later scope opened. |

## Explicit non-evidence

No result here proves Pi AP continuity, USB chipset concurrent AP/STA support, real Internet, real PC handshake, subnet/DHCP/DNS/firewall behavior, captive portal popup behavior or recovery from a physical failure. `PI_READ_ONLY_INVENTORY=BLOCKED`; `LIVE_NETWORK_AUTHORIZATION=NOT_GRANTED`.
