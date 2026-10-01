"""Offline-safe passive NMEA baud probe.

This module consumes an injected read-only source. It never opens a serial
device and exposes no transmit or GNSS configuration operation. A caller that
later receives explicit live-capture authorization can provide a source whose
``read(timeout)`` method reconfigures a receive-only port for each candidate.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable, Protocol, Sequence


SUPPORTED_BAUDS = (38400, 115200)
VALID_STATES = frozenset(
    {"DETECTED_38400", "DETECTED_115200", "AMBIGUOUS", "NO_VALID_NMEA", "TIMEOUT"}
)


class ReadSource(Protocol):
    """Minimal receive-only source expected by :func:`probe_bauds`."""

    def read(self, timeout: float) -> bytes:
        """Return received bytes, or ``b""`` when the bounded read times out."""


@dataclass(frozen=True)
class ProbeResult:
    state: str
    baudrate: int | None = None
    valid_frames: int = 0
    bytes_seen: int = 0

    def __post_init__(self) -> None:
        if self.state not in VALID_STATES:
            raise ValueError(f"unsupported probe state: {self.state}")


def _nmea_checksum(body: bytes) -> int:
    checksum = 0
    for byte in body:
        checksum ^= byte
    return checksum


def _valid_nmea_frame(line: bytes) -> bool:
    """Validate NMEA framing/checksum without decoding or interpreting payload."""

    text = line.strip()
    if not text.startswith(b"$") or b"*" not in text:
        return False
    body, supplied = text[1:].rsplit(b"*", 1)
    if len(body) == 0 or len(supplied) != 2:
        return False
    try:
        expected = int(supplied, 16)
        body.decode("ascii")
    except (UnicodeDecodeError, ValueError):
        return False
    return _nmea_checksum(body) == expected


def _valid_frames_from_buffer(buffer: bytes) -> tuple[bytes, int]:
    """Return an incomplete tail and count complete valid line-delimited frames."""

    lines = buffer.split(b"\n")
    tail = lines.pop()
    valid = sum(1 for line in lines if _valid_nmea_frame(line))
    return tail[-4096:], valid


def probe_bauds(
    source_factory: Callable[[int], ReadSource],
    *,
    bauds: Sequence[int] = SUPPORTED_BAUDS,
    timeout_per_baud: float = 2.0,
    clock: Callable[[], float] = time.monotonic,
) -> ProbeResult:
    """Passively test evidence-supported baud candidates within a time bound.

    ``source_factory`` is dependency-injected so synthetic tests can replay
    bytes. It is never called with a baud outside ``bauds`` and this function
    never invokes a write/send/configuration method.
    """

    if not bauds:
        raise ValueError("at least one baud candidate is required")
    if any(baud not in SUPPORTED_BAUDS for baud in bauds):
        raise ValueError(f"unsupported baud candidate; allowed: {SUPPORTED_BAUDS}")
    if any(baud <= 0 for baud in bauds):
        raise ValueError("baud candidates must be positive")
    if not 0 < timeout_per_baud <= 300:
        raise ValueError("timeout_per_baud must be within (0, 300] seconds")

    detected: list[tuple[int, int]] = []
    total_bytes = 0
    any_bytes = False
    for baud in bauds:
        source = source_factory(baud)
        buffer = b""
        valid_frames = 0
        deadline = clock() + timeout_per_baud
        try:
            while clock() < deadline:
                chunk = source.read(max(0.0, deadline - clock()))
                if not chunk:
                    continue
                if not isinstance(chunk, (bytes, bytearray)):
                    raise TypeError("read source must return bytes")
                chunk_bytes = bytes(chunk)
                any_bytes = True
                total_bytes += len(chunk_bytes)
                buffer, new_valid = _valid_frames_from_buffer(buffer + chunk_bytes)
                valid_frames += new_valid
                if valid_frames:
                    detected.append((baud, valid_frames))
                    break
        finally:
            close = getattr(source, "close", None)
            if close is not None:
                close()

    if len(detected) > 1:
        return ProbeResult("AMBIGUOUS", valid_frames=sum(count for _, count in detected), bytes_seen=total_bytes)
    if len(detected) == 1:
        baud, count = detected[0]
        state = f"DETECTED_{baud}"
        return ProbeResult(state, baudrate=baud, valid_frames=count, bytes_seen=total_bytes)
    if any_bytes:
        return ProbeResult("NO_VALID_NMEA", bytes_seen=total_bytes)
    return ProbeResult("TIMEOUT")
