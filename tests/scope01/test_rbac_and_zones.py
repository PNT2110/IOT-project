from __future__ import annotations

from dataclasses import replace
import secrets

from server.app.models import Credential, SessionRecord, User
from server.app.security import digest_token, hash_password, new_token, utcnow


def test_guest_cannot_read_internal_map(app):
    _, client = app
    response = client.get("/api/v1/internal/zones")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_admin_can_crud_with_version_guard_and_audit(app, admin_token):
    application, client = app
    headers = {"Authorization": f"Bearer {admin_token}"}
    internal = client.get("/api/v1/internal/zones", headers=headers)
    assert internal.status_code == 200
    source_id = internal.json()["data"]["items"][0]["source_id"]
    geometry = {"type": "Polygon", "coordinates": [[[30, 30], [30.1, 30], [30.1, 30.1], [30, 30.1], [30, 30]]]}
    created = client.post("/api/v1/internal/zones", headers=headers, json={"name": "New synthetic zone", "geometry": geometry, "visibility": "INTERNAL", "classification": "INTERNAL_RESEARCH", "source_id": source_id})
    assert created.status_code == 201
    zone_id = created.json()["data"]["id"]
    stale = client.patch(f"/api/v1/internal/zones/{zone_id}", headers={**headers, "If-Match": "99"}, json={"name": "Changed", "geometry": geometry, "visibility": "INTERNAL", "classification": "INTERNAL_RESEARCH", "source_id": source_id, "version": 99})
    assert stale.status_code == 409
    malformed = client.patch(f"/api/v1/internal/zones/{zone_id}", headers={**headers, "If-Match": "not-a-version"}, json={"name": "Changed", "geometry": geometry, "visibility": "INTERNAL", "classification": "INTERNAL_RESEARCH", "source_id": source_id, "version": 1})
    assert malformed.status_code == 422
    assert malformed.json()["error"]["code"] == "IF_MATCH_INVALID"
    update_headers = {**headers, "If-Match": "1", "Idempotency-Key": "zone-update-retry-1"}
    update_body = {"name": "Changed", "geometry": geometry, "visibility": "INTERNAL", "classification": "INTERNAL_RESEARCH", "source_id": source_id, "version": 1}
    updated = client.patch(f"/api/v1/internal/zones/{zone_id}", headers=update_headers, json=update_body)
    assert updated.status_code == 200
    retried_update = client.patch(f"/api/v1/internal/zones/{zone_id}", headers=update_headers, json=update_body)
    assert retried_update.status_code == 200
    assert retried_update.json()["data"] == updated.json()["data"]
    delete_headers = {**headers, "If-Match": "2", "Idempotency-Key": "zone-delete-retry-1"}
    deleted = client.delete(f"/api/v1/internal/zones/{zone_id}", headers=delete_headers)
    assert deleted.status_code == 200
    retried_delete = client.delete(f"/api/v1/internal/zones/{zone_id}", headers=delete_headers)
    assert retried_delete.status_code == 200
    assert retried_delete.json()["data"] == deleted.json()["data"]
    with application.state.session_factory() as db:
        from server.app.models import AuditEvent
        assert len(db.query(AuditEvent).filter(AuditEvent.object_id == zone_id).all()) == 3


def test_only_owner_can_register_a_zone_source(app, admin_token):
    _, client = app
    admin = {"Authorization": f"Bearer {admin_token}"}
    application, _ = app
    now = utcnow()
    with application.state.session_factory() as db:
        user = User(display_name="Fixture Owner", email_normalized="owner-source@sample.com", status="ACTIVE", role="OWNER", email_verified_at=now, created_at=now, updated_at=now)
        user.credential = Credential(password_hash=hash_password(secrets.token_urlsafe(18)), totp_active=True, created_at=now, updated_at=now)
        db.add(user)
        db.flush()
        token = new_token()
        db.add(SessionRecord(token_digest=digest_token(application.state.settings.session_secret, token), user_id=user.id, stage="AUTHENTICATED", csrf_digest=digest_token(application.state.settings.session_secret, "csrf"), expires_at=now.replace(year=now.year + 1), last_seen_at=now, created_at=now))
        db.commit()
    owner = {"Authorization": f"Bearer {token}"}
    denied = client.post("/api/v1/internal/zone-sources", headers=admin, json={"publisher": "Operator", "source_type": "OPERATOR_DRAWN", "license_name": "Internal", "checksum": "sha256:test-source"})
    assert denied.status_code == 403
    created = client.post("/api/v1/internal/zone-sources", headers=owner, json={"publisher": "Operator", "source_type": "OPERATOR_DRAWN", "license_name": "Internal", "checksum": "sha256:test-source"})
    assert created.status_code == 201
    assert created.json()["data"]["source_type"] == "OPERATOR_DRAWN"


