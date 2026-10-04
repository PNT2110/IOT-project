from __future__ import annotations

import json
import time
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import Settings
from ..db import get_db
from ..geo import GeometryError, validate_polygon_geojson
from ..models import (
    Credential,
    EmailChallenge,
    IdempotencyRecord,
    ProfileUpdateChallenge,
    RecoveryCode,
    RoleElevationRequest,
    SessionRecord,
    SimulatedFlightRequest,
    TermsAcceptance,
    User,
    Zone,
    ZoneSource,
    AuditEvent,
    Device,
    WorkflowHistory,
)
from ..schemas import (
    CodeRequest,
    EnrollmentCodeRequest,
    AccountRoleRequest,
    AccountStatusRequest,
    ChallengeRequest,
    LoginRequest,
    ProfileUpdateRequest,
    RecoveryRequest,
    RegisterRequest,
    RoleElevationCreateRequest,
    RoleElevationDecisionRequest,
    SimulatedFlightActionRequest,
    SimulatedFlightCreateRequest,
    SimulatedFlightDecisionRequest,
    ZoneCreateRequest,
    ZoneSourceCreateRequest,
    ZoneUpdateRequest,
    ok,
)
from ..security import (
    decrypt_secret,
    digest_token,
    encrypt_secret,
    hash_password,
    new_recovery_code,
    new_token,
    new_totp_secret,
    normalize_email,
    as_utc,
    totp_at,
    utcnow,
    verify_password,
)
from ..services import create_email_code, payload_digest, record_audit, record_history


def _now_iso() -> str:
    return utcnow().isoformat()


def _db(request: Request):
    yield from get_db(request.app.state.session_factory)


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _require_current_terms(request: Request, supplied: str) -> None:
    if supplied != request.app.state.settings.terms_version:
        raise HTTPException(status_code=400, detail={"code": "TERMS_VERSION_REQUIRED", "message_for_user": "Please accept the current terms before continuing"})


def _mail(request: Request):
    return request.app.state.fake_mail


def _token_from_request(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return request.cookies.get("session")


def _session(request: Request, db: Session, required_stage: str | None = "AUTHENTICATED") -> tuple[SessionRecord, User, str]:
    token = _token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail={"code": "AUTH_REQUIRED", "message_for_user": "Authentication required"})
    settings = request.app.state.settings
    record = db.scalar(select(SessionRecord).where(SessionRecord.token_digest == digest_token(settings.session_secret, token)))
    if not record or record.revoked_at or as_utc(record.expires_at) <= utcnow():
        raise HTTPException(status_code=401, detail={"code": "SESSION_INVALID", "message_for_user": "Session is invalid or expired"})
    if required_stage and record.stage != required_stage:
        raise HTTPException(status_code=403, detail={"code": "MFA_INCOMPLETE", "message_for_user": "Authentication steps are incomplete"})
    user = db.get(User, record.user_id)
    if not user:
        raise HTTPException(status_code=401, detail={"code": "SESSION_INVALID", "message_for_user": "Session is invalid"})
    _require_csrf(request, record, settings)
    if user.status in {"REJECTED", "SUSPENDED"} and record.stage == "AUTHENTICATED":
        record.revoked_at = utcnow()
        db.commit()
        raise HTTPException(status_code=401, detail={"code": "SESSION_REVOKED", "message_for_user": "Session is no longer active"})
    record.last_seen_at = utcnow()
    return record, user, token


def _staged_session(request: Request, db: Session, stage: str) -> tuple[SessionRecord, User, str]:
    return _session(request, db, required_stage=stage)


def _require_map_read(request: Request, db: Session) -> tuple[SessionRecord, User, str]:
    record, user, token = _session(request, db)
    if user.status != "ACTIVE" or user.role not in {"OPERATOR", "ADMIN", "OWNER"}:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message_for_user": "Internal map access is not available"})
    return record, user, token


def _require_map_write(request: Request, db: Session) -> tuple[SessionRecord, User, str]:
    record, user, token = _require_map_read(request, db)
    # The delegated level-2 operator is allowed to maintain airspace zones
    # and review flight requests, but remains blocked from account/role review.
    if user.role not in {"OPERATOR", "ADMIN", "OWNER"}:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message_for_user": "Map write access is restricted"})
    return record, user, token


