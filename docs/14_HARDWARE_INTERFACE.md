# SCOPE-00 — Hardware interface inventory

## What is known

| Interface | Verified from source/user | Not yet verified |
|---|---|---|
| ESP32 ↔ ICM20602 | Source: SPI, CS GPIO5, 1 MHz, `SPI_MODE0`; IMU register reads. | Exact board SPI pins, sensor identity/wiring, electrical validation. |
| ESP32 ↔ SBUS | Source: UART2 RX GPIO35, 100000 8E2, inverted, 16 channels. | Receiver model, signal inversion hardware, power/ground, whether GPIO35 is physically wired. |
| ESP32 ↔ ESC | Source: GPIO27/26/25/33 LEDC output. | ESC protocol/electrical setup; no physical test allowed. |
| ESP32 ↔ GNSS | User reports GPIO16/17, ~38400; archive has no GNSS code. | Module model, RX/TX direction, level, ground, power, UART ownership, actual baud/rate. **BLOCKED**. |
| Pi ↔ webcam | User reports USB webcam. | Camera model, `/dev/video*`, permissions, bandwidth, encoder. |
| Pi ↔ USB Wi-Fi | User reports USB adapter. | Chipset, driver, AP+STA concurrency, country/channel support. |
| Pi ↔ ESP32 | User reports connection. | USB-UART identity, cable, device permissions, protocol; no structured protocol in archive. |

## UART direction checklist

Document both endpoints explicitly: GNSS module TX → ESP RX; GNSS module RX ← ESP TX. Do not infer connector labels from GPIO names. Check common ground, 3.3 V logic, power budget and level shifting from the exact datasheet. GPIO16/17 are not enough to prove UART2 availability or physical routing.

## GNSS research gate

NMEA/UBX capability is model-specific. The cited u-blox documents are examples of official protocol documentation, not proof that the supplied module is u-blox or M9. Before parser selection, capture model/part number and datasheet. The read-only adapter must expose `fix`, `observed_at`, quality and stale status; it must never silently configure rate/baud or persist changes.

## Hardware safety boundary

Any later scope involving powered FC/ESC must state propeller/actuator isolation, supervisor, emergency stop, power limits, allowed instrumentation and stop conditions. “No telemetry” is not permission to alter flight behavior. SCOPE-00 performed no hardware connection, SSH, flash or motor action.
