from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
import pytest
import pyotp

from pi5.web.app import PiWebConfig, create_pi_app
from pi5.web.auth import PiAuthError, PiAuthService
from pi5.web.camera import MockCameraAdapter
from pi5.web.firmware import FirmwareReadiness
from pi5.web.models import PiRole
from pi5.web.persistence import PiUserStore
from pi5.web.cache import MapCache
from pi5.web.pc_sync import PcMapSyncClient, PcMapSyncConfig, PcMapSyncError


def make_client() -> tuple[TestClient, PiAuthService, MockCameraAdapter]:
    auth = PiAuthService(allow_inmemory_email=True)
    auth.add_user("alice", "correct horse battery staple", role=PiRole.USER, email="alice@example.test")
    camera = MockCameraAdapter()
    app = create_pi_app(PiWebConfig(secure_cookies=False), auth=auth, camera=camera)
    return TestClient(app), auth, camera


def login(client: TestClient, auth: PiAuthService) -> None:
    challenge = client.post("/api/pi/v1/auth/challenge", json={"username": "alice", "password": "correct horse battery staple", "terms_accepted": True})
    assert challenge.status_code == 200
    challenge_id = challenge.json()["data"]["challenge_id"]
    otp = auth.challenge_code_for_test(challenge_id)
    email_step = client.post("/api/pi/v1/auth/login", json={"challenge_id": challenge_id, "otp": otp})
    assert email_step.status_code == 200
    mfa_challenge_id = email_step.json()["data"]["mfa_challenge_id"]
    response = client.post("/api/pi/v1/auth/login", json={"mfa_challenge_id": mfa_challenge_id, "totp": auth.challenge_totp_for_test(mfa_challenge_id)})
    assert response.status_code == 200
    assert response.json()["data"]["role"] == "USER"


def test_pi_dashboard_requires_authentication_and_security_headers() -> None:
    client, _, _ = make_client()
    page = client.get("/")
    assert page.status_code == 200
    assert "F450 PNT PVD" in page.text
    assert client.get("/favicon.ico").status_code == 204
    csp = page.headers["content-security-policy"]
    assert "script-src 'self';" in csp
    assert "unsafe-inline" not in csp.split("script-src")[1].split(";")[0]
    response = client.get("/api/pi/v1/telemetry")
    assert response.status_code == 401
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert response.headers["cross-origin-opener-policy"] == "same-origin"


def test_pi_rejects_oversized_request_before_json_parsing() -> None:
    client, _, _ = make_client()
    response = client.post("/api/pi/v1/auth/register", content=b"{}", headers={"Content-Type": "application/json", "Content-Length": "1000001"})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_pi_rejects_malformed_or_non_object_json_without_500() -> None:
    client, _, _ = make_client()
    malformed = client.post("/api/pi/v1/auth/register", content=b"not-json", headers={"Content-Type": "application/json"})
    assert malformed.status_code == 400
    assert malformed.json()["error"]["code"] == "INVALID_JSON"
    non_object = client.post("/api/pi/v1/auth/register", json=["not", "an", "object"])
    assert non_object.status_code == 400
    assert non_object.json()["error"]["code"] == "INVALID_BODY"


def test_pi_user_can_read_camera_but_not_admin_map_or_telemetry() -> None:
    client, auth, camera = make_client()
    login(client, auth)
    camera.produce(b"jpeg-frame")
    frame = client.get("/api/pi/v1/camera/stream")
    assert frame.status_code == 200
    assert frame.headers["content-type"] == "image/jpeg"
    assert frame.headers["cache-control"] == "no-store"
    assert frame.content == b"jpeg-frame"
    assert client.get("/api/pi/v1/map/cache").status_code == 403
    assert client.get("/api/pi/v1/telemetry").status_code == 403
    assert client.get("/api/pi/v1/3d").status_code == 403
    assert client.post("/api/pi/v1/arm").status_code == 404


