from __future__ import annotations

import getpass
import os
import re
import sys

import pyotp

from .web.auth import PiAuthService
from .web.models import PiRole
from .web.persistence import PiUserStore, store_from_env


def provision_first_admin(
    store: PiUserStore,
    username: str,
    password: str,
    *,
    totp_secret: str | None = None,
    min_password_length: int = 12,
):
    """Create the one-time local Pi admin without embedding default credentials."""

    normalized_username = username.strip().casefold()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,63}", normalized_username):
        raise ValueError("Admin username must be 3 to 64 letters, digits, dots, underscores, or hyphens")
    if len(password) < min_password_length or len(password) > 128:
        raise ValueError(f"Admin password must contain {min_password_length} to 128 characters")
    if store.load_users():
        raise ValueError("First-admin bootstrap is allowed only for an empty Pi account store")

    secret = totp_secret or pyotp.random_base32()
    service = PiAuthService(store=store)
    user = service.add_user(
        normalized_username,
        password,
        role=PiRole.ADMIN,
        totp_secret=secret,
        email="",
    )
    return user


def seed_default_admin(store: PiUserStore, environ: dict[str, str] | None = None) -> bool:
    """Create the default Pi admin from the environment; a no-op once any account exists.

    The account has the configured 2FA secret and no email: the first login
    asks for one, and every later login needs the email OTP.
    """
    env = os.environ if environ is None else environ
    if store.load_users():
        return False
    secret = env.get("PI_DEFAULT_ADMIN_TOTP_SECRET", "").strip()
    if len(secret) < 16:
        raise ValueError("PI_DEFAULT_ADMIN_TOTP_SECRET must be a base32 secret of at least 16 characters")
    pyotp.TOTP(secret).now()
    provision_first_admin(store, env.get("PI_DEFAULT_ADMIN_USERNAME", ""), env.get("PI_DEFAULT_ADMIN_PASSWORD", ""), totp_secret=secret, min_password_length=6)
    return True


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "seed-default-admin":
        try:
            store = store_from_env()
            if store is None:
                raise ValueError("Set PI_AUTH_DB_PATH and PI_DATA_KEY before seeding the Pi admin")
            created = seed_default_admin(store)
        except Exception as exc:
            print(f"Seed failed: {exc}", file=sys.stderr)
            return 1
        print("Default Pi admin created." if created else "Pi accounts already exist; nothing changed.")
        return 0
    if len(sys.argv) != 2 or sys.argv[1] != "bootstrap-admin":
        print("Usage: python -m pi5.cli bootstrap-admin | seed-default-admin")
        return 2
    try:
        store = store_from_env()
        if store is None:
            raise ValueError("Set PI_AUTH_DB_PATH and PI_DATA_KEY before bootstrapping the Pi admin")
        username = input("First Pi admin username: ").strip()
        password = getpass.getpass("New admin password (12+ characters): ")
        confirmation = getpass.getpass("Repeat admin password: ")
        if password != confirmation:
            raise ValueError("Passwords do not match")
        user = provision_first_admin(store, username, password)
    except (RuntimeError, ValueError) as exc:
        print(f"Bootstrap failed: {exc}", file=sys.stderr)
        return 1

    issuer = "F450 PNT PVD Pi 5"
    account = user.username
    uri = pyotp.TOTP(user.totp_secret).provisioning_uri(name=account, issuer_name=issuer)
    print("First Pi admin created. No email is attached yet; configure it through the first-login email setup flow.")
    print("Save this TOTP secret now; it is not printed again:")
    print(user.totp_secret)
    print("Authenticator setup URI:")
    print(uri)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
