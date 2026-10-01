# SCOPE-03 — Pi Read-Only Inventory Access Request

**REQUEST STATUS: `NOT_GRANTED`**  
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)  
**Purpose:** Request a separately approved, read-only fact-gathering session for one named Raspberry Pi 5. This is a request form, not evidence that access occurred.

## Authorization defaults

```text
PI_READ_ONLY_INVENTORY_AUTHORIZATION=NOT_GRANTED
LIVE_NETWORK_AUTHORIZATION=NOT_GRANTED
INDEPENDENT_RECOVERY_PATH=UNVERIFIED
```

Owner approval must be new, separate and explicit for the exact device and read-only command scope. A continuation message alone is not treated as approval. No password, PSK, OTP/TOTP, private key or other credential is requested or stored here.

## Facts that must be supplied or verified

| Field | Current value | Required before any read-only session |
|---|---|---|
| Pi model / board identity | `UNVERIFIED` | Exact device identifier and physical location/label |
| OS and release | `UNVERIFIED` | Distribution, release, kernel and image provenance |
| Host/access method currently available | `UNVERIFIED` | Console, local display/keyboard, or SSH; state which is approved |
| Current username | `UNVERIFIED` | Named non-root account; do not send password in chat |
| Onboard adapter | `UNVERIFIED` | Interface name, role and presence |
| USB adapter(s) | `UNVERIFIED` | Presence, interface name and exact chipset |
| Chipset / driver | `UNVERIFIED` | Read-only identification and driver/module version |
| Current subnet / addressing | `UNVERIFIED` | Redacted current address/subnet facts; no assumption from historical notes |
| Person performing the session | `UNASSIGNED` | Named operator and owner of the session record |
| Approved time window | `UNASSIGNED` | Start/end time and timezone |
| Redacted output location | `UNASSIGNED` | Controlled repository/path with secrets and PII removed |
| Independent recovery path | `UNVERIFIED` | Physical console or genuinely independent out-of-band path, tested or explicitly confirmed |

Historical IPs, usernames, topology notes or prior reports must not be promoted to current verification. An SSH session over the interface that may later be changed is not an independent recovery path.

## Proposed read-only scope for approval

The following is a candidate scope only; it is not authorized until the owner approves the exact device, operator and time window:

- identify board/kernel/OS: `uname -a`, `/etc/os-release`, board identification;
- list interfaces and addresses: `ip -br link`, `ip -br addr`;
- inspect current routes only: `ip route`;
- inspect adapter/link metadata and installed driver/module facts without changing them;
- record current service/configuration facts only where the command is demonstrably read-only;
- redact addresses, hostnames, usernames, serials, logs, PII and any accidental secrets before storage.

Explicitly excluded even if read-only access is granted: Wi-Fi scanning, changing AP/STA profiles, changing IP/route/DHCP/DNS/firewall, restarting/rebooting services or the board, installing packages/drivers, accessing webcam/ESP32/GNSS/firmware, external probes, PC↔Pi data/PII transfer, and public exposure.

## Approval record to be completed by project owner

```text
DEVICE_SCOPE=UNASSIGNED
OPERATOR=UNASSIGNED
READ_ONLY_COMMAND_SCOPE=UNASSIGNED
APPROVED_TIME_WINDOW=UNASSIGNED
REDACTED_OUTPUT_LOCATION=UNASSIGNED
INDEPENDENT_RECOVERY_PATH=UNVERIFIED
OWNER_DECISION=NOT_RECORDED
OWNER_DECISION_TIME=UNASSIGNED
```

Until this record is completed by a separate approval message, no Pi login or inventory command may be attempted. Read-only approval, if later granted, does not authorize any network configuration change.
