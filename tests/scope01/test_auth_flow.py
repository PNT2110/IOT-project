from __future__ import annotations

import argparse
import json
import pyotp
import time
import secrets
from datetime import timedelta

from sqlalchemy import select

from server.cli import bootstrap_owner
from server.app.models import EmailChallenge, SessionRecord, User
from server.app.security import digest_token, new_token, utcnow


def test_registration_email_totp_and_login_chain(app):
    application, client = app
    password = "P" + secrets.token_urlsafe(18)
    registration = client.post("/api/v1/auth/register", json={"username": "test_user", "display_name": "Test User", "email": "test@sample.com", "password": password, "password_confirm": password, "terms_version": "terms-v1"})
    assert registration.status_code == 201
    challenge_id = registration.json()["data"]["challenge_id"]
    mail = application.state.fake_mail.latest("test@sample.com", "VERIFY_EMAIL")
    assert mail is not None

    verified = client.post("/api/v1/auth/verify-email", json={"challenge_id": challenge_id, "code": mail.code})
    assert verified.status_code == 200
    enrollment_token = verified.json()["data"]["enrollment_token"]
    enrolled = client.post("/api/v1/auth/mfa/enroll", headers={"Authorization": f"Bearer {enrollment_token}"})
    assert enrolled.status_code == 200
    secret = enrolled.json()["data"]["secret"]
    confirmed = client.post("/api/v1/auth/mfa/confirm", headers={"Authorization": f"Bearer {enrollment_token}"}, json={"code": pyotp.TOTP(secret).now()})
    assert confirmed.status_code == 200
    assert len(confirmed.json()["data"]["recovery_codes"]) == 8
    assert "session" not in confirmed.cookies
    assert "csrf" not in confirmed.cookies
    assert 'session=""' in confirmed.headers["set-cookie"]
    assert 'csrf=""' in confirmed.headers["set-cookie"]
    enrollment_replay = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {enrollment_token}"})
    assert enrollment_replay.status_code == 401
    assert enrollment_replay.json()["error"]["code"] == "SESSION_INVALID"

    login = client.post("/api/v1/auth/login", json={"email": "test@sample.com", "password": password, "terms_version": "terms-v1"})
    assert login.status_code == 200
    login_token = login.json()["data"]["login_token"]
    login_challenge = login.json()["data"]["challenge_id"]
    login_mail = application.state.fake_mail.latest("test@sample.com", "LOGIN_OTP")
    assert login_mail is not None
    otp = client.post("/api/v1/auth/verify-login-otp", headers={"Authorization": f"Bearer {login_token}"}, json={"challenge_id": login_challenge, "code": login_mail.code})
    assert otp.status_code == 200
    next_step_code = pyotp.TOTP(secret).at((int(time.time()) // 30 + 1) * 30)
    totp = client.post("/api/v1/auth/verify-totp", headers={"Authorization": f"Bearer {login_token}"}, json={"code": next_step_code})
    assert totp.status_code == 200
    access_token = totp.json()["data"]["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 200
    assert me.json()["data"]["status"] == "PENDING"
    assert me.json()["data"]["role"] == "GUEST"


def test_registration_otp_can_be_resent_and_old_challenge_is_invalidated(app):
    application, client = app
    password = "P" + secrets.token_urlsafe(18)
    registration = client.post("/api/v1/auth/register", json={"username": "resend_user", "display_name": "Resend User", "email": "resend@sample.com", "password": password, "password_confirm": password, "terms_version": "terms-v1"})
    assert registration.status_code == 201
    first_id = registration.json()["data"]["challenge_id"]
    first_mail = application.state.fake_mail.latest("resend@sample.com", "VERIFY_EMAIL")
    assert first_mail is not None

    resent = client.post("/api/v1/auth/resend-registration-otp", json={"challenge_id": first_id})
    assert resent.status_code == 200
    second_id = resent.json()["data"]["challenge_id"]
    assert second_id != first_id
    old_code = client.post("/api/v1/auth/verify-email", json={"challenge_id": first_id, "code": first_mail.code})
    assert old_code.status_code == 400
    assert old_code.json()["error"]["code"] == "CHALLENGE_INVALID"

    second_mail = application.state.fake_mail.latest("resend@sample.com", "VERIFY_EMAIL")
    assert second_mail is not None and second_mail.code != first_mail.code
    verified = client.post("/api/v1/auth/verify-email", json={"challenge_id": second_id, "code": second_mail.code})
    assert verified.status_code == 200


def test_login_otp_can_be_resent_only_for_the_same_staged_session(app):
    application, client = app
    password = "P" + secrets.token_urlsafe(18)
    registration = client.post("/api/v1/auth/register", json={"username": "login_resend_user", "display_name": "Login Resend User", "email": "login-resend@sample.com", "password": password, "password_confirm": password, "terms_version": "terms-v1"})
    verification = application.state.fake_mail.latest("login-resend@sample.com", "VERIFY_EMAIL")
    enrollment = client.post("/api/v1/auth/verify-email", json={"challenge_id": registration.json()["data"]["challenge_id"], "code": verification.code}).json()["data"]["enrollment_token"]
    secret = client.post("/api/v1/auth/mfa/enroll", headers={"Authorization": f"Bearer {enrollment}"}).json()["data"]["secret"]
    assert client.post("/api/v1/auth/mfa/confirm", headers={"Authorization": f"Bearer {enrollment}"}, json={"code": pyotp.TOTP(secret).now()}).status_code == 200

    login = client.post("/api/v1/auth/login", json={"email": "login-resend@sample.com", "password": password, "terms_version": "terms-v1"}).json()["data"]
    resent = client.post("/api/v1/auth/resend-login-otp", headers={"Authorization": f"Bearer {login['login_token']}"}, json={"challenge_id": login["challenge_id"]})
    assert resent.status_code == 200
    replacement = resent.json()["data"]["challenge_id"]
    login_mail = application.state.fake_mail.latest("login-resend@sample.com", "LOGIN_OTP")
    assert login_mail is not None
    verified = client.post("/api/v1/auth/verify-login-otp", headers={"Authorization": f"Bearer {login['login_token']}"}, json={"challenge_id": replacement, "code": login_mail.code})
    assert verified.status_code == 200
    assert verified.json()["data"]["next_step"] == "TOTP"


def test_login_email_otp_is_bound_to_the_requesting_session(app):
    application, client = app
    password = "P" + secrets.token_urlsafe(18)
    registration = client.post("/api/v1/auth/register", json={"username": "session_otp_user", "display_name": "Session OTP User", "email": "session-otp@sample.com", "password": password, "password_confirm": password, "terms_version": "terms-v1"})
    verification = application.state.fake_mail.latest("session-otp@sample.com", "VERIFY_EMAIL")
    enrollment = client.post("/api/v1/auth/verify-email", json={"challenge_id": registration.json()["data"]["challenge_id"], "code": verification.code}).json()["data"]["enrollment_token"]
    secret = client.post("/api/v1/auth/mfa/enroll", headers={"Authorization": f"Bearer {enrollment}"}).json()["data"]["secret"]
    client.post("/api/v1/auth/mfa/confirm", headers={"Authorization": f"Bearer {enrollment}"}, json={"code": pyotp.TOTP(secret).now()})

    first = client.post("/api/v1/auth/login", json={"email": "session-otp@sample.com", "password": password, "terms_version": "terms-v1"}).json()["data"]
    first_mail = application.state.fake_mail.latest("session-otp@sample.com", "LOGIN_OTP")
    second = client.post("/api/v1/auth/login", json={"email": "session-otp@sample.com", "password": password, "terms_version": "terms-v1"}).json()["data"]
    second_mail = application.state.fake_mail.latest("session-otp@sample.com", "LOGIN_OTP")
    assert first_mail.code != second_mail.code or first_mail.sent_at != second_mail.sent_at

    cross_session = client.post("/api/v1/auth/verify-login-otp", headers={"Authorization": f"Bearer {second['login_token']}"}, json={"challenge_id": first["challenge_id"], "code": first_mail.code})
    assert cross_session.status_code == 400
    assert cross_session.json()["error"]["code"] == "CHALLENGE_INVALID"

    valid = client.post("/api/v1/auth/verify-login-otp", headers={"Authorization": f"Bearer {second['login_token']}"}, json={"challenge_id": second["challenge_id"], "code": second_mail.code})
    assert valid.status_code == 200


def test_wrong_flow_does_not_consume_a_valid_email_challenge(app):
    application, client = app
    password = "P" + secrets.token_urlsafe(18)
    registration = client.post("/api/v1/auth/register", json={"username": "flow_user", "display_name": "Flow User", "email": "flow-user@sample.com", "password": password, "password_confirm": password, "terms_version": "terms-v1"})
    verification = application.state.fake_mail.latest("flow-user@sample.com", "VERIFY_EMAIL")
    enrollment = client.post("/api/v1/auth/verify-email", json={"challenge_id": registration.json()["data"]["challenge_id"], "code": verification.code}).json()["data"]["enrollment_token"]
    secret = client.post("/api/v1/auth/mfa/enroll", headers={"Authorization": f"Bearer {enrollment}"}).json()["data"]["secret"]
    assert client.post("/api/v1/auth/mfa/confirm", headers={"Authorization": f"Bearer {enrollment}"}, json={"code": pyotp.TOTP(secret).now()}).status_code == 200

    login = client.post("/api/v1/auth/login", json={"email": "flow-user@sample.com", "password": password, "terms_version": "terms-v1"}).json()["data"]
    login_mail = application.state.fake_mail.latest("flow-user@sample.com", "LOGIN_OTP")
    wrong_flow = client.post("/api/v1/auth/verify-email", json={"challenge_id": login["challenge_id"], "code": login_mail.code})
    assert wrong_flow.status_code == 400
    assert wrong_flow.json()["error"]["code"] == "CHALLENGE_WRONG_FLOW"

    valid = client.post("/api/v1/auth/verify-login-otp", headers={"Authorization": f"Bearer {login['login_token']}"}, json={"challenge_id": login["challenge_id"], "code": login_mail.code})
    assert valid.status_code == 200


def test_login_does_not_disclose_incomplete_mfa_state(app):
    application, client = app
    password = "P" + secrets.token_urlsafe(18)
    registration = client.post("/api/v1/auth/register", json={"username": "incomplete_user", "display_name": "Incomplete User", "email": "incomplete-mfa@sample.com", "password": password, "password_confirm": password, "terms_version": "terms-v1"})
    assert registration.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": "incomplete-mfa@sample.com", "password": password, "terms_version": "terms-v1"})
    assert login.status_code == 401
    assert login.json()["error"]["code"] == "AUTH_FAILED"
    assert application.state.fake_mail.latest("incomplete-mfa@sample.com", "VERIFY_EMAIL") is not None


def test_duplicate_registration_does_not_reveal_email_existence(app):
    _, client = app
    payload = {"username": "first_user", "display_name": "First User", "email": "duplicate@sample.com", "password": "P" + secrets.token_urlsafe(18), "password_confirm": "P" + secrets.token_urlsafe(18), "terms_version": "terms-v1"}
    payload["password_confirm"] = payload["password"]
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201
    duplicate = client.post("/api/v1/auth/register", json={**payload, "display_name": "Second User"})
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "REGISTRATION_UNAVAILABLE"
    assert duplicate.json()["error"]["message_for_user"] == "Unable to create an account with those details"


def test_cookie_authenticated_state_change_requires_csrf(app, admin_token):
    _, client = app
    client.cookies.set("session", admin_token)
    response = client.post("/api/v1/role-elevations", json={"requested_role": "ADMIN", "reason": "missing csrf test"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_REQUIRED"


def test_email_challenge_replay_and_attempt_limit_are_enforced(app):
    application, client = app
    password = "P" + secrets.token_urlsafe(18)
    registration = client.post("/api/v1/auth/register", json={"username": "challenge_user", "display_name": "Challenge User", "email": "challenge@sample.com", "password": password, "password_confirm": password, "terms_version": "terms-v1"})
    challenge_id = registration.json()["data"]["challenge_id"]
    mail = application.state.fake_mail.latest("challenge@sample.com", "VERIFY_EMAIL")
    assert mail is not None
    verified = client.post("/api/v1/auth/verify-email", json={"challenge_id": challenge_id, "code": mail.code})
    assert verified.status_code == 200
    replay = client.post("/api/v1/auth/verify-email", json={"challenge_id": challenge_id, "code": mail.code})
    assert replay.status_code == 400
    assert replay.json()["error"]["code"] == "CHALLENGE_INVALID"

    second = client.post("/api/v1/auth/register", json={"username": "attempt_user", "display_name": "Attempt User", "email": "attempt@sample.com", "password": password, "password_confirm": password, "terms_version": "terms-v1"})
    second_id = second.json()["data"]["challenge_id"]
    second_mail = application.state.fake_mail.latest("attempt@sample.com", "VERIFY_EMAIL")
    wrong = "000000" if second_mail.code != "000000" else "999999"
    for _ in range(5):
        failed = client.post("/api/v1/auth/verify-email", json={"challenge_id": second_id, "code": wrong})
        assert failed.status_code == 400
        assert failed.json()["error"]["code"] == "CODE_INVALID"
    limited = client.post("/api/v1/auth/verify-email", json={"challenge_id": second_id, "code": second_mail.code})
    assert limited.status_code == 400
    assert limited.json()["error"]["code"] == "CHALLENGE_INVALID"
    with application.state.session_factory() as db:
        challenge = db.get(EmailChallenge, second_id)
        assert challenge.attempts == 5


def test_invalid_totp_does_not_complete_auth(app):
    application, client = app
    password = "P" + secrets.token_urlsafe(18)
    registration = client.post("/api/v1/auth/register", json={"username": "replay_user", "display_name": "Replay User", "email": "replay@sample.com", "password": password, "password_confirm": password, "terms_version": "terms-v1"})
    challenge_id = registration.json()["data"]["challenge_id"]
    mail = application.state.fake_mail.latest("replay@sample.com", "VERIFY_EMAIL")
    enrollment = client.post("/api/v1/auth/verify-email", json={"challenge_id": challenge_id, "code": mail.code}).json()["data"]["enrollment_token"]
    enrolled = client.post("/api/v1/auth/mfa/enroll", headers={"Authorization": f"Bearer {enrollment}"}).json()["data"]
    bad_code = "000000" if pyotp.TOTP(enrolled["secret"]).now() != "000000" else "999999"
    bad = client.post("/api/v1/auth/mfa/confirm", headers={"Authorization": f"Bearer {enrollment}"}, json={"code": bad_code})
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "TOTP_INVALID"
    assert enrolled["secret"]
    for _ in range(4):
        assert client.post("/api/v1/auth/mfa/confirm", headers={"Authorization": f"Bearer {enrollment}"}, json={"code": bad_code}).status_code == 400
    limited = client.post("/api/v1/auth/mfa/confirm", headers={"Authorization": f"Bearer {enrollment}"}, json={"code": bad_code})
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "FACTOR_RATE_LIMITED"


def test_totp_step_cannot_be_replayed_or_moved_backwards(app):
    from server.app.security import totp_at

    secret = pyotp.random_base32()
    current_step = int(time.time()) // 30
    current_code = pyotp.TOTP(secret).at(current_step * 30)
    valid, step = totp_at(secret, current_code)
    assert valid
    assert step == current_step
    assert totp_at(secret, current_code, step)[0] is False
    previous_code = pyotp.TOTP(secret).at((current_step - 1) * 30)
    assert totp_at(secret, previous_code, step)[0] is False


def test_owner_bootstrap_has_a_complete_local_email_mfa_path(app, tmp_path, monkeypatch):
    application, client = app
    outbox = tmp_path / "owner-mail.jsonl"
    monkeypatch.setenv("SESSION_SECRET", application.state.settings.session_secret)
    monkeypatch.setenv("DATABASE_URL", application.state.settings.database_url)
    monkeypatch.setenv("FAKE_MAIL_OUTBOX", str(outbox))
    answers = iter(["OwnerPassword-12345", "OwnerPassword-12345"])
    monkeypatch.setattr("server.cli.getpass.getpass", lambda _prompt: next(answers))
    assert bootstrap_owner(argparse.Namespace(name="Local Owner", email="owner@sample.com")) == 0
    messages = [json.loads(line) for line in outbox.read_text(encoding="utf-8").splitlines()]
    verification = messages[-1]
    assert verification["purpose"] == "VERIFY_EMAIL"
    with application.state.session_factory() as db:
        owner = db.scalar(select(User).where(User.email_normalized == "owner@sample.com"))
        challenge = db.scalar(select(EmailChallenge).where(EmailChallenge.user_id == owner.id))
        assert owner.status == "PENDING"
        assert owner.role == "OWNER"
        assert owner.email_verified_at is None
        assert challenge.id
    verified = client.post("/api/v1/auth/verify-email", json={"challenge_id": challenge.id, "code": verification["code"]})
    enrollment = verified.json()["data"]["enrollment_token"]
    secret = client.post("/api/v1/auth/mfa/enroll", headers={"Authorization": f"Bearer {enrollment}"}).json()["data"]["secret"]
    completed = client.post("/api/v1/auth/mfa/confirm", headers={"Authorization": f"Bearer {enrollment}"}, json={"code": pyotp.TOTP(secret).now()})
    assert completed.status_code == 200
    assert completed.json()["data"]["role"] == "OWNER"
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 401
    assert me.json()["error"]["code"] == "AUTH_REQUIRED"


def test_expired_session_is_rejected(app, admin_token):
    application, client = app
    expired_token = new_token()
    with application.state.session_factory() as db:
        admin = db.scalar(select(User).where(User.role == "ADMIN"))
        now = utcnow()
        db.add(SessionRecord(token_digest=digest_token(application.state.settings.session_secret, expired_token), user_id=admin.id, stage="AUTHENTICATED", csrf_digest=digest_token(application.state.settings.session_secret, "expired-csrf"), expires_at=now - timedelta(minutes=1), last_seen_at=now, created_at=now))
        db.commit()
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "SESSION_INVALID"


def test_login_attempts_are_rate_limited(app):
    _, client = app
    payload = {"email": "unknown-rate-limit@sample.com", "password": "wrong-password", "terms_version": "terms-v1"}
    for _ in range(10):
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 401
    limited = client.post("/api/v1/auth/login", json=payload)
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "AUTH_RATE_LIMITED"


def test_login_otp_issuance_is_rate_limited_after_valid_credentials(app):
    application, client = app
    password = "P" + secrets.token_urlsafe(18)
    registration = client.post("/api/v1/auth/register", json={"username": "otp_rate_user", "display_name": "OTP Rate User", "email": "otp-rate@sample.com", "password": password, "password_confirm": password, "terms_version": "terms-v1"})
    verification = application.state.fake_mail.latest("otp-rate@sample.com", "VERIFY_EMAIL")
    enrollment = client.post("/api/v1/auth/verify-email", json={"challenge_id": registration.json()["data"]["challenge_id"], "code": verification.code}).json()["data"]["enrollment_token"]
    secret = client.post("/api/v1/auth/mfa/enroll", headers={"Authorization": f"Bearer {enrollment}"}).json()["data"]["secret"]
    client.post("/api/v1/auth/mfa/confirm", headers={"Authorization": f"Bearer {enrollment}"}, json={"code": pyotp.TOTP(secret).now()})
    payload = {"email": "otp-rate@sample.com", "password": password, "terms_version": "terms-v1"}
    for _ in range(5):
        assert client.post("/api/v1/auth/login", json=payload).status_code == 200
    limited = client.post("/api/v1/auth/login", json=payload)
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "OTP_RATE_LIMITED"


def test_recovery_factor_attempts_are_rate_limited(app):
    application, client = app
    password = "P" + secrets.token_urlsafe(18)
    registration = client.post("/api/v1/auth/register", json={"username": "recovery_rate_user", "display_name": "Recovery Rate User", "email": "recovery-rate@sample.com", "password": password, "password_confirm": password, "terms_version": "terms-v1"})
    verification = application.state.fake_mail.latest("recovery-rate@sample.com", "VERIFY_EMAIL")
    enrollment = client.post("/api/v1/auth/verify-email", json={"challenge_id": registration.json()["data"]["challenge_id"], "code": verification.code}).json()["data"]["enrollment_token"]
    secret = client.post("/api/v1/auth/mfa/enroll", headers={"Authorization": f"Bearer {enrollment}"}).json()["data"]["secret"]
    client.post("/api/v1/auth/mfa/confirm", headers={"Authorization": f"Bearer {enrollment}"}, json={"code": pyotp.TOTP(secret).now()})
    login = client.post("/api/v1/auth/login", json={"email": "recovery-rate@sample.com", "password": password, "terms_version": "terms-v1"}).json()["data"]
    login_mail = application.state.fake_mail.latest("recovery-rate@sample.com", "LOGIN_OTP")
    assert client.post("/api/v1/auth/verify-login-otp", headers={"Authorization": f"Bearer {login['login_token']}"}, json={"challenge_id": login["challenge_id"], "code": login_mail.code}).status_code == 200
    for _ in range(5):
        assert client.post("/api/v1/auth/recovery", headers={"Authorization": f"Bearer {login['login_token']}"}, json={"code": "00000000-00000000"}).status_code == 400
    limited = client.post("/api/v1/auth/recovery", headers={"Authorization": f"Bearer {login['login_token']}"}, json={"code": "00000000-00000000"})
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "FACTOR_RATE_LIMITED"


def test_factor_rate_limit_cannot_be_bypassed_by_starting_a_second_login(app):
    application, client = app
    password = "P" + secrets.token_urlsafe(18)
    registration = client.post("/api/v1/auth/register", json={"username": "cross_session_factor_user", "display_name": "Cross Session Factor User", "email": "cross-session-factor@sample.com", "password": password, "password_confirm": password, "terms_version": "terms-v1"})
    verification = application.state.fake_mail.latest("cross-session-factor@sample.com", "VERIFY_EMAIL")
    enrollment = client.post("/api/v1/auth/verify-email", json={"challenge_id": registration.json()["data"]["challenge_id"], "code": verification.code}).json()["data"]["enrollment_token"]
    secret = client.post("/api/v1/auth/mfa/enroll", headers={"Authorization": f"Bearer {enrollment}"}).json()["data"]["secret"]
    assert client.post("/api/v1/auth/mfa/confirm", headers={"Authorization": f"Bearer {enrollment}"}, json={"code": pyotp.TOTP(secret).now()}).status_code == 200

    first = client.post("/api/v1/auth/login", json={"email": "cross-session-factor@sample.com", "password": password, "terms_version": "terms-v1"}).json()["data"]
    first_mail = application.state.fake_mail.latest("cross-session-factor@sample.com", "LOGIN_OTP")
    assert client.post("/api/v1/auth/verify-login-otp", headers={"Authorization": f"Bearer {first['login_token']}"}, json={"challenge_id": first["challenge_id"], "code": first_mail.code}).status_code == 200

    second = client.post("/api/v1/auth/login", json={"email": "cross-session-factor@sample.com", "password": password, "terms_version": "terms-v1"}).json()["data"]
    second_mail = application.state.fake_mail.latest("cross-session-factor@sample.com", "LOGIN_OTP")
    assert client.post("/api/v1/auth/verify-login-otp", headers={"Authorization": f"Bearer {second['login_token']}"}, json={"challenge_id": second["challenge_id"], "code": second_mail.code}).status_code == 200

    bad_code = "000000" if pyotp.TOTP(secret).now() != "000000" else "999999"
    for _ in range(5):
        failed = client.post("/api/v1/auth/verify-totp", headers={"Authorization": f"Bearer {first['login_token']}"}, json={"code": bad_code})
        assert failed.status_code == 400
    blocked = client.post("/api/v1/auth/verify-totp", headers={"Authorization": f"Bearer {second['login_token']}"}, json={"code": pyotp.TOTP(secret).now()})
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "FACTOR_RATE_LIMITED"


def test_terms_version_and_whitespace_are_server_enforced(app):
    _, client = app
    password = "P" + secrets.token_urlsafe(18)
    terms = client.post("/api/v1/auth/register", json={"username": "terms_user", "display_name": "Terms User", "email": "terms-version@sample.com", "password": password, "password_confirm": password, "terms_version": "terms-v0"})
    assert terms.status_code == 400
    assert terms.json()["error"]["code"] == "TERMS_VERSION_REQUIRED"
    whitespace = client.post("/api/v1/auth/register", json={"username": "blank_user", "display_name": "   ", "email": "whitespace@sample.com", "password": password, "password_confirm": password, "terms_version": "terms-v1"})
    assert whitespace.status_code == 422


def test_invalid_email_validation_returns_localized_feedback(app):
    _, client = app
    password = "P" + secrets.token_urlsafe(18)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Invalid Email User",
            "email": "not-an-email",
            "password": password,
            "password_confirm": password,
            "terms_version": "terms-v1",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["message_for_user"] == "Email không hợp lệ. Hãy kiểm tra lại địa chỉ email."
    assert "not-an-email" not in response.text


def test_registration_attempts_are_rate_limited_by_client(app):
    _, client = app
    for index in range(20):
        password = "P" + secrets.token_urlsafe(18)
        response = client.post("/api/v1/auth/register", json={"username": f"rate_user_{index}", "display_name": f"Rate User {index}", "email": f"rate-{index}@sample.com", "password": password, "password_confirm": password, "terms_version": "terms-v1"})
        assert response.status_code == 201
    blocked_password = "P" + secrets.token_urlsafe(18)
    limited = client.post("/api/v1/auth/register", json={"username": "rate_user_blocked", "display_name": "Rate User blocked", "email": "rate-blocked@sample.com", "password": blocked_password, "password_confirm": blocked_password, "terms_version": "terms-v1"})
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "REGISTRATION_RATE_LIMITED"


def _register_until_secret(application, client, username, email, password):
    registration = client.post("/api/v1/auth/register", json={"username": username, "email": email, "password": password, "password_confirm": password, "terms_version": "terms-v1"})
    assert registration.status_code == 201, registration.text
    mail = application.state.fake_mail.latest(email, "VERIFY_EMAIL")
    verified = client.post("/api/v1/auth/verify-email", json={"challenge_id": registration.json()["data"]["challenge_id"], "code": mail.code})
    token = verified.json()["data"]["enrollment_token"]
    enrolled = client.post("/api/v1/auth/mfa/enroll", headers={"Authorization": f"Bearer {token}"})
    assert enrolled.status_code == 200
    return token, enrolled.json()["data"]["secret"]


def test_register_requires_username(app):
    _, client = app
    password = "P" + secrets.token_urlsafe(18)
    missing = client.post("/api/v1/auth/register", json={"display_name": "No Username", "email": "nouser@sample.com", "password": password, "password_confirm": password, "terms_version": "terms-v1"})
    assert missing.status_code == 422
    bad = client.post("/api/v1/auth/register", json={"username": "a b", "email": "nouser@sample.com", "password": password, "password_confirm": password, "terms_version": "terms-v1"})
    assert bad.status_code == 422


def test_login_by_username(app):
    application, client = app
    password = "P" + secrets.token_urlsafe(18)
    token, secret = _register_until_secret(application, client, "pilot_one", "pilot1@sample.com", password)
    assert client.post("/api/v1/auth/mfa/confirm", headers={"Authorization": f"Bearer {token}"}, json={"code": pyotp.TOTP(secret).now()}).status_code == 200
    login = client.post("/api/v1/auth/login", json={"identifier": "Pilot_One", "password": password, "terms_accepted": True, "terms_version": "terms-v1"})
    assert login.status_code == 200
    assert login.json()["data"]["next_step"] == "EMAIL_OTP"
    assert application.state.fake_mail.latest("pilot1@sample.com", "LOGIN_OTP") is not None
    unticked = client.post("/api/v1/auth/login", json={"identifier": "pilot_one", "password": password, "terms_accepted": False, "terms_version": "terms-v1"})
    assert unticked.status_code == 400
    assert unticked.json()["error"]["code"] == "TERMS_ACCEPTANCE_REQUIRED"


def test_reenroll_after_abandoned_mfa(app):
    application, client = app
    password = "P" + secrets.token_urlsafe(18)
    _, first_secret = _register_until_secret(application, client, "left_early", "left@sample.com", password)
    login = client.post("/api/v1/auth/login", json={"identifier": "left_early", "password": password, "terms_accepted": True, "terms_version": "terms-v1"})
    assert login.status_code == 200
    data = login.json()["data"]
    mail = application.state.fake_mail.latest("left@sample.com", "LOGIN_OTP")
    otp = client.post("/api/v1/auth/verify-login-otp", headers={"Authorization": f"Bearer {data['login_token']}"}, json={"challenge_id": data["challenge_id"], "code": mail.code})
    assert otp.status_code == 200
    assert otp.json()["data"]["next_step"] == "TOTP_ENROLLMENT"
    token = otp.json()["data"]["enrollment_token"]
    again = client.post("/api/v1/auth/mfa/enroll", headers={"Authorization": f"Bearer {token}"})
    assert again.status_code == 200
    second_secret = again.json()["data"]["secret"]
    assert second_secret != first_secret
    assert client.post("/api/v1/auth/mfa/confirm", headers={"Authorization": f"Bearer {token}"}, json={"code": pyotp.TOTP(second_secret).now()}).status_code == 200


def test_default_owner_skips_email_otp(app, monkeypatch):
    from server import cli
    application, client = app
    secret = pyotp.random_base32()
    monkeypatch.setenv("DEFAULT_OWNER_USERNAME", "chief")
    monkeypatch.setenv("DEFAULT_OWNER_PASSWORD", "chief-test-password")
    monkeypatch.setenv("DEFAULT_OWNER_TOTP_SECRET", secret)
    monkeypatch.setattr(cli, "load_settings", lambda: application.state.settings)
    assert cli.seed_default_owner(argparse.Namespace()) == 0
    before = len(application.state.fake_mail.messages)
    login = client.post("/api/v1/auth/login", json={"identifier": "chief", "password": "chief-test-password", "terms_accepted": True, "terms_version": "terms-v1"})
    assert login.status_code == 200
    assert login.json()["data"]["next_step"] == "TOTP"
    assert len(application.state.fake_mail.messages) == before
    totp = client.post("/api/v1/auth/verify-totp", headers={"Authorization": f"Bearer {login.json()['data']['login_token']}"}, json={"code": pyotp.TOTP(secret).now()})
    assert totp.status_code == 200
    assert totp.json()["data"]["role"] == "OWNER"
    assert totp.json()["data"]["status"] == "ACTIVE"
    health = client.get("/api/v1/health")
    assert health.json()["data"]["terms_version"] == "terms-v1"
