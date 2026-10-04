from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timezone

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from cryptography.fernet import Fernet


PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65_536, parallelism=2)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    """SQLite returns timezone-naive datetimes; interpret stored values as UTC."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


GMAIL_DOMAINS = {"gmail.com", "googlemail.com"}


def normalize_email(value: str) -> str:
    cleaned = value.strip().casefold()
    if "@" not in cleaned:
        return cleaned
    local_part, domain = cleaned.split("@", 1)
    local_part = local_part.split("+", 1)[0]
    if domain in GMAIL_DOMAINS:
        local_part = local_part.replace(".", "")
        domain = "gmail.com"
    return f"{local_part}@{domain}"


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return PASSWORD_HASHER.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


def digest_token(secret: str, token: str, salt: str = "") -> str:
    return hmac.new(secret.encode(), (salt + token).encode(), hashlib.sha256).hexdigest()


def new_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def new_recovery_code() -> str:
    return f"{secrets.token_hex(4)}-{secrets.token_hex(4)}"


def derive_fernet(secret: str) -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def encrypt_secret(secret_key: str, value: str) -> str:
    return derive_fernet(secret_key).encrypt(value.encode()).decode()


def decrypt_secret(secret_key: str, value: str) -> str:
    return derive_fernet(secret_key).decrypt(value.encode()).decode()


def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_at(secret: str, code: str, last_step: int | None = None) -> tuple[bool, int]:
    now = int(utcnow().timestamp())
    step = now // 30
    verifier = pyotp.TOTP(secret, interval=30)
    for candidate in (step - 1, step, step + 1):
        if last_step is not None and candidate <= last_step:
            continue
        if hmac.compare_digest(verifier.at(candidate * 30), code):
            return True, candidate
    return False, step
