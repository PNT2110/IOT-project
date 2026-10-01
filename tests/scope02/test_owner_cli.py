from __future__ import annotations

import argparse
from pathlib import Path

import pyotp
import pytest
from sqlalchemy import select

from server import cli
from server.app.config import Settings
from server.app.db import Base, make_engine, make_session_factory
from server.app.models import AuditEvent, Credential, EmailChallenge, User
from server.app.security import encrypt_secret, hash_password, utcnow, verify_password


@pytest.fixture()
def owner_cli(tmp_path, monkeypatch):
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{tmp_path / 'owner-cli.sqlite3'}",
        session_secret="isolated-owner-cli-test-key-" + "x" * 32,
        cookie_secure=False,
        allowed_origins=("http://testserver",),
        host="127.0.0.1",
        port=8765,
        fake_mail_outbox=str(tmp_path / "mail-outbox.jsonl"),
    )
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    monkeypatch.setattr(cli, "make_engine", lambda _url: engine)
    monkeypatch.setattr(cli, "make_session_factory", lambda _engine: factory)
    return settings, engine, factory


def test_bootstrap_owner_creates_pending_owner_and_sends_fake_verification(owner_cli, monkeypatch, capsys):
    settings, engine, factory = owner_cli
    answers = iter(["long-test-owner-password", "long-test-owner-password"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(answers))
    args = argparse.Namespace(name="Test Owner", email="Owner@Example.test")

    assert cli.bootstrap_owner(args) == 0

    with factory() as db:
        owner = db.scalar(select(User).where(User.email_normalized == "owner@example.test"))
        assert owner is not None
        assert owner.role == "OWNER"
        assert owner.status == "PENDING"
        assert owner.email_verified_at is None
        assert verify_password(owner.credential.password_hash, "long-test-owner-password")
        assert owner.credential.totp_active is False
        challenge = db.scalar(select(EmailChallenge).where(EmailChallenge.user_id == owner.id, EmailChallenge.purpose == "VERIFY_EMAIL"))
    outbox = Path(settings.fake_mail_outbox).read_text(encoding="utf-8")
    assert '"purpose": "VERIFY_EMAIL"' in outbox
    assert "long-test-owner-password" not in outbox
    console = capsys.readouterr().out
    assert f"#owner-bootstrap={challenge.id}" in console
    assert "long-test-owner-password" not in console
    engine.dispose()


@pytest.mark.parametrize("confirm", ["", "activate first owner", "ACTIVATE FIRST OWNER "])
def test_bootstrap_activation_rejects_wrong_confirmation(owner_cli, monkeypatch, confirm):
    _, engine, factory = owner_cli
    monkeypatch.setattr(cli, "load_settings", lambda: pytest.fail("settings loaded before confirmation"))
    with pytest.raises(SystemExit, match="exact confirmation phrase"):
        cli.activate_bootstrap_owner(argparse.Namespace(email="owner@example.test", confirm=confirm))
    engine.dispose()


def test_bootstrap_activation_requires_password_and_totp_then_audits(owner_cli, monkeypatch):
    settings, engine, factory = owner_cli
    secret = pyotp.random_base32()
    now = utcnow()
    with factory() as db:
        owner = User(display_name="Test Owner", email_normalized="owner@example.test", status="PENDING", role="OWNER", email_verified_at=now, created_at=now, updated_at=now)
        owner.credential = Credential(
            password_hash=hash_password("long-test-owner-password"),
            totp_secret_encrypted=encrypt_secret(settings.session_secret, secret),
            totp_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(owner)
        db.commit()

    current_code = pyotp.TOTP(secret).now()
    answers = iter(["long-test-owner-password", current_code])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(answers))
    args = argparse.Namespace(email="owner@example.test", confirm="ACTIVATE FIRST OWNER")

    assert cli.activate_bootstrap_owner(args) == 0
    with factory() as db:
        owner = db.scalar(select(User).where(User.email_normalized == "owner@example.test"))
        event = db.scalar(select(AuditEvent).where(AuditEvent.action == "LOCAL_BOOTSTRAP_ACTIVATION"))
        assert owner.status == "ACTIVE"
        assert event is not None
        assert event.outcome == "SUCCESS"
    engine.dispose()


@pytest.mark.parametrize("answers", [
    ["wrong-password", "000000"],
    ["long-test-owner-password", "000000"],
])
def test_bootstrap_activation_fails_closed_on_invalid_factors(owner_cli, monkeypatch, answers):
    settings, engine, factory = owner_cli
    secret = pyotp.random_base32()
    now = utcnow()
    with factory() as db:
        owner = User(display_name="Test Owner", email_normalized="owner@example.test", status="PENDING", role="OWNER", email_verified_at=now, created_at=now, updated_at=now)
        owner.credential = Credential(
            password_hash=hash_password("long-test-owner-password"),
            totp_secret_encrypted=encrypt_secret(settings.session_secret, secret),
            totp_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(owner)
        db.commit()
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: answers.pop(0))

    with pytest.raises(SystemExit, match="verification failed"):
        cli.activate_bootstrap_owner(argparse.Namespace(email="owner@example.test", confirm="ACTIVATE FIRST OWNER"))
    with factory() as db:
        owner = db.scalar(select(User).where(User.email_normalized == "owner@example.test"))
        assert owner.status == "PENDING"
        assert db.scalar(select(AuditEvent).where(AuditEvent.action == "LOCAL_BOOTSTRAP_ACTIVATION")) is None
    engine.dispose()


def test_bootstrap_activation_rejects_totp_step_already_used_for_enrollment(owner_cli, monkeypatch):
    settings, engine, factory = owner_cli
    secret = pyotp.random_base32()
    now = utcnow()
    current_step = int(now.timestamp()) // 30
    with factory() as db:
        owner = User(display_name="Test Owner", email_normalized="owner@example.test", status="PENDING", role="OWNER", email_verified_at=now, created_at=now, updated_at=now)
        owner.credential = Credential(
            password_hash=hash_password("long-test-owner-password"),
            totp_secret_encrypted=encrypt_secret(settings.session_secret, secret),
            totp_active=True,
            totp_last_step=current_step,
            created_at=now,
            updated_at=now,
        )
        db.add(owner)
        db.commit()
    answers = iter(["long-test-owner-password", pyotp.TOTP(secret).now()])
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt: next(answers))

    with pytest.raises(SystemExit, match="TOTP verification failed"):
        cli.activate_bootstrap_owner(argparse.Namespace(email="owner@example.test", confirm="ACTIVATE FIRST OWNER"))
    with factory() as db:
        owner = db.scalar(select(User).where(User.email_normalized == "owner@example.test"))
        assert owner.status == "PENDING"
        assert db.scalar(select(AuditEvent).where(AuditEvent.action == "LOCAL_BOOTSTRAP_ACTIVATION")) is None
    engine.dispose()