def test_public_zone_visibility_reaches_public_map(app, admin_token):
    _, client = app
    headers = {"Authorization": f"Bearer {admin_token}"}
    source_id = client.get("/api/v1/internal/zones", headers=headers).json()["data"]["items"][0]["source_id"]
    geometry = {"type": "Polygon", "coordinates": [[[31, 31], [31.1, 31], [31.1, 31.1], [31, 31.1], [31, 31]]]}
    created = client.post("/api/v1/internal/zones", headers=headers, json={"name": "Public acceptance zone", "geometry": geometry, "visibility": "PUBLIC", "classification": "NO_FLY", "source_id": source_id})
    assert created.status_code == 201
    zone_id = created.json()["data"]["id"]
    public_items = client.get("/api/v1/public/zones").json()["data"]["items"]
    assert any(item["id"] == zone_id and item["visibility"] == "PUBLIC" for item in public_items)
    deleted = client.delete(f"/api/v1/internal/zones/{zone_id}", headers={**headers, "If-Match": "1"})
    assert deleted.status_code == 200


def test_invalid_geometry_is_rejected(app, admin_token):
    _, client = app
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post("/api/v1/internal/zones", headers=headers, json={"name": "Bad", "geometry": {"type": "Point", "coordinates": [0, 0]}, "visibility": "INTERNAL", "classification": "INTERNAL_RESEARCH", "source_id": "00000000-0000-4000-8000-000000000001"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_GEOMETRY"


def test_unknown_zone_does_not_leak_object_details(app, admin_token):
    _, client = app
    headers = {"Authorization": f"Bearer {admin_token}"}
    unknown = "00000000-0000-4000-8000-000000000099"
    response = client.patch(f"/api/v1/internal/zones/{unknown}", headers={**headers, "If-Match": "1"}, json={"name": "Unknown", "geometry": {"type": "Polygon", "coordinates": [[[30, 30], [30.1, 30], [30.1, 30.1], [30, 30.1], [30, 30]]]}, "visibility": "INTERNAL", "classification": "INTERNAL_RESEARCH", "source_id": "00000000-0000-4000-8000-000000000001", "version": 1})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_pending_user_cannot_mutate_internal_map(app):
    application, client = app
    password = "P" + __import__("secrets").token_urlsafe(18)
    registration = client.post("/api/v1/auth/register", json={"username": "pending_map_user", "display_name": "Pending Map User", "email": "pending-map@sample.com", "password": password, "password_confirm": password, "terms_version": "terms-v1"})
    mail = application.state.fake_mail.latest("pending-map@sample.com", "VERIFY_EMAIL")
    enrollment = client.post("/api/v1/auth/verify-email", json={"challenge_id": registration.json()["data"]["challenge_id"], "code": mail.code}).json()["data"]["enrollment_token"]
    secret = client.post("/api/v1/auth/mfa/enroll", headers={"Authorization": f"Bearer {enrollment}"}).json()["data"]["secret"]
    enrolled = client.post("/api/v1/auth/mfa/confirm", headers={"Authorization": f"Bearer {enrollment}"}, json={"code": __import__("pyotp").TOTP(secret).now()})
    assert enrolled.status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": "pending-map@sample.com", "password": password, "terms_version": "terms-v1"}).json()["data"]
    login_mail = application.state.fake_mail.latest("pending-map@sample.com", "LOGIN_OTP")
    otp = client.post("/api/v1/auth/verify-login-otp", headers={"Authorization": f"Bearer {login['login_token']}"}, json={"challenge_id": login["challenge_id"], "code": login_mail.code})
    assert otp.status_code == 200
    totp_code = __import__("pyotp").TOTP(secret).at((int(__import__("time").time()) // 30 + 1) * 30)
    authenticated = client.post("/api/v1/auth/verify-totp", headers={"Authorization": f"Bearer {login['login_token']}"}, json={"code": totp_code})
    assert authenticated.status_code == 200
    response = client.get("/api/v1/internal/zones", headers={"Authorization": f"Bearer {authenticated.json()['data']['access_token']}"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_public_mode_rejects_fixture_sources_and_fake_pi_adapters(app, admin_token):
    application, client = app
    application.state.settings = replace(application.state.settings, public_mode=True)
    headers = {"Authorization": f"Bearer {admin_token}"}
    source_id = client.get("/api/v1/internal/zones", headers=headers).json()["data"]["items"][0]["source_id"]
    geometry = {"type": "Polygon", "coordinates": [[[32, 32], [32.1, 32], [32.1, 32.1], [32, 32.1], [32, 32]]]}
    fixture_zone = client.post("/api/v1/internal/zones", headers=headers, json={"name": "Fixture must not publish", "geometry": geometry, "visibility": "PUBLIC", "classification": "NO_FLY", "source_id": source_id})
    assert fixture_zone.status_code == 422
    assert fixture_zone.json()["error"]["code"] == "SOURCE_NOT_FOUND"
    fake_adapter = client.get("/api/v1/pi/v1/map", headers={**headers, "X-Fake-Pi-Client": "scope02-test-client"})
    assert fake_adapter.status_code == 404


def test_fake_pi_adapters_require_explicit_test_flag(app, admin_token):
    from dataclasses import replace

    application, client = app
    application.state.settings = replace(application.state.settings, enable_test_adapters=False)
    response = client.get("/api/v1/pi/v1/map", headers={"Authorization": f"Bearer {admin_token}", "X-Fake-Pi-Client": "scope02-test-client"})
    assert response.status_code == 404