def test_pi_profile_update_requires_current_password_and_email_otp() -> None:
    client, auth, _ = make_client()
    login(client, auth)
    assert client.get("/api/pi/v1/profile").json()["data"] == {
        "username": "alice",
        "email": "alice@example.test",
        "full_name": "",
        "license_code": "",
        "license_class": "",
        "license_expiry": "",
    }
    csrf = client.cookies.get("pi_csrf")
    body = {
        "username": "alice-operator",
        "email": "alice.new@example.test",
        "new_password": "new correct horse battery staple",
        "full_name": "Alice Operator",
        "license_code": "VN-123",
        "license_class": "A",
        "license_expiry": "2030-12-31",
        "current_password": "wrong password",
    }
    rejected = client.post("/api/pi/v1/profile/challenge", json=body, headers={"X-CSRF-Token": csrf})
    assert rejected.status_code == 401
    body["current_password"] = "correct horse battery staple"
    started = client.post("/api/pi/v1/profile/challenge", json=body, headers={"X-CSRF-Token": csrf})
    assert started.status_code == 201
    challenge_id = started.json()["data"]["challenge_id"]
    assert client.post("/api/pi/v1/profile/verify", json={"challenge_id": challenge_id, "otp": "wrong-code"}, headers={"X-CSRF-Token": csrf}).status_code == 401
    current_email_verified = client.post("/api/pi/v1/profile/verify", json={"challenge_id": challenge_id, "otp": auth.email_code_for_test(challenge_id)}, headers={"X-CSRF-Token": csrf})
    assert current_email_verified.status_code == 200
    assert current_email_verified.json()["data"]["next_step"] == "NEW_EMAIL_OTP"
    assert auth.users["alice"].email == "alice@example.test"
    assert client.post("/api/pi/v1/profile/verify", json={"challenge_id": challenge_id, "otp": "000000"}, headers={"X-CSRF-Token": csrf}).status_code == 401
    verified = client.post("/api/pi/v1/profile/verify", json={"challenge_id": challenge_id, "otp": auth.email_code_for_test(challenge_id, step="new_email")}, headers={"X-CSRF-Token": csrf})
    assert verified.status_code == 200
    assert auth.users["alice-operator"].email == "alice.new@example.test"
    assert auth.users["alice-operator"].license_code == "VN-123"
    assert client.get("/api/pi/v1/profile").json()["data"]["license_expiry"] == "2030-12-31"
    assert "password_hash" not in verified.text and "totp_secret" not in verified.text


def test_pi_login_requires_totp_and_rejects_totp_replay() -> None:
    client, auth, _ = make_client()
    email_challenge = client.post("/api/pi/v1/auth/challenge", json={"username": "alice", "password": "correct horse battery staple", "terms_accepted": True}).json()["data"]["challenge_id"]
    email_step = client.post("/api/pi/v1/auth/login", json={"challenge_id": email_challenge, "otp": auth.challenge_code_for_test(email_challenge)})
    mfa_challenge = email_step.json()["data"]["mfa_challenge_id"]
    assert client.post("/api/pi/v1/auth/login", json={"mfa_challenge_id": mfa_challenge, "totp": ""}).status_code == 401
    totp = auth.challenge_totp_for_test(mfa_challenge)
    assert client.post("/api/pi/v1/auth/login", json={"mfa_challenge_id": mfa_challenge, "totp": totp}).status_code == 200

    second_email = auth.start_challenge("alice", "correct horse battery staple", client_key="second-client")
    second_mfa = auth.complete_email_otp(second_email, auth.challenge_code_for_test(second_email), client_key="second-client")
    replay = client.post("/api/pi/v1/auth/login", json={"mfa_challenge_id": second_mfa, "totp": totp})
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "TOTP_REPLAY"


