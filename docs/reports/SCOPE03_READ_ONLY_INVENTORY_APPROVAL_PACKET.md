# SCOPE-03 Read-Only Inventory Approval Packet

**STATUS: `NOT_AUTHORIZED`**  
**Captured:** 2026-09-22 (Asia/Ho_Chi_Minh)  
**Purpose:** Prepare a separately approvable, read-only inventory session for one specific Raspberry Pi. This packet is not a login request and contains no credentials.

## Authorization defaults

```text
PI_READ_ONLY_INVENTORY_AUTHORIZATION=NOT_GRANTED
LIVE_NETWORK_AUTHORIZATION=NOT_GRANTED
INDEPENDENT_RECOVERY_PATH=UNVERIFIED
```

Owner acceptance of SCOPE-02 does not itself authorize Pi access. A new approval must name the exact device, operator, access method, command list, time window and redacted output location. Do not send or record password, PSK, OTP/TOTP, token, cookie or private key.

## Fields the owner/operator must complete

| Field | Value |
|---|---|
| Exact Pi device/label and physical location | `UNASSIGNED` |
| Pi model/board revision/serial handling | `UNVERIFIED` / redact serials from output |
| OS/image and kernel | `UNVERIFIED` |
| Approved operator | `UNASSIGNED` |
| Access method | `UNASSIGNED` — local console/display or SSH must be named |
| Current non-root username | `UNVERIFIED` — never provide password here |
| Onboard adapter/interface | `UNVERIFIED` |
| USB adapter/interface/chipset | `UNVERIFIED` |
| Driver/module facts | `UNVERIFIED` |
| Current subnet/addressing | `UNVERIFIED` — do not infer from history |
| Approved start/end time and timezone | `UNASSIGNED` |
| Redacted output path | `UNASSIGNED` — controlled location, no secrets/PII |
| Independent console/out-of-band recovery | `UNVERIFIED` |
| Owner approval message/reference | `NOT_RECORDED` |

An SSH session through the interface that might later be changed is not an independent recovery path.

## Proposed exact read-only command set

The following commands are candidates for approval only. They must run without `sudo`, without redirection that changes device state, and only after the owner completes the fields above. Output must be reviewed/redacted before storage.

```text
uname -a
cat /etc/os-release
cat /proc/device-tree/model
ip -br link
ip -br addr
ip route
lsusb
iw dev
iw phy
nmcli --fields GENERAL.DEVICE,GENERAL.TYPE,GENERAL.STATE,GENERAL.CONNECTION device status
for iface in /sys/class/net/*; do name="${iface##*/}"; printf '%s ' "$name"; readlink -f "$iface/device/driver"; done
```

The approved command set must not include Wi-Fi scan commands, `nmcli connection show`/secret output, `sudo`, package/driver installation, service restart, profile/config edits, reboot, external probes or any command that changes AP/STA/DHCP/DNS/firewall/route state. BSSID, SSID, addresses, usernames, serials, logs and accidental sensitive output must be redacted before storage.

## Explicit exclusions

This packet does not authorize Wi-Fi scanning, AP/STA configuration, network changes, reboot, firmware/driver installation, webcam/ESP32/GNSS access, firmware access, PC↔Pi transfer, public exposure, or Mức C real-network testing. No Pi login or command may be attempted until the owner gives a separate approval for this exact packet.

## Gate after a future approval

Read-only Mức B may establish OS/kernel/board/interface/chipset/driver/topology facts. It is not proof of AP continuity, client handshake or real network safety. Any Mức C change requires a separate change request, an independently verified console/out-of-band path, last-known-good snapshot, operator present, real client test plan and stepwise rollback. Mức C is not included in this packet.
