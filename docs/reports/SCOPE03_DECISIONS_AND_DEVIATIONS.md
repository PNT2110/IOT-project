# SCOPE-03 — Decisions and deviations

**STATUS:** `PC_MOCK_IMPLEMENTED / LIVE_BLOCKED`
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)

## Decisions applied

| ID | Decision | Reason / boundary |
|---|---|---|
| S03-D01 | Create a pure Python `pi5/network/` package because no Pi module exists in the worktree. | Smallest additive layout; no SCOPE-04 UI or OS integration. |
| S03-D02 | Use `InterfaceIdentity` with explicit `purpose` and `verified`; never infer onboard/USB roles from interface order/name. | Prevents accidental interface ownership when facts are unknown. |
| S03-D03 | `NetworkManagerAdapter` can discover and propose a redacted profile but has no live apply implementation. | Mức A only; Mức C authorization is not granted. |
| S03-D04 | Profile metadata stores SSID, interface, purpose, version and `credential_present`; never password/PSK. | Secret minimization and mock artifact safety. |
| S03-D05 | `ap_reachable`, `external_wifi_connected`, `internet_reachable`, `central_server_reachable` are independent typed signals with `UNKNOWN/UP/DOWN`, timestamps, timeout, stale, source and error. | Avoids inferring Internet/PC health from association alone. |
| S03-D06 | `central_server_reachable` has no implicit PC call or SCOPE-02 fake identity. | No PC↔Pi exchange before device identity/TLS and retention approval. |
| S03-D07 | State machine preserves AP state during STA failure/retry and bounds retries; restart returns to AP_UP + STA_DISCONNECTED + unknown probes. | Models recovery without touching a real interface. |
| S03-D08 | Captive portal, DHCP/DNS/firewall, subnet selection and real probes remain design/runbook items. | Requires Pi facts and live authorization. |

## Evidence classification

- `VERIFIED_FROM_SOURCE`: repo/toolchain/docs and PC mock test execution.
- `TESTED_ON_PC_MOCK`: all `tests/scope03` results and serialized `scope03.v1` fixture.
- `BLOCKED`: Pi model/OS/chipset/interface/route/recovery facts; no read-only access was authorized.
- `NOT_AUTHORIZED`: live AP/STA/profile/network changes, SSH/sudo/reboot, PC↔Pi exchange.

## Deviations

1. No real NetworkManager backend was created, even as a disabled import, because there are no verified interface facts and no need to add OS integration before Mức C.
2. The mock uses a placeholder manual URL only in a unit test; the default contract emits `null`. It is not a reachable Pi address.
3. No API route was added to the FastAPI PC server; SCOPE-03 mock is an injected library contract and does not expand SCOPE-04/PC↔Pi exchange.
4. `SCOPE02_AMENDMENT_ACCEPTANCE` remains `PENDING`; mock work is independent and no policy/PII path was changed.

## Owner decisions before live work

1. Provide/approve Pi model, OS, onboard interface, USB Wi-Fi chipset/driver, current topology and a lab time window.
2. Confirm an independent recovery path (physical console/HDMI+keyboard or verified out-of-band path) and responsible operator.
3. Approve the exact live changes, subnet/AP/STA/DHCP/DNS/firewall scope and rollback steps in [SCOPE03_LIVE_CHANGE_REQUEST.md](SCOPE03_LIVE_CHANGE_REQUEST.md).
4. Chốt device identity/TLS and retention/legal hold before any PC↔Pi data/PII exchange.
