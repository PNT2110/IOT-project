from __future__ import annotations

from datetime import datetime
import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from server.app.config import Settings
from server.app.main import create_app
from server.app.models import Credential, User
from server.app.security import digest_token, hash_password, new_token, utcnow


@pytest.fixture()
def app(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'scope01.sqlite3'}"
    settings = Settings(
        app_env="test",
        database_url=db_url,
        session_secret=secrets.token_urlsafe(32),
        cookie_secure=False,
        allowed_origins=("http://testserver",),
        host="127.0.0.1",
        port=8765,
        enable_test_adapters=True,
    )
    application = create_app(settings, initialize_schema=True)
    with TestClient(application) as client:
        yield application, client


@pytest.fixture()
def admin_token(app):
    application, _ = app
    now = utcnow()
    with application.state.session_factory() as db:
        user = User(display_name="Fixture Admin", email_normalized="admin@sample.com", status="ACTIVE", role="ADMIN", email_verified_at=now, created_at=now, updated_at=now)
        user.credential = Credential(password_hash=hash_password(secrets.token_urlsafe(18)), totp_active=True, created_at=now, updated_at=now)
        db.add(user)
        db.flush()
        token = new_token()
        from server.app.models import SessionRecord
        db.add(SessionRecord(token_digest=digest_token(application.state.settings.session_secret, token), user_id=user.id, stage="AUTHENTICATED", csrf_digest=digest_token(application.state.settings.session_secret, "csrf"), expires_at=now.replace(year=now.year + 1), last_seen_at=now, created_at=now))
        db.commit()
    return token
