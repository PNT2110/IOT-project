from __future__ import annotations

from pi5.telemetry.gnss_passive_baud_probe import ProbeResult, probe_bauds

from .fixtures import NO_FIX_GGA, VALID_GGA, nmea_sentence


class FakeSource:
    def __init__(self, chunks: list[bytes]):
        self.chunks = list(chunks)
        self.closed = False

    def read(self, timeout: float) -> bytes:
        assert timeout >= 0
        return self.chunks.pop(0) if self.chunks else b""

    def close(self) -> None:
        self.closed = True


def factory_for(mapping: dict[int, list[bytes]]):
    opened: list[int] = []

    def factory(baud: int) -> FakeSource:
        opened.append(baud)
        return FakeSource(mapping.get(baud, []))

    factory.opened = opened
    return factory


def test_valid_nmea_at_38400_is_detected():
    factory = factory_for({38400: [VALID_GGA.encode() + b"\r\n"]})
    result = probe_bauds(factory, timeout_per_baud=0.001)
    assert result == ProbeResult("DETECTED_38400", baudrate=38400, valid_frames=1, bytes_seen=len(VALID_GGA) + 2)


def test_valid_nmea_at_115200_is_detected():
    factory = factory_for({115200: [VALID_GGA.encode() + b"\n"]})
    result = probe_bauds(factory, timeout_per_baud=0.001)
    assert result.state == "DETECTED_115200"
    assert result.baudrate == 115200


def test_no_fix_valid_checksum_counts_as_nmea_framing():
    factory = factory_for({38400: [NO_FIX_GGA.encode() + b"\n"]})
    result = probe_bauds(factory, timeout_per_baud=0.001)
    assert result.state == "DETECTED_38400"
    assert result.valid_frames == 1


def test_malformed_first_candidate_then_valid_second_candidate():
    factory = factory_for({38400: [b"$GPGGA,bad*00\n"], 115200: [VALID_GGA.encode() + b"\n"]})
    result = probe_bauds(factory, timeout_per_baud=0.001)
    assert result.state == "DETECTED_115200"
    assert factory.opened == [38400, 115200]


def test_valid_looking_text_with_bad_checksum_does_not_detect():
    body = b"GPGGA,000000.00,,,,,0,00,,,M,,M,,"
    bad = b"$" + body + b"*00\n"
    factory = factory_for({38400: [bad], 115200: [bad]})
    result = probe_bauds(factory, timeout_per_baud=0.001)
    assert result.state == "NO_VALID_NMEA"


def test_empty_sources_return_timeout():
    factory = factory_for({38400: [], 115200: []})
    result = probe_bauds(factory, timeout_per_baud=0.001)
    assert result.state == "TIMEOUT"


def test_valid_frames_at_both_candidates_are_ambiguous():
    factory = factory_for({38400: [VALID_GGA.encode() + b"\n"], 115200: [VALID_GGA.encode() + b"\n"]})
    result = probe_bauds(factory, timeout_per_baud=0.001)
    assert result.state == "AMBIGUOUS"
    assert result.baudrate is None


def test_probe_has_no_transmit_path_and_limits_candidates():
    class WriteTrap(FakeSource):
        def write(self, data: bytes) -> None:
            raise AssertionError("probe attempted serial write")

    opened: list[int] = []

    def factory(baud: int) -> WriteTrap:
        opened.append(baud)
        return WriteTrap([])

    result = probe_bauds(factory, bauds=[38400, 115200], timeout_per_baud=0.001)
    assert result.state == "TIMEOUT"
    assert opened == [38400, 115200]
