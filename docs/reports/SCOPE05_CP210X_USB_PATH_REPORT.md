# SCOPE-05 CP2102 USB Path Report (legacy filename)

Canonical photo-ingest report: `SCOPE05_CP2102_USB_PATH_REPORT.md`.

Assessment date: `2026-09-26` (Asia/Ho_Chi_Minh).

## Owner-provided architecture

```text
USB_UART_BRIDGE=CP2102
USB_ARCHITECTURE=USB_UART_BRIDGE_CP2102
ONBOARD_USB_UART_BRIDGE=CP2102_OWNER_PROVIDED
EXTERNAL_USB_UART_BRIDGE=NOT_APPLICABLE
CP2102_LOCATION=ONBOARD
EVIDENCE_CLASS=OWNER_PROVIDED
```

The Owner has identified the onboard bridge as CP2102. This is not physical
photo or descriptor verification and does not prove VID:PID, driver binding or
USB data-path continuity.

## Current Linux observation

```text
USB_CP2102_ENUMERATION=FAIL_NO_EVENT
TTY_NODE=NOT_PRESENT
CP2102_EXACT_VARIANT=OWNER_PROVIDED
ESP_IDENTITY=BLOCKED
FLASH_GATE=BLOCKED
```

The latest live observation showed no CP2102/USB device in `lsusb`, no
`/dev/ttyUSB*` node, no serial symlink and no USB/serial kernel event. No
driver/module operation was attempted.

## Path separation

```text
SBUS=HardwareSerial(2), RX GPIO35
GNSS_UART=UNASSIGNED
CP2102_PROGRAMMING_UART=TO_BE_VERIFIED
```

The onboard CP2102 programming/debug path must not be treated as the BZ251
GNSS UART. No physical assignment is inferred.

## Next physical evidence

BOARD_PHOTO_EVIDENCE=INGESTED
USB_PHYSICAL_PATH_DIAGNOSIS=PARTIAL_PHOTO_RECONCILIATION
USB_PROGRAMMING_PATH=PARTIAL
CP2102_PHOTO_MARKING=UNVERIFIED_NOT_LEGIBLE
FLASH_GATE=BLOCKED

The Owner-provided top/bottom photos establish the connector and board control
labels but do not prove the CP2102 marking or USB/UART/reset routing. Do not
measure continuity/voltage, retry USB, install drivers or flash in this state.
