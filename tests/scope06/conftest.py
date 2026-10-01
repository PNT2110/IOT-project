from __future__ import annotations

import base64
from datetime import timedelta
import secrets

import pytest
from fastapi.testclient import TestClient

from server.app.config import Settings
from server.app.main import create_app
from server.app.models import Credential, Device, SessionRecord, User
from server.app.security import digest_token, encrypt_secret, hash_password, new_token, utcnow


@pytest.fixture()
def app(tmp_path):
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{tmp_path / 'scope06.sqlite3'}",
        session_secret=secrets.token_urlsafe(32),
        cookie_secure=False,
        allowed_origins=("http://testserver",),
        host="127.0.0.1",
        port=8765,
    )
    application = create_app(settings, initialize_schema=True)
    with TestClient(application) as client:
        yield application, client


def _add_device(application, name: str) -> dict:
    key = secrets.token_bytes(32)
    with application.state.session_factory() as db:
        device = Device(name=name, key_encrypted=encrypt_secret(application.state.settings.session_secret, base64.urlsafe_b64encode(key).decode()), created_at=utcnow())
        db.add(device)
        db.commit()
        return {"id": device.id, "key": key}


@pytest.fixture()
def device(app):
    return _add_device(app[0], "pitan")


@pytest.fixture()
def other_device(app):
    return _add_device(app[0], "other-pi")


@pytest.fixture()
def operator(app):
    application, _ = app
    now = utcnow()
    with application.state.session_factory() as db:
        user = User(username="operator", display_name="Operator", email_normalized="operator@sample.com", status="ACTIVE", role="OPERATOR", version=1, email_verified_at=now, created_at=now, updated_at=now)
        user.credential = Credential(password_hash=hash_password(secrets.token_urlsafe(18)), totp_active=True, created_at=now, updated_at=now)
        db.add(user)
        db.flush()
        token = new_token()
        db.add(SessionRecord(token_digest=digest_token(application.state.settings.session_secret, token), user_id=user.id, stage="AUTHENTICATED", csrf_digest=digest_token(application.state.settings.session_secret, new_token()), expires_at=now + timedelta(hours=1), last_seen_at=now, created_at=now))
        db.commit()
    return {"Authorization": f"Bearer {token}"}