def _challenge_or_error(
    db: Session,
    challenge_id: str,
    settings: Settings,
    code: str,
    *,
    session_id: str | None = None,
    expected_purpose: str | None = None,
) -> EmailChallenge:
    challenge = db.get(EmailChallenge, challenge_id)
    if not challenge or challenge.used_at or as_utc(challenge.expires_at) <= utcnow() or challenge.attempts >= challenge.max_attempts:
        raise HTTPException(status_code=400, detail={"code": "CHALLENGE_INVALID", "message_for_user": "Challenge is invalid or expired"})
    if session_id is not None and (challenge.session_id != session_id or challenge.purpose != "LOGIN_OTP"):
        raise HTTPException(status_code=400, detail={"code": "CHALLENGE_INVALID", "message_for_user": "Challenge is invalid or expired"})
    if expected_purpose is not None and challenge.purpose != expected_purpose:
        raise HTTPException(status_code=400, detail={"code": "CHALLENGE_WRONG_FLOW", "message_for_user": "Challenge is not valid for this flow"})
    if digest_token(settings.session_secret, code, salt=challenge.user_id) != challenge.code_digest:
        # Persist failed attempts so the challenge-level rate limit cannot be
        # bypassed by rolling back the request transaction.
        db.execute(update(EmailChallenge).where(EmailChallenge.id == challenge.id, EmailChallenge.used_at.is_(None), EmailChallenge.attempts < EmailChallenge.max_attempts).values(attempts=EmailChallenge.attempts + 1))
        db.commit()
        raise HTTPException(status_code=400, detail={"code": "CODE_INVALID", "message_for_user": "Code is invalid"})
    consumed_at = utcnow()
    consumed = db.execute(update(EmailChallenge).where(EmailChallenge.id == challenge.id, EmailChallenge.used_at.is_(None), EmailChallenge.attempts < EmailChallenge.max_attempts).values(used_at=consumed_at, attempts=EmailChallenge.attempts + 1))
    if consumed.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=400, detail={"code": "CHALLENGE_INVALID", "message_for_user": "Challenge is invalid or expired"})
    challenge.used_at = consumed_at
    challenge.attempts += 1
    return challenge


def _set_auth_cookies(response: Response, settings: Settings, token: str, csrf: str) -> None:
    response.set_cookie("session", token, httponly=True, secure=settings.cookie_secure, samesite="lax", max_age=settings.session_ttl_minutes * 60, path="/")
    response.set_cookie("csrf", csrf, httponly=False, secure=settings.cookie_secure, samesite="lax", max_age=settings.session_ttl_minutes * 60, path="/")


def _require_csrf(request: Request, record: SessionRecord, settings: Settings) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    if request.headers.get("authorization", "").lower().startswith("bearer "):
        return
    csrf = request.headers.get("x-csrf-token")
    if not csrf or digest_token(settings.session_secret, csrf) != record.csrf_digest:
        raise HTTPException(status_code=403, detail={"code": "CSRF_REQUIRED", "message_for_user": "CSRF token required"})


def _factor_rate_limit_check(request: Request, record: SessionRecord) -> None:
    failures = request.app.state.factor_failures
    # Bind the factor throttle to the account, not only to one staged
    # session. Otherwise an attacker who has reached the TOTP step could
    # create a fresh login session after every five failures and bypass the
    # lockout window.
    key = record.user_id
    entry = failures.get(key)
    if not entry:
        return
    now = time.monotonic()
    if now >= entry["expires_at"]:
        failures.pop(key, None)
        return
    if entry["count"] >= 5:
        raise HTTPException(status_code=429, detail={"code": "FACTOR_RATE_LIMITED", "message_for_user": "Too many invalid factor attempts"})


def _factor_failure(request: Request, record: SessionRecord) -> None:
    failures = request.app.state.factor_failures
    settings = request.app.state.settings
    key = record.user_id
    now = time.monotonic()
    expired = [candidate for candidate, value in failures.items() if now >= value["expires_at"]]
    for candidate in expired:
        failures.pop(candidate, None)
    if key not in failures and len(failures) >= settings.auth_rate_limit_max_entries:
        oldest = min(failures, key=lambda candidate: failures[candidate]["expires_at"])
        failures.pop(oldest, None)
    current = failures.get(key)
    failures[key] = {"count": (current["count"] if current else 0) + 1, "expires_at": now + settings.auth_rate_limit_window_seconds}


def _auth_rate_key(request: Request, email: str) -> str:
    client = request.client.host if request.client else "unknown"
    return f"{client}:{email}"


