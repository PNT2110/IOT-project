# SCOPE-05 USB Hot-Plug Identify Report

Assessment date: `2026-09-26` (Asia/Ho_Chi_Minh).

## Authorization and safety

```text
OWNER_DECISION=AUTHORIZE_SCOPE05_USB_HOTPLUG_IDENTIFY
BOARD_USB_CONNECTED=yes
PROPS_REMOVED_OR_PHYSICALLY_ISOLATED=OWNER_PROVIDED=yes
ESC_MOTOR_POWER_DISCONNECTED=OWNER_PROVIDED=yes
NO_LIPO_OR_HIGH_POWER_MOTOR_SUPPLY=OWNER_PROVIDED=yes
BOARD_POWERED_FROM_USB_ONLY=OWNER_PROVIDED=yes
```

Only read-only enumeration was attempted. No serial port was opened, no
`esptool` command was run, and no write/configuration/flash action occurred.

## USB enumeration

```text
USB_ENUMERATION=FAIL_NOT_VISIBLE
SERIAL_NODE=NOT_PRESENT
```

Fresh post-connection results:

- `lsusb`: only Linux root hubs, keyboard, mouse and USB hub; no ESP/USB-UART
  device appeared.
- `/dev/ttyUSB*`: none.
- `/dev/ttyACM*`: none.
- `/dev/serial/by-id/`: absent/empty.
- `/dev/serial/by-path/`: absent/empty.
- `journalctl -k --since '5 minutes ago'`: no entries.

No driver installation or package installation was attempted. No external
adapter wiring was guessed; the CH340G record remains procurement-only.

## ESP identity and board profile

```text
ESP_IDENTITY=BLOCKED
ESP_CHIP_FAMILY=NOT_IDENTIFIED
ESP_CHIP_REVISION=NOT_IDENTIFIED
FLASH_MANUFACTURER=NOT_IDENTIFIED
FLASH_DEVICE=NOT_IDENTIFIED
FLASH_SIZE=NOT_IDENTIFIED
BOARD_PROFILE=BLOCKED
```

The source archive still proves only the existing source declarations:
ICM20602/SPI, SBUS UART2 RX GPIO35, and ESC GPIO27/26/25/33. It does not
identify the carrier board.

## Build and flash gates

```text
BUILD_GATE=BLOCKED
BUILD_RESULT=NOT_RUN_NO_USB_ID_AND_NO_BUILD_SYSTEM
FLASH_GATE=BLOCKED
```

`esptool` was not installed because the prompt requires a positively identified
serial node before creating an isolated environment. No build target proposal
was created because the detected facts are insufficient to select a defensible
board/FQBN.

## BZ251 reconciliation

The BZ251 model, 38400 default baud, 1 Hz default rate, 10 Hz maximum/target,
NMEA 4.0/4.1 and UBX support are now recorded as `OWNER_PROVIDED_SPEC` in the
canonical reports. Exact electrical values, ESP32-side wiring and the exact
10 Hz command remain blocked.

## Live hot-plug result

The Owner confirmed `BOARD_REPLUG_COMPLETED=yes` while the read-only observer
was running. No USB add/remove event was observed. The post-plug `lsusb`, USB
topology, tty-node, serial-symlink and recent kernel-log snapshots were
unchanged from baseline.

```text
USB_PHYSICAL_ENUMERATION=FAIL_NO_EVENT
SERIAL_NODE=NOT_PRESENT
ESP_IDENTITY=BLOCKED
BUILD_GATE=BLOCKED
FLASH_GATE=BLOCKED
```

Full timestamps and the observation-procedure timing note are in
`SCOPE05_USB_PHYSICAL_PATH_DIAGNOSIS.md`.