def test_pi_factor_lockout_cannot_be_bypassed_by_correct_code_after_failures() -> None:
    auth = PiAuthService(allow_inmemory_email=True)
    auth.add_user("alice", "correct horse battery staple", email="alice@example.test")

    email_challenge = auth.start_challenge("alice", "correct horse battery staple", client_key="locked-email")
    expected_email = auth.challenge_code_for_test(email_challenge)
    wrong_email = "000000" if expected_email != "000000" else "999999"
    for _ in range(auth.max_failures):
        with pytest.raises(PiAuthError):
            auth.complete_email_otp(email_challenge, wrong_email, client_key="locked-email")
    with pytest.raises(PiAuthError) as email_locked:
        auth.complete_email_otp(email_challenge, expected_email, client_key="locked-email")
    assert email_locked.value.code == "RATE_LIMITED"

    # Use a fresh service for the independent TOTP half of this test because
    # account-level throttling intentionally blocks every new factor flow.
    auth = PiAuthService(allow_inmemory_email=True)
    auth.add_user("alice", "correct horse battery staple", email="alice@example.test")
    second = auth.start_challenge("alice", "correct horse battery staple", client_key="locked-totp")
    mfa_challenge = auth.complete_email_otp(second, auth.challenge_code_for_test(second), client_key="locked-totp")
    expected_totp = auth.challenge_totp_for_test(mfa_challenge)
    wrong_totp = "000000" if expected_totp != "000000" else "999999"
    for _ in range(auth.max_failures):
        with pytest.raises(PiAuthError):
            auth.complete_login(mfa_challenge, wrong_totp, client_key="locked-totp")
    with pytest.raises(PiAuthError) as totp_locked:
        auth.complete_login(mfa_challenge, expected_totp, client_key="locked-totp")
    assert totp_locked.value.code == "RATE_LIMITED"


def test_pi_factor_lockout_expires_and_does_not_permanently_disable_account() -> None:
    auth = PiAuthService(allow_inmemory_email=True)
    user = auth.add_user("alice", "correct horse battery staple", email="alice@example.test")
    auth.failures[user.user_id] = (auth.max_failures, datetime.now(timezone.utc) - timedelta(seconds=1))
    challenge_id = auth.start_challenge("alice", "correct horse battery staple", client_key="after-lockout")
    assert challenge_id


def test_pi_email_factor_lockout_is_bound_to_account_not_client_key() -> None:
    auth = PiAuthService(allow_inmemory_email=True)
    auth.add_user("alice", "correct horse battery staple", email="alice@example.test")
    first = auth.start_challenge("alice", "correct horse battery staple", client_key="client-a")
    second = auth.start_challenge("alice", "correct horse battery staple", client_key="client-b")
    wrong = "000000" if auth.challenge_code_for_test(first) != "000000" else "999999"
    for _ in range(auth.max_failures):
        with pytest.raises(PiAuthError):
            auth.complete_email_otp(first, wrong, client_key="client-a")
    with pytest.raises(PiAuthError) as blocked:
        auth.complete_email_otp(second, auth.challenge_code_for_test(second), client_key="client-b")
    assert blocked.value.code == "RATE_LIMITED"


def test_pi_registration_mfa_lockout_cannot_be_bypassed() -> None:
    auth = PiAuthService(allow_inmemory_email=True)
    app = create_pi_app(PiWebConfig(secure_cookies=False), auth=auth, camera=MockCameraAdapter())
    client = TestClient(app)
    registered = client.post("/api/pi/v1/auth/register", json={"username": "new-user", "email": "new-user@example.test", "password": "correct horse battery staple", "password_confirm": "correct horse battery staple", "terms_accepted": True})
    challenge_id = registered.json()["data"]["challenge_id"]
    verified = client.post("/api/pi/v1/auth/verify-email", json={"challenge_id": challenge_id, "code": auth.email_code_for_test(challenge_id)})
    enrollment = verified.json()["data"]["enrollment_token"]
    enrollment_data = client.post("/api/pi/v1/auth/mfa/enroll", headers={"Authorization": f"Bearer {enrollment}"})
    secret = enrollment_data.json()["data"]["secret"]
    wrong = "000000" if pyotp.TOTP(secret).now() != "000000" else "999999"
    for _ in range(auth.max_failures):
        response = client.post("/api/pi/v1/auth/mfa/confirm", headers={"Authorization": f"Bearer {enrollment}"}, json={"code": wrong})
        assert response.status_code in {400, 429}
    locked = client.post("/api/pi/v1/auth/mfa/confirm", headers={"Authorization": f"Bearer {enrollment}"}, json={"code": pyotp.TOTP(secret).now()})
    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "RATE_LIMITED"


