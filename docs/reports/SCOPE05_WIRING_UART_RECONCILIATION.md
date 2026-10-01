# SCOPE-05 Wiring / UART Reconciliation

Read-only reconciliation of source and supplied design/procurement evidence.
No physical wiring was touched or tested.

| Signal | Source device | Destination | Physical pin | UART/peripheral | Electrical level | Evidence | Status |
|---|---|---|---|---|---|---|---|
| SBUS RX | SBUS receiver (source label only) | ESP32 | GPIO35 | `HardwareSerial(2)` | Not stated | `FC_can_bang/Sbus.ino` | `VERIFIED_FROM_SOURCE` for firmware declaration |
| SBUS TX | None in source | ESP32 | `-1` | UART2 TX disabled | Not applicable in source | `FC_can_bang/Sbus.ino` | `VERIFIED_FROM_SOURCE` |
| GNSS TX | GNSS | ESP32 | Unknown | Unknown | Unknown | No GNSS source, wiring or datasheet | `MISSING` |
| GNSS RX | ESP32 | GNSS | Unknown | Unknown | Unknown | No GNSS source, wiring or datasheet | `MISSING` |
| GNSS VCC | Supply | GNSS | Unknown | n/a | Unknown | 5V/1A adapter appears on procurement record only | `BLOCKED` |
| GND | Common ground | ESP32/GNSS | Unknown | n/a | Unknown | No wiring diagram/photo proving connection | `MISSING` |
| USB-UART | Owner-provided onboard CP2102 | ESP32 UART0 candidate (`TX0`/`RX0` labels visible) | Board-specific; labels only | Unknown | Unknown | Photo shows USB-C, CP2102 candidate area and UART0 labels, but no readable route/net proof | `PARTIAL` / `UNVERIFIED` |

The two board photos additionally show `EN`, `TX0`, `RX0`, `GND` and `3V3`
labels plus `RST` and `BOOT` controls. These are label/control observations
only; they do not establish continuity, UART direction, common ground,
auto-reset wiring or rail connectivity. The Owner-provided BZ251 pin labels are recorded separately as
`OWNER_PROVIDED_SPEC`: TX TTL output, RX TTL input, GND, VCC, SCL and SDA.
They do not identify the ESP32-side physical pins or prove voltage tolerance.

## Conflict and compatibility checks

- UART2/SBUS ownership is source-verified, but physical board routing is not.
- GNSS UART ownership cannot be resolved because no GNSS endpoint or wiring is
  evidenced.
- GPIO16/GPIO17 cannot be assigned to GNSS.
- No pin-mux, boot/strapping, input-only, logic-level or power-rail conclusion
  can be made for the unknown board/module.
- The 5V/1A procurement item is not proof that the GNSS or ESP32 I/O accepts
  5V. Do not use it as electrical compatibility evidence.
- The board photos do not provide a readable schematic or route proof; they
  cannot prove net connectivity or common ground.

```text
UART_CONFLICT_STATUS=BLOCKED
LOGIC_POWER_COMPATIBILITY=BLOCKED
PHYSICAL_WIRING_VERIFIED=no
USB_PROGRAMMING_PATH=PARTIAL
CP2102_TO_UART0=UNVERIFIED
GNSS_UART=UNASSIGNED
ESP32_MODULE_MODEL=UNVERIFIED
BOARD_MODEL=MISSING
USB_VBUS_TO_CP2102=UNVERIFIED
USB_DP_DM_TO_CP2102=UNVERIFIED
CP2102_DTR_RTS_TO_EN_IO0=UNVERIFIED
```

## 2026-09-27 MEGA FAST TRACK V3 wiring reconciliation

The repository contains no KiCad/netlist/wiring diagram proving the GNSS
connector, power net, common ground or UART signal ownership. The existing
ESP32 board photographs show labels useful for board orientation only; they do
not prove a BZ251 connection. The candidate matrix is therefore retained
without selecting a live route.

