"""Disabled-by-default GNSS receive-only integration boundary.

This module deliberately contains no serial-device opener and no transmit,
configuration, or control operation. It provides a typed configuration boundary
for a future read-only capture implementation after hardware evidence passes.
"""

from __future__ import annotations

from dataclasses import dataclass

GNSS_ENABLED = False
GNSS_REAL_HARDWARE_TX = False
GNSS_CONFIG_WRITE = False
GNSS_BAUD = 38400
GNSS_UART_RX_PIN: int | None = None
GNSS_UART_TX_PIN: int | None = None


@dataclass(frozen=True)
class ReceiveOnlyConfig:
    """Configuration that cannot select an unverified physical UART."""

    enabled: bool = GNSS_ENABLED
    baudrate: int = GNSS_BAUD
    rx_pin: int | None = GNSS_UART_RX_PIN
    tx_pin: int | None = GNSS_UART_TX_PIN
    real_hardware_tx: bool = GNSS_REAL_HARDWARE_TX
    config_write: bool = GNSS_CONFIG_WRITE

    def validate(self) -> None:
        if self.real_hardware_tx or self.config_write:
            raise ValueError("receive-only GNSS boundary forbids transmit/configuration")
        if self.enabled and self.rx_pin is None:
            raise ValueError("an enabled GNSS path requires a separately verified RX pin")


def default_config() -> ReceiveOnlyConfig:
    """Return the safe disabled configuration; no hardware is opened."""

    config = ReceiveOnlyConfig()
    config.validate()
    return config
