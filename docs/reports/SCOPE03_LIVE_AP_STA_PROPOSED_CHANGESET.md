# SCOPE-03 Proposed Live AP/STA Change Set

**STATUS: `PROPOSAL ONLY — NOT AUTHORIZED — DO NOT EXECUTE`**  
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)  
**Purpose:** Prepare a bounded, reversible Mức C change plan after the console and recovery gates are verified. This document contains no authorization and no executable apply sequence.

## Known facts versus unresolved facts

### Known from the prior read-only inventory

- The prior Mức B session was scoped to the named Pi and used a non-root account with existing SSH-key authentication; no password is retained in this repository.
- The device reported Raspberry Pi 5 Model B Rev 1.0, Debian GNU/Linux 13/trixie, `aarch64`, and kernel `6.18.34+rpt-rpi-2712`.
- `lo`, `eth0`, `wlan0` and `wlan1` were present at that capture. The observed driver paths were `eth0 → macb`, `wlan0 → brcmfmac`, and `wlan1 → rtw88_8821cu`.
- A USB Realtek 802.11ac adapter was observed. The report does not promote interface names into physical AP/STA roles.
- `iw dev` and `iw phy` were unavailable in that session. The approved `nmcli` field query was rejected by the installed version; no profile or secret query was substituted.
- The owner's current statement is recorded separately as `RECOVERY_CAPABILITY=OWNER_CONFIRMED`; console login and independent recovery remain unverified.

### Still unknown and required before a live mutation

- Physical interface mapping and intended roles: onboard AP versus USB STA.
- AP+STA concurrency and driver/mode capability, regulatory domain, channel constraints and country setting.
- Current upstream subnet, gateway, DHCP/DNS ownership and overlap with any candidate AP subnet.
- NetworkManager service state and the exact profiles/files/services that would be touched.
- AP address/subnet, DHCP range, manual URL, SSID/security source and client test method.
- Device identity/TLS boundary, retention/legal hold and whether any status exchange with the PC is permitted.
- Independently usable console/OOB recovery and a last-known-good snapshot location.

## Read-only evidence still proposed — not approved

The following are candidate checks for a separately authorized local-console session or other explicitly approved read-only session. None was run in preparing this document. They must be approved as exact operations, with output redaction, before execution.

| Candidate check | Purpose | Sensitivity/redaction |
|---|---|---|
| `tty` | Prove the person is at a local terminal. | Return only a redacted TTY class/path. |
| `id -un` | Confirm the local operator account is non-root. | Account name may be returned only if needed; never send credentials. |
| `uname -r` | Correlate local-console evidence with the observed kernel. | No material secret; retain only the version. |
| `ip -br link`, `ip -br addr`, `ip route` | Refresh link/address/route state before planning. | Redact addresses, MACs, hostnames and topology before storage. |
| `lsusb` and read-only `/sys/class/net` driver metadata | Correlate USB adapter and driver paths. | Redact exact USB IDs, serials and MACs. |
| `systemctl is-active NetworkManager` and `systemctl is-enabled NetworkManager` | Record service state without restarting it. | Return state only; do not include full unit/environment output. |
| `nmcli --fields DEVICE,TYPE,STATE,CONNECTION device status` | Try a minimal status-only view compatible with the installed version. | Return device/type/state/connection labels only; do not query profiles or secrets. |
| `iw dev` and `iw phy` | Record wireless interfaces and capability if the utility already exists. | Return redacted interface/PHY/channel data; do not install `iw` in this gate. |

The last two wireless checks remain conditional. Installing `iw`, changing packages, querying saved profiles, or reading secrets is outside this proposal and would require a separate explicit change decision.

## Proposed order for a future live change

Every step below remains `PROPOSAL ONLY — NOT AUTHORIZED — DO NOT EXECUTE`.

1. Verify the local console gate, independent recovery path, responsible operator and approved time window. Record the owner's recovery assertion as context, not as a substitute for local evidence.
2. Capture a redacted last-known-good snapshot of relevant network state and the exact restore location. Do not copy secrets or entire credential-bearing profiles into the report.
3. Perform the approved read-only capability, role, service-state and upstream-overlap checks. Preserve the current upstream path until the AP path and rollback path are understood.
4. Select AP and STA roles only from observed evidence. Do not infer that `wlan0`/`wlan1` are roles, and do not assume AP+STA concurrency.
5. Select an AP private subnet only after measuring overlap. `192.168.4.1/24` remains a design proposal, not a pre-approved address, range or gateway.
6. Define the smallest single reversible change: one explicitly named interface/profile/service property, one operator, one stop condition and one rollback owner. No broad reset, profile deletion, firewall reset, route replacement or reboot.
7. Preserve the onboard AP/local recovery path while testing only the approved STA-side operation. Do not cut the current upstream path before a confirmed local recovery path and client test exist.
8. Verify from a real lab client, in separate checks, AP association/local URL, STA association, Internet reachability and PC/server reachability. These signals remain independent.
9. Only after a separately approved STA-failure exercise with a real client may N4 be evaluated. A PC mock, a status flag or an owner assertion cannot promote N4.

## Rollback design — high level only

The responsible operator at the Pi must be named before any change. The rollback must restore the last-known-good network state through the independent console/recovery path, verify AP/local access first, then verify STA and other reachability signals separately. Exact commands, profile names and service actions are intentionally omitted because the interface roles, service manager state and recovery gate are not yet verified. If console access, the local URL, expected interface identity, subnet separation, DHCP/DNS behavior or rollback state becomes unclear, stop and restore before proceeding.

## Stop conditions

Stop before or during any future change if:

- console/OOB recovery is unavailable or the operator cannot confirm how to restore;
- the interface-to-role mapping, AP+STA capability, subnet boundary or regulatory setting is uncertain;
- a command would require a secret, package install, `sudo` not expressly approved, profile/credential disclosure, reboot or broad reset;
- AP/local access, the manual URL, the current upstream path or the last-known-good snapshot becomes unclear;
- an unapproved client, PC↔Pi exchange, Internet/PC probe, peripheral access or public exposure would occur.

## Boundary

```text
PI_READ_ONLY_INVENTORY_AUTHORIZATION=NOT_GRANTED_FOR_THIS_NEW_PROPOSAL
LIVE_NETWORK_AUTHORIZATION=NOT_GRANTED
RECOVERY_CAPABILITY=OWNER_CONFIRMED
LOCAL_CONSOLE_LOGIN=UNVERIFIED
INDEPENDENT_RECOVERY_PATH=UNVERIFIED
N4=BLOCKED/NOT_RUN
```

No SSH session, local-console command, Wi-Fi scan, package installation, network mutation, service restart, reboot, secret/profile query or SCOPE-04/05/06 work was performed for this proposal.
