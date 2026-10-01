from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pi5.telemetry.gnss import parse_nmea, parse_ubx, timeout_sample

from .fixtures import MALFORMED_GGA, NO_FIX_GGA, VALID_GGA, nmea_sentence, ubx_frame


CAPTURE = datetime(2026, 9, 26, 0, 0, 10, tzinfo=timezone.utc)


def test_valid_synthetic_nmea_preserves_provenance_and_fields():
    sample = parse_nmea(VALID_GGA, capture_timestamp=CAPTURE, sequence=1)

    assert sample.fix_state == "VALID_FIX"
    assert sample.source_type == "SYNTHETIC"
    assert sample.parser == "nmea-gga"
    assert sample.latitude == 10.0
    assert sample.longitude == 106.0
    assert sample.altitude_m == 12.3
    assert sample.to_dict()["sample_timestamp"].endswith("Z")


def test_nmea_no_fix_keeps_unknown_coordinates_unavailable():
    sample = parse_nmea(NO_FIX_GGA, capture_timestamp=CAPTURE, sequence=2)

    assert sample.fix_state == "NO_FIX"
    assert sample.availability == "UNAVAILABLE"
    assert sample.latitude is None
    assert sample.longitude is None


def test_nmea_bad_checksum_is_typed():
    invalid = VALID_GGA[:-2] + ("00" if not VALID_GGA.endswith("00") else "FF")

    sample = parse_nmea(invalid, capture_timestamp=CAPTURE)

    assert sample.fix_state == "BAD_CHECKSUM"
    assert sample.error_code == "BAD_CHECKSUM"


def test_nmea_malformed_stale_and_sequence_gap_are_explicit():
    malformed = parse_nmea(MALFORMED_GGA, capture_timestamp=CAPTURE)
    stale_sentence = nmea_sentence("GPGGA,230000.00,1000.0000,N,10600.0000,E,1,08,0.9,12.3,M,0.0,M,,")
    stale = parse_nmea(stale_sentence, capture_timestamp=CAPTURE, stale_after=timedelta(seconds=30))
    gap = parse_nmea(VALID_GGA, capture_timestamp=CAPTURE, sequence=3, previous_sequence=1)

    assert malformed.fix_state == "MALFORMED"
    assert stale.fix_state == "STALE"
    assert stale.stale is True
    assert gap.fix_state == "SEQUENCE_GAP"
    assert gap.availability == "UNAVAILABLE"


def test_synthetic_ubx_frames_validate_safely_without_claiming_module_support():
    valid = parse_ubx(ubx_frame(), capture_timestamp=CAPTURE, sequence=1)
    bad_checksum = parse_ubx(ubx_frame()[:-1] + b"\x00", capture_timestamp=CAPTURE)
    truncated = parse_ubx(ubx_frame()[:-1], capture_timestamp=CAPTURE)
    timeout = timeout_sample(parser="ubx-frame", capture_timestamp=CAPTURE)

    assert valid.fix_state == "UNSUPPORTED_MESSAGE"
    assert valid.error_code == "UNSUPPORTED_MESSAGE"
    assert bad_checksum.fix_state == "BAD_CHECKSUM"
    assert truncated.error_code == "TRUNCATED"
    assert timeout.fix_state == "TIMEOUT"


def test_contract_has_no_serial_write_or_control_semantics():
    from pi5.telemetry import gnss

    assert not hasattr(gnss, "write")
    assert not hasattr(gnss, "send")
    payload = parse_nmea(VALID_GGA, capture_timestamp=CAPTURE).to_dict()
    assert "command" not in payload
    assert "arm" not in payload
    assert "disarm" not in payload
