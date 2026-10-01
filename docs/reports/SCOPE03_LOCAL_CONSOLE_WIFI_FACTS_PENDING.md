# SCOPE-03 Local Console and Wi-Fi Facts — Pending Owner Output

**STATUS: `WAITING_FOR_OWNER_LOCAL_OUTPUT`**  
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)  
**Scope:** Classify the owner-supplied terminal photo and wait for the owner to run the approved read-only commands directly at the Pi. No SSH session, Pi command or network change was performed by Codex in this turn.

## Evidence register

| Fact | Source | Observed at | Command or photo | Exit | Redacted result | Confidence | Limitation |
|---|---|---|---|---:|---|---|---|
| Terminal window visible | `OWNER_PHOTO_EVIDENCE` | `NOT_PROVIDED` | Owner-supplied image #1 | `NOT_AVAILABLE` | A desktop with a terminal window is visible. | `MEDIUM` | The image alone does not prove keyboard attachment, local physical path or absence of remote desktop. |
| Terminal identity | `OWNER_PHOTO_EVIDENCE` | `NOT_PROVIDED` | Owner-supplied image #1, visible `tty` output | `NOT_AVAILABLE` | `/dev/pts/0` | `MEDIUM` | `pts/0` is a pseudo-terminal and is not SSH or local-console proof by itself. |
| User identity | `OWNER_PHOTO_EVIDENCE` | `NOT_PROVIDED` | Owner-supplied image #1, visible `id -un` output | `NOT_AVAILABLE` | `pi5` | `MEDIUM` | The photo shows the command result but does not prove how the terminal was reached. |
| Kernel identity | `OWNER_PHOTO_EVIDENCE` | `NOT_PROVIDED` | Owner-supplied image #1, visible `uname -r` output | `NOT_AVAILABLE` | `6.18.34+rpt-rpi-2712` | `MEDIUM` | Image evidence only; no live command was run by Codex. |
| Keyboard directly attached | `NOT_RUN` | `NOT_PROVIDED` | No approved local check received | `NOT_AVAILABLE` | `NOT_TESTED` | `NONE` | Not visible or otherwise confirmed. |
| Physical local-console path | `NOT_RUN` | `NOT_PROVIDED` | No owner attestation for this image received | `NOT_AVAILABLE` | `PHOTO_OBSERVED_PHYSICAL_PATH_UNVERIFIED` | `NONE` | Do not promote to `OWNER_ATTESTED_WITH_PHOTO` without the owner confirming direct display and direct keyboard use. |
| Owner recovery capability | `OWNER_ATTESTED` | `NOT_PROVIDED` | Prior owner statement | `NOT_AVAILABLE` | `RECOVERY_CAPABILITY=OWNER_CONFIRMED` | `MEDIUM` | Capability assertion is not a recovery drill and does not prove recovery during Wi-Fi failure. |
| Prior upstream path | `PRIOR_SSH_OBSERVATION` | `2026-09-22 22:01` | Prior read-only inventory | `0` | `wlan0` previously carried the observed address/default route; exact network values remain redacted. | `HIGH_FOR_PRIOR_SNAPSHOT` | Stale, session-scoped evidence. Do not move `wlan0` to AP, interrupt Wi-Fi or assume a hotspot is active. |
| AP/STA role mapping | `NOT_RUN` | `NOT_PROVIDED` | No new approved survey output | `NOT_AVAILABLE` | `UNVERIFIED` | `NONE` | Driver/interface observations do not establish roles. |
| NetworkManager state | `NOT_RUN` | `NOT_PROVIDED` | No new approved local output | `NOT_AVAILABLE` | `UNVERIFIED` | `NONE` | No service action or profile/secret query is permitted. |
| AP capability / concurrent AP+STA | `NOT_RUN` | `NOT_PROVIDED` | `iw` not authorized and was unavailable in prior session | `NOT_AVAILABLE` | `UNVERIFIED` | `NONE` | Do not install `iw`, scan Wi-Fi or infer capability. |
| Recovery during network failure | `NOT_RUN` | `NOT_PROVIDED` | No failure drill | `NOT_AVAILABLE` | `NOT_TESTED` | `NONE` | No interface was interrupted. |

