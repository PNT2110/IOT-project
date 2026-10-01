# SCOPE-03 Pi Read-Only Inventory Result — Mức B

**STATUS: `OBSERVED_ON_PI_READ_ONLY`**  
**Captured:** 2026-09-22 22:01 (Asia/Ho_Chi_Minh)  
**Device scope:** `192.168.1.118` only  
**Authorization:** Explicit user approval in the current turn for Codex to SSH now as non-root user `pi5` for read-only inventory.  
**Access method:** SSH with an already trusted host key and existing SSH key authentication; password was not entered, stored or logged.  
**Operator:** Codex in the current PC workspace.  
**Output handling:** Only this redacted summary was written to the repository; raw addresses, MACs, SSID/BSSID, credentials and PII are not recorded.

## P0 gate

| Check | Result |
|---|---|
| Repository baseline | `/home/pnt/IOT`, branch `main`, HEAD `16dc418076b1a53a9d2fc9af482e3a514f0791f7`; dirty/untracked worktree preserved. |
| Host key | Pre-existing `known_hosts` entry matched; connection used `StrictHostKeyChecking=yes`. No new/changed host key was accepted. |
| Authentication | SSH key succeeded for the authorized non-root account; no password mechanism was used. |
| Console/HDMI/keyboard or independent OOB recovery | `UNVERIFIED`; this read-only session does not verify it. |
| Network-change authorization | `NOT_GRANTED`; no network mutation was attempted. |

## Exact commands and results

Commands were run sequentially over the authorized SSH session. Exit codes are from the remote command.

| Command | Exit | Redacted observation |
|---|---:|---|
| `uname -a` | 0 | Debian kernel `6.18.34+rpt-rpi-2712`, `aarch64`; hostname redacted. |
| `cat /etc/os-release` | 0 | Debian GNU/Linux 13 (`trixie`), full release `13.5`. |
| `cat /proc/device-tree/model` | 0 | Raspberry Pi 5 Model B Rev 1.0. |
| `ip -br link` | 0 | `lo`, `eth0`, `wlan0`, `wlan1` observed; link states recorded without MAC addresses. `wlan0` was up; `eth0` and `wlan1` had no carrier. |
| `ip -br addr` | 0 | Address data observed and redacted; `wlan0` carried address data at capture time. |
| `ip route` | 0 | Default and connected routes observed through `wlan0`; all address/subnet values redacted. |
| `lsusb` | 0 | USB inventory included a Realtek 802.11ac NIC and another USB composite device; exact IDs are not included here. |
| `iw dev` | 127 | `NOT_AVAILABLE`: `iw` command not found. No replacement command was attempted. |
| `iw phy` | 127 | `NOT_AVAILABLE`: `iw` command not found. No PHY/AP-managed capability evidence collected. |
| `nmcli --fields GENERAL.DEVICE,GENERAL.TYPE,GENERAL.STATE,GENERAL.CONNECTION device status` | 2 | `NOT_AVAILABLE`: installed `nmcli` rejected the requested `GENERAL.*` fields; no profile/secret query or alternative was attempted. |
| `for iface in /sys/class/net/*; do name="${iface##*/}"; printf '%s ' "$name"; readlink -f "$iface/device/driver"; done` | 0 | `eth0 → macb`; `wlan0 → brcmfmac`; `wlan1 → rtw88_8821cu`; loopback had no device driver path. |

## Evidence classification

### `OBSERVED_ON_PI_READ_ONLY`

- Raspberry Pi 5 Model B Rev 1.0, Debian 13/trixie, kernel/aarch64 facts above.
- Four network interfaces were present; only redacted state/address facts are retained.
- USB Realtek 802.11ac adapter was observed.
- Sysfs driver paths mapped `wlan0` to `brcmfmac` and `wlan1` to `rtw88_8821cu`; `eth0` mapped to `macb`.
- A current route/address state existed through `wlan0` at capture time.

### `INFERRED_NEEDS_VALIDATION`

- `wlan0` may correspond to the onboard Broadcom path and `wlan1` to the USB Realtek path based on driver metadata, but this report does not assert physical mapping beyond the observed driver names.
- Interface role AP versus STA was not established because `iw` was unavailable and the approved `nmcli` query was unsupported.

### `UNKNOWN`

- Independent console/OOB recovery path.
- Current SSID/BSSID/channel/regulatory domain and AP/managed modes.
- Concurrent AP+STA support, AP continuity during STA failure, client handshake, DHCP/DNS/firewall behavior, TLS/device identity and retention/legal hold.

### `NOT_RUN`

- Wi-Fi scan, Internet/PC probe, AP/STA change, route/DHCP/DNS/firewall change, reboot, package/driver install, hardware peripheral access, PII/data exchange and public exposure.
- Gate N4: real AP remains reachable when STA fails.
- Mức C real-network change or validation.

## Handoff boundary

`PI_READ_ONLY_INVENTORY_AUTHORIZATION=GRANTED_FOR_THIS_SESSION_ONLY`  
`LIVE_NETWORK_AUTHORIZATION=NOT_GRANTED`  
`INDEPENDENT_RECOVERY_PATH=UNVERIFIED`  
`N4=BLOCKED/NOT_RUN`

This result is Mức B inventory evidence only. It does not authorize configuration changes, does not prove AP continuity and does not change SCOPE-03 from `PARTIAL_PC_MOCK_PENDING_LIVE`. See [SCOPE03_READ_ONLY_INVENTORY_APPROVAL_PACKET.md](SCOPE03_READ_ONLY_INVENTORY_APPROVAL_PACKET.md) for the pre-session approval boundary.
