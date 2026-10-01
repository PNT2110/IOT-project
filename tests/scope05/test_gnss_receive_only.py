from __future__ import annotations


def test_gnss_receive_only_defaults_are_disabled_and_safe():
    from pi5.telemetry.gnss_receive_only import (
        GNSS_BAUD,
        GNSS_CONFIG_WRITE,
        GNSS_ENABLED,
        GNSS_REAL_HARDWARE_TX,
        GNSS_UART_RX_PIN,
        GNSS_UART_TX_PIN,
        default_config,
    )

    config = default_config()

    assert GNSS_ENABLED is False
    assert GNSS_REAL_HARDWARE_TX is False
    assert GNSS_CONFIG_WRITE is False
    assert GNSS_BAUD == 38400
    assert GNSS_UART_RX_PIN is None
    assert GNSS_UART_TX_PIN is None
    assert config.enabled is False


def test_receive_only_rejects_transmit_or_configuration_flags():
    from pi5.telemetry.gnss_receive_only import ReceiveOnlyConfig

    for kwargs in ({"real_hardware_tx": True}, {"config_write": True}):
        try:
            ReceiveOnlyConfig(**kwargs).validate()
        except ValueError:
            continue
        raise AssertionError("unsafe GNSS option was accepted")
