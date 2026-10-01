# SCOPE-05 Hardware Evidence Ingest

Assessment date: `2026-09-26` (Asia/Ho_Chi_Minh)

## Boundary and result

This is read-only evidence ingestion. No hardware was accessed or powered, no
serial port was opened, and no firmware, GNSS configuration, motor, ESC,
ARM/DISARM or actuator operation occurred.

```text
EVIDENCE_INGEST=COMPLETE
SCOPE05_HARDWARE_CAPTURE=BLOCKED
SCOPE05=BLOCKED_NOT_OPENED
```

## Evidence inventory

| Evidence | What is actually visible/read | Evidence class | Limitation |
|---|---|---|---|
| `image-1.png` | PCB/EDA routing-layer DFM screenshot; dialog says no schematic diagram available | `OWNER_PROVIDED` | Not a physical board photo; no ESP32/GNSS marking or wiring proof |
| `image-2.png` | PCB/EDA silkscreen-to-pad DFM screenshot; same board context | `OWNER_PROVIDED` | Does not identify fitted components or pin ownership |
| `image-3.png` | PCB/EDA silkscreen-to-hole DFM screenshot; no schematic diagram available | `OWNER_PROVIDED` | No physical identity or connectivity proof |
| `image-4.png` | EDA window title `FC_ESP32_DFM_RECHECK`; plated-drill/slot DFM view | `OWNER_PROVIDED` | Supports a design-label clue only; not an exact ESP32 module identity |
| `image-5.png` | PCB/EDA via-to-PTH spacing DFM screenshot; no schematic diagram available | `OWNER_PROVIDED` | No GNSS, UART or wiring evidence |
| `Thegioiic.com.pdf` | Procurement document lists a CH340G USB-to-TTL UART adapter and a 5V/1A adapter among purchased items | `OWNER_PROVIDED` | Purchase record does not prove installation, wiring, signal levels or current hardware identity; personal details were not copied |
| `FC_can_bang.zip` | Seven `.ino` files, hash and source findings | `VERIFIED_FROM_SOURCE` | Source truth is preserved; it has no GNSS identity/configuration |

The five images are design-review screenshots, not ESP32/GNSS product photos.
No legible physical module marking is present. The PDF is not a board or GNSS
datasheet and is not used as one.

Evidence hashes (for the accessible files) are:

```text
image-1.png  bbd5f36fd9fa4b5204bcca70c1003f6d971b0d8c5629c324d3cd05fe6bff2275
image-2.png  88d43ff31490c459715eb04faa7096bf876f6f6e0f66fbbb3d497190b7ecb048
image-3.png  3d464a32c3afec3dd28e5ea3014f72ae38e5f2b0bceae894cf50d4481d94772e
image-4.png  ed7d1581ae91f327fb62e835847dfe8d578a30cab91102342c6d47fb689670b7
image-5.png  78dd712f66828f2ea994294ff06bbc99f046cb0471731b7f99867b7d69246bf2
Thegioiic.com.pdf  e42cbc2cb5947651752111893a264a63f7b1d5295db4d509ed47144c3a5e4524
```

## Extracted facts and limits

| Fact | Value | Source | Evidence class | Confidence/limitation |
|---|---|---|---|---|
| PCB design label | `FC_ESP32_DFM_RECHECK` | `image-4.png` title | `OWNER_PROVIDED` | Design label only; does not prove fitted ESP32 variant |
| USB-UART item | CH340G USB-to-TTL UART adapter listed | `Thegioiic.com.pdf` | `OWNER_PROVIDED` | Procurement only; current connection unverified |
| Adapter item | 5V 1A adapter listed | `Thegioiic.com.pdf` | `OWNER_PROVIDED` | Procurement only; does not prove rail or GNSS voltage |
| Schematic | DFM screenshots visibly state no schematic available | images 1, 2, 3, 5 | `VERIFIED_FROM_PHOTO` | Prevents deriving wiring/pin ownership |
| SBUS source wiring | UART2 RX GPIO35, TX `-1`, 100000, `SERIAL_8E2`, inverted | `FC_can_bang/Sbus.ino` | `VERIFIED_FROM_SOURCE` | Firmware declaration, not physical wiring proof |
| GNSS source wiring | No GNSS UART/parser/configuration | archive audit | `VERIFIED_FROM_SOURCE` | GNSS identity and connection remain blocked |

## Historical note reassessment

| Historical note | Current result | Source/limitation |
|---|---|---|
| GPIO16/GPIO17 | `UNVERIFIED` | Not visible in supplied DFM screenshots; absent as GNSS evidence in archive |
| Approximately 38400 baud | `UNVERIFIED` | Not in GNSS source or a datasheet |
| NMEA | `UNVERIFIED` | No GNSS parser/source or exact-module datasheet |
| UBX | `UNVERIFIED` | No GNSS parser/source or exact-module datasheet |
| 1 Hz default | `UNVERIFIED` | No exact GNSS datasheet or capture |
| 10 Hz maximum | `UNVERIFIED` | No exact GNSS datasheet or capture |
| I2C mention | `UNVERIFIED` | No GNSS wiring/source/datasheet evidence |

No exact ESP32 or GNSS marking, GNSS datasheet, or wiring diagram was found in
the accessible evidence set. These remain `MISSING`/`BLOCKED`, not inferred.
