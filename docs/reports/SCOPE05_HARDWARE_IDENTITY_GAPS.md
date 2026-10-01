# SCOPE-05 Hardware Identity Gaps

## CURRENT_CANONICAL_STATE — 2026-09-27 V3

This block is the current V3 state. Older tables and addenda below are
historical evidence and are not promoted over the current fields.

```text
ESP32_SOC_FAMILY=VERIFIED_FROM_PI_ROM_READ
ESP32_CHIP_MODEL=ESP32-D0WD-V3
ESP32_CHIP_REVISION=v3.1
FLASH_SIZE=4MB
EXACT_BOARD_MODEL=UNVERIFIED
GNSS_PHOTO_MODEL_MARKING=NO_BZ251_MARKING_IN_ACCESSIBLE_PROJECT_PHOTOS
GNSS_PHOTO_REVISION_MARKING=UNREADABLE_OR_NOT_PRESENT
GNSS_MODEL_REVISION_MATCH=no
GNSS_WIRING_EVIDENCE_FILES=NONE_FOUND_KICAD_NETLIST_OR_WIRING_DIAGRAM
GNSS_VCC_RANGE=3.0..5.5V_PARTIAL_MANUAL_ONLY_vs_5V_NOMINAL_PRODUCT_PAGE
GNSS_IO_LEVEL=3.3V_PARTIAL_MANUAL_ONLY
PHYSICAL_WIRING_VERIFIED=no
GNSS_UART_SELECTED=NONE
LOGIC_POWER_COMPATIBILITY=PARTIAL_ELECTRICAL_ONLY_PHYSICAL_WIRING_UNVERIFIED
```

Repository-only assessment plus the supplied DFM screenshots and procurement
document. Missing evidence is left missing; no historical descriptive note is
promoted to hardware truth.

| Required fact | Evidence | Status |
|---|---|---|
| ESP32 exact variant | Photo shows an ESP32-family `WiFi+BT SoC` shield marking, but exact suffix is unreadable | `PARTIAL` / `UNVERIFIED_EXACT_VARIANT` |
| Dev board/module | Photos show a USB-C ESP32 development-board form with `RST`/`BOOT`; exact board/module model and datasheet remain absent | `PARTIAL` |
| USB-UART bridge | Owner identifies onboard CP2102; bridge-chip marking is unreadable in the photos; CH340G remains procurement-only | `OWNER_PROVIDED` / `UNVERIFIED_FROM_PHOTO` |
| USB connector | Symmetrical USB-C connector visible in photo | `VERIFIED_FROM_PHOTO` |
| USB-to-bridge routing | No readable schematic or trace/net evidence | `UNVERIFIED` |
| Bridge-to-UART0 routing | `TX0`/`RX0` labels visible, but no physical route proof | `UNVERIFIED` |
| EN/IO0 auto-reset path | `EN`, `RST` and `BOOT` labels/controls visible, but no auto-reset circuit proof | `UNVERIFIED` |
| GNSS exact part/model | Owner identifies target as BZ251; no primary datasheet/physical marking | `OWNER_PROVIDED` |
| GNSS supply range | No exact GNSS electrical datasheet; purchased 5V/1A adapter is not module evidence | `MISSING` |
| GNSS I/O voltage | Owner spec says TTL but gives no exact voltage/tolerance | `MISSING` |
| GNSS protocol support | Owner spec states NMEA 4.0/4.1 and UBX | `OWNER_PROVIDED` |
| GNSS default baud | Owner spec states 38400 bps | `OWNER_PROVIDED` |
| GNSS update rate | Owner spec states 1 Hz default, 10 Hz maximum/target | `OWNER_PROVIDED` |
| GNSS pinout | Owner spec provides BZ251 six-pin signal labels; ESP32-side wiring absent | `OWNER_PROVIDED` / `BLOCKED` |
| ESP32 pin compatibility | Board variant and physical routing unknown | `BLOCKED` |
| Shared-ground requirement | Required by interface safety; DFM screenshots have no schematic and no wiring proves it | `UNVERIFIED` |
| Board 3V3 power path | Auto-only policy has no machine-readable DMM/DAQ/ADC; earlier Owner reading is historical | `UNVERIFIED_NO_MACHINE_READABLE_SENSOR` |
| CP2102 power state | No labelled measurement or live descriptor evidence | `UNVERIFIED` |

