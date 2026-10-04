from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from typing import Any, Generator

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PI_ROOT = PROJECT_ROOT / "edge" / "pi5"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from server.app.config import Settings
from server.app.device_crypto import seal
from server.app.main import create_app
from server.app.models import Credential, Device, SessionRecord, User, Zone, SimulatedFlightRequest
from server.app.security import digest_token, encrypt_secret, hash_password, new_token, utcnow

from pi5.web.app import PiWebConfig, create_pi_app
from pi5.web.auth import PiAuthService
from pi5.web.camera import MockCameraAdapter
from pi5.web.models import PiRole


@pytest.fixture()
def app_env(tmp_path: Path) -> Generator[tuple[Any, TestClient, Settings], None, None]:
    """Create a fully isolated PC Server instance with in-memory/temp SQLite."""
    db_path = tmp_path / "e2e_pc_server.sqlite3"
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{db_path}",
        session_secret=secrets.token_urlsafe(32),
        cookie_secure=False,
        allowed_origins=("http://testserver", "http://localhost:5173"),
        host="127.0.0.1",
        port=8765,
        enable_test_adapters=True,
    )
    application = create_app(settings, initialize_schema=True)
    with TestClient(application) as client:
        yield application, client, settings


@pytest.fixture()
def pc_client(app_env: tuple[Any, TestClient, Settings]) -> TestClient:
    return app_env[1]


@pytest.fixture()
def pc_app(app_env: tuple[Any, TestClient, Settings]) -> Any:
    return app_env[0]


@pytest.fixture()
def pc_settings(app_env: tuple[Any, TestClient, Settings]) -> Settings:
    return app_env[2]


def _create_user_with_session(app: Any, username: str, email: str, role: str) -> tuple[User, str]:
    now = utcnow()
    settings = app.state.settings
    with app.state.session_factory() as db:
        user = User(
            username=username,
            display_name=f"{username.capitalize()} User",
            email_normalized=email.lower().strip(),
            status="ACTIVE",
            role=role,
            version=1,
            email_verified_at=now,
            created_at=now,
            updated_at=now,
        )
        user.credential = Credential(
            password_hash=hash_password("E2E_Secure_Password_123!"),
            totp_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        db.flush()

        raw_token = new_token()
        session = SessionRecord(
            token_digest=digest_token(settings.session_secret, raw_token),
            user_id=user.id,
            stage="AUTHENTICATED",
            csrf_digest=digest_token(settings.session_secret, "e2e-csrf-token"),
            expires_at=now + timedelta(hours=8),
            last_seen_at=now,
            created_at=now,
        )
        db.add(session)
        db.commit()
        db.refresh(user)
        return user, raw_token


@pytest.fixture()
def operator_auth(pc_app: Any) -> dict[str, str]:
    _, token = _create_user_with_session(pc_app, "operator_e2e", "operator@example.test", "OPERATOR")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def pilot_auth(pc_app: Any) -> dict[str, str]:
    _, token = _create_user_with_session(pc_app, "pilot_e2e", "pilot@example.test", "PILOT")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_auth(pc_app: Any) -> dict[str, str]:
    _, token = _create_user_with_session(pc_app, "admin_e2e", "admin@example.test", "ADMIN")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def registered_device(pc_app: Any) -> dict[str, Any]:
    """Register a drone device on PC server and return ID and raw AES key."""
    settings = pc_app.state.settings
    raw_key = secrets.token_bytes(32)
    b64_key = base64.urlsafe_b64encode(raw_key).decode()
    encrypted_key = encrypt_secret(settings.session_secret, b64_key)
    
    with pc_app.state.session_factory() as db:
        device = Device(
            name="F450-Drone-Alpha",
            key_encrypted=encrypted_key,
            created_at=utcnow(),
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        return {
            "id": device.id,
            "name": device.name,
            "key": raw_key,
            "key_b64": b64_key,
        }


@pytest.fixture()
def pi_env(tmp_path: Path) -> Generator[tuple[TestClient, PiAuthService, MockCameraAdapter], None, None]:
    """Create Pi 5 Gateway TestClient with in-memory auth and mock camera."""
    auth = PiAuthService(allow_inmemory_email=True)
    auth.add_user("pi_operator", "pi_secret_password_123", role=PiRole.USER, email="pi@example.test")
    camera = MockCameraAdapter()
    config = PiWebConfig(secure_cookies=False)
    app = create_pi_app(config, auth=auth, camera=camera)
    with TestClient(app) as client:
        yield client, auth, camera


@pytest.fixture()
def pi_client(pi_env: tuple[TestClient, PiAuthService, MockCameraAdapter]) -> TestClient:
    return pi_env[0]


@pytest.fixture()
def pi_camera(pi_env: tuple[TestClient, PiAuthService, MockCameraAdapter]) -> MockCameraAdapter:
    return pi_env[2]


def make_sealed_envelope(
    key: bytes,
    device_id: str,
    payload: dict[str, Any],
    ts: int | None = None,
    nonce: bytes | None = None,
) -> dict[str, Any]:
    """Helper to create an authentic DeviceEnvelope."""
    now = int(time.time()) if ts is None else ts
    return seal(key, device_id, payload, now, nonce=nonce)