def test_wildcard_pi_bind_is_rejected() -> None:
    with pytest.raises(ValueError, match="wildcard bind is forbidden"):
        create_pi_app(PiWebConfig(bind_host="0.0.0.0"))


def test_role_request_needs_csrf_and_admin_approval() -> None:
    auth = PiAuthService(allow_inmemory_email=True)
    user = auth.add_user("alice", "correct horse battery staple", role=PiRole.USER, email="alice@example.test")
    admin = auth.add_user("root", "another correct horse battery staple", role=PiRole.ADMIN, email="root@example.test")
    item = auth.request_admin(user, "Need local monitoring access")
    assert user.role is PiRole.USER
    camera = MockCameraAdapter()
    app = create_pi_app(PiWebConfig(secure_cookies=False), auth=auth, camera=camera)
    client = TestClient(app)
    login(client, auth)
    response = client.post("/api/pi/v1/role-requests", json={"reason": "missing csrf"})
    assert response.status_code == 403

    with pytest.raises(PiAuthError) as forbidden:
        auth.decide_role_request(user, item["request_id"], "APPROVED")
    assert forbidden.value.code == "ROLE_FORBIDDEN"
    result = auth.decide_role_request(admin, item["request_id"], "APPROVED")
    assert result["status"] == "APPROVED"
    assert user.role is PiRole.ADMIN


def test_role_request_write_failure_does_not_leave_memory_state() -> None:
    class FailingRoleStore:
        def load_users(self):
            return []

        def load_role_requests(self):
            return []

        def save_user(self, _user):
            return None

        def save_role_request(self, _item):
            raise OSError("disk full")

    auth = PiAuthService(store=FailingRoleStore())
    user = auth.add_user("alice", "correct horse battery staple", email="alice@example.test")
    with pytest.raises(PiAuthError) as failed:
        auth.request_admin(user, "Need local monitoring access")
    assert failed.value.code == "PERSISTENCE_FAILED"
    assert auth.role_requests == {}


def test_admin_user_list_is_redacted_and_forbidden_to_user() -> None:
    auth = PiAuthService(allow_inmemory_email=True)
    user = auth.add_user("alice", "correct horse battery staple", role=PiRole.USER, email="alice@example.test")
    admin = auth.add_user("root", "another correct horse battery staple", role=PiRole.ADMIN, email="root@example.test")
    app = create_pi_app(PiWebConfig(secure_cookies=False), auth=auth, camera=MockCameraAdapter())
    client = TestClient(app)
    login(client, auth)
    assert client.get("/api/pi/v1/admin/users").status_code == 403
    admin_client = TestClient(app)
    challenge = admin_client.post("/api/pi/v1/auth/challenge", json={"username": "root", "password": "another correct horse battery staple", "terms_accepted": True}).json()["data"]["challenge_id"]
    code = auth.challenge_code_for_test(challenge)
    email_step = admin_client.post("/api/pi/v1/auth/login", json={"challenge_id": challenge, "otp": code})
    assert email_step.status_code == 200
    mfa_challenge_id = email_step.json()["data"]["mfa_challenge_id"]
    assert admin_client.post("/api/pi/v1/auth/login", json={"mfa_challenge_id": mfa_challenge_id, "totp": auth.challenge_totp_for_test(mfa_challenge_id)}).status_code == 200
    response = admin_client.get("/api/pi/v1/admin/users")
    assert response.status_code == 200
    assert response.json()["data"]
    assert all("password_hash" not in item and "totp_secret" not in item for item in response.json()["data"])
    assert any(item["user_id"] == user.user_id for item in response.json()["data"])


