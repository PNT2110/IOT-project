# SCOPE-05 USB Identify / Build Gate Report

Assessment date: `2026-09-26` (Asia/Ho_Chi_Minh).

## SAFETY_CONFIRMATION

The following conditions were explicitly supplied by the Owner and recorded as
`OWNER_PROVIDED`; they were not independently probed:

```text
PROPS_REMOVED_OR_PHYSICALLY_ISOLATED=yes
ESC_MOTOR_POWER_DISCONNECTED=yes
NO_LIPO_OR_HIGH_POWER_MOTOR_SUPPLY=yes
BOARD_POWERED_FROM_USB_ONLY=yes
```

No ESP32 board was accessed or powered by Codex. No serial port was opened.

## USB_DEVICE

```text
USB_SERIAL_NODE=NOT_DETECTED
USB_VID_PID=NOT_DETECTED
USB_BRIDGE=NOT_DETECTED
```

Read-only `lsusb` showed only Linux root hubs, an Apple keyboard, a Logitech
mouse and a Genesys Logic USB hub. No `/dev/ttyUSB*` or `/dev/ttyACM*` node was
present, so no `udevadm` target or chip-identification command was run.

## ESP_CHIP

```text
ESP_CHIP_FAMILY=NOT_IDENTIFIED
ESP_REVISION=NOT_IDENTIFIED
FLASH_VENDOR=NOT_IDENTIFIED
FLASH_SIZE=NOT_IDENTIFIED
MAC_REDACTED=NOT_IDENTIFIED
```

`esptool` is not installed in the PC environment, and there was no selected
USB serial node on which to run read-only identification. No MAC or other
device identifier was fabricated.

## FLASH

```text
FLASH_OPERATION=NOT_RUN
ERASE_FLASH=NOT_RUN
WRITE_FLASH=NOT_RUN
EFUSE_OR_SECURITY_CHANGE=NOT_RUN
```

No flash-related command was executed.

## BOARD_PROFILE

```text
BOARD_PROFILE=BLOCKED_NO_USB_ID
BOARD_TARGET=NOT_VERIFIED
```

The repository contains only the read-only `FC_can_bang.zip` archive with
seven `.ino` files. It has no `platformio.ini`, Arduino CLI project, ESP-IDF
configuration, board selection or build manifest. The archive source facts
remain unchanged: ICM20602/SPI, SBUS UART2 RX GPIO35, and ESC outputs
GPIO27/26/25/33.

## BUILD

```text
BUILD_COMMAND=NOT_RUN_BLOCKED_NO_BUILD_SYSTEM_OR_BOARD_TARGET
TOOLCHAIN_VERSION=NOT_AVAILABLE
BINARY_SIZE=NOT_AVAILABLE
FLASH_USAGE=NOT_AVAILABLE
RAM_USAGE=NOT_AVAILABLE
BUILD_RESULT=BLOCKED
```

No firmware source was modified and no build artifact was produced. A build
cannot be claimed without a verified board target and an applicable build
configuration/toolchain.

## GNSS_WIRING_STATUS

```text
GNSS_PHYSICAL_WIRING=BLOCKED
GNSS_POWER_LOGIC_COMPATIBILITY=BLOCKED
```

USB identification does not establish BZ251 wiring, VCC, I/O voltage, GNSS
RX/TX pins or common ground. `TTL` is not treated as proof of 5V tolerance.

## BZ251_10HZ_COMMAND_STATUS

```text
BZ251_10HZ_CAPABILITY=OWNER_PROVIDED_SPEC
BZ251_10HZ_COMMAND=BLOCKED_PENDING_EXACT_COMMAND_REFERENCE
```

No generic UBX rate command was constructed or transmitted.

## FLASH_GATE

```text
FLASH_GATE=BLOCKED
```

The safety precondition is Owner-provided, but USB/chip identity, board/build
target and firmware build are not verified. This report does not authorize a
future flash operation.
