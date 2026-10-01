from __future__ import annotations

from .deps import *  # noqa: F401,F403

router = APIRouter()


@router.post("/auth/register", status_code=201)
def register(body: RegisterRequest, request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings), mail=Depends(_mail)):
    _require_current_terms(request, body.terms_version)
    registration_rate_key = _registration_rate_limit_check(request)
    email = normalize_email(str(body.email))
    rate_key = _auth_rate_limit_check(request, email)
    if db.scalar(select(User).where(or_(User.email_normalized == email, User.username == body.username))):
        _registration_rate_failure(request, registration_rate_key)
        _auth_rate_failure(request, rate_key)
        raise HTTPException(status_code=409, detail={"code": "REGISTRATION_UNAVAILABLE", "message_for_user": "Unable to create an account with those details"})
    now = utcnow()
    user = User(username=body.username, display_name=body.display_name or body.username, email_normalized=email, status="PENDING", role="GUEST", created_at=now, updated_at=now)
    user.credential = Credential(password_hash=hash_password(body.password), created_at=now, updated_at=now)
    db.add(user)
    try:
        # The pre-check above is only an optimization.  The unique
        # constraint remains authoritative when two registrations race
        # for the same email.
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        _registration_rate_failure(request, registration_rate_key)
        _auth_rate_failure(request, rate_key)
        raise HTTPException(status_code=409, detail={"code": "REGISTRATION_UNAVAILABLE", "message_for_user": "Unable to create an account with those details"}) from exc
    if not db.scalar(select(TermsAcceptance).where(TermsAcceptance.user_id == user.id, TermsAcceptance.terms_version == body.terms_version)):
        db.add(TermsAcceptance(user_id=user.id, terms_version=body.terms_version, accepted_at=now))
    challenge = create_email_code(db, settings, mail, user_id=user.id, email=email, purpose="VERIFY_EMAIL")
    record_audit(db, actor_user_id=None, action="REGISTER", object_type="USER", object_id=user.id, outcome="SUCCESS", request_id=request.state.request_id)
    db.commit()
    _registration_rate_failure(request, registration_rate_key)
    _auth_rate_failure(request, rate_key)
    return ok({"challenge_id": challenge.id, "next_step": "VERIFY_EMAIL", "status": "PENDING"}, request.state.request_id, _now_iso())


@router.post("/auth/verify-email")
def verify_email(body: CodeRequest, request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings)):
    challenge = _challenge_or_error(db, body.challenge_id, settings, body.code, expected_purpose="VERIFY_EMAIL")
    user = db.get(User, challenge.user_id)
    user.email_verified_at = utcnow()
    token = new_token()
    csrf = new_token()
    db.add(SessionRecord(token_digest=digest_token(settings.session_secret, token), user_id=user.id, stage="MFA_ENROLLMENT", csrf_digest=digest_token(settings.session_secret, csrf), expires_at=utcnow() + timedelta(minutes=settings.session_ttl_minutes), last_seen_at=utcnow(), created_at=utcnow()))
    db.commit()
    return ok({"enrollment_token": token, "next_step": "TOTP_ENROLLMENT"}, request.state.request_id, _now_iso())


@router.post("/auth/resend-registration-otp")
def resend_registration_otp(body: ChallengeRequest, request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings), mail=Depends(_mail)):
    challenge = db.get(EmailChallenge, body.challenge_id)
    if not challenge or challenge.purpose != "VERIFY_EMAIL":
        raise HTTPException(status_code=400, detail={"code": "CHALLENGE_INVALID", "message_for_user": "Challenge is invalid or expired"})
    user = db.get(User, challenge.user_id)
    if not user or user.status != "PENDING" or user.email_verified_at:
        raise HTTPException(status_code=400, detail={"code": "CHALLENGE_INVALID", "message_for_user": "Challenge is invalid or expired"})
    registration_rate_key = _registration_rate_limit_check(request)
    challenge_rate_key = _auth_challenge_rate_limit_check(request, user.email_normalized)
    replacement = create_email_code(db, settings, mail, user_id=user.id, email=user.email_normalized, purpose="VERIFY_EMAIL")
    challenge.used_at = utcnow()
    db.commit()
    _registration_rate_failure(request, registration_rate_key)
    _auth_challenge_rate_record(request, challenge_rate_key)
    return ok({"challenge_id": replacement.id, "next_step": "VERIFY_EMAIL", "status": "PENDING"}, request.state.request_id, _now_iso())


