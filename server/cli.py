from __future__ import annotations

import argparse
import base64
import getpass
import os
import re
import secrets
import uuid

import pyotp
from sqlalchemy import select

from server.app.config import load_settings
from server.app.db import make_engine, make_session_factory
from server.app.mail import FakeEmailSender, email_sender_for_settings
from server.app.models import Credential, Device, User, ZoneSource
from server.app.security import decrypt_secret, encrypt_secret, hash_password, normalize_email, totp_at, utcnow, verify_password
from server.app.services import create_email_code, record_audit, record_history


def bootstrap_owner(args: argparse.Namespace) -> int:
    settings = load_settings()
    engine = make_engine(settings.database_url)
    factory = make_session_factory(engine)
    mail = email_sender_for_settings(settings)
    if isinstance(mail, FakeEmailSender) and not settings.fake_mail_outbox:
        raise SystemExit("FAKE_MAIL_OUTBOX is required for a test/development owner bootstrap")
    email = normalize_email(args.email)
    password = getpass.getpass("Owner password (hidden): ")
    confirm = getpass.getpass("Repeat owner password (hidden): ")
    if password != confirm or len(password) < 12:
        raise SystemExit("passwords must match and be at least 12 characters")
    with factory() as db:
        if db.scalar(select(User).where(User.role == "OWNER")):
            raise SystemExit("owner bootstrap has already been used")
        now = utcnow()
        user = User(display_name=args.name, email_normalized=email, status="PENDING", role="OWNER", created_at=now, updated_at=now)
        user.credential = Credential(password_hash=hash_password(password), created_at=now, updated_at=now)
        db.add(user)
        db.flush()
        challenge = create_email_code(db, settings, mail, user_id=user.id, email=email, purpose="VERIFY_EMAIL")
        db.commit()
    engine.dispose()
    setup_url = f"{settings.allowed_origins[0].rstrip('/')}/#owner-bootstrap={challenge.id}"
    print(f"Owner record created in PENDING state; verification challenge: {challenge.id}")
    print(f"Open this link after receiving the email OTP to verify and enroll MFA: {setup_url}")
    if isinstance(mail, FakeEmailSender):
        print(f"Test-only fake verification mail written to {settings.fake_mail_outbox}.")
    print("After MFA enrollment, restart the Windows launcher with -ActivateBootstrapOwner; the account remains PENDING until that operator step succeeds.")
    return 0


def activate_bootstrap_owner(args: argparse.Namespace) -> int:
    if args.confirm != "ACTIVATE FIRST OWNER":
        raise SystemExit("exact confirmation phrase is required")
    settings = load_settings()
    engine = make_engine(settings.database_url)
    factory = make_session_factory(engine)
    email = normalize_email(args.email)
    password = getpass.getpass("Existing owner password (hidden): ")
    totp_code = getpass.getpass("Current owner TOTP code (hidden): ")
    request_id = f"cli-{uuid.uuid4()}"
    with factory() as db:
        owner = db.scalar(select(User).where(User.email_normalized == email, User.role == "OWNER"))
        if not owner or owner.status != "PENDING":
            raise SystemExit("no pending bootstrap owner found")
        if not owner.email_verified_at or not owner.credential or not owner.credential.totp_active:
            raise SystemExit("owner email verification and MFA must be complete first")
        if not verify_password(owner.credential.password_hash, password):
            raise SystemExit("owner password verification failed")
        secret = decrypt_secret(settings.session_secret, owner.credential.totp_secret_encrypted or "")
        valid, step = totp_at(secret, totp_code, owner.credential.totp_last_step)
        if not valid:
            raise SystemExit("owner TOTP verification failed")
        old_version = owner.version
        owner.status = "ACTIVE"
        owner.version += 1
        owner.updated_at = utcnow()
        now = utcnow()
        owner.credential.totp_last_step = step
        owner.credential.updated_at = now
        record_audit(db, actor_user_id=None, action="LOCAL_BOOTSTRAP_ACTIVATION", object_type="USER", object_id=owner.id, outcome="SUCCESS", request_id=request_id, metadata={"from_status": "PENDING", "to_status": "ACTIVE", "operator_confirmation": True})
        record_history(db, actor_user_id=None, object_type="USER", object_id=owner.id, action="LOCAL_BOOTSTRAP_ACTIVATION", from_state="PENDING", to_state="ACTIVE", from_version=old_version, to_version=owner.version, reason="Local operator confirmation and MFA", request_id=request_id, metadata={"operator_confirmation": True})
        db.commit()
    engine.dispose()
    print("Bootstrap owner activated through the explicit local operator procedure.")
    return 0