def test_pi_registration_requires_email_otp_then_totp() -> None:
    auth = PiAuthService(allow_inmemory_email=True)
    app = create_pi_app(PiWebConfig(secure_cookies=False), auth=auth, camera=MockCameraAdapter())
    client = TestClient(app)
    registered = client.post("/api/pi/v1/auth/register", json={"username": "new-user", "email": "new-user@example.test", "password": "correct horse battery staple", "password_confirm": "correct horse battery staple", "terms_accepted": True})
    assert registered.status_code == 201
    challenge_id = registered.json()["data"]["challenge_id"]
    verified = client.post("/api/pi/v1/auth/verify-email", json={"challenge_id": challenge_id, "code": auth.email_code_for_test(challenge_id)})
    assert verified.status_code == 200
    enrollment = verified.json()["data"]["enrollment_token"]
    enrollment_data = client.post("/api/pi/v1/auth/mfa/enroll", headers={"Authorization": f"Bearer {enrollment}"})
    assert enrollment_data.status_code == 200
    secret = enrollment_data.json()["data"]["secret"]
    confirmed = client.post("/api/pi/v1/auth/mfa/confirm", headers={"Authorization": f"Bearer {enrollment}"}, json={"code": pyotp.TOTP(secret).now()})
    assert confirmed.status_code == 200
    login_challenge = client.post("/api/pi/v1/auth/challenge", json={"username": "new-user", "password": "correct horse battery staple", "terms_accepted": True})
    assert login_challenge.status_code == 200
    code = auth.challenge_code_for_test(login_challenge.json()["data"]["challenge_id"])
    email_step = client.post("/api/pi/v1/auth/login", json={"challenge_id": login_challenge.json()["data"]["challenge_id"], "otp": code})
    mfa_challenge_id = email_step.json()["data"]["mfa_challenge_id"]
    logged_in = client.post("/api/pi/v1/auth/login", json={"mfa_challenge_id": mfa_challenge_id, "totp": auth.challenge_totp_for_test(mfa_challenge_id)})
    assert logged_in.status_code == 200
    assert logged_in.json()["data"]["role"] == "USER"


def test_pi_registration_rate_limit_and_smtp_failure_do_not_leave_pending_users() -> None:
    def failing_sender(_recipient: str, _purpose: str, _code: str) -> None:
        raise RuntimeError("smtp unavailable")

    auth = PiAuthService(email_sender=failing_sender)
    app = create_pi_app(PiWebConfig(secure_cookies=False), auth=auth, camera=MockCameraAdapter())
    client = TestClient(app)
    failed = client.post("/api/pi/v1/auth/register", json={"username": "smtp-user", "email": "smtp@example.test", "password": "correct horse battery staple", "password_confirm": "correct horse battery staple", "terms_accepted": True})
    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "EMAIL_DELIVERY_FAILED"
    assert not auth.users

    limited_auth = PiAuthService(allow_inmemory_email=True)
    for index in range(5):
        assert limited_auth.register(f"user-{index}", f"user-{index}@example.test", "correct horse battery staple", "correct horse battery staple", client_key="same-client")
    with pytest.raises(PiAuthError) as limited:
        limited_auth.register("user-6", "user-6@example.test", "correct horse battery staple", "correct horse battery staple", client_key="same-client")
    assert limited.value.code == "RATE_LIMITED"


def test_pi_login_sends_email_otp_and_rolls_back_on_delivery_failure() -> None:
    sent: list[tuple[str, str, str]] = []

    def sender(recipient: str, purpose: str, code: str) -> None:
        sent.append((recipient, purpose, code))

    auth = PiAuthService(email_sender=sender)
    auth.add_user("mail-user", "correct horse battery staple", email="mail-user@example.test")
    app = create_pi_app(PiWebConfig(secure_cookies=False), auth=auth, camera=MockCameraAdapter())
    client = TestClient(app)
    challenge = client.post("/api/pi/v1/auth/challenge", json={"username": "mail-user", "password": "correct horse battery staple", "terms_accepted": True})
    assert challenge.status_code == 200
    assert sent and sent[-1][0:2] == ("mail-user@example.test", "PI_LOGIN")
    assert sent[-1][2] == auth.challenge_code_for_test(challenge.json()["data"]["challenge_id"])

    failing = PiAuthService(email_sender=lambda *_: (_ for _ in ()).throw(RuntimeError("smtp down")))
    failing.add_user("mail-user", "correct horse battery staple", email="mail-user@example.test")
    failing_client = TestClient(create_pi_app(PiWebConfig(secure_cookies=False), auth=failing, camera=MockCameraAdapter()))
    failed = failing_client.post("/api/pi/v1/auth/challenge", json={"username": "mail-user", "password": "correct horse battery staple", "terms_accepted": True})
    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "EMAIL_DELIVERY_FAILED"
    assert not failing.challenges