@router.post("/auth/mfa/enroll")
def enroll_mfa(request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings)):
    record, user, _ = _staged_session(request, db, "MFA_ENROLLMENT")
    if not user.email_verified_at:
        raise HTTPException(status_code=403, detail={"code": "EMAIL_NOT_VERIFIED", "message_for_user": "Email verification is required"})
    # A secret that was shown but never confirmed is replaced, so a user who
    # left before saving it can finish enrollment after signing in again.
    if user.credential.totp_active:
        raise HTTPException(status_code=409, detail={"code": "TOTP_ALREADY_ENROLLED", "message_for_user": "TOTP is already active"})
    secret = new_totp_secret()
    user.credential.totp_secret_encrypted = encrypt_secret(settings.session_secret, secret)
    db.commit()
    uri = __import__("pyotp").TOTP(secret).provisioning_uri(name=user.username or user.email_normalized, issuer_name="IOT Research Prototype")
    return ok({"secret": secret, "otpauth_uri": uri, "warning": "Display once; never log or store in client persistence"}, request.state.request_id, _now_iso())


@router.post("/auth/mfa/confirm")
def confirm_mfa(body: EnrollmentCodeRequest, request: Request, response: Response, db: Session = Depends(_db), settings: Settings = Depends(_settings)):
    record, user, _ = _staged_session(request, db, "MFA_ENROLLMENT")
    _factor_rate_limit_check(request, record)
    secret = decrypt_secret(settings.session_secret, user.credential.totp_secret_encrypted or "")
    valid, step = totp_at(secret, body.code)
    if not valid:
        _factor_failure(request, record)
        raise HTTPException(status_code=400, detail={"code": "TOTP_INVALID", "message_for_user": "TOTP code is invalid or already used"})
    activated = db.execute(update(Credential).where(Credential.user_id == user.id, Credential.totp_active.is_(False), Credential.totp_last_step.is_(None)).values(totp_active=True, totp_last_step=step))
    if activated.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=400, detail={"code": "TOTP_INVALID", "message_for_user": "TOTP code is invalid or already used"})
    user.credential.totp_active = True
    user.credential.totp_last_step = step
    codes = []
    for _ in range(8):
        code = new_recovery_code()
        codes.append(code)
        db.add(RecoveryCode(user_id=user.id, code_digest=digest_token(settings.session_secret, code, salt=user.id), created_at=utcnow()))
    # Enrollment is a setup flow, not a login. Revoke its bearer session
    # atomically after MFA is activated so a lost follow-up logout request
    # cannot leave a newly registered account signed in.
    record.stage = "REVOKED"
    record.revoked_at = utcnow()
    db.commit()
    request.app.state.factor_failures.pop(record.user_id, None)
    response.delete_cookie("session", path="/", secure=settings.cookie_secure, httponly=True, samesite="lax")
    response.delete_cookie("csrf", path="/", secure=settings.cookie_secure, httponly=False, samesite="lax")
    return ok({"status": "PENDING", "role": user.role, "recovery_codes": codes, "warning": "Recovery codes are shown once"}, request.state.request_id, _now_iso())


