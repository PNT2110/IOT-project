from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Protocol

from ..telemetry.gnss import parse_nmea, timeout_sample
from .models import FixState, TelemetrySample


class TelemetrySource(Protocol):
    """Minimal read-only source contract used by the Pi web routes."""

    def read(self) -> dict[str, object]: ...


class MockTelemetrySource:
    def __init__(self, sample: TelemetrySample | None = None) -> None:
        self.sample = sample or TelemetrySample(
            schema_version="scope04.telemetry.v1",
            source="MOCK",
            timestamp=datetime.now(timezone.utc),
            sequence=0,
            stale=True,
            fix_state=FixState.UNAVAILABLE,
        )

    def read(self) -> dict[str, object]:
        return self.sample.as_dict()

    def set_sample(self, sample: TelemetrySample) -> None:
        if sample.source != "MOCK":
            raise ValueError("SCOPE-04 mock source must identify source=MOCK")
        self.sample = sample


class ReadOnlyGnssTelemetrySource:
    """Adapt an injected NMEA reader to the Pi web telemetry contract.

    The reader is deliberately injected instead of opened here.  This keeps
    the web layer independent from serial devices and prevents an unverified
    GPIO mapping from becoming an accidental hardware write path.  A future
    hardware adapter may supply ``read_line(timeout_seconds)`` after board,
    wiring and receive-only authorization have been verified.
    """

    def __init__(
        self,
        read_line: Callable[[float], str | bytes | None] | None = None,
        *,
        baudrate: int = 38400,
        source: str = "GNSS:NMEA",
    ) -> None:
        if baudrate <= 0:
            raise ValueError("baudrate must be positive")
        self._read_line = read_line
        self.baudrate = baudrate
        self.source = source
        self._sequence = 0

    def read(self) -> dict[str, object]:
        capture_timestamp = datetime.now(timezone.utc)
        self._sequence += 1
        if self._read_line is None:
            parsed = timeout_sample(
                parser="nmea-gga",
                capture_timestamp=capture_timestamp,
                sequence=self._sequence,
                source=self.source,
            )
        else:
            try:
                raw_line = self._read_line(0.25)
                if raw_line is None or raw_line == b"" or raw_line == "":
                    parsed = timeout_sample(
                        parser="nmea-gga",
                        capture_timestamp=capture_timestamp,
                        sequence=self._sequence,
                        source=self.source,
                    )
                else:
                    line = raw_line.decode("ascii") if isinstance(raw_line, bytes) else raw_line
                    parsed = parse_nmea(
                        line,
                        capture_timestamp=capture_timestamp,
                        sequence=self._sequence,
                        source=self.source,
                    )
            except Exception:
                # A hardware adapter must fail closed: a reader error must
                # never turn into a control action or an unhandled web 500.
                parsed = parse_nmea(
                    "",
                    capture_timestamp=capture_timestamp,
                    sequence=self._sequence,
                    source=self.source,
                )

        state = {
            "VALID_FIX": FixState.FIX,
            "NO_FIX": FixState.NO_FIX,
            "STALE": FixState.STALE,
            "TIMEOUT": FixState.UNAVAILABLE,
            "UNAVAILABLE": FixState.UNAVAILABLE,
            "MALFORMED": FixState.INVALID,
            "BAD_CHECKSUM": FixState.INVALID,
            "SEQUENCE_GAP": FixState.STALE,
        }.get(parsed.fix_state, FixState.INVALID)
        return TelemetrySample(
            schema_version="scope05.telemetry.v1",
            source=self.source,
            timestamp=parsed.sample_timestamp or parsed.capture_timestamp,
            sequence=parsed.sequence or 0,
            stale=parsed.stale or state in {FixState.STALE, FixState.UNAVAILABLE, FixState.INVALID},
            fix_state=state,
            latitude=parsed.latitude,
            longitude=parsed.longitude,
            altitude_m=parsed.altitude_m,
            gnss_baudrate=self.baudrate,
        ).as_dict()


def build_3d_view(telemetry: dict[str, object]) -> dict[str, object]:
    orientation_fields = ("heading_deg", "pitch_deg", "roll_deg")
    available = all(telemetry.get(field) is not None for field in orientation_fields)
    return {
        "enabled": available,
        "orientation": {field: telemetry.get(field) if available else None for field in orientation_fields},
        "label": "AVAILABLE" if available else "UNAVAILABLE",
        "animation": False,
        "reason": None if available else "orientation fields are unavailable",
    }