def test_pi_web_requires_terms_before_auth_or_registration() -> None:
    auth = PiAuthService(allow_inmemory_email=True)
    auth.add_user("alice", "correct horse battery staple")
    client = TestClient(create_pi_app(PiWebConfig(secure_cookies=False), auth=auth, camera=MockCameraAdapter()))
    assert client.post("/api/pi/v1/auth/challenge", json={"username": "alice", "password": "correct horse battery staple"}).json()["error"]["code"] == "TERMS_REQUIRED"
    assert client.post("/api/pi/v1/auth/register", json={"username": "new-user", "email": "new@example.test", "password": "correct horse battery staple", "password_confirm": "correct horse battery staple"}).json()["error"]["code"] == "TERMS_REQUIRED"


def test_pi_default_account_can_configure_email_before_first_otp_login() -> None:
    auth = PiAuthService(allow_inmemory_email=True)
    auth.add_user("default-admin", "correct horse battery staple", role=PiRole.ADMIN)
    client = TestClient(create_pi_app(PiWebConfig(secure_cookies=False), auth=auth, camera=MockCameraAdapter()))
    missing = client.post("/api/pi/v1/auth/challenge", json={"username": "default-admin", "password": "correct horse battery staple", "terms_accepted": True})
    assert missing.status_code == 409
    assert missing.json()["error"]["code"] == "EMAIL_SETUP_REQUIRED"
    setup = client.post("/api/pi/v1/auth/email/setup", json={"username": "default-admin", "password": "correct horse battery staple", "email": "default-admin@example.test", "terms_accepted": True})
    assert setup.status_code == 201
    challenge_id = setup.json()["data"]["challenge_id"]
    verified = client.post("/api/pi/v1/auth/email/verify", json={"challenge_id": challenge_id, "code": auth.email_code_for_test(challenge_id)})
    assert verified.status_code == 200
    assert auth.users["default-admin"].email == "default-admin@example.test"
    assert client.post("/api/pi/v1/auth/challenge", json={"username": "default-admin", "password": "correct horse battery staple", "terms_accepted": True}).status_code == 200


def test_pi_email_setup_and_login_challenges_are_rate_limited() -> None:
    auth = PiAuthService(allow_inmemory_email=True)
    auth.add_user("default-admin", "correct horse battery staple", role=PiRole.ADMIN)
    for _ in range(auth.max_registration_attempts):
        with pytest.raises(PiAuthError) as invalid:
            auth.start_email_setup("default-admin", "wrong password", "admin@example.test", client_key="same-client")
        assert invalid.value.code == "AUTHENTICATION_FAILED"
    with pytest.raises(PiAuthError) as limited_setup:
        auth.start_email_setup("default-admin", "wrong password", "admin@example.test", client_key="same-client")
    assert limited_setup.value.code == "RATE_LIMITED"

    for _ in range(auth.max_auth_challenge_attempts):
        with pytest.raises(PiAuthError) as invalid:
            auth.start_challenge("default-admin", "wrong password", client_key="login-client")
        assert invalid.value.code == "AUTHENTICATION_FAILED"
    with pytest.raises(PiAuthError) as limited_login:
        auth.start_challenge("default-admin", "wrong password", client_key="login-client")
    assert limited_login.value.code == "RATE_LIMITED"


def test_pi_identity_and_role_requests_persist_with_encrypted_totp_secret(tmp_path) -> None:
    path = tmp_path / "pi-auth.sqlite3"
    key = "K" * 40
    first = PiAuthService(store=PiUserStore(str(path), key))
    user = first.add_user("alice", "correct horse battery staple", email="alice@example.test")
    admin = first.add_user("root", "another correct horse battery staple", role=PiRole.ADMIN, email="root@example.test")
    request = first.request_admin(user, "Need local monitoring access")
    assert request["status"] == "PENDING"

    second = PiAuthService(store=PiUserStore(str(path), key))
    assert second.users["alice"].totp_secret == user.totp_secret
    assert second.users["root"].role is PiRole.ADMIN
    assert list(second.role_requests)[0] == request["request_id"]
    raw = path.read_bytes()
    assert user.totp_secret.encode("utf-8") not in raw


