# SCOPE-05 Mega Fast Track V3 — GNSS Evidence and Wiring

Assessment date: `2026-09-27` (Asia/Ho_Chi_Minh).

This is the single V3 reconciliation. Frozen V2 PASS results were not reopened.
No live GNSS, serial, flash, erase, configuration or actuator operation was
performed.

## Current canonical state

```text
PI5_KEY_AUTH=PASS
PI5_USB_PATH=PASS
ESP_IDENTITY=PASS_READ_ONLY
BUILD_ORIGINAL_RESULT=PASS
BUILD_GNSS_DISABLED_RESULT=PASS_UNCHANGED_FROM_V2
ERRNO28_REMEDIATION=PASS_FROZEN_FROM_V2

BZ251_CONFLICT_CLASS=UNRESOLVED
GNSS_DATASHEET_STATUS=REVISION_CONFLICT_UNRESOLVED
GNSS_DEFAULT_BAUD=UNRESOLVED_38400_vs_115200
GNSS_DEFAULT_RATE=UNRESOLVED_1HZ_vs_10HZ
GNSS_VCC_RANGE=3.0..5.5V_PARTIAL_MANUAL_ONLY_vs_5V_NOMINAL_PRODUCT_PAGE
GNSS_IO_LEVEL=3.3V_PARTIAL_MANUAL_ONLY
GNSS_10HZ_COMMAND_REFERENCE=BLOCKED

GNSS_PHOTO_MODEL_MARKING=NO_BZ251_MARKING_IN_ACCESSIBLE_PROJECT_PHOTOS
GNSS_PHOTO_REVISION_MARKING=UNREADABLE_OR_NOT_PRESENT
ESP32_BOARD_PHOTO_MODEL=UNVERIFIED
CONNECTOR_ORIENTATION_EVIDENCE=USB_C_AND_ESP32_HEADER_LABELS_ONLY_GNSS_CONNECTOR_NOT_EVIDENCED

GNSS_WIRING_EVIDENCE_FILES=NONE_FOUND_KICAD_NETLIST_OR_WIRING_DIAGRAM
GNSS_VCC_NET=UNVERIFIED
GNSS_GND_NET=UNVERIFIED
GNSS_TX_TO_ESP_RX=UNVERIFIED
ESP_TX_TO_GNSS_RX=UNVERIFIED
GNSS_CONNECTOR=UNVERIFIED
PHYSICAL_WIRING_VERIFIED=no

GNSS_POWER_COMPATIBILITY=PARTIAL_EVIDENCE_MANUAL_ONLY
GNSS_TX_TO_ESP_RX_LOGIC_COMPATIBILITY=PARTIAL_ELECTRICAL_ONLY
ESP_TX_TO_GNSS_RX_LOGIC_COMPATIBILITY=PARTIAL_ELECTRICAL_ONLY
COMMON_GROUND_EVIDENCE=MANUAL_REQUIRES_GROUND_UNVERIFIED_PHYSICALLY
LOGIC_POWER_COMPATIBILITY=PARTIAL_ELECTRICAL_ONLY_PHYSICAL_WIRING_UNVERIFIED

GNSS_UART_CANDIDATES=UART0_OR_GPIO_MATRIX_CANDIDATES_UNVERIFIED
GNSS_UART_SELECTED=NONE
UART2_SBUS_OWNERSHIP=FROZEN_GPIO35_RX_ONLY_TX_DISABLED
UART1_GPIO9_GPIO10=FORBIDDEN_FLASH_RESERVED_RISK
GPIO16_GPIO17=TECHNICAL_CANDIDATES_ONLY_NO_PHYSICAL_PROOF

GNSS_PASSIVE_BAUD_PROBE_SYNTHETIC=PASS
GNSS_BAUD_PROBE_WRITE_PATH=ABSENT
GNSS_LIVE_CAPTURE=BLOCKED
EXACT_BOARD_MODEL=UNVERIFIED

TEST_SCOPE05=16_passed_exit_0
TEST_SCOPE01_05=64_passed_exit_0_1_deprecation_warning
GIT_DIFF_CHECK=PASS_exit_0
FLIGHT_CONTROL_BEHAVIOR_CHANGED=no
SCOPE05_HARDWARE_CAPTURE=BLOCKED
FLASH_GATE=BLOCKED
NEXT_GATE=GNSS_EXACT_REVISION_OR_PHYSICAL_MARKING_EVIDENCE
```

## Revision/document matrix

