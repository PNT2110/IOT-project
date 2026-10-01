# SCOPE-05 Mega Fast Track V2 — Current Reconciliation

Assessment date: `2026-09-27` (Asia/Ho_Chi_Minh).

This is the single V2 reconciliation for the Errno 28 remediation, temporary
compatibility builds, GNSS-disabled candidate, and evidence gates. No Pi/USB/
ESP identity gate was reopened.

## Current canonical state

```text
PI5_KEY_AUTH=PASS
PI5_USB_PATH=PASS
ESP_IDENTITY=PASS_READ_ONLY
ESP_CHIP_MODEL=ESP32-D0WD-V3
FLASH_SIZE=4MB

ERRNO28_ROOT_CAUSE=HOME_FILESYSTEM_CAPACITY_INSUFFICIENT_FOR_PLATFORMIO_STAGING
ERRNO28_FILESYSTEM=/home (/dev/nvme0n1p7)
ERRNO28_FREE_BYTES_BEFORE=2197536768
ERRNO28_FREE_INODES_BEFORE=3026211
SAFE_CLEANUP_PERFORMED=yes
SPACE_RECLAIMED_BYTES=34611200_approximately
BUILD_HOST=pnt-MS-7D48 (Linux x86_64)
BUILD_ROOT=/var/tmp/scope05-build-v2
BUILD_ROOT_FREE_BYTES_AFTER=19731869696
BUILD_ROOT_FREE_INODES_AFTER=2743888
BUILD_TOOLCHAIN=PlatformIO 6.2.0; espressif32 7.1.3; Arduino-ESP32 4.20017.260907+sha.dcc1105b; Xtensa 8.4.0+2021r2-patch5
BUILD_TARGET_CLASS=GENERIC_COMPATIBILITY_TARGET
BUILD_TARGET_USED=esp32dev
EXACT_BOARD_MODEL=UNVERIFIED
BUILD_ORIGINAL_RESULT=PASS
PROGRAM_SIZE=285745_bytes_flash_code; 21.8_percent_of_1310720
RAM_USAGE=22268_bytes; 6.8_percent_of_327680
BUILD_GNSS_DISABLED_RESULT=PASS
PROGRAM_SIZE_GNSS_DISABLED=285745_bytes_flash_code
RAM_USAGE_GNSS_DISABLED=22268_bytes
PROGRAM_SIZE_DELTA=0
RAM_USAGE_DELTA=0

SKETCH_HARNESS_METHOD=TEMPORARY_COMBINED_TRANSLATION_UNIT_FROM_UNMODIFIED_SEVEN_INO_FILES
ORIGINAL_SOURCE_MODIFIED=no
COMPATIBILITY_MATRIX_RESULT=NOT_REQUIRED_AFTER_TEMPORARY_HARNESS_FIX
BUILD_FAILURE_CLASS=SKETCH_PREPROCESSING/MISSING_DECLARATION_IN_INITIAL_MULTIFILE_HARNESS
BEHAVIORAL_SOURCE_CHANGE_REQUIRED=no

GNSS_REPO_BOUNDARY_PATCH=PASS
GNSS_FIRMWARE_PATCH=PREPARED_DISABLED_BY_DEFAULT_TEMPORARY_CANDIDATE
GNSS_CAPTURE_TOOL_SYNTHETIC_TEST=PASS
GNSS_SERIAL_WRITE_PATH=ABSENT
GNSS_LIVE_CAPTURE=BLOCKED

GNSS_DATASHEET_STATUS=CONFLICT_UNRESOLVED
GNSS_UART_CANDIDATES=UART0_OR_GPIO_MATRIX_CANDIDATES_UNVERIFIED
GNSS_UART_SELECTED=NONE
PHYSICAL_WIRING_VERIFIED=no
LOGIC_POWER_COMPATIBILITY=PARTIAL_ELECTRICAL_ONLY_PHYSICAL_WIRING_UNVERIFIED

FLIGHT_CONTROL_BEHAVIOR_CHANGED=no
ARM_DISARM_CHANGED=no
ESC_OUTPUT_CHANGED=no
ESC_PIN_ASSIGNMENT_CHANGED=no
PID_CHANGED=no
CONTROL_LOOP_CHANGED=no
SBUS_MAPPING_CHANGED=no
ICM20602_SETTINGS_CHANGED=no

TEST_SCOPE05=8_passed_exit_0
TEST_SCOPE01_05=56_passed_exit_0_1_deprecation_warning
GIT_DIFF_CHECK=PASS_exit_0

SCOPE05_HARDWARE_CAPTURE=BLOCKED
GNSS_LIVE_CAPTURE=BLOCKED
FLASH_GATE=BLOCKED
NEXT_GATE=GNSS_REVISION_AND_PHYSICAL_WIRING_EVIDENCE
```

## Evidence and limits

- Errno 28 was caused by byte capacity on `/home`, not inode exhaustion or a
  `/tmp` limit. Only exact disposable generated SCOPE-05 temporary directories
  were cleaned; repository, source, archives, SSH material and user data were
  not cleaned.
- The original archive was copied without source edits. The first compile error
  was a temporary PlatformIO multi-file sketch-preprocessing issue; the final
  temporary combined harness preserved setup/loop, SBUS, ESC, ICM20602, PID and
  loop timing semantics and compiled successfully.
- The GNSS firmware candidate contains only disabled/unassigned constants:
  `GNSS_ENABLED=false`, baud `38400`, RX/TX unassigned and configuration TX
  disabled. It does not initialize a UART or contain a UBX command.
- The repository-side receive-only boundary and bounded capture utility passed
  tests plus a synthetic malformed-byte fixture, duration-limit check and fake
  serial read-only replay. `stream.write()` is JSONL file output; no
  `device.write/send/sendall` path exists.
- BZ251 evidence remains conflicting between the vendor page and the mirrored
  product specification; no baud/rate or physical UART was selected. Historical
  PC USB evidence remains non-authoritative for the Pi attachment.
- No flash, erase, upload, GNSS configuration, live GNSS capture, motor/ESC,
  ARM/DISARM or flight test was run.