def _auth_rate_limit_check(request: Request, email: str) -> str:
    settings = request.app.state.settings
    key = _auth_rate_key(request, email)
    now = time.monotonic()
    failures = request.app.state.auth_failures
    expired_keys = [candidate for candidate, value in failures.items() if now - value["started"] >= settings.auth_rate_limit_window_seconds]
    for candidate in expired_keys:
        failures.pop(candidate, None)
    if key not in failures and len(failures) >= settings.auth_rate_limit_max_entries:
        oldest_key = min(failures, key=lambda candidate: failures[candidate]["started"])
        failures.pop(oldest_key, None)
    entry = failures.get(key)
    if not entry or now - entry["started"] >= settings.auth_rate_limit_window_seconds:
        failures[key] = {"started": now, "count": 0}
        return key
    if entry["count"] >= settings.auth_rate_limit_max_attempts:
        raise HTTPException(status_code=429, detail={"code": "AUTH_RATE_LIMITED", "message_for_user": "Too many authentication attempts; try again later"})
    return key


def _auth_rate_failure(request: Request, key: str) -> None:
    entry = request.app.state.auth_failures.setdefault(key, {"started": time.monotonic(), "count": 0})
    entry["count"] += 1


def _auth_rate_success(request: Request, key: str) -> None:
    request.app.state.auth_failures.pop(key, None)


def _registration_rate_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _registration_rate_limit_check(request: Request) -> str:
    settings = request.app.state.settings
    key = _registration_rate_key(request)
    now = time.monotonic()
    failures = request.app.state.registration_failures
    expired_keys = [candidate for candidate, value in failures.items() if now - value["started"] >= settings.auth_rate_limit_window_seconds]
    for candidate in expired_keys:
        failures.pop(candidate, None)
    if key not in failures and len(failures) >= settings.auth_rate_limit_max_entries:
        oldest_key = min(failures, key=lambda candidate: failures[candidate]["started"])
        failures.pop(oldest_key, None)
    entry = failures.get(key)
    if not entry or now - entry["started"] >= settings.auth_rate_limit_window_seconds:
        failures[key] = {"started": now, "count": 0}
        return key
    if entry["count"] >= settings.registration_rate_limit_max_attempts:
        raise HTTPException(status_code=429, detail={"code": "REGISTRATION_RATE_LIMITED", "message_for_user": "Too many registration attempts; try again later"})
    return key


def _registration_rate_failure(request: Request, key: str) -> None:
    entry = request.app.state.registration_failures.setdefault(key, {"started": time.monotonic(), "count": 0})
    entry["count"] += 1


def _auth_challenge_rate_key(request: Request, email: str) -> str:
    client = request.client.host if request.client else "unknown"
    return f"{client}:{email}"


def _auth_challenge_rate_limit_check(request: Request, email: str) -> str:
    settings = request.app.state.settings
    key = _auth_challenge_rate_key(request, email)
    now = time.monotonic()
    attempts = request.app.state.auth_challenge_failures
    expired = [candidate for candidate, value in attempts.items() if now - value["started"] >= settings.auth_rate_limit_window_seconds]
    for candidate in expired:
        attempts.pop(candidate, None)
    if key not in attempts and len(attempts) >= settings.auth_rate_limit_max_entries:
        oldest = min(attempts, key=lambda candidate: attempts[candidate]["started"])
        attempts.pop(oldest, None)
    entry = attempts.get(key)
    if not entry or now - entry["started"] >= settings.auth_rate_limit_window_seconds:
        attempts[key] = {"started": now, "count": 0}
        return key
    if entry["count"] >= settings.auth_challenge_rate_limit_max_attempts:
        raise HTTPException(status_code=429, detail={"code": "OTP_RATE_LIMITED", "message_for_user": "Too many email verification requests; try again later"})
    return key


def _auth_challenge_rate_record(request: Request, key: str) -> None:
    entry = request.app.state.auth_challenge_failures.setdefault(key, {"started": time.monotonic(), "count": 0})
    entry["count"] += 1


def _require_owner(request: Request, db: Session) -> tuple[SessionRecord, User, str]:
    record, user, token = _session(request, db)
    if user.status != "ACTIVE" or user.role != "OWNER" or not user.credential or not user.credential.totp_active:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message_for_user": "Owner review access is required"})
    return record, user, token


def _require_account_status_reviewer(request: Request, db: Session) -> tuple[SessionRecord, User, str]:
    # Level 1 (ADMIN) and the main account (OWNER) review accounts and roles;
    # level 2 (OPERATOR) only maintains zones and reviews flight requests.
    record, user, token = _session(request, db)
    if user.status != "ACTIVE" or user.role not in {"OWNER", "ADMIN"} or not user.credential or not user.credential.totp_active:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message_for_user": "Account review access is required"})
    return record, user, token


_require_role_reviewer = _require_account_status_reviewer