@router.post("/auth/login")
def login(body: LoginRequest, request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings), mail=Depends(_mail)):
    _require_current_terms(request, body.terms_version)
    if not body.terms_accepted:
        raise HTTPException(status_code=400, detail={"code": "TERMS_ACCEPTANCE_REQUIRED", "message_for_user": "Please accept the terms before continuing"})
    identifier = normalize_email(body.identifier)
    rate_key = _auth_rate_limit_check(request, identifier)
    user = db.scalar(select(User).where(or_(User.email_normalized == identifier, User.username == identifier)))
    if not user or not user.credential or not verify_password(user.credential.password_hash, body.password):
        _auth_rate_failure(request, rate_key)
        raise HTTPException(status_code=401, detail={"code": "AUTH_FAILED", "message_for_user": "Authentication failed"})
    # The seeded default owner has no mailbox: it goes straight to TOTP.
    without_email = user.email_normalized is None
    ready = user.credential.totp_active if without_email else bool(user.email_verified_at)
    if user.status in {"REJECTED", "SUSPENDED"} or not ready:
        _auth_rate_failure(request, rate_key)
        raise HTTPException(status_code=401, detail={"code": "AUTH_FAILED", "message_for_user": "Authentication failed"})
    email = user.email_normalized
    now = utcnow()
    if without_email:
        token = new_token()
        csrf = new_token()
        db.add(SessionRecord(token_digest=digest_token(settings.session_secret, token), user_id=user.id, stage="TOTP", terms_version=body.terms_version, csrf_digest=digest_token(settings.session_secret, csrf), expires_at=now + timedelta(minutes=settings.session_ttl_minutes), last_seen_at=now, created_at=now))
        if not db.scalar(select(TermsAcceptance).where(TermsAcceptance.user_id == user.id, TermsAcceptance.terms_version == body.terms_version)):
            db.add(TermsAcceptance(user_id=user.id, terms_version=body.terms_version, accepted_at=now))
        db.commit()
        _auth_rate_success(request, rate_key)
        return ok({"login_token": token, "next_step": "TOTP"}, request.state.request_id, _now_iso())
    challenge_rate_key = _auth_challenge_rate_limit_check(request, email)
    if not db.scalar(select(TermsAcceptance).where(TermsAcceptance.user_id == user.id, TermsAcceptance.terms_version == body.terms_version)):
        db.add(TermsAcceptance(user_id=user.id, terms_version=body.terms_version, accepted_at=now))
    token = new_token()
    csrf = new_token()
    session = SessionRecord(token_digest=digest_token(settings.session_secret, token), user_id=user.id, stage="EMAIL_OTP", terms_version=body.terms_version, csrf_digest=digest_token(settings.session_secret, csrf), expires_at=now + timedelta(minutes=settings.session_ttl_minutes), last_seen_at=now, created_at=now)
    db.add(session)
    db.flush()
    _auth_challenge_rate_record(request, challenge_rate_key)
    challenge = create_email_code(db, settings, mail, user_id=user.id, email=email, purpose="LOGIN_OTP", session_id=session.id)
    db.commit()
    _auth_rate_success(request, rate_key)
    return ok({"login_token": token, "challenge_id": challenge.id, "next_step": "EMAIL_OTP"}, request.state.request_id, _now_iso())


@router.post("/auth/verify-login-otp")
def verify_login_otp(body: CodeRequest, request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings)):
    record, user, token = _staged_session(request, db, "EMAIL_OTP")
    if body.challenge_id not in {c.id for c in db.scalars(select(EmailChallenge).where(EmailChallenge.user_id == user.id, EmailChallenge.purpose == "LOGIN_OTP"))}:
        raise HTTPException(status_code=400, detail={"code": "CHALLENGE_WRONG_FLOW", "message_for_user": "Challenge is not valid for this session"})
    _challenge_or_error(db, body.challenge_id, settings, body.code, session_id=record.id)
    if not user.credential.totp_active:
        record.stage = "MFA_ENROLLMENT"
        db.commit()
        return ok({"enrollment_token": token, "next_step": "TOTP_ENROLLMENT"}, request.state.request_id, _now_iso())
    record.stage = "TOTP"
    db.commit()
    return ok({"login_token": token, "next_step": "TOTP"}, request.state.request_id, _now_iso())


@router.post("/auth/resend-login-otp")
def resend_login_otp(body: ChallengeRequest, request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings), mail=Depends(_mail)):
    record, user, _ = _staged_session(request, db, "EMAIL_OTP")
    challenge = db.get(EmailChallenge, body.challenge_id)
    if not challenge or challenge.user_id != user.id or challenge.session_id != record.id or challenge.purpose != "LOGIN_OTP":
        raise HTTPException(status_code=400, detail={"code": "CHALLENGE_INVALID", "message_for_user": "Challenge is invalid or expired"})
    challenge_rate_key = _auth_challenge_rate_limit_check(request, user.email_normalized)
    replacement = create_email_code(db, settings, mail, user_id=user.id, email=user.email_normalized, purpose="LOGIN_OTP", session_id=record.id)
    challenge.used_at = utcnow()
    db.commit()
    _auth_challenge_rate_record(request, challenge_rate_key)
    return ok({"challenge_id": replacement.id, "next_step": "EMAIL_OTP"}, request.state.request_id, _now_iso())


