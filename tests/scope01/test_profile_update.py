from datetime import timedelta

from server.app.models import Credential, SessionRecord, User
from server.app.security import digest_token, hash_password, new_token, utcnow, verify_password


def authenticated_client(application, client, *, username="profile-user", email="profile@example.com"):
    now = utcnow()
    token = new_token()
    other_token = new_token()
    with application.state.session_factory() as db:
        user = User(
            display_name=username,
            email_normalized=email,
            status="ACTIVE",
            role="GUEST",
            email_verified_at=now,
            created_at=now,
            updated_at=now,
        )
        user.credential = Credential(password_hash=hash_password("correct horse battery staple"), totp_active=True, created_at=now, updated_at=now)
        db.add(user)
        db.flush()
        db.add_all([
            SessionRecord(token_digest=digest_token(application.state.settings.session_secret, token), user_id=user.id, stage="AUTHENTICATED", csrf_digest=digest_token(application.state.settings.session_secret, "profile-csrf"), expires_at=now + timedelta(hours=1), last_seen_at=now, created_at=now),
            SessionRecord(token_digest=digest_token(application.state.settings.session_secret, other_token), user_id=user.id, stage="AUTHENTICATED", csrf_digest=digest_token(application.state.settings.session_secret, "other-csrf"), expires_at=now + timedelta(hours=1), last_seen_at=now, created_at=now),
        ])
        db.commit()
        user_id = user.id
    client.cookies.set("session", token)
    client.cookies.set("csrf", "profile-csrf")
    return user_id, {"X-CSRF-Token": "profile-csrf"}, other_token


def profile_body(**overrides):
    body = {
        "current_password": "correct horse battery staple",
        "display_name": "New display name",
        "email": "profile@example.com",
        "full_name": "Nguyen Van An",
        "new_password": None,
        "license_code": "VN-A-12345",
        "license_class": "A",
        "license_expiry": "2030-12-31",
    }
    return {**body, **overrides}


def test_profile_update_requires_authenticated_csrf_and_current_password(app):
    application, client = app
    response = client.post("/api/v1/auth/profile/update-challenge", json=profile_body())
    assert response.status_code == 401, response.text

    user_id, headers, _ = authenticated_client(application, client)
    bad_password = client.post("/api/v1/auth/profile/update-challenge", json=profile_body(current_password="incorrect"), headers=headers)
    assert bad_password.status_code == 401
    with application.state.session_factory() as db:
        user = db.get(User, user_id)
        assert user.display_name == "profile-user"
        assert user.license_code is None

    no_csrf = client.post("/api/v1/auth/profile/update-challenge", json=profile_body())
    assert no_csrf.status_code == 403


def test_profile_update_changes_fields_only_after_current_email_otp(app):
    application, client = app
    user_id, headers, other_token = authenticated_client(application, client)
    started = client.post("/api/v1/auth/profile/update-challenge", json=profile_body(new_password="a new secure password"), headers=headers)
    assert started.status_code == 200
    challenge_id = started.json()["data"]["challenge_id"]
    code = application.state.fake_mail.latest(recipient="profile@example.com", purpose="PROFILE_UPDATE_CURRENT").code

    verified = client.post("/api/v1/auth/profile/verify-current-email", json={"challenge_id": challenge_id, "code": code}, headers=headers)
    assert verified.status_code == 200
    data = verified.json()["data"]
    assert data["updated"] is True
    assert data["profile"]["display_name"] == "New display name"
    assert data["profile"]["full_name"] == "Nguyen Van An"
    assert data["profile"]["license_class"] == "A"
    assert data["profile"]["license_expiry"] == "2030-12-31"
    assert client.get("/api/v1/auth/me").json()["data"]["license_code"] == "VN-A-12345"
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {other_token}"}).status_code == 401
    with application.state.session_factory() as db:
        user = db.get(User, user_id)
        assert verify_password(user.credential.password_hash, "a new secure password")


def test_email_change_requires_otp_at_old_and_new_addresses_before_commit(app):
    application, client = app
    user_id, headers, _ = authenticated_client(application, client)
    started = client.post("/api/v1/auth/profile/update-challenge", json=profile_body(email="new-profile@example.com"), headers=headers)
    assert started.status_code == 200
    challenge_id = started.json()["data"]["challenge_id"]
    old_code = application.state.fake_mail.latest(recipient="profile@example.com", purpose="PROFILE_UPDATE_CURRENT").code

    old_verified = client.post("/api/v1/auth/profile/verify-current-email", json={"challenge_id": challenge_id, "code": old_code}, headers=headers)
    assert old_verified.status_code == 200
    assert old_verified.json()["data"]["next_step"] == "NEW_EMAIL_OTP"
    with application.state.session_factory() as db:
        assert db.get(User, user_id).email_normalized == "profile@example.com"

    new_code = application.state.fake_mail.latest(recipient="new-profile@example.com", purpose="PROFILE_UPDATE_NEW").code
    completed = client.post("/api/v1/auth/profile/verify-new-email", json={"challenge_id": challenge_id, "code": new_code}, headers=headers)
    assert completed.status_code == 200
    assert completed.json()["data"]["profile"]["email"] == "new-profile@example.com"
    assert client.get("/api/v1/auth/me").json()["data"]["email"] == "new-profile@example.com"


def test_wrong_new_email_otp_does_not_apply_profile_changes(app):
    application, client = app
    user_id, headers, _ = authenticated_client(application, client)
    started = client.post("/api/v1/auth/profile/update-challenge", json=profile_body(email="new-profile@example.com"), headers=headers)
    challenge_id = started.json()["data"]["challenge_id"]
    old_code = application.state.fake_mail.latest(recipient="profile@example.com", purpose="PROFILE_UPDATE_CURRENT").code
    assert client.post("/api/v1/auth/profile/verify-current-email", json={"challenge_id": challenge_id, "code": old_code}, headers=headers).status_code == 200

    real_code = application.state.fake_mail.latest(recipient="new-profile@example.com", purpose="PROFILE_UPDATE_NEW").code
    wrong_code = "000000" if real_code != "000000" else "000001"
    bad = client.post("/api/v1/auth/profile/verify-new-email", json={"challenge_id": challenge_id, "code": wrong_code}, headers=headers)
    assert bad.status_code == 400
    with application.state.session_factory() as db:
        user = db.get(User, user_id)
        assert user.email_normalized == "profile@example.com"
        assert user.display_name == "profile-user"
