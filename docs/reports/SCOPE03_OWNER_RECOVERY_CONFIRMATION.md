# SCOPE-03 Owner Recovery Confirmation

**STATUS: `OWNER_CONFIRMED — LOCAL_VERIFICATION_PENDING`**  
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)  
**Scope:** Record the owner's recovery statement only; no Pi command, SSH session or network action was performed for this record.

## Owner statement and interpretation

The owner stated:

> “tao xác nhận tao có thể phục hồi lại hết”

For this project record, the statement means that the owner asserts they can restore the Pi if a future approved operation causes a problem. It is not evidence that Codex observed a local console, tested a recovery drill, or verified an independent recovery path. It is also not approval for AP/STA, route, DHCP/DNS, firewall, service, reboot or other live network changes.

## Evidence matrix

| Item | State | Evidence boundary |
|---|---|---|
| Owner recovery capability | `OWNER_CONFIRMED` | Current owner statement recorded above. No credential or recovery secret is recorded. |
| Monitor attached | `OWNER_REPORTED` | Previously reported physical state; not inspected by Codex. |
| Keyboard attached and usable | `NOT_TESTED` | No direct physical confirmation was supplied in this turn. |
| Local terminal/TTY visible | `NOT_TESTED` | No local display or TTY was inspected. |
| Local non-root console login | `NOT_TESTED` | No local login result was supplied. |
| `tty` result | `NOT_TESTED` | No result supplied. |
| `id -un` result | `NOT_TESTED` | No result supplied. |
| `uname -r` local-console result | `NOT_TESTED` | No result supplied; the prior SSH observation is not local-console evidence. |
| Recovery during network failure | `NOT_TESTED` | No interface failure or recovery drill was attempted. |
| Independent recovery path | `UNVERIFIED` | Owner capability is asserted, but independence from the WLAN path was not demonstrated. |
| Live network authorization | `NOT_GRANTED` | This record grants no permission to modify the Pi or network. |

## Required local evidence for the next gate

If the owner wants to advance the console gate, the person physically at the named Pi may, after separately agreeing to the read-only check, use the local console only and return redacted results for:

```text
tty
id -un
uname -r
```

Do not send a password, TOTP, serial number, MAC address, PSK, private key or full log. A concise response should state whether the keyboard and local terminal were usable, whether the login was non-root, the redacted TTY class/path, and the local time. These checks do not change network configuration.

## Current gate values

```text
RECOVERY_CAPABILITY=OWNER_CONFIRMED
LOCAL_CONSOLE_LOGIN=UNVERIFIED
RECOVERY_DURING_NETWORK_FAILURE=NOT_TESTED
INDEPENDENT_RECOVERY_PATH=UNVERIFIED
LIVE_NETWORK_AUTHORIZATION=NOT_GRANTED
N4=BLOCKED/NOT_RUN
```

No owner acceptance of SCOPE-02, live-network approval, SCOPE-04/05/06 work, or N4 pass is recorded here.
