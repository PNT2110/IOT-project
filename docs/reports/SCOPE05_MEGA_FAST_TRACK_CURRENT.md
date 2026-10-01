# SCOPE-05 MEGA FAST TRACK — Current Reconciliation

**Execution date:** 2026-09-27 (Asia/Ho_Chi_Minh)  
**Mode:** one-pass independent task execution; report reconciliation performed at the end.  
**Safety boundary:** no flash, erase, firmware upload, eFuse write, GNSS configuration write, motor/ESC command, ARM/DISARM or live GNSS capture.

## Canonical result

```text
PI5_KEY_AUTH=PASS
PI5_USB_PATH=PASS
ESP_IDENTITY=PASS_READ_ONLY
ESP_CHIP_MODEL=ESP32-D0WD-V3
ESP_CHIP_REVISION=v3.1
FLASH_SIZE=4MB
```

The dedicated key was repaired through the already authenticated Pi session by
updating the user-owned `~/.ssh/authorized_keys` path. The key-only retry then
returned `KEY_AUTH_OK` and `hostname=pitan`. No password was stored in the
repository or reports.

The previously verified Pi USB/ESP results were frozen and not re-probed:
CP2102 `10c4:ea60`, `/dev/ttyUSB0`, `cp210x`, Pi 5 model
`Raspberry Pi 5 Model B Rev 1.0`, and read-only ESP ROM identity.

## Source inventory and dependency matrix

The firmware archive `FC_can_bang.zip` contains seven `.ino` files and no
project manifest. The archive hash remains
`95809c58d61bb20c12a9541719ad90ec4afc8dab74597a20517486174849771f`.

| Source | Role | Includes/API | UART/GPIO/control relevance |
|---|---|---|---|
| `FC_can_bang.ino` | main setup/loop, arm/mode dispatch | Arduino timing APIs | calls ICM, SBUS, PID and ESC; 5 ms pacing |
| `Sbus.ino` | SBUS decode | `HardwareSerial.h` | UART2, 100000 8E2 inverted, RX GPIO35, TX `-1` |
| `ESCino.ino` | PWM output | LEDC APIs | ESC GPIO27/26/25/33; actuator path present |
| `ICM20602.ino` | SPI IMU read/calibration | `SPI.h` | CS GPIO5, SPI mode 0, 1 MHz, `Serial.begin(115200)` |
| `MODE.ino` | angle/no-fly mode | Arduino math/control calls | flight-mode and arm-state behavior |
| `PID.ino` | PID state and reset | Arduino math | control behavior |
| `display.ino` | display/debug function | commented Serial diagnostics | no additional active peripheral include |

No external source library is referenced by the archive. Required dependency
resolution is therefore Arduino core + ESP32 Arduino framework, but the
framework was not successfully installed in the isolated build environment.

## Compatibility build result

Two temporary PlatformIO attempts were made with generic `esp32dev` and
`board_build.flash_size=4MB`, explicitly labeled as compatibility targets, not
the physical board identity. PlatformIO 6.2.0 and the Xtensa toolchain began
installing, but the Arduino ESP32 framework package failed during staging with
`Errno 28: No space left on device`; the second attempt used a separate `/tmp`
core/package location and was stopped after the same dependency path remained
unavailable. No compiler/linker result was produced.

```text
BUILD_TOOLCHAIN=BLOCKED_FRAMEWORK_INSTALL_ERRNO_28
BUILD_TARGET_CLASS=GENERIC_COMPATIBILITY_TARGET
BUILD_TARGET_USED=esp32dev_NOT_BUILT
BUILD_ORIGINAL_RESULT=BLOCKED_BEFORE_COMPILE
BUILD_GNSS_DISABLED_RESULT=BLOCKED_SAME_TOOLCHAIN_DEPENDENCY
PROGRAM_SIZE=NOT_AVAILABLE
RAM_USAGE=NOT_AVAILABLE
```

No production firmware source was altered to force compilation.

## ESP32-D0WD-V3 pin audit

```text
SOURCE_PINMAP_COMPATIBILITY=PARTIAL_COMPATIBLE_WITH_STRAPPING_REVIEW
PIN_GPIO35=RX_ONLY_COMPATIBLE_INPUT_ONLY; physical SBUS wiring unverified
PIN_GPIO27=OUTPUT_CAPABLE_SOURCE_ONLY
PIN_GPIO26=OUTPUT_CAPABLE_SOURCE_ONLY
PIN_GPIO25=OUTPUT_CAPABLE_SOURCE_ONLY
PIN_GPIO33=OUTPUT_CAPABLE_SOURCE_ONLY
PIN_GPIO5=GPIO/SPI_CS_CAPABLE_BUT_STRAPPING_RISK
```

GPIO35 is not proposed as a TX pin. GPIO5 remains a source-declared SPI chip
select and requires board pull-state/routing evidence because it is a
strapping pin. No pin assignment was changed.

## BZ251 evidence hunt and conflict

