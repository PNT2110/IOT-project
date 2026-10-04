from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .security import utcnow


def new_id() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[Optional[str]] = mapped_column(String(32), unique=True, index=True, nullable=True)
    display_name: Mapped[str] = mapped_column(String(160))
    # NULL only for the seeded default owner, which signs in without email OTP.
    email_normalized: Mapped[Optional[str]] = mapped_column(String(320), unique=True, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    role: Mapped[str] = mapped_column(String(20), default="GUEST")
    version: Mapped[int] = mapped_column(Integer, default=1)
    full_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    license_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    license_class: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    license_expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    credential: Mapped["Credential"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class Credential(Base):
    __tablename__ = "credentials"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    totp_secret_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    totp_active: Mapped[bool] = mapped_column(Boolean, default=False)
    totp_last_step: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    user: Mapped[User] = relationship(back_populates="credential")


class EmailChallenge(Base):
    __tablename__ = "email_challenges"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # Login OTPs are bound to the exact staged session that requested them.
    # Registration email challenges remain session-less until enrollment.
    session_id: Mapped[Optional[str]] = mapped_column(ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    purpose: Mapped[str] = mapped_column(String(32))
    code_digest: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProfileUpdateChallenge(Base):
    __tablename__ = "profile_update_challenges"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    current_email_challenge_id: Mapped[str] = mapped_column(ForeignKey("email_challenges.id", ondelete="CASCADE"), unique=True)
    new_email_challenge_id: Mapped[Optional[str]] = mapped_column(ForeignKey("email_challenges.id", ondelete="SET NULL"), nullable=True, unique=True)
    original_email: Mapped[str] = mapped_column(String(320))
    requested_email: Mapped[str] = mapped_column(String(320))
    changes_ciphertext: Mapped[str] = mapped_column(Text)
    credential_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SessionRecord(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    token_digest: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(32))
    terms_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    csrf_digest: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RecoveryCode(Base):
    __tablename__ = "recovery_codes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code_digest: Mapped[str] = mapped_column(String(128))
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TermsAcceptance(Base):
    __tablename__ = "terms_acceptances"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    terms_version: Mapped[str] = mapped_column(String(64))
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("user_id", "terms_version", name="uq_terms_user_version"),)


class ZoneSource(Base):
    __tablename__ = "zone_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    publisher: Mapped[str] = mapped_column(String(160))
    source_type: Mapped[str] = mapped_column(String(32))
    license_name: Mapped[str] = mapped_column(String(160))
    checksum: Mapped[str] = mapped_column(String(128))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Zone(Base):
    __tablename__ = "zones"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("zone_sources.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    geometry_json: Mapped[str] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(String(16), index=True)
    classification: Mapped[str] = mapped_column(String(32))
    version: Mapped[int] = mapped_column(Integer, default=1)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80))
    object_type: Mapped[str] = mapped_column(String(80))
    object_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    outcome: Mapped[str] = mapped_column(String(32))
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    metadata_redacted: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RoleElevationRequest(Base):
    __tablename__ = "role_elevation_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    requester_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    requested_role: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    reason: Mapped[str] = mapped_column(String(500))
    reviewer_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reviewer_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("requested_role IN ('OPERATOR', 'ADMIN')", name="ck_role_elevation_target"),
        CheckConstraint("status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')", name="ck_role_elevation_status"),
        Index("uq_role_elevation_pending_target", "requester_user_id", "requested_role", unique=True, sqlite_where=text("status = 'PENDING'"), postgresql_where=text("status = 'PENDING'")),
    )


class Device(Base):
    """A Pi that may submit sealed flight requests."""
    __tablename__ = "devices"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    key_encrypted: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class SimulatedFlightRequest(Base):
    __tablename__ = "simulated_flight_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    # NULL when the request came from a Pi device instead of a PC web user.
    submitter_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    device_id: Mapped[Optional[str]] = mapped_column(ForeignKey("devices.id", ondelete="SET NULL"), index=True, nullable=True)
    client_ref: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    summary: Mapped[str] = mapped_column(String(240))
    scheduled_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    scheduled_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    simulated_geometry_json: Mapped[str] = mapped_column(Text, default="null")
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(40), default="USER_SIMULATED")
    request_details_ciphertext: Mapped[str] = mapped_column(Text, default="{}")
    request_payload_digest: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("status IN ('DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'NEEDS_INFORMATION', 'REJECTED', 'APPROVED_SIMULATED')", name="ck_simulated_request_status"),
        CheckConstraint("simulated = 1", name="ck_simulated_request_flag"),
        UniqueConstraint("device_id", "client_ref", name="uq_flight_device_client_ref"),
    )


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(80))
    object_type: Mapped[str] = mapped_column(String(80))
    object_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    payload_digest: Mapped[str] = mapped_column(String(128))
    response_json: Mapped[str] = mapped_column(Text)
    status_code: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("actor_user_id", "idempotency_key", name="uq_idempotency_actor_key"),)


class WorkflowHistory(Base):
    __tablename__ = "workflow_history"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    object_type: Mapped[str] = mapped_column(String(80), index=True)
    object_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(80))
    from_state: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    to_state: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    from_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    to_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    metadata_redacted: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CapabilityGrant(Base):
    __tablename__ = "capability_grants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    grantor_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    grantee_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    actions_json: Mapped[str] = mapped_column(String(300))
    resource_scope: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str] = mapped_column(String(500))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    revoked_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    __table_args__ = (
        CheckConstraint("resource_scope = 'PC_GUEST'", name="ck_capability_grant_scope"),
        Index("uq_active_capability_grant_target", "grantee_user_id", "resource_scope", unique=True, sqlite_where=text("revoked_at IS NULL"), postgresql_where=text("revoked_at IS NULL")),
    )
