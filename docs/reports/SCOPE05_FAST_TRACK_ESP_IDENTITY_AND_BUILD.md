# SCOPE-05 FAST TRACK — ESP Identity, Build and GNSS Preparation

**Execution date:** 2026-09-27 (Asia/Ho_Chi_Minh)  
**Scope:** read-only ESP identity, repository/source audit, build eligibility and GNSS preparation.  
**Out of scope:** flash, erase, firmware write, persistent GNSS configuration, motor/ESC activity, ARM/DISARM and SCOPE-06+.

## Evidence boundary

The USB endpoint evidence in this addendum was collected on the Raspberry Pi 5
host, not on the PC. The Pi shell was verified as:

```text
PI5_HOSTNAME=pitan
PI5_MODEL=Raspberry Pi 5 Model B Rev 1.0
PI5_USB_ENUMERATION=PASS
PI5_SERIAL_NODE=PASS
PI5_CP2102_DRIVER_STATE=BOUND
PI5_VID_PID=10c4:ea60
PI5_USB_PRODUCT=CP2102_USB_to_UART_Bridge_Controller
PI5_TTY_NODE=/dev/ttyUSB0
PI5_TTY_DRIVER=cp210x
```

Before identity probing, the Pi-side exclusivity check found no process owning
`/dev/ttyUSB0` (`fuser` produced no owner; `lsof` produced no owner output).
The device was not used for application serial capture.

## Read-only ESP identity

`esptool` was absent from the Pi's normal PATH. Per the approved fast-track
procedure it was installed into the temporary, isolated directory
`/tmp/scope05-esptool`; no system package or driver was installed.

Commands and observed result:

| Command | Exit | Result |
|---|---:|---|
| `python3 -m venv /tmp/scope05-esptool` | 0 | Temporary venv created |
| `/tmp/scope05-esptool/bin/python -m pip install esptool` | 0 | esptool 5.4.0 installed in temporary venv |
| `/tmp/scope05-esptool/bin/python -m esptool version` | 0 | 5.4.0 |
| `... esptool --port /dev/ttyUSB0 --before default-reset --after no-reset --no-stub --connect-attempts 1 chip-id` | 0 | ROM identity read |
| same options + `read-mac` | 0 | MAC read; raw identifier redacted and not stored |
| same options + `flash-id` | 0 | flash identification read |

Observed identity:

```text
ESP_IDENTITY=PASS_READ_ONLY
ESP_CHIP_FAMILY=ESP32
ESP_CHIP_MODEL=ESP32-D0WD-V3
ESP_CHIP_REVISION=v3.1
ESP_FEATURES=Wi-Fi, BT, dual core + LP core, 240MHz
ESP_CRYSTAL=40MHz
FLASH_SIZE=4MB
FLASH_VOLTAGE_REPORTED=3.3V_STRAPPING_PIN
ESP_MAC=REDACTED_NOT_STORED
```

No write-flash, erase, verify, load-ram, run, GNSS configuration or other
mutation command was executed. The tool remained in the bootloader after each
read-only command; no application serial stream was opened.

## Existing source and build audit

The archive `FC_can_bang.zip` was inspected read-only. Its recorded SHA-256 is
`95809c58d61bb20c12a9541719ad90ec4afc8dab74597a20517486174849771f`.
The archive contains seven `.ino` files and no `platformio.ini`, Arduino CLI
manifest, ESP-IDF `CMakeLists.txt`/`sdkconfig`, dependency manifest or board
target metadata. The PC also has no `platformio`, `pio`, `arduino-cli`,
`idf.py` or ESP32 cross-compiler on PATH.

```text
BUILD_SYSTEM=NONE_FOUND
BUILD_TARGET_USED=NONE
BUILD_RESULT=BLOCKED_MISSING_BUILD_METADATA_AND_TOOLCHAIN
```

Compiling was therefore not attempted. A guessed board target would not be
defensible evidence.

## Source pin and peripheral reconciliation

The following are source declarations only; they are not physical continuity
or wiring proof:

| Function | Source fact | ESP32-D0WD-V3 compatibility assessment |
|---|---|---|
| SBUS RX | `HardwareSerial(2)`, `100000`, `SERIAL_8E2`, inverted, RX `GPIO35`, TX `-1` (`FC_can_bang.zip:FC_can_bang/Sbus.ino:2-3,61-64`) | `SOURCE_COMPATIBLE`: GPIO35 is input-only and is used only as RX; physical wiring remains unverified |
| ESC outputs | GPIO27, 26, 25, 33 (`ESCino.ino:6-9`) | `SOURCE_COMPATIBLE_OUTPUT_CAPABLE`; actuator path is not tested or enabled by this task |
| ICM20602 CS | GPIO5, SPI mode 0, 1 MHz (`ICM20602.ino:7-8,20,40-43`) | `PARTIAL`: GPIO5 is usable as a GPIO/SPI CS after boot but is a strapping pin; external pull state and board routing are unverified |
| UART0/debug candidate | `Serial.begin(115200)` (`ICM20602.ino:40`) and board labels `TX0/RX0` from prior photo evidence | `PARTIAL`: USB-UART-to-UART0 net and auto-reset routing are not proven by schematic/continuity |
| Loop timing | busy wait `5000` microseconds (`FC_can_bang.ino:125-126`) | `SOURCE_DECLARED_APPROX_200HZ`; jitter/overrun not measured |

No source declaration assigns a GNSS UART. Historical GPIO16/GPIO17 notes are
not promoted to a current assignment.

## GNSS preparation

The current BZ251 facts remain Owner-provided: 38400 bps default, 1 Hz default,
10 Hz maximum/target, NMEA 4.0/4.1 and UBX, with TX/RX/GND/VCC/SCL/SDA labels.
The exact module datasheet, VCC range, I/O voltage/tolerance, ESP32-side route,
common ground and exact 10 Hz command remain unverified.

```text
GNSS_UART_CANDIDATES=UNASSIGNED
GNSS_UART_SELECTED=NONE
LOGIC_POWER_COMPATIBILITY=BLOCKED_EXACT_BZ251_ELECTRICAL_DATA_MISSING
GNSS_INTEGRATION_PATCH=NOT_PREPARED_BLOCKED_BUILD_AND_PHYSICAL_UART
```

No firmware patch, GNSS parser route, UART assignment or configuration command
was created. Existing SBUS/UART2, ICM20602 and ESC source paths were left
unchanged.

## Gate result

```text
ESP_IDENTITY=PASS_READ_ONLY
SOURCE_PINMAP_COMPATIBILITY=PARTIAL_SOURCE_ONLY
BUILD_SYSTEM=NONE_FOUND
BUILD_TARGET_USED=NONE
BUILD_RESULT=BLOCKED
GNSS_UART_CANDIDATES=UNASSIGNED
GNSS_UART_SELECTED=NONE
LOGIC_POWER_COMPATIBILITY=BLOCKED
GNSS_INTEGRATION_PATCH=NOT_PREPARED
NEXT_GATE=BUILD_TARGET_RECONCILIATION_AND_GNSS_HARDWARE_EVIDENCE
FLASH_GATE=BLOCKED
```

The successful ROM identity read closes the ESP identity blocker, but it does
not establish an exact development-board model, wiring, GNSS electrical
compatibility or a reproducible firmware build.

## 2026-09-27 MEGA FAST TRACK continuation

The dedicated Pi key is now repaired and verified with `KEY_AUTH_OK`. The
compatibility build was retried through isolated PlatformIO environments but
did not reach compilation: Arduino ESP32 framework staging failed with
`Errno 28: No space left on device`.

New BZ251 evidence is conflicting: the vendor page reports 115200 bps and
10 Hz default, while the product-spec PDF/manual reports 38400 bps and 1 Hz
default. The Owner-provided `38400/1 Hz` intent remains preserved; no live
configuration value was selected.

```text
PI5_KEY_AUTH=PASS
BUILD_TOOLCHAIN=BLOCKED_FRAMEWORK_INSTALL_ERRNO_28
BUILD_ORIGINAL_RESULT=BLOCKED_BEFORE_COMPILE
BUILD_GNSS_DISABLED_RESULT=BLOCKED_SAME_TOOLCHAIN_DEPENDENCY
GNSS_DATASHEET_STATUS=CONFLICTING_VENDOR_PAGE_AND_DATASHEET_MIRROR
GNSS_UART_SELECTED=NONE
GNSS_INTEGRATION_PATCH=PREPARED_DISABLED_BY_DEFAULT_REPO_BOUNDARY
GNSS_READ_ONLY_CAPTURE_TOOL=PREPARED_NOT_RUN
GNSS_LIVE_CAPTURE=BLOCKED
NEXT_GATE=BUILD_COMPATIBILITY_FIX
FLASH_GATE=BLOCKED
```