| Pi 5 USB-host evidence | No Pi 5 shell/session available; PC USB evidence is non-authoritative for this attachment | `NOT_COLLECTED` |

## Exact-identity gate re-evaluation

```text
ESP32_SOC_FAMILY=PARTIAL
ESP32_MODULE_MODEL=UNVERIFIED
BOARD_MODEL=MISSING
BOARD_MANUFACTURER=MISSING
CP2102_EXACT_VARIANT=OWNER_PROVIDED_NOT_PHOTO_VERIFIED
USB_CONNECTOR=USB-C_VERIFIED_FROM_PHOTO
```

No new schematic, manufacturer document or readable marking was supplied in
this gate. A generic ESP32 development-board appearance is not promoted to an
exact board identity.

Evidence classes used here are limited to `VERIFIED_FROM_SOURCE`,
`VERIFIED_FROM_PHOTO`, `VERIFIED_FROM_DATASHEET`, `OWNER_PROVIDED`,
`UNVERIFIED`, `MISSING` and `BLOCKED`. The two supplied images are physical
board photos. They do not prove net
connectivity, USB enumeration, GPIO16/GPIO17 assignment, GNSS voltage or an
exact 10 Hz command; those remain unverified or blocked.
The BZ251 model, 38400 default, NMEA/UBX and 1–10 Hz specification are now
explicitly `OWNER_PROVIDED_SPEC`.

## 2026-09-27 Pi ROM identity update

The attached device was identified directly through the Pi 5 USB host using
isolated esptool 5.4.0 read-only commands. Raw MAC output is intentionally
redacted and not stored.

| Required fact | New evidence | Status |
|---|---|---|
| ESP32 SoC family | Pi ROM `chip-id` | `VERIFIED_FROM_PI_ROM_READ` |
| ESP32 chip/revision | `ESP32-D0WD-V3`, revision `v3.1` | `VERIFIED_FROM_PI_ROM_READ` |
| Flash capacity | Pi `flash-id` reports 4 MB | `VERIFIED_FROM_PI_ROM_READ` |
| Exact development-board model | No build metadata or manufacturer marking/datasheet | `UNVERIFIED` |
| Board-specific USB/UART0 route | CP2102 endpoint and TX0/RX0 labels only | `UNVERIFIED` |
| GNSS electrical compatibility | Exact BZ251 VCC/I/O limits absent | `BLOCKED` |

```text
ESP32_SOC_FAMILY=VERIFIED
ESP32_MODULE_MODEL=UNVERIFIED
ESP32_CHIP_MODEL=ESP32-D0WD-V3
ESP32_CHIP_REVISION=v3.1
FLASH_SIZE=4MB
BOARD_MODEL=UNVERIFIED
CP2102_EXACT_VARIANT=PI_USB_PRODUCT_CP2102
GNSS_UART_SELECTED=NONE
NEXT_GATE=BUILD_TARGET_RECONCILIATION_AND_GNSS_HARDWARE_EVIDENCE
FLASH_GATE=BLOCKED
```

## 2026-09-27 BZ251 evidence update

```text
GNSS_DATASHEET_STATUS=CONFLICTING_VENDOR_PAGE_AND_DATASHEET_MIRROR
GNSS_VCC_RANGE=3.0..5.5V_DATASHEET_MIRROR_VENDOR_NOMINAL_5V
GNSS_IO_LEVEL=3.3V_DATASHEET_MIRROR
GNSS_DEFAULT_BAUD=CONFLICT_38400_vs_115200
GNSS_DEFAULT_RATE=CONFLICT_1HZ_vs_10HZ
GNSS_MAX_RATE=10HZ
GNSS_UART_SELECTED=NONE
LOGIC_POWER_COMPATIBILITY=PARTIAL_ELECTRICAL_ONLY_PHYSICAL_WIRING_UNVERIFIED
```

The new source material improves the electrical evidence but does not identify
the exact purchased revision or prove ESP32-side wiring, common ground or a
safe selected UART. The conflict is preserved rather than resolved by guess.