def test_seed_default_owner_idempotent(owner_cli, monkeypatch, capsys):
    from server.app.models import ZoneSource
    settings, engine, factory = owner_cli
    secret = pyotp.random_base32()
    monkeypatch.setenv("DEFAULT_OWNER_USERNAME", "Chief")
    monkeypatch.setenv("DEFAULT_OWNER_PASSWORD", "chief-test-password")
    monkeypatch.setenv("DEFAULT_OWNER_TOTP_SECRET", secret)
    assert cli.seed_default_owner(argparse.Namespace()) == 0
    monkeypatch.setenv("DEFAULT_OWNER_PASSWORD", "another-password-entirely")
    assert cli.seed_default_owner(argparse.Namespace()) == 0
    with factory() as db:
        owners = db.scalars(select(User).where(User.role == "OWNER")).all()
        assert len(owners) == 1
        owner = owners[0]
        assert owner.username == "chief" and owner.status == "ACTIVE" and owner.email_normalized is None
        assert owner.credential.totp_active is True
        assert verify_password(owner.credential.password_hash, "chief-test-password")
        sources = db.scalars(select(ZoneSource).where(ZoneSource.source_type == "OPERATOR_DRAWN")).all()
        assert len(sources) == 1
    console = capsys.readouterr().out
    assert secret not in console and "chief-test-password" not in console


def test_seed_default_owner_rejects_missing_env(owner_cli, monkeypatch):
    monkeypatch.delenv("DEFAULT_OWNER_PASSWORD", raising=False)
    monkeypatch.setenv("DEFAULT_OWNER_USERNAME", "chief")
    monkeypatch.setenv("DEFAULT_OWNER_TOTP_SECRET", pyotp.random_base32())
    with pytest.raises(SystemExit):
        cli.seed_default_owner(argparse.Namespace())
