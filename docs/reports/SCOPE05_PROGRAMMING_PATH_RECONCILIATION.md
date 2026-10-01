# SCOPE-05 Programming-Path Reconciliation

Assessment date: `2026-09-26` (Asia/Ho_Chi_Minh).

## Evidence boundary

This is a read-only visual ingest of the two Owner-provided board photos. No
USB retry, serial open, driver installation, electrical measurement,
continuity test, firmware operation or hardware access was performed.

## Photo-supported facts

| Element | Photo evidence | Status |
|---|---|---|
| USB connector | Symmetrical USB-C receptacle is visible at the board edge | `VERIFIED_FROM_PHOTO` |
| CP2102 bridge identity | Owner states onboard `CP2102`; the lower bridge-chip marking is not legible | `OWNER_PROVIDED` / `UNVERIFIED_FROM_PHOTO` |
| ESP32 family | Shield visibly carries `WiFi+BT SoC` and an `ESP32...`-like marking; suffix is unreadable | `PARTIAL` |
| `RST` / reset control | `RST` button is visibly labelled | `VERIFIED_FROM_PHOTO` for label/control only |
| `BOOT` / IO0 control | `BOOT` button is visibly labelled | `VERIFIED_FROM_PHOTO` for label/control only |
| ESP32 `EN` | `EN` side-header label is visible | `VERIFIED_FROM_PHOTO` for label only |
| ESP32 `TX0` / `RX0` | `TX0` and `RX0` side-header labels are visible | `VERIFIED_FROM_PHOTO` for labels only |
| `GND` / `3V3` | These side-header labels are visible | `VERIFIED_FROM_PHOTO` for labels only |

The rear photo does not expose a readable schematic, net names or routing that
would prove connectivity between the connector, bridge, UART0 or reset logic.

## Path matrix

| Required path/fact | Assessment | Reason |
|---|---|---|
| USB connector -> CP2102 physical connection | `UNVERIFIED` | Connector and a candidate bridge location are visible, but no trace/net proof is readable |
| USB VBUS -> CP2102 | `UNVERIFIED` | No readable schematic or trace proof |
| USB D+ / D- -> CP2102 | `UNVERIFIED` | No readable schematic or trace proof |
| CP2102 TX -> ESP32 UART0 RX | `UNVERIFIED` | `RX0` label is visible, but no bridge-to-pin routing is proven |
| CP2102 RX <- ESP32 UART0 TX | `UNVERIFIED` | `TX0` label is visible, but no bridge-to-pin routing is proven |
| CP2102 DTR/RTS auto-reset | `UNVERIFIED` | `RST`/`BOOT` buttons do not prove DTR/RTS circuitry |
| ESP32 EN/reset circuit | `PARTIAL` | `EN` label and `RST` control are visible; circuit/net behavior is not proven |
| ESP32 IO0/BOOT circuit | `PARTIAL` | `BOOT` control is visible; circuit/net behavior is not proven |
| 5V rail | `UNVERIFIED` | No sufficiently clear 5V label or routing evidence |
| 3V3 rail | `PARTIAL` | `3V3` label is visible; rail connectivity is not proven |
| Ground path | `PARTIAL` | `GND` labels are visible; common USB/bridge/ESP ground is not traced |

```text
USB_PROGRAMMING_PATH=PARTIAL
CP2102_PROGRAMMING_UART=UART0_OR_BOARD_SPECIFIC_PATH_TO_BE_VERIFIED
BOARD_PROFILE=PARTIAL
FLASH_GATE=BLOCKED
```

The procurement record for `CH340G` remains procurement evidence only and is
not treated as the onboard bridge.

## Current USB-host qualification

The physical path remains a photo-based `PARTIAL` result. Runtime USB evidence
must be collected on the Raspberry Pi 5 because that is the current USB host.
No Pi 5 shell was available; the PC-local USB observations are not substituted.

```text
CURRENT_USB_HOST=RASPBERRY_PI_5
PI5_SHELL_UNAVAILABLE
PI5_USB_EVIDENCE=NOT_COLLECTED
USB_PROGRAMMING_PATH=PARTIAL
FLASH_GATE=BLOCKED
```

```text
CURRENT_USB_HOST=RASPBERRY_PI_5
PC_USB_EVIDENCE=HISTORICAL_NON_AUTHORITATIVE_FOR_CURRENT_ATTACHMENT
PI5_USB_DIAGNOSIS=BLOCKED_NO_EXISTING_AUTHORIZED_SHELL
PI5_DISCOVERY_METHOD=PASSIVE_MDNS_AND_NEIGHBOR
PI5_CANDIDATE_IPS=192.168.1.118
PI5_AUTH_STATE=NO_NONINTERACTIVE_AUTHORIZED_PATH
```

```text
PI5_AUTOMATION_KEY_FINGERPRINT=SHA256:VrUiXWY9kkxBKt+BwjXv6NMBtsUxOl8kxBXR+rv46i4
PI5_KEYPAIR_PREPARED=yes
PI5_KEY_INSTALLATION=BLOCKED_REQUIRES_ONE_TIME_OWNER_BOOTSTRAP
PI5_USB_EVIDENCE=NOT_COLLECTED
PI5_USB_DIAGNOSIS=BLOCKED_REQUIRES_ONE_TIME_OWNER_BOOTSTRAP
FLASH_GATE=BLOCKED
```

## Board-identity gate re-evaluation

No new sharp marking, schematic, manufacturer document or net diagram was
provided in this turn. The canonical result therefore remains:

```text
ESP_IDENTITY=PARTIAL_EXACT_VARIANT_UNVERIFIED
BOARD_PROFILE=PARTIAL
USB_PROGRAMMING_PATH=PARTIAL
MEASUREMENT_PLAN=BLOCKED_INSUFFICIENT_TEST_POINT_EVIDENCE
FLASH_GATE=BLOCKED
```

## Pi-host runtime confirmation

```text
USB_DIAG_HOST=RASPBERRY_PI_5
PI5_USB_ENUMERATION=PASS
PI5_SERIAL_NODE=PASS
PI5_CP2102_DRIVER_STATE=BOUND
PI5_VID_PID=10c4:ea60
PI5_TTY_NODE=/dev/ttyUSB0
PI5_TTY_DRIVER=cp210x
USB_PROGRAMMING_PATH=PARTIAL
NEXT_GATE=PI5_READ_ONLY_ESP_IDENTITY
FLASH_GATE=BLOCKED
```

Runtime enumeration confirms the USB bridge and tty path on the Pi, but does
not prove PCB-level USB-to-UART routing or ESP32 identity.

## 2026-09-27 FAST TRACK update

Pi-host read-only identity commands succeeded through the already verified
CP2102 endpoint:

```text
PI5_USB_ENUMERATION=PASS
PI5_SERIAL_NODE=PASS
PI5_CP2102_DRIVER_STATE=BOUND
PI5_TTY_NODE=/dev/ttyUSB0
ESP_IDENTITY=PASS_READ_ONLY
ESP_CHIP_MODEL=ESP32-D0WD-V3
ESP_CHIP_REVISION=v3.1
FLASH_SIZE=4MB
USB_PROGRAMMING_PATH=PARTIAL
CP2102_TO_UART0=UNVERIFIED
EN_IO0_AUTO_RESET=UNVERIFIED
FLASH_GATE=BLOCKED
```

The path is `PARTIAL`, not `VERIFIED`: the Pi proves USB enumeration and ROM
response, while the board photos/labels do not prove the USB differential
route, UART0 net continuity or EN/IO0 auto-reset circuit. No write or erase
operation was attempted.