def test_pc_map_sync_is_https_bounded_and_read_only() -> None:
    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, limit: int) -> bytes:
            assert limit == 20_001
            return b'{"schema_version":"v1","data":{"items":[{"id":"z1","geometry":{"type":"Polygon","coordinates":[]}}]}}'

    calls: list[str] = []

    def opener(request, *, timeout: float):
        calls.append(f"{request.full_url}|{timeout}")
        return Response()

    client = PcMapSyncClient(PcMapSyncConfig("https://pc.example", timeout_seconds=2, stale_after_seconds=60, max_response_bytes=20_000), opener=opener)
    cache = MapCache()
    result = client.sync(cache)
    assert result["state"] == "AVAILABLE"
    assert result["payload"]["items"][0]["id"] == "z1"
    assert result["provenance"]["source_type"] == "PC_PUBLIC_API"
    assert calls == ["https://pc.example/api/v1/public/zones|2"]
    with pytest.raises(ValueError, match="HTTPS"):
        PcMapSyncConfig("http://pc.example").validate()


def test_firmware_status_is_admin_only_and_never_enables_flash() -> None:
    auth = PiAuthService(allow_inmemory_email=True)
    auth.add_user("root", "correct horse battery staple", role=PiRole.ADMIN, email="root@example.test")
    client = TestClient(create_pi_app(PiWebConfig(secure_cookies=False), auth=auth, camera=MockCameraAdapter()))
    assert client.get("/api/pi/v1/firmware/status").status_code == 401

    challenge = client.post("/api/pi/v1/auth/challenge", json={"username": "root", "password": "correct horse battery staple", "terms_accepted": True}).json()["data"]["challenge_id"]
    email_step = client.post("/api/pi/v1/auth/login", json={"challenge_id": challenge, "otp": auth.challenge_code_for_test(challenge)}).json()["data"]["mfa_challenge_id"]
    assert client.post("/api/pi/v1/auth/login", json={"mfa_challenge_id": email_step, "totp": auth.challenge_totp_for_test(email_step)}).status_code == 200

    status = client.get("/api/pi/v1/firmware/status")
    assert status.status_code == 200
    assert status.json()["data"]["state"] == "BLOCKED"
    assert status.json()["data"]["can_flash"] is False
    assert "reviewed_flash_execution_not_implemented" in status.json()["data"]["blockers"]


def test_firmware_readiness_never_authorizes_flash_from_inventory_alone(tmp_path) -> None:
    bundle = tmp_path / "vendor.signed.bin"
    key = tmp_path / "vendor.pub"
    rollback = tmp_path / "rollback.bin"
    approval = tmp_path / "approval.txt"
    device = tmp_path / "ttyUSB0"
    for path in (bundle, key, rollback, approval, device):
        path.write_bytes(b"configured")
    service = FirmwareReadiness(
        environ={
            "SCOPE07_ESP_DEVICE": str(device),
            "SCOPE07_VENDOR_PUBLIC_KEY": str(key),
            "SCOPE07_SIGNED_BUNDLE": str(bundle),
            "SCOPE07_EXPECTED_CHIP": "esp32",
            "SCOPE07_ROLLBACK_BUNDLE": str(rollback),
            "SCOPE07_SAFETY_APPROVAL_RECORD": str(approval),
        },
        executable_lookup=lambda _name: "esptool",
    )
    status = service.read()
    assert status["checks"]["vendor_public_key_file_present"] is True
    assert status["checks"]["firmware_bundle_file_present_unverified"] is True
    assert status["checks"]["cp210x_device_present"] is False
    assert status["can_flash"] is False
    assert status["state"] == "BLOCKED"
    assert "vendor_signature_and_manifest_verification_not_implemented" in status["blockers"]


def test_pi_hides_api_schema_and_interactive_docs() -> None:
    client = TestClient(create_pi_app(PiWebConfig(secure_cookies=False), camera=MockCameraAdapter()))

    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
