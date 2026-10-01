from __future__ import annotations

from datetime import datetime, timezone

from pi5.web.models import FixState
from pi5.web.telemetry import ReadOnlyGnssTelemetrySource

from .fixtures import nmea_sentence


def test_web_adapter_maps_a_valid_nmea_fix_without_opening_hardware():
    calls: list[float] = []
    now = datetime.now(timezone.utc)
    sentence = nmea_sentence(f"GNGGA,{now.strftime('%H%M%S.%f')},1000.0000,N,10600.0000,E,1,08,0.9,12.3,M,0.0,M,,")

    def read_line(timeout: float) -> str:
        calls.append(timeout)
        return sentence

    source = ReadOnlyGnssTelemetrySource(read_line, baudrate=38400)
    sample = source.read()

    assert calls == [0.25]
    assert source.baudrate == 38400
    assert sample["schema_version"] == "scope05.telemetry.v1"
    assert sample["fix_state"] == FixState.FIX.value
    assert sample["latitude"] == 10.0
    assert sample["longitude"] == 106.0
    assert sample["altitude_m"] == 12.3
    assert sample["gnss"] == {"baudrate": 38400, "rx_pin": None, "tx_pin": None}


def test_web_adapter_is_unavailable_without_an_injected_reader():
    sample = ReadOnlyGnssTelemetrySource().read()

    assert sample["fix_state"] == FixState.UNAVAILABLE.value
    assert sample["stale"] is True
    assert sample["latitude"] is None
    assert sample["longitude"] is None


def test_web_adapter_fails_closed_when_reader_raises():
    def read_line(timeout: float) -> str:
        raise OSError("serial unavailable")

    sample = ReadOnlyGnssTelemetrySource(read_line).read()

    assert sample["fix_state"] == FixState.INVALID.value
    assert sample["stale"] is True
    assert sample["latitude"] is None