def _effective_review_capabilities(db: Session, user: User) -> dict:
    allowed = user.status == "ACTIVE" and user.role in {"OWNER", "ADMIN"} and bool(user.credential and user.credential.totp_active)
    return {"policy": "TWO_LEVEL", "role": user.role, "status": user.status, "can_approve_accounts": allowed, "can_change_roles": allowed}


def _require_workflow_reviewer(request: Request, db: Session) -> tuple[SessionRecord, User, str]:
    record, user, token = _session(request, db)
    if user.status != "ACTIVE" or user.role not in {"OPERATOR", "ADMIN", "OWNER"}:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message_for_user": "Workflow review access is not available"})
    return record, user, token


def _require_active_user(request: Request, db: Session) -> tuple[SessionRecord, User, str]:
    record, user, token = _session(request, db)
    if user.status != "ACTIVE":
        raise HTTPException(status_code=403, detail={"code": "ACCOUNT_NOT_ACTIVE", "message_for_user": "Account approval is required"})
    return record, user, token


def _parse_if_match(if_match: str | None, *, required: bool = True) -> int | None:
    if if_match is None:
        if required:
            raise HTTPException(status_code=428, detail={"code": "IF_MATCH_REQUIRED", "message_for_user": "If-Match is required"})
        return None
    try:
        return int(if_match.strip('"'))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "IF_MATCH_INVALID", "message_for_user": "If-Match must be an integer version"}) from exc


def _require_idempotency_key(value: str | None) -> str:
    if not value or len(value) > 128 or not value.strip():
        raise HTTPException(status_code=400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED", "message_for_user": "Idempotency-Key is required"})
    return value.strip()


def _idempotency_replay(db: Session, *, actor_user_id: str, key: str, digest: str):
    existing = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.actor_user_id == actor_user_id, IdempotencyRecord.idempotency_key == key))
    if not existing:
        return None
    if existing.payload_digest != digest:
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_KEY_REUSE", "message_for_user": "Idempotency key was already used with different data"})
    return existing


def _remember_idempotency(db: Session, *, actor_user_id: str, key: str, action: str, object_type: str, object_id: str | None, digest: str, data: dict, status_code: int = 200) -> None:
    db.add(IdempotencyRecord(actor_user_id=actor_user_id, idempotency_key=key, action=action, object_type=object_type, object_id=object_id, payload_digest=digest, response_json=json.dumps(data, sort_keys=True), status_code=status_code, created_at=utcnow()))


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat() if value.tzinfo else value.replace(tzinfo=timezone.utc).isoformat()


def _account_view(user: User) -> dict:
    return {"id": user.id, "username": user.username, "display_name": user.display_name, "email": user.email_normalized, "status": user.status, "role": user.role, "version": user.version, "email_verified": bool(user.email_verified_at), "created_at": _iso(user.created_at), "updated_at": _iso(user.updated_at)}


def _elevation_view(item: RoleElevationRequest, requester: User | None = None) -> dict:
    result = {"id": item.id, "requester_user_id": item.requester_user_id, "requested_role": item.requested_role, "status": item.status, "reason": item.reason, "reviewer_user_id": item.reviewer_user_id, "reviewer_reason": item.reviewer_reason, "reviewed_at": _iso(item.reviewed_at) if item.reviewed_at else None, "version": item.version, "created_at": _iso(item.created_at), "updated_at": _iso(item.updated_at)}
    if requester is not None:
        result["requester"] = _account_view(requester)
    return result


def _flight_details(body: SimulatedFlightCreateRequest) -> dict:
    return {
        "applicant_full_name": body.applicant_full_name.strip(),
        "license_code": body.license_code.strip(),
        "license_class": body.license_class,
        "vehicle": body.vehicle.strip(),
        "gps": {"latitude": body.gps_latitude, "longitude": body.gps_longitude, "accuracy_m": body.gps_accuracy_m},
    }


def _profile_view(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email_normalized,
        "full_name": user.full_name or "",
        "license_code": user.license_code or "",
        "license_class": user.license_class,
        "license_expiry": user.license_expiry.isoformat() if user.license_expiry else "",
        "status": user.status,
        "role": user.role,
    }