Local repository evidence contains the Owner specification and no exact BZ251
electrical datasheet. A vendor product page identifies the BZ-251 variant as
M10050, 6-pin SH1.0, NMEA/UBLOX, 1–10 Hz with 10 Hz default, and 115200 bps.
The separately indexed BZ251 product-spec PDF/manual states 3.0–5.5 V VCC,
3.3 V digital I/O, NMEA 4.0/4.1, UBX, 38400 bps default, 1 Hz default and
10 Hz maximum. These values conflict and are not silently merged.

Sources:

- [BZGNSS product page](https://bzgnss.com/products/bzgnss-bz-121-bz-181-bz-251-dual-protocol-gps-positioning-module-m10-fpv-out-of-control-rescue-fixed-wing-crossing-drones)
- [BZ251 product-spec PDF mirror](https://device.report/m/7204e90255a063cc1e53bc7d9d564ea980e7bc12613c66eeedcafe4a0ea25ac7.pdf)

```text
GNSS_DATASHEET_STATUS=CONFLICTING_VENDOR_PAGE_AND_DATASHEET_MIRROR
GNSS_VCC_RANGE=3.0..5.5V_FROM_DATASHEET_MIRROR; vendor_page_nominal=5V
GNSS_IO_LEVEL=3.3V_FROM_DATASHEET_MIRROR
GNSS_DEFAULT_BAUD=CONFLICT_38400_DATASHEET_vs_115200_VENDOR_PAGE
GNSS_DEFAULT_RATE=CONFLICT_1HZ_DATASHEET_vs_10HZ_VENDOR_PAGE
GNSS_MAX_RATE=10HZ
GNSS_10HZ_COMMAND_REFERENCE=BLOCKED_NO_EXACT_CONFIGURATION_COMMAND
LOGIC_POWER_COMPATIBILITY=PARTIAL_ELECTRICAL_EVIDENCE_PHYSICAL_WIRING_UNVERIFIED
```

The Owner-provided `38400/1 Hz` intent remains recorded; no configuration value
was selected and no command was sent.

## UART candidates

| UART/resource | Candidate pins | Conflict/risk | Status |
|---|---|---|---|
| UART0 | RX GPIO3 / TX GPIO1; board labels TX0/RX0 | USB programming/debug candidate; route and auto-reset unverified | `UNVERIFIED_NOT_SELECTED` |
| UART1 | classic defaults GPIO9/10 | flash-reserved risk | `FORBIDDEN` |
| UART2 | RX GPIO35 / TX disabled | already owned by SBUS | `OCCUPIED_BY_SBUS` |
| GPIO-matrix alternative | GPIO16/17 only as technical candidates | historical note only; physical header/wiring unverified | `CANDIDATE_NOT_SELECTED` |

```text
GNSS_UART_CANDIDATES=UART0_OR_GPIO_MATRIX_CANDIDATES_UNVERIFIED
GNSS_UART_SELECTED=NONE
```

## Disabled GNSS preparation and capture tooling

Added repository-side, disabled-by-default receive-only boundary:

- `pi5/telemetry/gnss_receive_only.py`: `GNSS_ENABLED=false`, baud default
  38400, RX/TX unassigned, hardware TX/config writes forbidden.
- `tools/scope05_gnss_capture.py`: bounded duration (maximum 300 seconds),
  optional pyserial read-only capture, JSONL base64 records, no transmit or
  configuration API. It was not run against hardware.

```text
GNSS_INTEGRATION_PATCH=PREPARED_DISABLED_BY_DEFAULT_REPO_BOUNDARY
GNSS_READ_ONLY_CAPTURE_TOOL=PREPARED_NOT_RUN
GNSS_LIVE_CAPTURE=BLOCKED_PHYSICAL_UART_AND_ELECTRICAL_GATE
```

The archived ESP32 flight firmware was not modified, so FC/PID/arming/ESC/
SBUS/ICM behavior remains unchanged.

## Tests and safety audit

```text
.venv/bin/pytest -q tests/scope05 -W default
8 passed, exit code 0

.venv/bin/pytest -q tests/scope01 tests/scope02 tests/scope03 tests/scope04 tests/scope05 -W default
56 passed, 1 deprecation warning, exit code 0

git diff --check
PASS, exit code 0

FLIGHT_CONTROL_BEHAVIOR_CHANGED=no
ARM_DISARM_CHANGED=no
ESC_OUTPUT_CHANGED=no
PID_CHANGED=no
CONTROL_LOOP_CHANGED=no
SBUS_MAPPING_CHANGED=no
ICM20602_SETTINGS_CHANGED=no
```

## Final gates

```text
NEXT_GATE=BUILD_COMPATIBILITY_FIX
FLASH_GATE=BLOCKED
```

The first decision blocker is the compatibility build environment, not USB or
ESP identity. After a reproducible build environment exists, the next
independent hardware gate remains physical GNSS wiring and resolution of the
BZ251 baud/rate evidence conflict.
