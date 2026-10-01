# SCOPE-05 USB Physical-Path Diagnosis

Assessment date: `2026-09-26` (Asia/Ho_Chi_Minh).

## Safety and boundary

```text
PROPS_REMOVED_OR_PHYSICALLY_ISOLATED=OWNER_PROVIDED=yes
ESC_MOTOR_POWER_DISCONNECTED=OWNER_PROVIDED=yes
NO_LIPO_OR_HIGH_POWER_MOTOR_SUPPLY=OWNER_PROVIDED=yes
BOARD_POWERED_FROM_USB_ONLY=OWNER_PROVIDED=yes
```

The observation was read-only. No serial port was opened, no driver or package
was installed, and no firmware/GNSS/motor action occurred.

## BASELINE_USB

Captured at `2026-09-26T16:51:30+07:00` with the board not visible:

```text
lsusb=Linux root hubs + keyboard + mouse + Genesys Logic hub only
ttyUSB=none
ttyACM=none
serial_by_id=none
serial_by_path=none
```

The baseline topology contained no ESP/USB-UART device.

Owner clarification received after the observation:

```text
USB_UART_BRIDGE=CP2102
CP2102_LOCATION=ONBOARD
EVIDENCE_CLASS=OWNER_PROVIDED
BOARD_PHOTO_EVIDENCE=REQUIRED
USB_PHYSICAL_PATH_DIAGNOSIS=PENDING_PHOTO_EVIDENCE
```

This was the pre-photo state. The later Owner-provided photos are reconciled
below; they do not change the observed no-enumeration result.

## LIVE_HOTPLUG_EVENT

```text
OWNER_CONFIRMATION=BOARD_REPLUG_COMPLETED=yes
OBSERVER=udevadm monitor --kernel --udev --property
USB_ADD_EVENT=NOT_OBSERVED
USB_REMOVE_EVENT=NOT_OBSERVED
TTY_EVENT=NOT_OBSERVED
KERNEL_EVENT=NOT_OBSERVED
```

The observer produced no event output during the reported unplug/replug.
The observer was stopped after the post-plug snapshot.

Protocol note: the observer remained active for approximately 9 minutes 43
seconds while waiting for the Owner confirmation, exceeding the prompt's
nominal 120-second observation bound. No state-changing operation occurred;
this is recorded as an observation-procedure deviation.

## POST_PLUG_USB

Captured at `2026-09-26T17:01:13+07:00`:

```text
lsusb=unchanged; no ESP/USB-UART device
lsusb_-t=unchanged; no new USB topology entry
ttyUSB=none
ttyACM=none
serial_by_id=none
serial_by_path=none
recent_kernel_usb_serial_log=no matching entries
```

## Classification

```text
USB_PHYSICAL_ENUMERATION=FAIL_NO_EVENT
SERIAL_NODE=NOT_PRESENT
VID_PID=NOT_DETECTED
USB_PRODUCT=NOT_DETECTED
USB_DRIVER=NOT_DETECTED
```

This result does not distinguish cable, PC port, board connector, board USB
power/LED state or absence of onboard USB-UART. It only proves that this PC
observed no USB enumeration event in this attempt.

## Owner board-photo ingest

Two Owner-provided photos were ingested read-only on `2026-09-26`:

```text
BOARD_PHOTO_EVIDENCE=INGESTED
USB_CONNECTOR=USB_TYPE_C_VERIFIED_FROM_PHOTO
RST_BUTTON=VISIBLE
BOOT_BUTTON=VISIBLE
EN_LABEL=VISIBLE
TX0_LABEL=VISIBLE
RX0_LABEL=VISIBLE
GND_LABEL=VISIBLE
3V3_LABEL=VISIBLE
CP2102_MARKING=UNVERIFIED_NOT_LEGIBLE
USB_TO_CP2102_ROUTING=UNVERIFIED
CP2102_TO_UART0_ROUTING=UNVERIFIED
EN_IO0_AUTO_RESET=UNVERIFIED
```

The rear photo does not provide readable routing or a schematic. The visible
labels are not continuity evidence and do not change the earlier no-event
observation.

```text
USB_PHYSICAL_PATH_DIAGNOSIS=PARTIAL_PHOTO_RECONCILIATION
USB_PROGRAMMING_PATH=PARTIAL
FLASH_GATE=BLOCKED
```

## NEXT_BLOCKER

Keep the flash and hardware gates blocked. The smallest physical-path evidence
request is:

1. obtain a readable board schematic or net-level evidence for the USB-to-
   bridge and bridge-to-UART0 paths;
2. confirm the exact ESP32 module/board variant from a legible marking or
   authoritative board documentation;
3. if live USB diagnosis is later authorized, separately verify the cable,
   PC port and board connector without assuming the photo proves enumeration.

Do not guess adapter wiring or install drivers before a USB device identity is
observed.

## Autonomous machine-readable refresh

At `2026-09-26T20:14:48+07:00` through `2026-09-26T20:15:58+07:00`, the
auto-only snapshot and a bounded 55-second `udevadm monitor` window found no
CP210x/ESP32 device, tty node or board-related kernel event. The host xHCI
controller and existing unrelated USB devices were visible.

