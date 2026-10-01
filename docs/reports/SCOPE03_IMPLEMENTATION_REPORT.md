# SCOPE-03 — Implementation report

**STATUS:** `PARTIAL — PC MOCK`
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)
**Live authorization:** `NOT_GRANTED`

## Task → file → result

| Task | Files | Result |
|---|---|---|
| S03-P0 baseline | `docs/reports/SCOPE03_BASELINE_REPORT.md` | Rebaseline, SCOPE-02 amendment acceptance, Pi inventory/live authorization, manifest and safety boundary recorded before code. |
| S03-P1 typed models/contract | `pi5/network/models.py`, `contract.py`, `contracts/v1/SCOPE03_PI_NETWORK_MOCK.md` | `scope03.v1` redacted status with typed independent signals, interface identity, state and mock evidence class. |
| S03-P1 validation/adapters | `pi5/network/validation.py`, `adapters.py` | SSID/interface/credential validation; mock NetworkManager proposal only; profile store version/concurrency; recovery controller; no OS calls/apply path. |
| S03-P1 state machine | `pi5/network/state.py` | AP/STA states, bounded retry/cancel/restart, independent Internet/PC probes, AP continuity on STA failure. |
| S03-P3 PC mock tests | `tests/scope03/test_network_mock.py` | 7 offline tests for validation, injection-safe proposal, signal independence, retries, version conflict, rollback and restart. |
| S03 handoff | `docs/reports/SCOPE03_LIVE_CHANGE_REQUEST.md`, `SCOPE03_RECOVERY_RUNBOOK.md`, prompt/preparation report | Planning only, explicitly `NOT AUTHORIZED — DO NOT EXECUTE`. |

## Design invariants

- The module has no subprocess, shell, NetworkManager, socket, root helper, watchdog, Pi address or credential-store integration.
- A profile proposal has `applied=false`, `requires_live_authorization=true`, and no commands. Calling its mock `apply` raises `PermissionError`.
- Profile and contract serialization never includes password/PSK; only `credential_present` is retained.
- `external_wifi_connected`, `internet_reachable` and `central_server_reachable` are updated independently. Unknown is not converted to success.
- AP state is preserved through STA failure/retry in the simulated state machine; this is logic evidence only, not hardware AP continuity.

## Rollback

The PC mock is additive and has no runtime service or DB migration. Disable/remove only the new `pi5/`, `tests/scope03/`, SCOPE-03 contract/docs/reports after owner review if rollback is requested; preserve evidence and existing SCOPE-00/01/02 work. No destructive rollback was run.

## Not implemented by design

No Pi read-only inventory, real NetworkManager backend, AP/STA/DHCP/DNS/firewall config, subnet selection, captive portal, live probe, TLS/device identity, PC↔Pi data exchange, SCOPE-04 UI, camera, telemetry, firmware or public deployment was implemented.
