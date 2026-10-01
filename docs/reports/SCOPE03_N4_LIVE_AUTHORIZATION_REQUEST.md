# SCOPE-03 N4 Live Authorization Request

**STATUS: `GRANTED — EXECUTION_RECONCILED`**  
**N4:** `OWNER_ATTESTED_SUCCESS_NOT_FULLY_EVIDENCED`  
**Captured:** 2026-09-24 (Asia/Ho_Chi_Minh)

## Purpose

Request a separate, explicit owner approval for one bounded SCOPE-03 N4 failure/recovery test after read-only verification. This request is not authorization. The current prompt, prior read-only SSH approval, architecture override, owner recovery assertion and old live-change draft are not treated as N4 authorization.

## Current target profile — owner-provided, not yet re-verified

```text
STA interface/profile: wlan0 / netplan-wlan0-C25B
AP interface/profile:  ap0 / F450-1RADIO
AP SSID/gateway:      F450 / 192.168.4.1/24
Service:              f450-ap.service
Failure scope:        disconnect only the verified upstream STA profile
Recovery scope:       reactivate only the verified upstream STA profile
```

These names must be confirmed read-only immediately before any mutation. If any name or binding differs, stop and create a corrected approval rather than guessing.

## Approval fields — owner must complete explicitly

```text
OWNER_LIVE_AUTHORIZATION=GRANTED
TARGET_DEVICE_AND_PHYSICAL_LABEL:
RESPONSIBLE_OPERATOR_AT_PI:
APPROVED_TIME_WINDOW:
APPROVED_ACCESS_METHOD: local console only for mutation
LOCAL_CONSOLE_RECOVERY=VERIFIED_FOR_THIS_TEST
REAL_F450_CLIENT=VERIFIED
VERIFIED_STA_PROFILE:
VERIFIED_AP_PROFILE:
VERIFIED_AP_GATEWAY:
READ_ONLY_BASELINE_COMMANDS_APPROVED:
FAILURE_INJECTION=disconnect only the verified STA profile
RECOVERY=reactivate only the verified STA profile
AP_PROFILE_MUST_REMAIN_UNTOUCHED=yes
NO_REBOOT=yes
NO_NETWORKMANAGER_RESET=yes
NO_FIREWALL_FLUSH=yes
NO_PROFILE_DELETION=yes
ROLLBACK_OPERATOR_AND_METHOD:
STOP_IF_LOCAL_AP_LOST=yes
STOP_IF_CONSOLE_OR_ROLLBACK_UNCERTAIN=yes
OWNER_APPROVAL_TIMESTAMP:
```

Do not enter a password, PSK, OTP/TOTP, private key, saved secret or raw client identifier in this record.

## Pre-mutation read-only gate

Only after the owner completes the approval above, and only through the approved access method, verify the current device/operator and runtime state without printing secrets:

```bash
date --iso-8601=seconds
hostname
id -un
uname -r
cat /proc/device-tree/model
nmcli -f DEVICE,TYPE,STATE,CONNECTION device status
ip -4 -br addr show wlan0
ip -4 -br addr show ap0
ip -4 route
iw dev
systemctl is-active f450-ap.service
systemctl is-enabled f450-ap.service
ip neigh show dev ap0
```

Redact addresses, MACs, BSSID, client identifiers and hostnames as required. Confirm the real F450 client can reach `192.168.4.1` before failure injection. If `iw` is unavailable, record that fact and stop; do not install it or substitute a secret/profile query.

## Exact mutation and recovery — not executable until approved

Run only from the local Pi console, never from an SSH session dependent on `wlan0`, and only after the verified profile identity is recorded in an approved authorization:

```bash
# Failure injection — NOT AUTHORIZED until the approval fields are complete.
sudo nmcli connection down id <VERIFIED_STA_PROFILE>

# Recovery — NOT AUTHORIZED until the failure observations are recorded.
sudo nmcli connection up id <VERIFIED_STA_PROFILE> ifname wlan0
```

The AP service/profile must not be stopped, deleted, reset or modified. No reboot, firewall flush, manual route replacement, package installation or later-scope work is included.

## Required N4 evidence

Record timestamps and redacted PASS/FAIL results for:

- upstream STA becomes unavailable as intended;
- `ap0`/F450 remains present and usable;
- the real client remains associated or reconnects and reaches `192.168.4.1`;
- AP gateway/DHCP/local recovery remain usable;
- local console remains usable;
- STA recovery restores upstream address/default route and approved Internet probe;
- F450 remains usable after recovery without manual AP rebuild;
- no uncontrolled restart loop occurs.

If AP/local access or recovery becomes uncertain, mark `N4=FAIL_LIVE`, execute only the approved recovery path and stop.

## Current decision

```text
OWNER_LIVE_AUTHORIZATION=GRANTED
LIVE_NETWORK_AUTHORIZATION=GRANTED_FOR_BOUNDED_TEST
N4=OWNER_ATTESTED_SUCCESS_NOT_FULLY_EVIDENCED
N4_FAILURE_INJECTION=OWNER_ATTESTED_COMPLETION
N4_RECOVERY=OWNER_ATTESTED_COMPLETION
N4_PROTOCOL_COMPLIANCE=DEVIATION_RECORDED
SCOPE04=NOT_OPENED
```

## Owner completion record received

The owner supplied the previously missing fields and confirmed the bounded N4 conditions:

```text
TARGET_DEVICE_AND_PHYSICAL_LABEL=Raspberry Pi 5 — hostname pitan — direct device at owner's desk
RESPONSIBLE_OPERATOR_AT_PI=Owner — physically present with local screen/terminal
APPROVED_TIME_WINDOW=2026-09-24 02:40–03:40 Asia/Ho_Chi_Minh
OWNER_APPROVAL_TIMESTAMP=2026-09-24 02:40 Asia/Ho_Chi_Minh
LOCAL_CONSOLE_RECOVERY=VERIFIED_FOR_THIS_TEST
REAL_F450_CLIENT=VERIFIED
OWNER_LIVE_AUTHORIZATION=GRANTED
```

The owner-provided evidence summary says the baseline matched and the sequence completed. Codex did not execute or independently observe the Pi session; the mutation path is recorded as SSH over `wlan0`, a deviation from the approved local-console-only path.
