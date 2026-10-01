"""Synthetic/read-only GNSS frame parsing primitives.

This module consumes supplied bytes/strings only. It has no serial-device
dependency and deliberately exposes no write/configuration operation. NMEA
support is limited to GGA scaffolding; UBX framing is validated, but payload
compatibility with an actual module is intentionally not claimed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, time, timedelta, timezone
import re
from typing import Any

SCHEMA_VERSION = "scope05.telemetry.v1"
FIX_STATES = frozenset(
    {
        "VALID_FIX",
        "NO_FIX",
        "STALE",
        "TIMEOUT",
        "BAD_CHECKSUM",
        "MALFORMED",
        "SEQUENCE_GAP",
        "UNAVAILABLE",
        "UNSUPPORTED_MESSAGE",
    }
)

_HEX = re.compile(r"^[0-9A-Fa-f]{2}$")


@dataclass(frozen=True)
class TelemetrySample:
    """Versioned read-only telemetry envelope with unknowns represented by None."""

    source: str
    source_type: str
    parser: str
    schema_version: str
    capture_timestamp: datetime
    sample_timestamp: datetime | None
    sequence: int | None
    stale: bool
    fix_state: str
    availability: str
    latitude: float | None = None
    longitude: float | None = None
    altitude_m: float | None = None
    hdop: float | None = None
    accuracy_m: float | None = None
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for field in ("capture_timestamp", "sample_timestamp"):
            value = result[field]
            result[field] = _isoformat(value) if value is not None else None
        return result


def _isoformat(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _base_sample(
    *,
    source: str,
    parser: str,
    capture_timestamp: datetime,
    sample_timestamp: datetime | None,
    sequence: int | None,
    fix_state: str,
    stale: bool,
    error_code: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    altitude_m: float | None = None,
    hdop: float | None = None,
) -> TelemetrySample:
    if capture_timestamp.tzinfo is None:
        raise ValueError("capture_timestamp must be timezone-aware")
    if sample_timestamp is not None and sample_timestamp.tzinfo is None:
        raise ValueError("sample_timestamp must be timezone-aware")
    if fix_state not in FIX_STATES:
        raise ValueError(f"unsupported fix state: {fix_state}")
    available = fix_state == "VALID_FIX" and latitude is not None and longitude is not None
    return TelemetrySample(
        source=source,
        source_type="SYNTHETIC",
        parser=parser,
        schema_version=SCHEMA_VERSION,
        capture_timestamp=capture_timestamp,
        sample_timestamp=sample_timestamp,
        sequence=sequence,
        stale=stale,
        fix_state=fix_state,
        availability="AVAILABLE" if available else "UNAVAILABLE",
        latitude=latitude,
        longitude=longitude,
        altitude_m=altitude_m,
        hdop=hdop,
        error_code=error_code,
    )


def _sequence_state(sample: TelemetrySample, previous_sequence: int | None) -> TelemetrySample:
    if previous_sequence is None or sample.sequence is None:
        return sample
    if sample.sequence == previous_sequence + 1:
        return sample
    return replace(
        sample,
        stale=True,
        fix_state="SEQUENCE_GAP",
        availability="UNAVAILABLE",
        error_code="SEQUENCE_GAP",
    )


def _error_sample(
    *,
    source: str,
    parser: str,
    capture_timestamp: datetime,
    sequence: int | None,
    state: str,
    error_code: str,
) -> TelemetrySample:
    return _base_sample(
        source=source,
        parser=parser,
        capture_timestamp=capture_timestamp,
        sample_timestamp=None,
        sequence=sequence,
        fix_state=state,
        stale=state != "MALFORMED",
        error_code=error_code,
    )


def _nmea_checksum(body: str) -> int:
    checksum = 0
    for byte in body.encode("ascii"):
        checksum ^= byte
    return checksum


def _nmea_time(value: str, capture_timestamp: datetime) -> datetime:
    # NMEA permits both hhmmss and hhmmss.sss forms.  Accepting only the
    # fractional form incorrectly marks otherwise valid GGA frames malformed.
    format_string = "%H%M%S.%f" if "." in value else "%H%M%S"
    parsed = datetime.strptime(value, format_string).time()
    capture_utc = capture_timestamp.astimezone(timezone.utc)
    candidate = datetime.combine(capture_utc.date(), parsed, tzinfo=timezone.utc)
    delta = candidate - capture_utc
    if delta > timedelta(hours=12):
        candidate -= timedelta(days=1)
    elif delta < -timedelta(hours=12):
        candidate += timedelta(days=1)
    return candidate


def _coordinate(value: str, hemisphere: str, degree_digits: int) -> float:
    if not value or hemisphere not in {"N", "S", "E", "W"}:
        raise ValueError("invalid coordinate")
    degrees = float(value[:degree_digits])
    minutes = float(value[degree_digits:])
    maximum = 90.0 if degree_digits == 2 else 180.0
    if minutes >= 60 or degrees > maximum or (degrees == maximum and minutes != 0):
        raise ValueError("invalid coordinate minutes")
    result = degrees + minutes / 60
    return -result if hemisphere in {"S", "W"} else result


def parse_nmea(
    sentence: str,
    *,
    capture_timestamp: datetime,
    sequence: int | None = None,
    previous_sequence: int | None = None,
    stale_after: timedelta = timedelta(seconds=30),
    source: str = "SYNTHETIC:nmea",
) -> TelemetrySample:
    """Parse a synthetic NMEA GGA sentence without touching a serial device."""

    text = sentence.strip()
    parser = "nmea-gga"
    if not text.startswith("$") or "*" not in text:
        return _error_sample(source=source, parser=parser, capture_timestamp=capture_timestamp, sequence=sequence, state="MALFORMED", error_code="MALFORMED")
    body, supplied = text[1:].split("*", 1)
    if not _HEX.fullmatch(supplied):
        return _error_sample(source=source, parser=parser, capture_timestamp=capture_timestamp, sequence=sequence, state="MALFORMED", error_code="MALFORMED")
    if _nmea_checksum(body) != int(supplied, 16):
        return _error_sample(source=source, parser=parser, capture_timestamp=capture_timestamp, sequence=sequence, state="BAD_CHECKSUM", error_code="BAD_CHECKSUM")
    fields = body.split(",")
    if not fields or not fields[0].upper().endswith("GGA"):
        return _error_sample(source=source, parser=parser, capture_timestamp=capture_timestamp, sequence=sequence, state="UNSUPPORTED_MESSAGE", error_code="UNSUPPORTED_MESSAGE")
    if len(fields) < 15:
        return _error_sample(source=source, parser=parser, capture_timestamp=capture_timestamp, sequence=sequence, state="MALFORMED", error_code="MALFORMED")
    try:
        sample_timestamp = _nmea_time(fields[1], capture_timestamp)
        quality = int(fields[6])
        hdop = float(fields[8]) if fields[8] else None
        if quality == 0:
            sample = _base_sample(
                source=source, parser=parser, capture_timestamp=capture_timestamp,
                sample_timestamp=sample_timestamp, sequence=sequence,
                fix_state="NO_FIX", stale=False, hdop=hdop,
            )
        else:
            latitude = _coordinate(fields[2], fields[3], 2)
            longitude = _coordinate(fields[4], fields[5], 3)
            altitude = float(fields[9]) if fields[9] else None
            age = capture_timestamp.astimezone(timezone.utc) - sample_timestamp
            stale = age > stale_after
            sample = _base_sample(
                source=source, parser=parser, capture_timestamp=capture_timestamp,
                sample_timestamp=sample_timestamp, sequence=sequence,
                fix_state="STALE" if stale else "VALID_FIX", stale=stale,
                latitude=latitude, longitude=longitude, altitude_m=altitude, hdop=hdop,
                error_code="STALE" if stale else None,
            )
    except (TypeError, ValueError):
        return _error_sample(source=source, parser=parser, capture_timestamp=capture_timestamp, sequence=sequence, state="MALFORMED", error_code="MALFORMED")
    return _sequence_state(sample, previous_sequence)


def parse_ubx(
    frame: bytes,
    *,
    capture_timestamp: datetime,
    sequence: int | None = None,
    previous_sequence: int | None = None,
    source: str = "SYNTHETIC:ubx",
) -> TelemetrySample:
    """Validate UBX framing; payload decoding remains deliberately unsupported."""

    parser = "ubx-frame"
    if len(frame) < 8 or frame[:2] != b"\xb5\x62":
        return _error_sample(source=source, parser=parser, capture_timestamp=capture_timestamp, sequence=sequence, state="MALFORMED", error_code="MALFORMED")
    payload_length = int.from_bytes(frame[4:6], "little")
    expected_length = 8 + payload_length
    if len(frame) < expected_length:
        return _error_sample(source=source, parser=parser, capture_timestamp=capture_timestamp, sequence=sequence, state="MALFORMED", error_code="TRUNCATED")
    if len(frame) > expected_length:
        return _error_sample(source=source, parser=parser, capture_timestamp=capture_timestamp, sequence=sequence, state="MALFORMED", error_code="MALFORMED")
    payload = frame[2:6 + payload_length]
    ck_a = 0
    ck_b = 0
    for byte in payload:
        ck_a = (ck_a + byte) & 0xFF
        ck_b = (ck_b + ck_a) & 0xFF
    if frame[-2:] != bytes((ck_a, ck_b)):
        return _error_sample(source=source, parser=parser, capture_timestamp=capture_timestamp, sequence=sequence, state="BAD_CHECKSUM", error_code="BAD_CHECKSUM")
    sample = _error_sample(
        source=source, parser=parser, capture_timestamp=capture_timestamp,
        sequence=sequence, state="UNSUPPORTED_MESSAGE", error_code="UNSUPPORTED_MESSAGE",
    )
    return _sequence_state(sample, previous_sequence)


def timeout_sample(
    *,
    parser: str,
    capture_timestamp: datetime,
    sequence: int | None = None,
    source: str = "SYNTHETIC:timeout",
) -> TelemetrySample:
    """Create an explicit timeout result without pretending a frame arrived."""

    return _error_sample(
        source=source, parser=parser, capture_timestamp=capture_timestamp,
        sequence=sequence, state="TIMEOUT", error_code="TIMEOUT",
    )