## Current classification

```text
PHOTO_TERMINAL_VISIBLE=OWNER_PHOTO_EVIDENCE
PHOTO_TTY=/dev/pts/0
PHOTO_USER=pi5
PHOTO_KERNEL=6.18.34+rpt-rpi-2712
LOCAL_CONSOLE_LOGIN=PHOTO_OBSERVED_PHYSICAL_PATH_UNVERIFIED
RECOVERY_CAPABILITY=OWNER_CONFIRMED
RECOVERY_DURING_NETWORK_FAILURE=NOT_TESTED
INDEPENDENT_RECOVERY_PATH=UNVERIFIED
AP_MODE_SUPPORTED=UNVERIFIED
ONBOARD_AP_VERIFIED=UNVERIFIED
USB_STA_VERIFIED=UNVERIFIED
UPSTREAM_SUBNET_CONFLICT_CHECK=NOT_EVALUATED
LIVE_NETWORK_AUTHORIZATION=NOT_GRANTED
N4=BLOCKED/NOT_RUN
OWNER_LOCAL_OUTPUT=NOT_RECEIVED
```

The image does not justify `OWNER_ATTESTED_WITH_PHOTO`, `INDEPENDENT_RECOVERY_PATH=VERIFIED`, `AP_MODE_SUPPORTED=YES`, `ONBOARD_AP_VERIFIED`, `USB_STA_VERIFIED` or `N4=PASS`.

## Exact owner-run read-only block

These are commands for the owner to type directly into the terminal on the Pi screen. They are not commands for Codex to run over SSH or on the PC. Run sequentially only if the owner chooses; return `NOT_RUN` instead of substituting another command. Do not use `sudo`, change files/configuration, query saved connections/secrets or install packages.

```bash
# A — local-console context (chỉ Owner chạy trên terminal Pi)
tty
id -un
uname -r

# B — trạng thái trình quản lý mạng (không khởi động hoặc restart)
systemctl is-active NetworkManager
systemctl is-enabled NetworkManager

# C — trạng thái interface; các dòng có MAC/IP/SSID phải được che trước khi gửi
nmcli --fields DEVICE,TYPE,STATE,CONNECTION device status
ip -br link
ip -br addr
ip route

# D — chỉ xem nhận diện driver cho hai interface, không suy ra vai trò từ tên
for iface in wlan0 wlan1; do printf '%s driver=' "$iface"; basename "$(readlink -f "/sys/class/net/$iface/device/driver")"; done
```

If the `nmcli` command is rejected, stop that step and report `UNSUPPORTED_FIELDS`; do not use `nmcli connection show` and do not inspect profiles or PSKs. Do not try `iw`, install `iw`/a driver/package, scan Wi-Fi, interrupt the current Wi-Fi path or change interface names. If an interface in section D is absent, report `INTERFACE_NOT_PRESENT`.

Before sending output, redact IP addresses, MACs, SSID/BSSID, gateway values, serials, saved-profile names if sensitive, credentials and full logs. For the subnet check, send only `UPSTREAM_SUBNET_CONFLICT_CHECK=PASS`, `CONFLICT` or `UNKNOWN` plus the checked scope; if no AP range has been approved, use `NOT_EVALUATED`.

## Stop boundary

Until the owner returns the redacted local output, no result report will be created and no addendum will be appended to the live AP/STA proposal. The prior Mức B SSH session is finished and grants no SSH permission for this turn. No Wi-Fi scan, AP/STA test, network failure test, package installation, service restart, reboot, PC↔Pi exchange or SCOPE-04/05/06 work is authorized.
