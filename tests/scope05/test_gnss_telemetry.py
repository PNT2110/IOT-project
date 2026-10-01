from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pi5.telemetry.gnss import parse_nmea, parse_ubx, timeout_sample

from .fixtures import NO_FIX_GGA, VALID_GGA, VALID_GGA_NO_FRACTION, nmea_sentence


CAPTURE = datetime(2026, 9, 26, 0, 0, 10, tzinfo=timezone.utc)


def test_valid_gga_preserves_coordinates_and_provenance():
    sample = parse_nmea(VALID_GGA, capture_timestamp=CAPTURE, sequence=1)

    assert sample.fix_state == "VALID_FIX"
    assert sample.source_type == "SYNTHETIC"
    assert sample.latitude == 10.0
    assert sample.longitude == 106.0
    assert sample.altitude_m == 12.3
    assert sample.to_dict()["sample_timestamp"].endswith("Z")


def test_nmea_time_without_fraction_is_valid():
    sample = parse_nmea(VALID_GGA_NO_FRACTION, capture_timestamp=CAPTURE)

    assert sample.fix_state == "VALID_FIX"
    assert sample.sample_timestamp == CAPTURE


def test_no_fix_never_claims_coordinates():
    sample = parse_nmea(NO_FIX_GGA, capture_timestamp=CAPTURE)

    assert sample.fix_state == "NO_FIX"
    assert sample.availability == "UNAVAILABLE"
    assert sample.latitude is None
    assert sample.longitude is None


def test_bad_checksum_stale_and_sequence_gap_are_explicit():
    invalid = VALID_GGA[:-2] + ("00" if not VALID_GGA.endswith("00") else "FF")
    bad = parse_nmea(invalid, capture_timestamp=CAPTURE)
    stale_sentence = nmea_sentence("GPGGA,230000.00,1000.0000,N,10600.0000,E,1,08,0.9,12.3,M,0.0,M,,")
    stale = parse_nmea(stale_sentence, capture_timestamp=CAPTURE, stale_after=timedelta(seconds=30))
    gap = parse_nmea(VALID_GGA, capture_timestamp=CAPTURE, sequence=3, previous_sequence=1)

    assert bad.fix_state == "BAD_CHECKSUM"
    assert stale.fix_state == "STALE"
    assert stale.stale is True
    assert gap.fix_state == "SEQUENCE_GAP"
    assert gap.availability == "UNAVAILABLE"


def test_coordinate_bounds_reject_impossible_latitude():
    impossible = nmea_sentence("GPGGA,000010,9000.0001,N,10600.0000,E,1,08,0.9,12.3,M,0.0,M,,")

    sample = parse_nmea(impossible, capture_timestamp=CAPTURE)

    assert sample.fix_state == "MALFORMED"
    assert sample.availability == "UNAVAILABLE"


def test_ubx_validation_is_read_only_and_does_not_claim_decoded_telemetry():
    payload = b"\x01\x07\x00\x00"
    checksum_a = 0
    checksum_b = 0
    for byte in payload:
        checksum_a = (checksum_a + byte) & 0xFF
        checksum_b = (checksum_b + checksum_a) & 0xFF
    frame = b"\xb5\x62" + payload + bytes((checksum_a, checksum_b))

    sample = parse_ubx(frame, capture_timestamp=CAPTURE)
    timeout = timeout_sample(parser="ubx-frame", capture_timestamp=CAPTURE)

    assert sample.fix_state == "UNSUPPORTED_MESSAGE"
    assert sample.error_code == "UNSUPPORTED_MESSAGE"
    assert timeout.fix_state == "TIMEOUT"