```text
AUTO_USB_RESULT=NO_DEVICE_NO_EVENT
AUTO_DIAG_LIMIT=PHYSICAL_LAYER_NOT_MACHINE_OBSERVABLE
DRIVER_DIAGNOSIS=NOT_REACHED_DEVICE_DID_NOT_ENUMERATE
ELECTRICAL_MEASUREMENT=UNAVAILABLE_AUTONOMOUSLY
USB_POWER_SANITY_CHECK=AUTO_ONLY
```

This is an autonomous refresh, not a replacement of the earlier historical
hot-plug snapshot. It does not distinguish cable, connector, CP2102, regulator
or board-power failure.

## Current host qualification

The Owner reports the board is now attached to the Pi 5. The current shell was
verified as Ubuntu x86_64 on `pnt-MS-7D48`, not Raspberry Pi 5. Therefore no
Pi-side USB inventory or observer was run.

```text
CURRENT_USB_HOST=RASPBERRY_PI_5
USB_DIAG_HOST=NOT_PI5
PI5_SHELL_UNAVAILABLE
PI5_USB_EVIDENCE=NOT_COLLECTED
PI5_USB_ENUMERATION=NOT_COLLECTED
PI5_SERIAL_NODE=NOT_COLLECTED
PI5_PASSIVE_USB_EVENT=NOT_RUN
```

The PC-local autonomous result above remains historical and is not a conclusion
about the current Pi 5 USB host.

## Pi access discovery

```text
PI5_SHELL_UNAVAILABLE
PI5_USB_EVIDENCE=NOT_COLLECTED
PI5_USB_DIAGNOSIS=BLOCKED_NO_EXISTING_AUTHORIZED_SHELL
PC_USB_EVIDENCE=HISTORICAL_NON_AUTHORITATIVE_FOR_CURRENT_ATTACHMENT
PI5_DISCOVERY_METHOD=PASSIVE_MDNS_AND_NEIGHBOR
PI5_CANDIDATE_IPS=192.168.1.118
PI5_AUTH_METHOD=EXISTING_SSH_KEY_ONLY
PI5_AUTH_STATE=NO_NONINTERACTIVE_AUTHORIZED_PATH
```

```text
PI5_AUTOMATION_KEY_FINGERPRINT=SHA256:VrUiXWY9kkxBKt+BwjXv6NMBtsUxOl8kxBXR+rv46i4
PI5_KEYPAIR_PREPARED=yes
PI5_KEY_INSTALLATION=BLOCKED_REQUIRES_ONE_TIME_OWNER_BOOTSTRAP
PI5_USB_EVIDENCE=NOT_COLLECTED
FLASH_GATE=BLOCKED
```

```text
PI5_KEY_AUTH=FAILED
PI5_SSH_RESULT=PERMISSION_DENIED_PUBLICKEY
PI5_USB_EVIDENCE=NOT_COLLECTED
PI5_USB_DIAGNOSIS=BLOCKED_PI5_KEY_AUTH_FAILED
NEXT_GATE=PI5_KEY_INSTALLATION_RECONCILIATION
FLASH_GATE=BLOCKED
```

No Pi USB evidence is asserted in this report.

## Current Pi-host evidence

The latest authenticated session changed the current host evidence from
`NOT_COLLECTED` to a verified Pi-side USB result:

```text
CURRENT_USB_HOST=RASPBERRY_PI_5
PI5_USB_EVIDENCE=COLLECTED_ON_PI5
PI5_USB_ENUMERATION=PASS
PI5_SERIAL_NODE=PASS
PI5_CP2102_DRIVER_STATE=BOUND
PI5_VID_PID=10c4:ea60
PI5_USB_PRODUCT=CP2102_USB_to_UART_Bridge_Controller
PI5_TTY_NODE=/dev/ttyUSB0
PI5_PASSIVE_USB_EVENT=NONE_OBSERVED
NEXT_GATE=PI5_READ_ONLY_ESP_IDENTITY
FLASH_GATE=BLOCKED
```

## 2026-09-27 Pi-host continuation

The already verified Pi USB path was used for read-only ESP ROM identity. No
USB retry, driver installation, flash, erase, serial write or GNSS command was
performed.

```text
USB_DIAG_HOST=RASPBERRY_PI_5
PI5_USB_ENUMERATION=PASS
PI5_SERIAL_NODE=PASS
PI5_CP2102_DRIVER_STATE=BOUND
PI5_TTY_NODE=/dev/ttyUSB0
ESP_IDENTITY=PASS_READ_ONLY
ESP_CHIP_MODEL=ESP32-D0WD-V3
ESP_CHIP_REVISION=v3.1
FLASH_SIZE=4MB
USB_PHYSICAL_PATH=PI_ENUMERATED_CP2102_PATH
USB_TO_UART0=UNVERIFIED_BOARD_ROUTE
FLASH_GATE=BLOCKED
```
