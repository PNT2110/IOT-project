from __future__ import annotations

import json
import hashlib
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings
from .geo import INTERNAL_FIXTURE, PUBLIC_FIXTURE, validate_polygon_geojson
from .mail import FakeEmailSender
from .models import AuditEvent, CapabilityGrant, WorkflowHistory, Zone, ZoneSource
from .security import digest_token, new_code, utcnow


DEMO_SOURCE_ID = "00000000-0000-4000-8000-000000000001"
ACCOUNT_APPROVE = "ACCOUNT_APPROVE"
ADMIN_ROLE_APPROVE = "ADMIN_ROLE_APPROVE"
PC_GUEST_SCOPE = "PC_GUEST"


_SENSITIVE_METADATA_PARTS = ("password", "secret", "token", "otp", "recovery", "authorization", "cookie")


def redact_metadata(value: Any) -> Any:
    """Return audit-safe metadata without credentials or one-time factors."""
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key).casefold()
            result[str(key)] = "[REDACTED]" if any(part in key_text for part in _SENSITIVE_METADATA_PARTS) else redact_metadata(item)
        return result
    if isinstance(value, list):
        return [redact_metadata(item) for item in value]
    if isinstance(value, tuple):
        return [redact_metadata(item) for item in value]
    return value


def record_audit(
    db: Session,
    *,
    actor_user_id: str | None,
    action: str,
    object_type: str,
    object_id: str | None,
    outcome: str,
    request_id: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            outcome=outcome,
            request_id=request_id,
            metadata_redacted=json.dumps(redact_metadata(metadata or {}), sort_keys=True),
            created_at=utcnow(),
        )
    )


def record_history(
    db: Session,
    *,
    actor_user_id: str | None,
    object_type: str,
    object_id: str,
    action: str,
    from_state: str | None,
    to_state: str | None,
    from_version: int | None,
    to_version: int | None,
    reason: str | None,
    request_id: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    db.add(
        WorkflowHistory(
            actor_user_id=actor_user_id,
            object_type=object_type,
            object_id=object_id,
            action=action,
            from_state=from_state,
            to_state=to_state,
            from_version=from_version,
            to_version=to_version,
            reason=reason[:500] if reason else None,
            request_id=request_id,
            metadata_redacted=json.dumps(redact_metadata(metadata or {}), sort_keys=True),
            created_at=utcnow(),
        )
    )


def payload_digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def grant_actions(grant: CapabilityGrant) -> set[str]:
    values = json.loads(grant.actions_json or "[]")
    return {value for value in values if isinstance(value, str)}


def has_active_capability(db: Session, *, user_id: str, action: str, resource_scope: str = PC_GUEST_SCOPE) -> bool:
    grants = db.scalars(select(CapabilityGrant).where(CapabilityGrant.grantee_user_id == user_id, CapabilityGrant.resource_scope == resource_scope, CapabilityGrant.revoked_at.is_(None))).all()
    return any(action in grant_actions(grant) for grant in grants)


def seed_demo_zones(db: Session) -> None:
    source = db.get(ZoneSource, DEMO_SOURCE_ID)
    if source:
        return
    now = utcnow()
    source = ZoneSource(
        id=DEMO_SOURCE_ID,
        publisher="TEST_FIXTURE",
        source_type="SIMULATED",
        license_name="TEST_ONLY",
        checksum="synthetic-scope01-v1",
        retrieved_at=now,
    )
    db.add(source)
    db.flush()
    db.add_all(
        [
            Zone(
                name="Demo public polygon",
                source_id=DEMO_SOURCE_ID,
                geometry_json=json.dumps(validate_polygon_geojson(PUBLIC_FIXTURE), separators=(",", ":")),
                visibility="PUBLIC",
                classification="DEMO",
                version=1,
                retrieved_at=now,
                created_at=now,
                updated_at=now,
            ),
            Zone(
                name="Research-only polygon",
                source_id=DEMO_SOURCE_ID,
                geometry_json=json.dumps(validate_polygon_geojson(INTERNAL_FIXTURE), separators=(",", ":")),
                visibility="INTERNAL",
                classification="INTERNAL_RESEARCH",
                version=1,
                retrieved_at=now,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    db.commit()


def create_email_code(db: Session, settings: Settings, mail: FakeEmailSender, *, user_id: str, email: str, purpose: str, session_id: str | None = None):
    from .models import EmailChallenge

    now = utcnow()
    code = new_code()
    challenge = EmailChallenge(
        user_id=user_id,
        session_id=session_id,
        purpose=purpose,
        code_digest=digest_token(settings.session_secret, code, salt=user_id),
        expires_at=now + timedelta(minutes=settings.challenge_ttl_minutes),
        attempts=0,
        max_attempts=5,
        created_at=now,
    )
    db.add(challenge)
    db.flush()
    mail.send_code(email, purpose, code, now)
    return challenge