@router.post("/auth/verify-totp")
def verify_login_totp(body: EnrollmentCodeRequest, request: Request, response: Response, db: Session = Depends(_db), settings: Settings = Depends(_settings)):
    record, user, token = _staged_session(request, db, "TOTP")
    _factor_rate_limit_check(request, record)
    secret = decrypt_secret(settings.session_secret, user.credential.totp_secret_encrypted or "")
    valid, step = totp_at(secret, body.code, user.credential.totp_last_step)
    if not valid:
        _factor_failure(request, record)
        raise HTTPException(status_code=400, detail={"code": "TOTP_INVALID", "message_for_user": "TOTP code is invalid or already used"})
    updated = db.execute(update(Credential).where(Credential.user_id == user.id, (Credential.totp_last_step.is_(None) | (Credential.totp_last_step < step))).values(totp_last_step=step))
    if updated.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=400, detail={"code": "TOTP_INVALID", "message_for_user": "TOTP code is invalid or already used"})
    user.credential.totp_last_step = step
    record.stage = "AUTHENTICATED"
    csrf = new_token()
    record.csrf_digest = digest_token(settings.session_secret, csrf)
    db.commit()
    request.app.state.factor_failures.pop(record.user_id, None)
    _set_auth_cookies(response, settings, token, csrf)
    return ok({"access_token": token, "role": user.role, "status": user.status, "next_step": "AUTHENTICATED"}, request.state.request_id, _now_iso())


@router.post("/auth/recovery")
def recovery(body: RecoveryRequest, request: Request, response: Response, db: Session = Depends(_db), settings: Settings = Depends(_settings)):
    record, user, token = _staged_session(request, db, "TOTP")
    _factor_rate_limit_check(request, record)
    digest = digest_token(settings.session_secret, body.code, salt=user.id)
    code_row = db.scalar(select(RecoveryCode).where(RecoveryCode.user_id == user.id, RecoveryCode.code_digest == digest, RecoveryCode.used_at.is_(None)))
    if not code_row:
        _factor_failure(request, record)
        raise HTTPException(status_code=400, detail={"code": "RECOVERY_INVALID", "message_for_user": "Recovery code is invalid or already used"})
    consumed = db.execute(update(RecoveryCode).where(RecoveryCode.id == code_row.id, RecoveryCode.used_at.is_(None)).values(used_at=utcnow()))
    if consumed.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=400, detail={"code": "RECOVERY_INVALID", "message_for_user": "Recovery code is invalid or already used"})
    code_row.used_at = utcnow()
    record.stage = "AUTHENTICATED"
    csrf = new_token()
    record.csrf_digest = digest_token(settings.session_secret, csrf)
    db.commit()
    request.app.state.factor_failures.pop(record.user_id, None)
    _set_auth_cookies(response, settings, token, csrf)
    return ok({"access_token": token, "role": user.role, "status": user.status, "next_step": "AUTHENTICATED"}, request.state.request_id, _now_iso())


@router.post("/auth/profile/update-challenge")
def profile_update_challenge(body: ProfileUpdateRequest, request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings), mail=Depends(_mail)):
    record, user, _ = _session(request, db)
    if not user.email_verified_at or not user.credential:
        raise HTTPException(status_code=403, detail={"code": "EMAIL_NOT_VERIFIED", "message_for_user": "Hãy xác minh email trước khi thay đổi hồ sơ."})
    auth_rate_key = _auth_rate_limit_check(request, user.email_normalized)
    if not verify_password(user.credential.password_hash, body.current_password):
        _auth_rate_failure(request, auth_rate_key)
        record_audit(db, actor_user_id=user.id, action="PROFILE_PASSWORD_FAILURE", object_type="USER", object_id=user.id, outcome="DENIED", request_id=request.state.request_id)
        db.commit()
        raise HTTPException(status_code=401, detail={"code": "AUTHENTICATION_FAILED", "message_for_user": "Mật khẩu hiện tại không đúng."})
    _auth_rate_success(request, auth_rate_key)
    requested_email = normalize_email(str(body.email))
    if requested_email != user.email_normalized and db.scalar(select(User.id).where(User.email_normalized == requested_email, User.id != user.id)):
        raise HTTPException(status_code=409, detail={"code": "EMAIL_UNAVAILABLE", "message_for_user": "Email này đã được sử dụng."})
    challenge_rate_key = _auth_challenge_rate_limit_check(request, user.email_normalized)
    now = utcnow()
    changes = body.model_dump(mode="json", exclude={"current_password", "email"})
    current_code = create_email_code(db, settings, mail, user_id=user.id, email=user.email_normalized, purpose="PROFILE_UPDATE_CURRENT", session_id=record.id)
    pending = ProfileUpdateChallenge(
        id=str(uuid4()),
        user_id=user.id,
        session_id=record.id,
        current_email_challenge_id=current_code.id,
        original_email=user.email_normalized,
        requested_email=requested_email,
        changes_ciphertext=encrypt_secret(settings.session_secret, json.dumps(changes, separators=(",", ":"))),
        credential_updated_at=user.credential.updated_at,
        expires_at=now + timedelta(minutes=settings.challenge_ttl_minutes),
        created_at=now,
    )
    db.add(pending)
    db.commit()
    _auth_challenge_rate_record(request, challenge_rate_key)
    local, _, domain = user.email_normalized.partition("@")
    masked = f"{local[:2]}***@{domain}" if domain else "email đã xác minh"
    return ok({"challenge_id": pending.id, "next_step": "CURRENT_EMAIL_OTP", "email_masked": masked}, request.state.request_id, _now_iso())


