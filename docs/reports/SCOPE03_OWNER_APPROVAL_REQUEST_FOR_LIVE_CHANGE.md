# SCOPE-03 Owner Approval Request for Live Change

**STATUS: `DRAFT — NOT AUTHORIZED`**  
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)  
**Purpose:** Request a future, explicit decision for a narrowly bounded AP/STA change. This document does not record owner approval and does not authorize SSH, sudo or any network operation.

## Current evidence

| Field | Current value | Authority/limit |
|---|---|---|
| Device | Raspberry Pi 5 Model B Rev 1.0 | Prior read-only inventory; device scope was the named Pi only. |
| OS / architecture / kernel | Debian 13/trixie / `aarch64` / `6.18.34+rpt-rpi-2712` | Prior read-only inventory. |
| Observed interfaces | `lo`, `eth0`, `wlan0`, `wlan1` | Prior snapshot; roles are not established. |
| Observed driver metadata | `macb`, `brcmfmac`, `rtw88_8821cu` | Prior snapshot; physical role mapping still requires validation. |
| USB wireless evidence | Realtek 802.11ac adapter observed | Prior snapshot; exact IDs are intentionally omitted. |
| Owner recovery assertion | `RECOVERY_CAPABILITY=OWNER_CONFIRMED` | Owner statement only; not a console or recovery-drill test. |
| Local console login | `UNVERIFIED` | No local `tty`, `id -un`, `uname -r` result supplied. |
| Independent recovery path | `UNVERIFIED` | SSH over WLAN is not independent recovery. |
| AP/STA capability | `UNVERIFIED` | `iw` was unavailable in the prior session. |
| Upstream/AP subnet overlap | `UNVERIFIED` | Must be measured; `192.168.4.1/24` is not approved. |
| Retention/legal hold | `UNDECIDED` | Must be decided before PC↔Pi exchange/integration/public deployment. |
| Live network authorization | `NOT_GRANTED` | No live operation may begin from this draft. |

## Smallest proposed first operation

The first operation should be a non-mutating gate, not a network change: the person physically at the Pi confirms keyboard/local console access and returns redacted results for `tty`, `id -un` and `uname -r`. Separately, the owner must identify the independent recovery path, operator and time window. This is the minimum evidence needed before even selecting a live mutation.

If those gates pass, the smallest first live mutation should be one explicitly named, reversible AP/STA property on one verified interface/profile, after a redacted last-known-good snapshot and upstream-overlap check. The exact property, profile/file, command, privilege, service action and expected output are intentionally blank until discovery and owner approval; no command name is implied by this request.

## Owner decisions required before any live mutation

The owner must provide a separate approval containing all of the following. An approval for one numbered item does not approve any other item.

1. Exact device identity and physical label.
2. Named responsible operator physically at the Pi.
3. Approved date/time window and maximum duration.
4. Confirmation of the independent console/OOB recovery path and how the operator will restore the last-known-good state.
5. Approval for the exact read-only evidence commands, including output redaction and storage location.
6. Verified onboard AP interface, USB STA interface, driver/mode evidence and whether concurrent AP+STA is supported.
7. Measured upstream subnet/gateway/DHCP/DNS facts and the exact non-overlapping AP subnet, DHCP range and manual URL.
8. Exact first mutation: interface/profile/file/property, command or tool, privilege, expected result and whether a service reload/restart is allowed.
9. AP security/SSID/channel/country source. No PSK or other secret should be placed in this report.
10. Real client and test method for AP/local access, STA association, Internet reachability and PC/server reachability.
11. Exact rollback owner, operation sequence, stop criteria and snapshot location.
12. Device identity/TLS boundary and retention/legal-hold decision before any PC↔Pi status or PII exchange.

## Approval record — intentionally unfilled

```text
OWNER:
DEVICE_AND_PHYSICAL_LABEL:
RESPONSIBLE_OPERATOR_AT_PI:
APPROVED_DATE_TIME_WINDOW:
INDEPENDENT_RECOVERY_PATH_AND_RESTORE_METHOD:
READ_ONLY_COMMANDS_APPROVED:
REDACTED_OUTPUT_STORAGE_LOCATION:
VERIFIED_ONBOARD_AP_INTERFACE:
VERIFIED_USB_STA_INTERFACE:
AP_STA_CAPABILITY_EVIDENCE:
UPSTREAM_SUBNET_GATEWAY_DHCP_DNS:
APPROVED_AP_SUBNET_DHCP_RANGE_MANUAL_URL:
EXACT_FIRST_MUTATION:
APPROVED_PRIVILEGE_AND_SERVICE_ACTION:
EXPECTED_RESULT:
REAL_CLIENT_AND_TEST_METHOD:
ROLLBACK_OPERATOR_AND_EXACT_ROLLBACK:
STOP_CRITERIA:
DEVICE_IDENTITY_TLS_DECISION:
RETENTION_LEGAL_HOLD_DECISION:
OWNER_APPROVAL_TIMESTAMP:
LIVE_NETWORK_AUTHORIZATION=NOT_GRANTED
```

Until this record is completed through a new, explicit owner decision, the state remains:

```text
RECOVERY_CAPABILITY=OWNER_CONFIRMED
LOCAL_CONSOLE_LOGIN=UNVERIFIED
INDEPENDENT_RECOVERY_PATH=UNVERIFIED
LIVE_NETWORK_AUTHORIZATION=NOT_GRANTED
N4=BLOCKED/NOT_RUN
```

No owner approval, network change, SSH session, password use, package installation, service restart, reboot or SCOPE-04/05/06 work is recorded here.
