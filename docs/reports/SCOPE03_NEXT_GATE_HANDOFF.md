# SCOPE-03 Next-Gate Handoff

**STATUS: `PARTIAL_PC_MOCK_PENDING_LIVE`**  
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)  
**Basis:** fresh PC-only verification in [SCOPE02_AMENDMENT_CLOSEOUT_VERIFICATION.md](SCOPE02_AMENDMENT_CLOSEOUT_VERIFICATION.md).

## What is genuinely new in this handoff

| Evidence class | Finding |
|---|---|
| `TESTED_ON_PC` | Fresh combined SCOPE-01/02/03 run: `31 passed, 1 warning`, exit `0`; this is not copied from the earlier 29/22 reports. |
| `VERIFIED_IN_SOURCE` | Active role/account response DTOs, contract text, frontend types and UI now use `OWNER_OR_GRANTED_ADMIN_SCOPED` and per-action effective scope. |
| `TESTED_ON_PC` | Owner, ungranted Admin and granted Admin representation/enforcement, list filtering, self-review, Owner elevation, audit/history, idempotency and version cases passed. |
| `TESTED_ON_PC` | Temporary SQLite migration ended at `a71e8c4b2d90`; `capability_grants` was present after restore and absent during the controlled downgrade. |
| `OWNER_DECISION_PENDING` | SCOPE-02 code/evidence is ready for owner acceptance; no owner acceptance was authored here. Retention/legal hold remains undecided. |
| `NOT_RUN` | No Pi inventory, SSH/console, live AP/STA, external probe or N4 test was run. |

## Gate status

| Gate | Status | Evidence/meaning |
|---|---|---|
| N0A | `PASS_PC_MOCK / PENDING_OWNER_ACCEPTANCE` | SCOPE-02 amendment closeout is ready for owner acceptance; not owner-accepted. |
| N0B | `BLOCKED / NOT_RUN` | Exact Pi identity, current OS/interfaces and independent recovery are unverified; read-only authorization is not granted. |
| N1 | `PASS_PC_MOCK` | Pure local mock/validation/state tests remain green; no hardware inference. |
| N2 | `DESIGN_READY / PC_MOCK` | AP/STA separation and recovery design exist; no Pi configuration was applied. |
| N3 | `PASS_PC_MOCK` | Independent simulated signals and stale/error semantics remain tested locally. |
| N4 | `BLOCKED / NOT_RUN` | Real Pi AP continuity during STA failure has no evidence and cannot be promoted from mock. |
| N5 | `PARTIAL / PENDING_OWNER` | Reports, contract and read-only approval packet are prepared; live approval and owner acceptance remain open. |

## Decisions still required from owner

1. Separately accept or correct the SCOPE-02 amendment closeout: capability matrix, PC `GUEST` mapping, migration/bootstrap evidence and effective response contract.
2. Decide retention/legal hold before any PC↔Pi data exchange, integration or public deployment.
3. If desired after SCOPE-02 acceptance, separately approve Mức B using [SCOPE03_READ_ONLY_INVENTORY_APPROVAL_PACKET.md](SCOPE03_READ_ONLY_INVENTORY_APPROVAL_PACKET.md), naming the device, operator, access method, time and redacted output path.
4. Before any Mức C real-network trial, separately approve a change request with independently verified console/out-of-band recovery, last-known-good snapshot, operator presence, real client test and stepwise rollback.
5. Decide device identity/TLS and status/PII boundary before any PC↔Pi exchange.

## Stop boundary

```text
PI_READ_ONLY_INVENTORY_AUTHORIZATION=NOT_GRANTED
LIVE_NETWORK_AUTHORIZATION=NOT_GRANTED
INDEPENDENT_RECOVERY_PATH=UNVERIFIED
N4=BLOCKED/NOT_RUN
```

No SCOPE-04/05/06 work was opened. No credentials or historical Pi identity was used; no network modification, firmware/device access or public exposure occurred.

## Addendum — Mức B read-only inventory

**Captured:** 2026-09-22 22:01 (Asia/Ho_Chi_Minh)  
**Result:** [SCOPE03_PI_READONLY_INVENTORY_RESULT.md](SCOPE03_PI_READONLY_INVENTORY_RESULT.md)

The owner explicitly authorized SSH now for the named device `192.168.1.118` and non-root account `pi5`. The pre-existing host key was verified by strict matching; SSH key authentication succeeded and the supplied password was not used or recorded. The approved read-only command list ran sequentially. Pi 5 Model B Rev 1.0, Debian 13/trixie, kernel/aarch64, interface/driver metadata and a USB Realtek 802.11ac adapter were observed. `iw` was unavailable and the exact approved `nmcli` fields were unsupported; no alternative or secret/profile query was attempted.

`N0B=PASS_READ_ONLY_INVENTORY_FOR_THIS_SESSION`  
`LIVE_NETWORK_AUTHORIZATION=NOT_GRANTED`  
`INDEPENDENT_RECOVERY_PATH=UNVERIFIED`  
`N4=BLOCKED/NOT_RUN`

The observation does not establish AP/STA roles, concurrent AP+STA capability, AP continuity, client handshake, recovery independence, device identity/TLS or retention/legal hold. Mức C still requires a separate owner-approved change request with an independently verified console/OOB path, last-known-good snapshot, operator presence, real client test and stepwise rollback. No SCOPE-04/05/06 work was opened.