def _apply_profile_update(
    db: Session,
    challenge: ProfileUpdateChallenge,
    user: User,
    session: SessionRecord,
    request: Request,
    settings: Settings,
) -> dict:
    now = utcnow()
    if user.email_normalized != challenge.original_email or as_utc(user.credential.updated_at) != as_utc(challenge.credential_updated_at):
        challenge.used_at = now
        db.commit()
        raise HTTPException(status_code=409, detail={"code": "PROFILE_CHANGED", "message_for_user": "Thông tin xác thực đã đổi trong lúc chờ OTP. Hãy bắt đầu lại."})
    changes = json.loads(decrypt_secret(settings.session_secret, challenge.changes_ciphertext))
    if challenge.requested_email != challenge.original_email:
        if not challenge.new_email_challenge_id:
            raise HTTPException(status_code=409, detail={"code": "NEW_EMAIL_NOT_VERIFIED", "message_for_user": "Email mới chưa được xác minh."})
        if db.scalar(select(User.id).where(User.email_normalized == challenge.requested_email, User.id != user.id)):
            raise HTTPException(status_code=409, detail={"code": "EMAIL_UNAVAILABLE", "message_for_user": "Email này đã được sử dụng."})
    changed_fields = [key for key in ("display_name", "email", "full_name", "license_code", "license_class", "license_expiry") if key in changes]
    email_changed = challenge.requested_email != challenge.original_email
    password_changed = bool(changes.get("new_password"))
    user.display_name = changes["display_name"]
    user.email_normalized = challenge.requested_email
    user.email_verified_at = now
    user.full_name = changes.get("full_name") or None
    user.license_code = changes.get("license_code") or None
    user.license_class = changes.get("license_class") or None
    user.license_expiry = date.fromisoformat(changes["license_expiry"]) if changes.get("license_expiry") else None
    user.version += 1
    user.updated_at = now
    if password_changed:
        user.credential.password_hash = hash_password(changes["new_password"])
        user.credential.updated_at = now
    challenge.used_at = now
    db.execute(update(SessionRecord).where(SessionRecord.user_id == user.id, SessionRecord.id != session.id, SessionRecord.revoked_at.is_(None)).values(revoked_at=now))
    db.execute(update(ProfileUpdateChallenge).where(ProfileUpdateChallenge.user_id == user.id, ProfileUpdateChallenge.id != challenge.id, ProfileUpdateChallenge.used_at.is_(None)).values(used_at=now))
    record_audit(
        db,
        actor_user_id=user.id,
        action="PROFILE_UPDATED",
        object_type="USER",
        object_id=user.id,
        outcome="SUCCESS",
        request_id=request.state.request_id,
        metadata={"changed_fields": changed_fields, "email_changed": email_changed, "password_changed": password_changed},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "EMAIL_UNAVAILABLE", "message_for_user": "Email này đã được sử dụng."}) from exc
    return _profile_view(user)


def _store_flight_details(item: SimulatedFlightRequest, body: SimulatedFlightCreateRequest, settings: Settings) -> None:
    details = _flight_details(body)
    item.request_details_ciphertext = encrypt_secret(settings.session_secret, json.dumps(details, separators=(",", ":")))
    item.request_payload_digest = payload_digest(details)


def _flight_view(item: SimulatedFlightRequest, settings: Settings | None = None, *, include_details: bool = False, device_name: str | None = None) -> dict:
    result = {"id": item.id, "submitter_user_id": item.submitter_user_id, "device_id": item.device_id, "device_name": device_name, "summary": item.summary, "scheduled_start_at": _iso(item.scheduled_start_at) if item.scheduled_start_at else None, "scheduled_end_at": _iso(item.scheduled_end_at) if item.scheduled_end_at else None, "geometry": json.loads(item.simulated_geometry_json) if item.simulated_geometry_json else None, "status": item.status, "version": item.version, "simulated": True, "authority_contract": "PC_INTERNAL_V1", "legal_status": "NOT_A_GOVERNMENT_PERMIT", "label": "PC INTERNAL DECISION — NOT A GOVERNMENT PERMIT", "source": item.source, "payload_digest": item.request_payload_digest, "updated_at": _iso(item.updated_at), "created_at": _iso(item.created_at)}
    if include_details and settings and item.request_details_ciphertext:
        try:
            result["request_details"] = json.loads(decrypt_secret(settings.session_secret, item.request_details_ciphertext))
        except Exception:
            result["request_details"] = {"error": "DETAILS_UNAVAILABLE"}
    return result


def _history_view(item: WorkflowHistory) -> dict:
    return {"id": item.id, "actor_user_id": item.actor_user_id, "object_type": item.object_type, "object_id": item.object_id, "action": item.action, "from_state": item.from_state, "to_state": item.to_state, "from_version": item.from_version, "to_version": item.to_version, "reason": item.reason, "request_id": item.request_id, "metadata": json.loads(item.metadata_redacted or "{}"), "created_at": _iso(item.created_at)}


# Public names for the router modules.
current_session = _session
require_active = _require_active_user
require_map_write = _require_map_write
require_reviewer = _require_workflow_reviewer
require_account_admin = _require_account_status_reviewer

__all__ = [name for name in list(globals()) if not name.startswith("__")]
