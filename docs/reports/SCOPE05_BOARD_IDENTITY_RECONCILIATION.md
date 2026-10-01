# SCOPE-05 Board Identity Reconciliation

Assessment date: `2026-09-26` (Asia/Ho_Chi_Minh).

## Evidence boundary

This gate was executed as repository/report-only evidence reconciliation. No
new hardware access, USB retry, electrical measurement, serial operation or
driver/toolchain operation was performed. No new Owner photo, schematic or
manufacturer document was supplied in this turn; the evidence below is the
existing two-photo ingest plus explicit Owner-provided claims.

| Field | Value | Source | Evidence class | Limitation |
|---|---|---|---|---|
| `ESP32_SOC_FAMILY` | ESP32-family / WiFi+BT SoC appearance | Owner board photo 1 | `PARTIAL` | Exact silicon marking is not fully legible |
| `ESP32_MODULE_MODEL` | Not resolved | Owner board photo 1 | `UNVERIFIED` | Marking suffix cannot be read; no authoritative module document |
| `BOARD_MODEL` | Not resolved | No exact model supplied | `MISSING` | Generic development-board appearance is not a model identity |
| `BOARD_MANUFACTURER` | Not resolved | No manufacturer evidence supplied | `MISSING` | No readable manufacturer/product marking |
| `USB_BRIDGE` | CP2102 | Owner claim; chip area in photo 1 | `OWNER_PROVIDED` | Chip marking is too blurred for photo verification |
| `USB_CONNECTOR` | USB-C | Owner board photo 1 | `VERIFIED_FROM_PHOTO` | Connector type only; USB data path is not proven |

## Identity gate

```text
ESP_IDENTITY=PARTIAL_EXACT_VARIANT_UNVERIFIED
BOARD_PROFILE=PARTIAL
USB_PROGRAMMING_PATH=PARTIAL
```

The photos show `RST`, `BOOT`, `EN`, `TX0`, `RX0`, `GND` and `3V3` labels or
controls, but these observations do not establish the exact board model,
manufacturer, schematic nets or CP2102-to-UART0 connectivity. The procurement
record for `CH340G` remains procurement evidence only.
