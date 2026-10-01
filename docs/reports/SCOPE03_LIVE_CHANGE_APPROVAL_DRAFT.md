# SCOPE-03 Live Change Approval Draft — Mức C

**STATUS: `PROPOSAL ONLY — NOT AUTHORIZED — DO NOT EXECUTE`**  
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)  
**Purpose:** Collect owner decisions for a future change request. This document is not an executable runbook and intentionally contains no command sequence because console login and independent recovery are unverified.

## Prerequisites currently not met

| Prerequisite | State | Owner/operator input required |
|---|---|---|
| Monitor | `OWNER_REPORTED` | Confirm still connected at the named Pi. |
| Direct keyboard | `UNVERIFIED` | Confirm attached and usable. |
| Local console login | `UNVERIFIED` | Confirm a direct non-root login and redacted `tty`, `id -un`, `uname -r` results. |
| Independent recovery path | `UNVERIFIED` | Confirm console/HDMI+keyboard or genuine OOB path independent of the WLAN interface. |
| Physical onboard/USB roles | `UNVERIFIED` | Reconfirm from approved local evidence; do not infer from `wlan0`/`wlan1` names. |
| AP/managed concurrency capability | `UNVERIFIED` | Requires a separately approved read-only capability check; prior `iw` was unavailable. |
| NetworkManager/service state | `UNVERIFIED` | Requires an approved read-only check; do not query secrets/profiles. |
| Upstream/subnet overlap | `UNVERIFIED` | Must be measured before selecting any AP subnet; do not assume `192.168.4.1/24`. |
| Identity/TLS and retention/legal hold | `UNDECIDED` | Owner must decide before any PC↔Pi status/PII exchange. |

## Proposed change outline — not approved

Every item below is `PROPOSAL ONLY — NOT AUTHORIZED — DO NOT EXECUTE`:

1. After console/recovery verification, collect a redacted last-known-good snapshot and record its controlled storage location.
2. Separately verify physical interface mapping, driver/mode capability, regulatory domain, NetworkManager/service state and upstream/subnet overlap using an owner-approved read-only session.
3. Owner reviews exact AP/STA roles, proposed subnet, channel/country, security method and service/profile files. Secrets must be supplied only through a secure operator path and never entered into this report.
4. Define one small reversible change at a time, the console rollback actor, the stop condition, and the second-client verification after each step.
5. Keep AP/local recovery distinct from STA association, Internet reachability and PC/server reachability. No AP continuity claim is allowed before a real client test.
6. Roll back through the independently available console/operator path if AP, local URL, console, interface identity, subnet separation or expected service state becomes unclear.

No command sequence is included until the console gate and all owner inputs above are verified. In particular, do not install `iw`, replace the unsupported `nmcli` query with secret/profile queries, or restart services as part of this draft.

## Required change-request fields — intentionally blank

```text
DEVICE_AND_PHYSICAL_LABEL:
RESPONSIBLE_OPERATOR_AT_PI:
APPROVED_TIME_WINDOW:
CONSOLE_AND_KEYBOARD_VERIFIED_AT:
INDEPENDENT_RECOVERY_PATH:
ONBOARD_INTERFACE_AND_EVIDENCE:
USB_INTERFACE_AND_EVIDENCE:
CAPABILITY_AND_REGULATORY_DOMAIN_EVIDENCE:
NETWORKMANAGER_SERVICE_STATE:
UPSTREAM_AND_SUBNET_CONFLICT_CHECK:
AP_SUBNET_AND_CHANNEL:
SSID_AND_SECURITY_SOURCE:
FILES_PROFILES_SERVICES_TO_TOUCH:
LAST_KNOWN_GOOD_SNAPSHOT_LOCATION:
ROLLBACK_OPERATOR_AND_STEPS:
SECOND_CLIENT_VERIFICATION:
STOP_CRITERIA:
DEVICE_IDENTITY_TLS_DECISION:
RETENTION_LEGAL_HOLD_DECISION:
OWNER_APPROVED_CHANGES:
OWNER_APPROVED_ROLLBACK:
OWNER_APPROVAL_TIME:
LIVE_NETWORK_AUTHORIZATION=NOT_GRANTED
```

No Owner approval is recorded. No Mức C action, service restart, reboot, network change or external probe is authorized by this draft.
