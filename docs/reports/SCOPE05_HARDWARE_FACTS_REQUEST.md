# SCOPE-05 Hardware Facts Request

Provide only the following missing facts for later gate review. Do not send
passwords, Wi-Fi secrets, private keys, OTP/TOTP material or unrelated PII.

```text
ESP32_BOARD_MODEL:
GNSS_MODEL:
GNSS_DATASHEET_OR_LINK:
GNSS_POWER_VOLTAGE:
GNSS_LOGIC_LEVEL:
GNSS_TX_TO_ESP32_PIN:
GNSS_RX_FROM_ESP32_PIN:
GNSS_GND_SHARED:
SBUS_UART_OWNERSHIP_CONFIRMED:
PROPS_REMOVED_OR_ISOLATED:
ESC_ACTUATION_PATH_ISOLATED:
BENCH_POWER_METHOD:
SUPERVISOR:
STOP_AUTHORITY:
IMMEDIATE_POWER_CUT_METHOD:
```

Prefer board markings, exact datasheet links and a redacted wiring diagram or
photo over guessed text. These facts do not themselves authorize capture;
capture requires a separate Owner decision.