| Document | Part/revision | Baud | Rate | Power/I/O | Evidence class |
|---|---|---:|---|---|---|
| BZGNSS BZ-121/BZ-181/BZ-251 product page | BZ-251, u-blox M10050; revision/date not stated | 115200 | 1–10 Hz, page says default 10 Hz | 5 V nominal; I/O not stated | Manufacturer product page |
| BZ251 GPS Module Owner's Manual / Product Specification Data Sheet | BZ251, Revision V1.0, 2022-10-08 | 38400 default; 9600–460800 | 1 Hz default, 10 Hz max/configurable | VCC 3.0–5.5 V; digital I/O 3.3 V | Document mirror; physical revision unmatched |
| u-blox UBX-M10050-KB Product Summary, UBX-20017986 R17 | Die/product summary, not BZ251 carrier | Not a carrier default | Up to 10 Hz in stated modes | Die supply 1.0–1.8 V; I/O 1.8/3.3 V | Official chip source; not carrier truth |

Sources reviewed read-only:

- <https://bzgnss.com/products/bzgnss-bz-121-bz-181-bz-251-dual-protocol-gps-positioning-module-m10-fpv-out-of-control-rescue-fixed-wing-crossing-drones>
- <https://manuals.plus/bzgnss/bz251-gps-module-manual.pdf>
- <https://device.report/m/7204e90255a063cc1e53bc7d9d564ea980e7bc12613c66eeedcafe4a0ea25ac7.pdf>
- <https://content.u-blox.com/sites/default/files/UBX-M10050-KB_ProductSummary_UBX-20017986.pdf>

The product page and V1.0 manual cannot be mapped to the physical module
revision because no BZ251 photo/marking, purchase SKU revision, or exact
manufacturer revision identifier is available. The conflict remains
`UNRESOLVED`; no current live baud/rate is selected.

## Physical wiring acceptance record

Repository/workspace search found no KiCad schematic/PCB, netlist, wiring
diagram or GNSS photo proving a net. Existing ESP32 board-photo evidence is
limited to USB-C, `RST`/`BOOT`, `EN`, `TX0`/`RX0`, `GND` and `3V3` labels. These
are label observations, not continuity or routing evidence.

```text
GNSS_MODEL_REVISION_MATCH=no
GNSS_VCC_RANGE_VERIFIED=partial_manual_only
GNSS_IO_LEVEL_VERIFIED=partial_manual_only
GNSS_PIN_TX_IDENTIFIED=owner_spec_only
GNSS_PIN_RX_IDENTIFIED=owner_spec_only
GNSS_PIN_GND_IDENTIFIED=owner_spec_only
GNSS_PIN_VCC_IDENTIFIED=owner_spec_only
ESP_RX_GPIO_IDENTIFIED=no
ESP_TX_GPIO_IDENTIFIED=no
ESP_GPIO_HEADER_ACCESS_VERIFIED=no
COMMON_GROUND_VERIFIED=no
UART_CONFLICT_FREE=unverified
STRAPPING_RISK_ACCEPTABLE=unverified
PHYSICAL_WIRING_VERIFIED=no
```

## UART candidate matrix

| UART | RX | TX | Capability | Conflict/risk | USB/debug | Physical evidence | Status |
|---|---:|---:|---|---|---|---|---|
| UART0 | GPIO3 | GPIO1 | RX/TX capable | Programming/debug resource | CP2102 candidate | `RX0`/`TX0` labels only | `UNVERIFIED` |
| UART1 default | GPIO9 | GPIO10 | RX/TX capable abstractly | Flash-reserved risk | None established | None | `FORBIDDEN` |
| UART1 matrix candidate | GPIO16 | GPIO17 | RX/TX capable on classic ESP32 mapping | Exact board/module variant unknown | No direct USB conflict established | No GNSS net/header proof | `TECHNICAL_CANDIDATE_UNVERIFIED` |
| UART2 | GPIO35 | disabled | GPIO35 input-only; TX cannot use it | Source-verified SBUS ownership | No direct USB conflict | No GNSS route proof | `RESERVED_SBUS` |

No candidate is selected. Source ownership remains UART2/SBUS GPIO35 RX-only,
ESC GPIO27/26/25/33 and ICM20602 CS GPIO5.

## Passive baud probe

Added `pi5/telemetry/gnss_passive_baud_probe.py` with injected read-only
`source_factory(baud)` and bounded `read(timeout)` calls. It tests only 38400
and 115200, validates NMEA checksum/framing, accepts valid no-fix NMEA,
rejects malformed/bad-checksum data, and returns `DETECTED_38400`,
`DETECTED_115200`, `AMBIGUOUS`, `NO_VALID_NMEA`, or `TIMEOUT`.

Eight synthetic tests cover both rates, no-fix, malformed-then-valid, bad
checksum, timeout, ambiguity and transmit-path absence. No real serial source
was opened. Because only Pi telemetry tooling changed, the V2 ESP32 builds
were not unnecessarily rerun.

## Safety and next gate

ESC isolation, bench power limits, supervisor, stop authority, immediate
power-cut method and separate live-capture authorization remain absent or
blocked. The smallest next action is exact BZ251 physical revision/marking
evidence matched to one document family. No live capture or wiring change is
authorized by this report.