def seed_default_owner(args: argparse.Namespace) -> int:
    """Create the default main account from the local environment, once."""
    username = os.getenv("DEFAULT_OWNER_USERNAME", "").strip().casefold()
    password = os.getenv("DEFAULT_OWNER_PASSWORD", "")
    totp_secret = os.getenv("DEFAULT_OWNER_TOTP_SECRET", "").strip()
    if not re.fullmatch(r"[a-z0-9_.-]{3,32}", username):
        raise SystemExit("DEFAULT_OWNER_USERNAME must be 3-32 characters of a-z 0-9 _ . -")
    if len(password) < 6:
        raise SystemExit("DEFAULT_OWNER_PASSWORD must be set (at least 6 characters)")
    try:
        pyotp.TOTP(totp_secret).now()
    except Exception as exc:
        raise SystemExit("DEFAULT_OWNER_TOTP_SECRET must be a base32 TOTP secret") from exc
    if len(totp_secret) < 16:
        raise SystemExit("DEFAULT_OWNER_TOTP_SECRET must be at least 16 base32 characters")
    settings = load_settings()
    engine = make_engine(settings.database_url)
    factory = make_session_factory(engine)
    with factory() as db:
        now = utcnow()
        if not db.scalar(select(ZoneSource).where(ZoneSource.source_type == "OPERATOR_DRAWN")):
            db.add(ZoneSource(publisher="Vùng do cán bộ vẽ", source_type="OPERATOR_DRAWN", license_name="Nội bộ", checksum="operator-drawn", retrieved_at=now))
        if db.scalar(select(User).where(User.role == "OWNER")):
            db.commit()
            print("Default owner already exists; nothing changed.")
        else:
            user = User(username=username, display_name=username, email_normalized=None, status="ACTIVE", role="OWNER", created_at=now, updated_at=now)
            user.credential = Credential(password_hash=hash_password(password), totp_secret_encrypted=encrypt_secret(settings.session_secret, totp_secret), totp_active=True, created_at=now, updated_at=now)
            db.add(user)
            db.flush()
            record_audit(db, actor_user_id=None, action="LOCAL_DEFAULT_OWNER_SEED", object_type="USER", object_id=user.id, outcome="SUCCESS", request_id=f"cli-{uuid.uuid4()}")
            db.commit()
            print(f"Default owner {username!r} created (ACTIVE, TOTP from DEFAULT_OWNER_TOTP_SECRET, no email).")
    engine.dispose()
    return 0


def add_device(args: argparse.Namespace) -> int:
    """Register a Pi and print its id and key once, for the Pi environment file."""
    settings = load_settings()
    engine = make_engine(settings.database_url)
    factory = make_session_factory(engine)
    key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    with factory() as db:
        if db.scalar(select(Device).where(Device.name == args.name)):
            raise SystemExit(f"device {args.name!r} already exists")
        device = Device(name=args.name, key_encrypted=encrypt_secret(settings.session_secret, key), created_at=utcnow())
        db.add(device)
        db.commit()
        print(f"PI_DEVICE_ID={device.id}")
        print(f"PI_DEVICE_KEY={key}")
    engine.dispose()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Local-only PC administration")
    sub = parser.add_subparsers(dest="command", required=True)
    owner = sub.add_parser("bootstrap-owner")
    owner.add_argument("--name", required=True)
    owner.add_argument("--email", required=True)
    owner.set_defaults(func=bootstrap_owner)
    activate = sub.add_parser("activate-bootstrap-owner")
    activate.add_argument("--email", required=True)
    activate.add_argument("--confirm", required=True)
    activate.set_defaults(func=activate_bootstrap_owner)
    sub.add_parser("seed-default-owner").set_defaults(func=seed_default_owner)
    device = sub.add_parser("add-device")
    device.add_argument("--name", required=True)
    device.set_defaults(func=add_device)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
