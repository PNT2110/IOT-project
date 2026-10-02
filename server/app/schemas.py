from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class RegisterRequest(BaseModel):
    username: str = Field(pattern=r"^[a-z0-9_.-]{3,32}$")
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    password_confirm: str = Field(min_length=12, max_length=128)
    terms_version: str = Field(min_length=1, max_length=64)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value):
        return value.strip().casefold() if isinstance(value, str) else value

    @field_validator("display_name", "terms_version")
    @classmethod
    def strip_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("field must not be empty")
        return value

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.password_confirm:
            raise ValueError("passwords do not match")
        return self


class CodeRequest(BaseModel):
    challenge_id: str = Field(min_length=1, max_length=64)
    code: str = Field(pattern=r"^\d{6}$")


class ChallengeRequest(BaseModel):
    challenge_id: str = Field(min_length=1, max_length=64)


class EnrollmentCodeRequest(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class LoginRequest(BaseModel):
    # Username or email; "email" stays accepted for older clients.
    identifier: str = Field(min_length=3, max_length=320, validation_alias=AliasChoices("identifier", "email"))
    password: str = Field(min_length=1, max_length=128)
    terms_accepted: bool = True
    terms_version: str = Field(min_length=1, max_length=64)

    @field_validator("terms_version")
    @classmethod
    def strip_terms_version(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("terms_version must not be empty")
        return value


class ProfileUpdateRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=160)
    email: EmailStr
    full_name: str = Field(default="", max_length=200)
    new_password: str | None = Field(default=None, min_length=12, max_length=128)
    license_code: str = Field(default="", max_length=100)
    license_class: Literal["A", "B"] | None = None
    license_expiry: date | None = None

    @field_validator("display_name", "full_name", "license_code")
    @classmethod
    def strip_profile_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_license(self):
        if self.license_code and not self.license_class:
            raise ValueError("license_class is required when license_code is provided")
        if self.license_class and not self.license_code:
            raise ValueError("license_code is required when license_class is provided")
        return self


class RecoveryRequest(BaseModel):
    code: str = Field(min_length=8, max_length=32)


class ZoneCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    geometry: dict[str, Any]
    visibility: Literal["PUBLIC", "INTERNAL"]
    classification: Literal["NO_FLY", "RESTRICTED", "DEMO", "INTERNAL_RESEARCH"]
    source_id: str = Field(min_length=1, max_length=64)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be empty")
        return value


class ZoneUpdateRequest(ZoneCreateRequest):
    version: int = Field(ge=1)


class PublicZone(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    geometry: dict[str, Any]
    visibility: Literal["PUBLIC"]
    classification: Literal["NO_FLY", "RESTRICTED", "DEMO", "INTERNAL_RESEARCH"]
    version: int
    retrieved_at: str


class InternalZone(PublicZone):
    visibility: Literal["PUBLIC", "INTERNAL"]
    classification: Literal["NO_FLY", "RESTRICTED", "DEMO", "INTERNAL_RESEARCH"]
    source_id: str


class ZoneSourceCreateRequest(BaseModel):
    publisher: str = Field(min_length=1, max_length=160)
    source_type: Literal["OPERATOR_DRAWN", "OFFICIAL_GEOJSON", "OFFICIAL_API", "OTHER"]
    license_name: str = Field(min_length=1, max_length=160)
    checksum: str = Field(min_length=1, max_length=128)

    @field_validator("publisher", "license_name", "checksum")
    @classmethod
    def strip_source_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("source metadata must not be empty")
        return value


class AccountRoleRequest(BaseModel):
    role: Literal["ADMIN", "OPERATOR"]
    reason: str | None = Field(default=None, max_length=500)


class AccountStatusRequest(BaseModel):
    status: Literal["ACTIVE", "REJECTED", "SUSPENDED"]
    # Required when approving a pending account: level 1 = ADMIN, level 2 = OPERATOR.
    role: Literal["ADMIN", "OPERATOR"] | None = None
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("reason must not be empty")
        return value


class RoleElevationCreateRequest(BaseModel):
    requested_role: Literal["OPERATOR", "ADMIN"]
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("reason must not be empty")
        return value


class RoleElevationDecisionRequest(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("reason must not be empty")
        return value


class SimulatedFlightCreateRequest(BaseModel):
    summary: str = Field(min_length=3, max_length=240)
    scheduled_start_at: datetime
    scheduled_end_at: datetime
    geometry: dict[str, Any]
    applicant_full_name: str = Field(min_length=1, max_length=160)
    license_code: str = Field(min_length=1, max_length=80)
    license_class: Literal["A", "B"]
    vehicle: str = Field(min_length=1, max_length=80)
    gps_latitude: float | None = Field(default=None, ge=-90, le=90)
    gps_longitude: float | None = Field(default=None, ge=-180, le=180)
    gps_accuracy_m: float | None = Field(default=None, ge=0, le=100000)

    @field_validator("summary")
    @classmethod
    def strip_summary(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("summary must not be empty")
        return value

    @field_validator("applicant_full_name", "license_code", "vehicle")
    @classmethod
    def strip_required_details(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("applicant details must not be empty")
        return value

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.scheduled_start_at.tzinfo is None or self.scheduled_end_at.tzinfo is None:
            raise ValueError("scheduled times must include a timezone")
        if self.scheduled_end_at <= self.scheduled_start_at:
            raise ValueError("scheduled_end_at must be after scheduled_start_at")
        if (self.gps_latitude is None) != (self.gps_longitude is None):
            raise ValueError("gps_latitude and gps_longitude must be supplied together")
        if self.gps_accuracy_m is not None and self.gps_latitude is None:
            raise ValueError("gps_accuracy_m requires a latitude and longitude")
        return self


class SimulatedFlightActionRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("reason must not be empty")
        return value


class SimulatedFlightDecisionRequest(BaseModel):
    decision: Literal["NEEDS_INFORMATION", "REJECTED", "APPROVED_SIMULATED"]
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("reason must not be empty")
        return value


class DeviceEnvelope(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    ts: int
    nonce: str = Field(min_length=1, max_length=64)
    ciphertext: str = Field(min_length=1, max_length=20000)


class DeviceGps(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    fix_state: str = Field(min_length=1, max_length=32)
    satellites: int | None = Field(default=None, ge=0, le=99)


class DeviceFlightPayload(BaseModel):
    client_ref: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    applicant_full_name: str = Field(min_length=1, max_length=160)
    license_code: str = Field(min_length=1, max_length=80)
    flight_date: date
    flight_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    # End of the flight window, same day. Optional for older Pi builds (one hour).
    flight_end_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    vehicle: str = Field(min_length=1, max_length=80)
    pi_username: str = Field(min_length=1, max_length=64)
    gps: DeviceGps | None = None

    @field_validator("applicant_full_name", "license_code", "vehicle", "pi_username")
    @classmethod
    def strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be empty")
        return value

    @model_validator(mode="after")
    def end_after_start(self):
        if self.flight_end_time is not None and self.flight_end_time <= self.flight_time:
            raise ValueError("flight_end_time must be after flight_time")
        return self


def ok(data: Any, request_id: str, observed_at: str) -> dict[str, Any]:
    return {"schema_version": "v1", "request_id": request_id, "data": data, "error": None, "observed_at": observed_at}
