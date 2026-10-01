from __future__ import annotations

import pyotp
from fastapi.testclient import TestClient

from app.db import db
from app.main import app


def test_role_boundaries_csrf_and_command_lock(tmp_path):
    db.path = tmp_path / "test.sqlite3"
    db.initialize()
    secret = pyotp.random_base32()
    db.create_user("admin-test", "correct horse battery staple", "admin", secret)
    db.create_user("viewer-test", "correct horse battery staple", "user")

    with TestClient(app) as client:
        admin_login = client.post(
            "/api/v1/auth/login",
            json={"username": "admin-test", "password": "correct horse battery staple", "totp": pyotp.TOTP(secret).now()},
        )
        assert admin_login.status_code == 200
        csrf = admin_login.json()["csrf_token"]
        assert client.get("/api/v1/status").status_code == 200
        assert client.post("/api/v1/commands/land", headers={"X-CSRF-Token": csrf}).status_code == 423
        assert client.post("/api/v1/auth/logout").status_code == 403
        assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 200

        viewer_login = client.post(
            "/api/v1/auth/login",
            json={"username": "viewer-test", "password": "correct horse battery staple"},
        )
        assert viewer_login.status_code == 200
        assert client.get("/api/v1/camera/status").status_code == 200
        assert client.get("/api/v1/status").status_code == 403
        assert client.get("/api/v1/telemetry/latest").status_code == 403
        assert client.get("/api/v1/geofence/zones").status_code == 403

    db.set_password("viewer-test", "a different secure password")
    assert db.authenticate("viewer-test", "correct horse battery staple") is None
    assert db.authenticate("viewer-test", "a different secure password") is not None
    replacement_secret = pyotp.random_base32()
    db.set_totp_secret("admin-test", replacement_secret)
    assert db.authenticate("admin-test", "correct horse battery staple")["totp_secret"] == replacement_secret
