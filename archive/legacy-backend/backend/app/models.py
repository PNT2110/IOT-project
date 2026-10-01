from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GpsFix(BaseModel):
    timestamp: datetime = Field(default_factory=utc_now)
    latitude: float | None = None
    longitude: float | None = None
    altitude_m: float | None = None
    speed_mps: float | None = None
    course_deg: float | None = None
    satellites: int | None = None
    hdop: float | None = None
    fix_quality: int = 0
    valid: bool = False
    stale: bool = True
    raw: str | None = None


class PidAxis(BaseModel):
    kp: float | None = None
    ki: float | None = None
    kd: float | None = None
    setpoint: float | None = None
    measured: float | None = None
    output: float | None = None


class Attitude(BaseModel):
    roll: float = 0
    pitch: float = 0
    yaw: float = 0


class GeofenceState(BaseModel):
    status: Literal["unknown", "safe", "warning", "breach"] = "unknown"
    zone_id: str | None = None
    zone_name: str | None = None
    distance_m: float | None = None
    data_ready: bool = False
    checked_at: datetime | None = None


class TelemetryFrame(BaseModel):
    timestamp: datetime = Field(default_factory=utc_now)
    gps: GpsFix = Field(default_factory=GpsFix)
    attitude: Attitude = Field(default_factory=Attitude)
    pid: dict[str, PidAxis] = Field(
        default_factory=lambda: {"roll": PidAxis(), "pitch": PidAxis(), "yaw": PidAxis()}
    )
    armed: bool = False
    flight_mode: str = "DISCONNECTED"
    esp_connected: bool = False
    gps_connected: bool = False
    geofence: GeofenceState = Field(default_factory=GeofenceState)


class CommandFrame(BaseModel):
    version: int = 1
    type: Literal["command"] = "command"
    id: UUID
    command: Literal["LAND"]
    reason: Literal["GEOFENCE_BREACH", "GPS_LOST", "ADMIN"]
    timestamp: datetime = Field(default_factory=utc_now)


class AckFrame(BaseModel):
    version: int = 1
    type: Literal["ack"] = "ack"
    command_id: UUID
    accepted: bool
    message: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=256)
    totp: str | None = Field(default=None, pattern=r"^\d{6}$")


class LoginResponse(BaseModel):
    username: str
    role: Literal["admin", "user"]
    csrf_token: str


class CameraStatus(BaseModel):
    available: bool = False
    mode: Literal["unavailable", "webrtc"] = "unavailable"
    message: str = "Chưa kết nối camera"
    webrtc_url: str | None = None

