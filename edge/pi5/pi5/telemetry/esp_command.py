"""Pi -> ESP32 command channel (USB serial, same fd as telemetry).

Protocol (one ASCII line, NMEA-style XOR checksum, max 128 bytes)::

    $AUTH,ALLOW,<seconds>,<request_ref>*HH   allow arming for <seconds>
    $AUTH,DENY,<request_ref>*HH              deny / revoke arming
    $PID,<roll|pitch|yaw|angle>,<kp>,<ki>,<kd>*HH   (ESP rejects while ARMED)
    $MAXALT,<metres>*HH                      (ESP rejects while ARMED)
    $PING*HH

Safety boundary
---------------
* There is deliberately NO arm/disarm/motor command. The Pi can only grant or
  revoke the *permission* to arm; the pilot still arms with the RC switch.
* Authorization lives only in ESP RAM: after an ESP reboot it is BLOCKED
  until the Pi re-sends an ALLOW, so :meth:`EspFlightAuthorizationBridge.refresh`
  must be called periodically.
* A revoke while airborne does not cut motors (that would drop the aircraft);
  it prevents the next arm. This is enforced in firmware (FC_can_bang/FC_can_bang.ino).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Literal

_TOKEN = re.compile(r"^[A-Za-z0-9_.\-]{1,32}$")
MAX_AUTH_SECONDS = 86_400
PID_AXES = ("roll", "pitch", "yaw", "angle")


class EspCommandError(ValueError):
    pass


def checksum(body: str) -> str:
    value = 0
    for char in body.encode("ascii"):
        value ^= char
    return f"{value:02X}"


def build_command(*fields: str) -> bytes:
    if not fields:
        raise EspCommandError("empty command")
    for field in fields:
        if not _TOKEN.match(field):
            raise EspCommandError(f"invalid command field: {field!r}")
    body = ",".join(fields)
    line = f"${body}*{checksum(body)}\n".encode("ascii")
    if len(line) > 128:
        raise EspCommandError("command too long")
    return line


def _num(value: float, low: float, high: float, name: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise EspCommandError(f"{name} must be a finite number")
    if not low <= float(value) <= high:
        raise EspCommandError(f"{name} out of range {low}..{high}")
    return f"{float(value):.4f}".rstrip("0").rstrip(".") or "0"


def _ref(request_ref: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_\-]", "_", request_ref)[:32]
    if not cleaned:
        raise EspCommandError("request_ref is required")
    return cleaned


def auth_allow(seconds: int, request_ref: str) -> bytes:
    if isinstance(seconds, bool) or not isinstance(seconds, int) or not 1 <= seconds <= MAX_AUTH_SECONDS:
        raise EspCommandError("seconds must be 1..86400")
    return build_command("AUTH", "ALLOW", str(seconds), _ref(request_ref))


def auth_deny(request_ref: str) -> bytes:
    return build_command("AUTH", "DENY", _ref(request_ref))


def set_pid(axis: str, kp: float, ki: float, kd: float) -> bytes:
    if axis not in PID_AXES:
        raise EspCommandError("axis must be roll, pitch, yaw or angle")
    return build_command("PID", axis, _num(kp, 0, 50, "kp"), _num(ki, 0, 50, "ki"), _num(kd, 0, 5, "kd"))


def set_max_altitude(metres: float) -> bytes:
    return build_command("MAXALT", _num(metres, 2, 500, "metres"))


def ping() -> bytes:
    return build_command("PING")


Decision = Literal["APPROVED", "REJECTED"]


@dataclass
class _ActiveDecision:
    request_ref: str
    decision: Decision
    valid_until: datetime | None


class EspFlightAuthorizationBridge:
    """Turns an authority decision into ESP arm-permission commands.

    ``write`` is normally ``UsbSerialLineReader(..., allow_commands=True).write_line``.
    """

    def __init__(self, write: Callable[[bytes], None], *, clock: Callable[[], datetime] | None = None) -> None:
        self._write = write
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._active: _ActiveDecision | None = None

    def apply_decision(self, request_ref: str, decision: Decision, valid_until: datetime | None = None) -> bytes:
        if decision not in ("APPROVED", "REJECTED"):
            raise EspCommandError("decision must be APPROVED or REJECTED")
        if decision == "APPROVED":
            if valid_until is None or valid_until.tzinfo is None:
                raise EspCommandError("an approval needs a timezone-aware end time")
        self._active = _ActiveDecision(request_ref, decision, valid_until)
        return self.refresh()

    def refresh(self) -> bytes:
        """(Re)send the current state. Anything other than a live approval is DENY."""
        active = self._active
        if active is None:
            line = auth_deny("NONE")
        elif active.decision == "APPROVED" and active.valid_until is not None:
            remaining = int((active.valid_until - self._clock()).total_seconds())
            line = auth_allow(min(remaining, MAX_AUTH_SECONDS), active.request_ref) if remaining >= 1 else auth_deny(active.request_ref)
        else:
            line = auth_deny(active.request_ref)
        self._write(line)
        return line
