from __future__ import annotations

from dataclasses import dataclass

from pi5.telemetry.gnss_passive_baud_probe import probe_bauds

from .fixtures import VALID_GGA


@dataclass
class Source:
    payload: bytes
    closed: bool = False

    def read(self, timeout: float) -> bytes:
        del timeout
        payload, self.payload = self.payload, b""
        return payload

    def close(self) -> None:
        self.closed = True


def test_passive_probe_detects_valid_nmea_without_write_path():
    sources: list[Source] = []

    def factory(baud: int) -> Source:
        source = Source((VALID_GGA + "\n").encode() if baud == 38400 else b"")
        sources.append(source)
        return source

    result = probe_bauds(factory, bauds=(38400,), timeout_per_baud=0.1)

    assert result.state == "DETECTED_38400"
    assert result.baudrate == 38400
    assert result.valid_frames == 1
    assert all(source.closed for source in sources)
