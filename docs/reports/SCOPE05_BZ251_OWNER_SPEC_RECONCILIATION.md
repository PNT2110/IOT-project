# SCOPE-05 BZ251 Owner-Spec Reconciliation

Assessment date: `2026-09-26` (Asia/Ho_Chi_Minh).

## Evidence class

The following values come from the Owner-provided BZ251 specification in the
current SCOPE-05 instruction. No manufacturer command manual or primary
electrical datasheet for the exact revision is present in the repository.

```text
EVIDENCE_CLASS=OWNER_PROVIDED_SPEC
GNSS_MODEL=BZ251
DEFAULT_BAUD=38400
BAUD_RANGE=9600..460800_bps
DEFAULT_NAVIGATION_UPDATE_RATE=1_HZ
MAX_NAVIGATION_UPDATE_RATE=10_HZ
TARGET_NAVIGATION_UPDATE_RATE=10_HZ
NAVIGATION_RATE_CONFIGURABLE=yes
NMEA_0183=4.0_and_4.1
UBX=yes
PIN_1=TX_TTL_OUTPUT
PIN_2=RX_TTL_INPUT
PIN_3=GND
PIN_4=VCC
PIN_5=SCL_I2C
PIN_6=SDA_I2C
```

## 2026-09-27 MEGA FAST TRACK V3 revision reconciliation

V3 compared the official product page with the accessible BZ251 V1.0 manual
mirror. The page does not state a hardware revision or date, so the two
descriptions cannot be safely mapped to the photographed or intended physical
unit. The conflict therefore remains unresolved rather than being assigned to
a guessed revision.

```text
BZ251_CONFLICT_CLASS=UNRESOLVED
DOCUMENT_A=BZGNSS_BZ-251_PRODUCT_PAGE
PART_A=BZ-251_u-blox_M10050
REVISION_A=NOT_STATED
BAUD_A=115200
RATE_A=1..10HZ_DEFAULT_10HZ_PAGE_WORDING
VCC_A=5V_NOMINAL
IO_A=UNSPECIFIED
DOCUMENT_B=BZ251_PRODUCT_SPECIFICATION_DATA_SHEET
PART_B=BZ251
REVISION_B=V1.0_2022-10-08
BAUD_B=38400_DEFAULT
RATE_B=1HZ_DEFAULT_10HZ_MAX_CONFIGURABLE
VCC_B=3.0..5.5V
IO_B=3.3V
GNSS_DEFAULT_BAUD=UNRESOLVED_38400_vs_115200
GNSS_DEFAULT_RATE=UNRESOLVED_1HZ_vs_10HZ
GNSS_10HZ_COMMAND_REFERENCE=BLOCKED
```

No physical BZ251 marking, revision label or carrier wiring evidence is
available in the accessible repository evidence; no live configuration was
attempted.

## Limits

- `TTL` does not establish an exact I/O voltage or 5V tolerance.
- The pin list does not establish the ESP32 carrier-board pins, physical
  wiring, common ground or power rail.
- The supported 10 Hz capability does not prove the exact configuration bytes
  for this BZ251 revision.
- No generic UBX rate packet was built for transmission or sent.

```text
BZ251_EXACT_10HZ_CONFIG_COMMAND=BLOCKED_PENDING_EXACT_COMMAND_REFERENCE
GNSS_VCC_EXACT_VOLTAGE=MISSING
GNSS_LOGIC_LEVEL_EXACT_VOLTAGE=MISSING
GNSS_PHYSICAL_UART_PINS_ON_ESP32=BLOCKED_PENDING_BOARD_WIRING
```

## 2026-09-27 external evidence reconciliation

Local repository search found no exact BZ251 electrical/manual source. A
manufacturer/vendor product page and a separately indexed BZ251 product-spec
PDF were reviewed read-only:

- [BZGNSS BZ-251 product page](https://bzgnss.com/products/bzgnss-bz-121-bz-181-bz-251-dual-protocol-gps-positioning-module-m10-fpv-out-of-control-rescue-fixed-wing-crossing-drones)
- [BZ251 product-spec PDF mirror](https://device.report/m/7204e90255a063cc1e53bc7d9d564ea980e7bc12613c66eeedcafe4a0ea25ac7.pdf)

The vendor page identifies BZ-251 as M10050, a 6-pin SH1.0 module with 5 V
nominal power, NMEA/UBLOX output, 1–10 Hz range and 115200 bps. The PDF/manual
states VCC 3.0–5.5 V, digital I/O 3.3 V, NMEA 4.0/4.1, UBX, 38400 bps
default, 1 Hz default and 10 Hz maximum. These are conflicting revisions or
product descriptions; the Owner-provided `38400/1 Hz` intent is preserved and
no value is selected for live configuration.

```text
EVIDENCE_CLASS=CONFLICTING_VENDOR_PRODUCT_PAGE_AND_DATASHEET_MIRROR
GNSS_DATASHEET_STATUS=PARTIAL_CONFLICT_REQUIRES_REVISION_RESOLUTION
GNSS_VCC_MIN=3.0V_DATASHEET_MIRROR
GNSS_VCC_MAX=5.5V_DATASHEET_MIRROR
GNSS_IO_VOLTAGE=3.3V_DATASHEET_MIRROR
GNSS_DEFAULT_BAUD=CONFLICT_38400_vs_115200
GNSS_DEFAULT_RATE=CONFLICT_1HZ_vs_10HZ
GNSS_MAX_RATE=10HZ
GNSS_10HZ_COMMAND_REFERENCE=BLOCKED
LOGIC_POWER_COMPATIBILITY=PARTIAL_ELECTRICAL_ONLY_PHYSICAL_WIRING_UNVERIFIED
```

## 2026-09-27 MEGA FAST TRACK V2 status

The conflict remains unresolved after the V2 read-only reconciliation. No live
baud, update rate or configuration command was selected.

```text
GNSS_DATASHEET_STATUS=CONFLICT_UNRESOLVED
GNSS_DEFAULT_BAUD=CONFLICT_38400_vs_115200
GNSS_DEFAULT_RATE=CONFLICT_1HZ_vs_10HZ
GNSS_10HZ_COMMAND_REFERENCE=BLOCKED
GNSS_UART_SELECTED=NONE
PHYSICAL_WIRING_VERIFIED=no
LOGIC_POWER_COMPATIBILITY=PARTIAL_ELECTRICAL_ONLY_PHYSICAL_WIRING_UNVERIFIED
GNSS_LIVE_CAPTURE=BLOCKED
FLASH_GATE=BLOCKED
```