```text
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
GNSS_UART_CANDIDATES=UART0_OR_GPIO_MATRIX_CANDIDATES_UNVERIFIED
GNSS_UART_SELECTED=NONE
UART2_SBUS_OWNERSHIP=FROZEN_GPIO35_RX_ONLY_TX_DISABLED
UART1_GPIO9_GPIO10=FORBIDDEN_FLASH_RESERVED_RISK
GPIO16_GPIO17=TECHNICAL_CANDIDATES_ONLY_NO_PHYSICAL_PROOF
LOGIC_POWER_COMPATIBILITY=PARTIAL_ELECTRICAL_ONLY_PHYSICAL_WIRING_UNVERIFIED
```

## 2026-09-27 FAST TRACK identity reconciliation

Direct Pi-side ROM identity read now verifies the attached SoC as
`ESP32-D0WD-V3`, revision `v3.1`, with 4 MB flash. This closes the SoC-family
identity gap only; it does not identify the development-board manufacturer or
prove PCB nets.

```text
ESP32_SOC_FAMILY=VERIFIED_FROM_PI_ROM_READ
ESP32_CHIP_MODEL=ESP32-D0WD-V3
ESP32_CHIP_REVISION=v3.1
FLASH_SIZE=4MB
UART2_SBUS=SOURCE_COMPATIBLE_GPIO35_RX_ONLY
GNSS_UART_CANDIDATES=UNASSIGNED
GNSS_UART_SELECTED=NONE
CP2102_TO_UART0=UNVERIFIED
CP2102_DTR_RTS_TO_EN_IO0=UNVERIFIED
LOGIC_POWER_COMPATIBILITY=BLOCKED
```

Source compatibility review: GPIO35 is input-only and is appropriate for the
declared SBUS RX-only use; GPIO27/26/25/33 are output-capable for the declared
ESC paths; GPIO5 is used as SPI CS but is also a boot-strapping pin, so its
external pull state and board route require evidence. No source or photo proves
GNSS UART ownership, common ground, logic voltage, USB differential routing or
auto-reset continuity.

## 2026-09-27 MEGA FAST TRACK UART update

```text
GNSS_UART_CANDIDATES=UART0_OR_GPIO_MATRIX_CANDIDATES_UNVERIFIED
GNSS_UART_SELECTED=NONE
UART0_STATUS=PROGRAMMING_DEBUG_CANDIDATE_ROUTE_UNVERIFIED
UART1_STATUS=FLASH_RESERVED_FORBIDDEN
UART2_STATUS=OCCUPIED_BY_SBUS_GPIO35_RX_ONLY
GPIO16_GPIO17_STATUS=TECHNICAL_CANDIDATES_ONLY_NO_PHYSICAL_PROOF
LOGIC_POWER_COMPATIBILITY=PARTIAL_ELECTRICAL_EVIDENCE_PHYSICAL_WIRING_UNVERIFIED
```

The receive-only GNSS boundary is prepared with RX/TX unassigned and no
configuration path. The BZ251 source conflict is recorded in the dedicated
Owner-spec reconciliation; no baud/rate was sent or selected.

## 2026-09-27 MEGA FAST TRACK V2 status

The temporary firmware build verified the existing source only; it did not
promote any GNSS wiring candidate.

```text
UART0_STATUS=PROGRAMMING_DEBUG_CANDIDATE_ROUTE_UNVERIFIED
UART1_STATUS=FLASH_RESERVED_FORBIDDEN
UART2_STATUS=OCCUPIED_BY_SBUS_GPIO35_RX_ONLY
GPIO16_GPIO17_STATUS=TECHNICAL_CANDIDATES_ONLY_NO_PHYSICAL_PROOF
GNSS_UART_CANDIDATES=UART0_OR_GPIO_MATRIX_CANDIDATES_UNVERIFIED
GNSS_UART_SELECTED=NONE
PHYSICAL_WIRING_VERIFIED=no
CP2102_TO_UART0=UNVERIFIED
CP2102_DTR_RTS_TO_EN_IO0=UNVERIFIED
LOGIC_POWER_COMPATIBILITY=PARTIAL_ELECTRICAL_ONLY_PHYSICAL_WIRING_UNVERIFIED
```