@router.post("/auth/profile/verify-current-email")
def profile_verify_current_email(body: CodeRequest, request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings), mail=Depends(_mail)):
    record, user, _ = _session(request, db)
    pending = db.get(ProfileUpdateChallenge, body.challenge_id)
    if not pending or pending.user_id != user.id or pending.session_id != record.id or pending.used_at or as_utc(pending.expires_at) <= utcnow():
        raise HTTPException(status_code=400, detail={"code": "CHALLENGE_INVALID", "message_for_user": "Yêu cầu thay đổi hồ sơ đã hết hạn hoặc không hợp lệ."})
    email_challenge = db.get(EmailChallenge, pending.current_email_challenge_id)
    if not email_challenge or email_challenge.session_id != record.id or email_challenge.user_id != user.id:
        raise HTTPException(status_code=400, detail={"code": "CHALLENGE_INVALID", "message_for_user": "Mã OTP không thuộc phiên đăng nhập này."})
    _challenge_or_error(db, email_challenge.id, settings, body.code, expected_purpose="PROFILE_UPDATE_CURRENT")
    pending.current_email_verified_at = utcnow()
    if pending.requested_email != pending.original_email:
        challenge_rate_key = _auth_challenge_rate_limit_check(request, pending.requested_email)
        new_email_code = create_email_code(db, settings, mail, user_id=user.id, email=pending.requested_email, purpose="PROFILE_UPDATE_NEW", session_id=record.id)
        pending.new_email_challenge_id = new_email_code.id
        db.commit()
        _auth_challenge_rate_record(request, challenge_rate_key)
        local, _, domain = pending.requested_email.partition("@")
        masked = f"{local[:2]}***@{domain}" if domain else "email mới"
        return ok({"challenge_id": pending.id, "next_step": "NEW_EMAIL_OTP", "email_masked": masked}, request.state.request_id, _now_iso())
    profile = _apply_profile_update(db, pending, user, record, request, settings)
    return ok({"updated": True, "profile": profile}, request.state.request_id, _now_iso())


@router.post("/auth/profile/verify-new-email")
def profile_verify_new_email(body: CodeRequest, request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings)):
    record, user, _ = _session(request, db)
    pending = db.get(ProfileUpdateChallenge, body.challenge_id)
    if not pending or pending.user_id != user.id or pending.session_id != record.id or pending.used_at or as_utc(pending.expires_at) <= utcnow() or not pending.current_email_verified_at or not pending.new_email_challenge_id:
        raise HTTPException(status_code=400, detail={"code": "CHALLENGE_INVALID", "message_for_user": "Yêu cầu xác minh email mới đã hết hạn hoặc không hợp lệ."})
    email_challenge = db.get(EmailChallenge, pending.new_email_challenge_id)
    if not email_challenge or email_challenge.session_id != record.id or email_challenge.user_id != user.id:
        raise HTTPException(status_code=400, detail={"code": "CHALLENGE_INVALID", "message_for_user": "Mã OTP không thuộc phiên đăng nhập này."})
    _challenge_or_error(db, email_challenge.id, settings, body.code, expected_purpose="PROFILE_UPDATE_NEW")
    profile = _apply_profile_update(db, pending, user, record, request, settings)
    return ok({"updated": True, "profile": profile}, request.state.request_id, _now_iso())


@router.get("/auth/me")
def me(request: Request, db: Session = Depends(_db)):
    _, user, _ = _session(request, db)
    return ok(_profile_view(user), request.state.request_id, _now_iso())


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(_db), settings: Settings = Depends(_settings)):
    record, _, _ = _session(request, db)
    _require_csrf(request, record, settings)
    record.revoked_at = utcnow()
    db.commit()
    response.delete_cookie("session", path="/")
    response.delete_cookie("csrf", path="/")
    return ok({"logged_out": True}, request.state.request_id, _now_iso())
