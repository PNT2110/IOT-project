# SCOPE-03 Console Recovery Verification

**STATUS: `CONSOLE_LOGIN_UNVERIFIED`**  
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)  
**Scope:** PC-only review and owner-reported physical state; no new SSH session and no Pi/network action in this turn.

## Evidence matrix

| Evidence item | State | Evidence / limitation |
|---|---|---|
| `MONITOR_CONNECTED` | `OWNER_REPORTED` | The current project instruction says an external monitor has been connected to the Pi. Codex did not inspect the physical display. |
| `KEYBOARD_CONNECTED` | `UNVERIFIED` | No confirmation that a keyboard is directly attached and usable. |
| `LOCAL_CONSOLE_VISIBLE` | `UNVERIFIED` | No evidence that a terminal is visible or that a local TTY can be reached. |
| `LOCAL_CONSOLE_LOGIN` | `UNVERIFIED` | No person has reported a direct console login into the non-root account. No password/TOTP was requested or copied. |
| `CONSOLE_TTY` | `UNVERIFIED` | `/dev/tty*` was not checked at the physical console. |
| `RECOVERY_DURING_NETWORK_FAILURE` | `NOT_TESTED` | No Wi-Fi/interface was interrupted; no recovery drill was attempted. |
| `INDEPENDENT_RECOVERY_PATH` | `UNVERIFIED` | SSH over the WLAN interface is not independent recovery. The prior SSH inventory session does not verify console/OOB recovery. |
| `LIVE_NETWORK_AUTHORIZATION` | `NOT_GRANTED` | No permission exists in this turn to change AP/STA, route, DHCP/DNS, firewall, service state or reboot. |

## What the person at the Pi must confirm directly

The owner/operator should perform these checks at the physical console only and return redacted results; Codex must not receive a password, TOTP, serial, MAC, PSK or full log:

1. A keyboard is directly attached and usable.
2. The monitor shows a terminal or can switch to a local TTY.
3. The person logs in locally as the approved non-root account without sharing the secret.
4. On that console, the person runs only the non-mutating checks `tty`, `id -un`, and `uname -r`.
5. The person reports the redacted TTY class/path, login success, and local time.

Until these facts are supplied, record:

```text
MONITOR_CONNECTED=OWNER_REPORTED
KEYBOARD_CONNECTED=UNVERIFIED
LOCAL_CONSOLE_LOGIN=UNVERIFIED
RECOVERY_DURING_NETWORK_FAILURE=NOT_TESTED
INDEPENDENT_RECOVERY_PATH=UNVERIFIED
```

## Boundary

The prior Mức B SSH report remains evidence for that one read-only SSH session only. It does not authorize a new SSH session in this turn and does not prove console recovery. N4 remains `BLOCKED/NOT_RUN`; no AP/STA failure, client test, reboot, service restart, package installation, peripheral access or SCOPE-04/05/06 work was performed.
