from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import smtplib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Callable

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from .models import PiRole
from .persistence import PiUserStore, store_from_env


PASSWORD_HASHER = PasswordHasher(time_cost=2, memory_cost=32_768, parallelism=2)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def smtp_sender_from_env() -> Callable[[str, str, str], None] | None:
    """Build an explicit SMTP OTP sender; return None when Pi SMTP is unset."""

    host = os.getenv("PI_SMTP_HOST")
    sender = os.getenv("PI_SMTP_FROM")
    if not host or not sender:
        return None
    port = int(os.getenv("PI_SMTP_PORT", "587"))
    username = os.getenv("PI_SMTP_USERNAME")
    password = os.getenv("PI_SMTP_PASSWORD", "")

    def send(recipient: str, purpose: str, code: str) -> None:
        message = EmailMessage()
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = "F450 PNT PVD - mã xác nhận"
        message.set_content(f"Mã xác nhận trên trạm Pi 5 của bạn là {code}.\nMã hết hạn sau ít phút và chỉ dùng một lần. Nếu bạn không yêu cầu mã này, hãy bỏ qua thư.")
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)

    return send


@dataclass
class PiUser:
    user_id: str
    username: str
    password_hash: str
    role: PiRole
    totp_secret: str
    active: bool = True
    email: str = ""
    email_verified: bool = True
    totp_active: bool = True
    full_name: str = ""
    license_code: str = ""
    license_class: str = ""
    license_expiry: str = ""


@dataclass(frozen=True)
class PiSession:
    session_id: str
    user_id: str
    token_digest: str
    csrf_digest: str
    expires_at: datetime
    created_at: datetime


class PiAuthError(Exception):
    def __init__(self, code: str, message: str = "Authentication failed") -> None:
        super().__init__(message)
        self.code = code


class PiAuthService:
    """Pi-local identity domain with staged email and TOTP enrollment.

    It deliberately has no PC session, federation, actuator or synchronization
    path. Production persistence remains a separate deployment gate; tests use
    the same service with ephemeral data.
    """

    def __init__(self, *, session_ttl_minutes: int = 30, max_failures: int = 5, email_sender: Callable[[str, str, str], None] | None = None, allow_inmemory_email: bool = False, store: PiUserStore | None = None) -> None:
        self.users: dict[str, PiUser] = {}
        self.sessions: dict[str, PiSession] = {}
        self._credentials: dict[str, tuple[str, str]] = {}
        self.challenges: dict[str, tuple[str, str, datetime]] = {}
        self.mfa_challenges: dict[str, tuple[str, datetime]] = {}
        self._last_totp_step: dict[str, int] = {}
        self.email_challenges: dict[str, tuple[str, str, datetime, int]] = {}
        self.email_setup_challenges: dict[str, tuple[str, str, str, datetime, int]] = {}
        self.enrollments: dict[str, tuple[str, datetime]] = {}
        self.enrollment_attempts: dict[str, int] = {}
        self.profile_challenges: dict[str, dict[str, object]] = {}
        self.email_sender = email_sender
        self.allow_inmemory_email = allow_inmemory_email
        self.store = store
        self._test_email_codes: dict[str, str] = {}
        self._test_profile_new_email_codes: dict[str, str] = {}
        self.registration_attempts: dict[str, tuple[int, datetime]] = {}
        self.registration_window = timedelta(minutes=15)
        self.max_registration_attempts = 5
        self.email_setup_attempts: dict[str, tuple[int, datetime]] = {}
        self.auth_challenge_attempts: dict[str, tuple[int, datetime]] = {}
        self.otp_resend_attempts: dict[str, tuple[int, datetime]] = {}
        self.auth_attempt_window = timedelta(minutes=15)
        self.max_auth_challenge_attempts = 10
        self.max_otp_resends = 5
        self.failures: dict[str, tuple[int, datetime]] = {}
        self.audit_events: list[dict[str, str]] = []
        self.role_requests: dict[str, dict[str, str]] = {}
        self.session_ttl = timedelta(minutes=session_ttl_minutes)
        self.max_failures = max_failures
        if self.store:
            for record in self.store.load_users():
                user = PiUser(**record)
                self.users[user.username] = user
            for item in self.store.load_role_requests():
                self.role_requests[item["request_id"]] = {key: value for key, value in item.items() if value is not None}

    @classmethod
    def from_env(cls, **kwargs: object) -> "PiAuthService":
        return cls(store=store_from_env(), **kwargs)

    def _save_user(self, user: PiUser) -> None:
        if self.store:
            self.store.save_user(user)

    @staticmethod
    def _key(value: str) -> str:
        return value.strip().casefold()

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def add_user(self, username: str, password: str, *, role: PiRole = PiRole.USER, totp_secret: str | None = None, email: str = "") -> PiUser:
        key = self._key(username)
        if not key or key in self.users:
            raise ValueError("username is unavailable")
        user = PiUser(
            user_id=secrets.token_hex(8),
            username=key,
            password_hash=PASSWORD_HASHER.hash(password),
            role=role,
            totp_secret=totp_secret or pyotp.random_base32(),
            email=email.strip().casefold(),
        )
        self.users[key] = user
        try:
            self._save_user(user)
        except Exception:
            self.users.pop(key, None)
            raise
        return user

    def register(self, username: str, email: str, password: str, password_confirm: str, *, client_key: str = "local") -> str:
        now = _now()
        count, reset_at = self.registration_attempts.get(client_key, (0, now))
        if reset_at <= now:
            count, reset_at = 0, now + self.registration_window
        if count >= self.max_registration_attempts:
            raise PiAuthError("RATE_LIMITED", "Too many registration attempts")
        self.registration_attempts[client_key] = (count + 1, reset_at)
        key = self._key(username)
        email_key = self._key(email)
        if len(key) < 3 or len(key) > 64 or "@" not in email_key:
            raise PiAuthError("REGISTRATION_INVALID")
        if len(password) < 12 or len(password) > 128 or password != password_confirm:
            raise PiAuthError("REGISTRATION_INVALID")
        if key in self.users or any(user.email == email_key for user in self.users.values() if user.email):
            raise PiAuthError("REGISTRATION_UNAVAILABLE")
        if self.email_sender is None and not self.allow_inmemory_email:
            raise PiAuthError("EMAIL_DELIVERY_UNAVAILABLE")
        user = PiUser(
            user_id=secrets.token_hex(8),
            username=key,
            password_hash=PASSWORD_HASHER.hash(password),
            role=PiRole.USER,
            totp_secret=pyotp.random_base32(),
            active=False,
            email=email_key,
            email_verified=False,
            totp_active=False,
        )
        self.users[key] = user
        try:
            self._save_user(user)
        except Exception:
            self.users.pop(key, None)
            raise PiAuthError("PERSISTENCE_FAILED")
        challenge_id = secrets.token_urlsafe(18)
        code = f"{secrets.randbelow(1_000_000):06d}"
        self.email_challenges[challenge_id] = (key, code, _now() + timedelta(minutes=10), 0)
        self._test_email_codes[challenge_id] = code
        if self.email_sender is None:
            # Tests may inspect the code through the explicit test-only hook;
            # the production ASGI entry point supplies SMTP when configured.
            self._audit("REGISTRATION_EMAIL_QUEUED", key, "local")
        else:
            try:
                self.email_sender(email_key, "PI_REGISTER", code)
            except Exception as exc:
                self.users.pop(key, None)
                if self.store:
                    self.store.delete_user(key)
                self.email_challenges.pop(challenge_id, None)
                self._test_email_codes.pop(challenge_id, None)
                raise PiAuthError("EMAIL_DELIVERY_FAILED") from exc
        return challenge_id

    def start_email_setup(self, username: str, password: str, email: str, *, client_key: str = "local") -> str:
        now = _now()
        count, reset_at = self.email_setup_attempts.get(client_key, (0, now))
        if reset_at <= now:
            count, reset_at = 0, now + self.auth_attempt_window
        if count >= self.max_registration_attempts:
            raise PiAuthError("RATE_LIMITED", "Too many email setup attempts")
        self.email_setup_attempts[client_key] = (count + 1, reset_at)
        key = self._key(username)
        user = self.users.get(key)
        if not user or not user.active or not self._verify_password(user, password):
            raise PiAuthError("AUTHENTICATION_FAILED")
        if user.email:
            raise PiAuthError("EMAIL_ALREADY_CONFIGURED")
        email_key = self._key(email)
        if len(email_key) < 5 or len(email_key) > 320 or "@" not in email_key or any(candidate.email == email_key for candidate in self.users.values() if candidate.email):
            raise PiAuthError("EMAIL_INVALID")
        if self.email_sender is None and not self.allow_inmemory_email:
            raise PiAuthError("EMAIL_DELIVERY_UNAVAILABLE")
        challenge_id = secrets.token_urlsafe(18)
        code = f"{secrets.randbelow(1_000_000):06d}"
        self.email_setup_challenges[challenge_id] = (key, email_key, code, _now() + timedelta(minutes=10), 0)
        self._test_email_codes[challenge_id] = code
        if self.email_sender is None:
            self._audit("EMAIL_SETUP_QUEUED", key, client_key)
        else:
            try:
                self.email_sender(email_key, "PI_EMAIL_SETUP", code)
            except Exception as exc:
                self.email_setup_challenges.pop(challenge_id, None)
                self._test_email_codes.pop(challenge_id, None)
                raise PiAuthError("EMAIL_DELIVERY_FAILED") from exc
        return challenge_id

    def verify_email_setup(self, challenge_id: str, code: str) -> PiUser:
        item = self.email_setup_challenges.get(challenge_id)
        if not item or item[3] <= _now() or item[4] >= 5:
            raise PiAuthError("CHALLENGE_INVALID")
        username, email, expected, expires, attempts = item
        if not hmac.compare_digest(expected, str(code)):
            self.email_setup_challenges[challenge_id] = (username, email, expected, expires, attempts + 1)
            raise PiAuthError("CODE_INVALID")
        user = self.users.get(username)
        if not user or user.email:
            raise PiAuthError("CHALLENGE_INVALID")
        user.email = email
        user.email_verified = True
        try:
            self._save_user(user)
        except Exception as exc:
            user.email = ""
            raise PiAuthError("PERSISTENCE_FAILED") from exc
        self.email_setup_challenges.pop(challenge_id, None)
        self._test_email_codes.pop(challenge_id, None)
        self._audit("EMAIL_SETUP_CONFIRMED", user.username, "local")
        return user

    def email_code_for_test(self, challenge_id: str, *, step: str = "current") -> str:
        try:
            if step == "new_email":
                return self._test_profile_new_email_codes[challenge_id]
            return self._test_email_codes[challenge_id]
        except KeyError as exc:
            raise PiAuthError("CHALLENGE_NOT_FOUND") from exc

    def _check_otp_resend_limit(self, key: str) -> None:
        now = _now()
        count, reset_at = self.otp_resend_attempts.get(key, (0, now))
        if reset_at <= now:
            count, reset_at = 0, now + self.auth_attempt_window
        if count >= self.max_otp_resends:
            raise PiAuthError("RATE_LIMITED", "Too many OTP resend attempts")
        self.otp_resend_attempts[key] = (count + 1, reset_at)

    def resend_registration_otp(self, challenge_id: str, *, client_key: str = "local") -> str:
        item = self.email_challenges.get(challenge_id)
        if not item:
            raise PiAuthError("CHALLENGE_INVALID")
        username, _, _, _ = item
        user = self.users.get(username)
        if not user or user.active or user.email_verified:
            raise PiAuthError("CHALLENGE_INVALID")
        self._check_otp_resend_limit(f"registration:{user.user_id}")
        new_challenge_id = secrets.token_urlsafe(18)
        code = f"{secrets.randbelow(1_000_000):06d}"
        self._test_email_codes[new_challenge_id] = code
        try:
            if self.email_sender is None:
                if not self.allow_inmemory_email:
                    raise PiAuthError("EMAIL_DELIVERY_UNAVAILABLE")
                self._audit("REGISTRATION_EMAIL_RESEND_QUEUED", username, client_key)
            else:
                self.email_sender(user.email, "PI_REGISTER", code)
        except PiAuthError:
            self._test_email_codes.pop(new_challenge_id, None)
            raise
        except Exception as exc:
            self._test_email_codes.pop(new_challenge_id, None)
            raise PiAuthError("EMAIL_DELIVERY_FAILED") from exc
        self.email_challenges.pop(challenge_id, None)
        self._test_email_codes.pop(challenge_id, None)
        self.email_challenges[new_challenge_id] = (username, code, _now() + timedelta(minutes=10), 0)
        return new_challenge_id

    def resend_login_otp(self, challenge_id: str, *, client_key: str = "local") -> str:
        item = self.challenges.get(challenge_id)
        if not item:
            raise PiAuthError("CHALLENGE_INVALID")
        username, _, _ = item
        user = self.users.get(username)
        if not user or not user.active or not user.email_verified or not user.totp_active or not user.email:
            raise PiAuthError("CHALLENGE_INVALID")
        self._check_otp_resend_limit(f"login:{user.user_id}")
        new_challenge_id = secrets.token_urlsafe(18)
        code = f"{secrets.randbelow(1_000_000):06d}"
        self._test_email_codes[new_challenge_id] = code
        try:
            if self.email_sender is None:
                if not self.allow_inmemory_email:
                    raise PiAuthError("EMAIL_DELIVERY_UNAVAILABLE")
                self._audit("LOGIN_EMAIL_RESEND_QUEUED", username, client_key)
            else:
                self.email_sender(user.email, "PI_LOGIN", code)
        except PiAuthError:
            self._test_email_codes.pop(new_challenge_id, None)
            raise
        except Exception as exc:
            self._test_email_codes.pop(new_challenge_id, None)
            raise PiAuthError("EMAIL_DELIVERY_FAILED") from exc
        self.challenges.pop(challenge_id, None)
        self._test_email_codes.pop(challenge_id, None)
        self.challenges[new_challenge_id] = (username, code, _now() + timedelta(minutes=5))
        return new_challenge_id

    def resend_email_setup_otp(self, challenge_id: str, *, client_key: str = "local") -> str:
        item = self.email_setup_challenges.get(challenge_id)
        if not item:
            raise PiAuthError("CHALLENGE_INVALID")
        username, email, _, _, _ = item
        user = self.users.get(username)
        if not user or not user.active or user.email:
            raise PiAuthError("CHALLENGE_INVALID")
        self._check_otp_resend_limit(f"email-setup:{user.user_id}")
        new_challenge_id = secrets.token_urlsafe(18)
        code = f"{secrets.randbelow(1_000_000):06d}"
        self._test_email_codes[new_challenge_id] = code
        try:
            if self.email_sender is None:
                if not self.allow_inmemory_email:
                    raise PiAuthError("EMAIL_DELIVERY_UNAVAILABLE")
                self._audit("EMAIL_SETUP_RESEND_QUEUED", username, client_key)
            else:
                self.email_sender(email, "PI_EMAIL_SETUP", code)
        except PiAuthError:
            self._test_email_codes.pop(new_challenge_id, None)
            raise
        except Exception as exc:
            self._test_email_codes.pop(new_challenge_id, None)
            raise PiAuthError("EMAIL_DELIVERY_FAILED") from exc
        self.email_setup_challenges.pop(challenge_id, None)
        self._test_email_codes.pop(challenge_id, None)
        self.email_setup_challenges[new_challenge_id] = (username, email, code, _now() + timedelta(minutes=10), 0)
        return new_challenge_id

    def verify_registration_email(self, challenge_id: str, code: str) -> str:
        item = self.email_challenges.get(challenge_id)
        if not item or item[2] <= _now() or item[3] >= 5:
            raise PiAuthError("CHALLENGE_INVALID")
        username, expected, expires, attempts = item
        if not hmac.compare_digest(expected, str(code)):
            self.email_challenges[challenge_id] = (username, expected, expires, attempts + 1)
            raise PiAuthError("CODE_INVALID")
        user = self.users.get(username)
        if not user:
            raise PiAuthError("CHALLENGE_INVALID")
        user.email_verified = True
        try:
            self._save_user(user)
        except Exception as exc:
            user.email_verified = False
            raise PiAuthError("PERSISTENCE_FAILED") from exc
        token = secrets.token_urlsafe(32)
        self.enrollments[token] = (user.user_id, _now() + timedelta(minutes=10))
        del self.email_challenges[challenge_id]
        self._test_email_codes.pop(challenge_id, None)
        return token

    def _enrollment_user(self, token: str) -> PiUser:
        item = self.enrollments.get(token)
        if not item or item[1] <= _now():
            raise PiAuthError("ENROLLMENT_INVALID")
        user = next((candidate for candidate in self.users.values() if candidate.user_id == item[0]), None)
        if not user or not user.email_verified:
            raise PiAuthError("ENROLLMENT_INVALID")
        return user

    def enrollment_details(self, token: str) -> tuple[PiUser, str]:
        user = self._enrollment_user(token)
        return user, user.totp_secret

    def confirm_registration_mfa(self, token: str, code: str) -> PiUser:
        user = self._enrollment_user(token)
        attempts = self.enrollment_attempts.get(token, 0)
        if attempts >= self.max_failures:
            raise PiAuthError("RATE_LIMITED", "Too many MFA attempts")
        valid = pyotp.TOTP(user.totp_secret).verify(str(code), valid_window=1)
        if not valid:
            self.enrollment_attempts[token] = attempts + 1
            if attempts + 1 >= self.max_failures:
                raise PiAuthError("RATE_LIMITED", "Too many MFA attempts")
            raise PiAuthError("TOTP_INVALID")
        old_totp_active, old_active = user.totp_active, user.active
        user.totp_active = True
        user.active = True
        try:
            self._save_user(user)
        except Exception as exc:
            user.totp_active, user.active = old_totp_active, old_active
            raise PiAuthError("PERSISTENCE_FAILED") from exc
        self.enrollments.pop(token, None)
        self.enrollment_attempts.pop(token, None)
        self._audit("REGISTRATION_MFA_CONFIRMED", user.username, "local")
        return user

    def _verify_password(self, user: PiUser, password: str) -> bool:
        try:
            return PASSWORD_HASHER.verify(user.password_hash, password)
        except (VerifyMismatchError, VerificationError):
            return False

    @staticmethod
    def _factor_key(user: PiUser | str) -> str:
        """Use the account as the MFA throttle key, not a client IP alone."""

        return user.user_id if isinstance(user, PiUser) else user

    def _active_factor_failures(self, factor_key: str) -> int:
        """Return the current account-factor failure count and expire lockouts.

        The previous implementation checked ``count >= max_failures`` without
        considering the expiry timestamp, which permanently locked an account
        after the first full lockout window.  Lockouts are intentionally
        temporary; once the window has elapsed the next authentication starts
        with a clean factor budget.
        """

        state = self.failures.get(factor_key)
        if not state:
            return 0
        count, blocked_until = state
        if blocked_until <= _now():
            self.failures.pop(factor_key, None)
            return 0
        return count

    def start_challenge(self, username: str, password: str, *, client_key: str = "local") -> str:
        now = _now()
        count, reset_at = self.auth_challenge_attempts.get(client_key, (0, now))
        if reset_at <= now:
            count, reset_at = 0, now + self.auth_attempt_window
        if count >= self.max_auth_challenge_attempts:
            raise PiAuthError("RATE_LIMITED", "Too many authentication attempts")
        self.auth_challenge_attempts[client_key] = (count + 1, reset_at)
        key = self._key(username)
        user = self.users.get(key)
        if not user or not user.active or not user.email_verified or not user.totp_active or not self._verify_password(user, password):
            self._audit("LOGIN_FAILURE", key, client_key)
            raise PiAuthError("AUTHENTICATION_FAILED")
        if not user.email:
            raise PiAuthError("EMAIL_SETUP_REQUIRED")
        if self.email_sender is None and not self.allow_inmemory_email:
            raise PiAuthError("EMAIL_DELIVERY_UNAVAILABLE")
        if self.email_sender is not None and not user.email:
            raise PiAuthError("EMAIL_DELIVERY_UNAVAILABLE")
        factor_key = self._factor_key(user)
        if self._active_factor_failures(factor_key) >= self.max_failures:
            raise PiAuthError("RATE_LIMITED", "Too many authentication attempts")
        challenge_id = secrets.token_urlsafe(18)
        otp = f"{secrets.randbelow(1_000_000):06d}"
        self.challenges[challenge_id] = (key, otp, _now() + timedelta(minutes=5))
        self._test_email_codes[challenge_id] = otp
        if self.email_sender is None:
            self._audit("LOGIN_EMAIL_QUEUED", key, "local")
        else:
            try:
                self.email_sender(user.email, "PI_LOGIN", otp)
            except Exception as exc:
                self.challenges.pop(challenge_id, None)
                self._test_email_codes.pop(challenge_id, None)
                raise PiAuthError("EMAIL_DELIVERY_FAILED") from exc
        self._audit("LOGIN_CHALLENGE", key, client_key)
        return challenge_id

    def challenge_code_for_test(self, challenge_id: str) -> str:
        """Test-only inspection hook; never exposed by the web API or audit log."""
        item = self.challenges.get(challenge_id)
        if not item:
            raise PiAuthError("CHALLENGE_NOT_FOUND")
        return item[1]

    def complete_email_otp(self, challenge_id: str, otp: str, *, client_key: str = "local") -> str:
        challenge = self.challenges.get(challenge_id)
        if not challenge or challenge[2] <= _now():
            raise PiAuthError("CHALLENGE_EXPIRED")
        username, expected, _ = challenge
        factor_key = self._factor_key(username)
        if self._active_factor_failures(factor_key) >= self.max_failures:
            raise PiAuthError("RATE_LIMITED", "Too many authentication attempts")
        if not hmac.compare_digest(expected, str(otp)):
            factor_key = self._factor_key(username)
            count, _ = self.failures.get(factor_key, (0, _now()))
            count += 1
            self.failures[factor_key] = (count, _now() + timedelta(seconds=min(60, count * 5)))
            self._audit("MFA_FAILURE", username, client_key)
            if count >= self.max_failures:
                raise PiAuthError("RATE_LIMITED", "Too many authentication attempts")
            raise PiAuthError("MFA_FAILED")
        del self.challenges[challenge_id]
        self._test_email_codes.pop(challenge_id, None)
        mfa_challenge_id = secrets.token_urlsafe(18)
        self.mfa_challenges[mfa_challenge_id] = (username, _now() + timedelta(minutes=5))
        self._audit("LOGIN_EMAIL_OTP_CONFIRMED", username, client_key)
        return mfa_challenge_id

    def challenge_totp_for_test(self, mfa_challenge_id: str) -> str:
        """Test-only inspection hook; never exposed by the web API or audit log."""
        challenge = self.mfa_challenges.get(mfa_challenge_id)
        if not challenge or challenge[1] <= _now():
            raise PiAuthError("CHALLENGE_NOT_FOUND")
        user = self.users.get(challenge[0])
        if not user:
            raise PiAuthError("CHALLENGE_NOT_FOUND")
        return pyotp.TOTP(user.totp_secret).now()

    def complete_login(self, mfa_challenge_id: str, totp_code: str, *, client_key: str = "local") -> PiSession:
        challenge = self.mfa_challenges.get(mfa_challenge_id)
        if not challenge or challenge[1] <= _now():
            raise PiAuthError("CHALLENGE_EXPIRED")
        factor_key = self._factor_key(challenge[0])
        if self._active_factor_failures(factor_key) >= self.max_failures:
            raise PiAuthError("RATE_LIMITED", "Too many authentication attempts")
        username, _ = challenge
        user = self.users.get(username)
        if not user or not user.active or not user.totp_active:
            raise PiAuthError("AUTHENTICATION_FAILED")
        totp = pyotp.TOTP(user.totp_secret)
        now = _now()
        current_step = int(now.timestamp()) // int(totp.interval)
        accepted_step = next(
            (
                candidate
                for candidate in range(current_step - 1, current_step + 2)
                if hmac.compare_digest(totp.at(candidate * int(totp.interval)), str(totp_code))
            ),
            None,
        )
        if accepted_step is None:
            count, _ = self.failures.get(factor_key, (0, now))
            count += 1
            self.failures[factor_key] = (count, now + timedelta(seconds=min(60, count * 5)))
            self._audit("MFA_FAILURE", username, client_key)
            if count >= self.max_failures:
                raise PiAuthError("RATE_LIMITED", "Too many authentication attempts")
            raise PiAuthError("MFA_FAILED")
        if accepted_step <= self._last_totp_step.get(user.user_id, -1):
            self._audit("TOTP_REPLAY", username, client_key)
            raise PiAuthError("TOTP_REPLAY")
        user = self.users[username]
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        now = _now()
        session = PiSession(secrets.token_hex(12), user.user_id, self._digest(token), self._digest(csrf), now + self.session_ttl, now)
        self.sessions[session.token_digest] = session
        self._credentials[session.session_id] = (token, csrf)
        del self.mfa_challenges[mfa_challenge_id]
        self._last_totp_step[user.user_id] = accepted_step
        self.failures.pop(factor_key, None)
        self._audit("LOGIN_SUCCESS", username, client_key)
        return session

    def issue_test_credentials(self, challenge_id: str, *, client_key: str = "test") -> tuple[str, str]:
        """Return bearer/CSRF values for tests without adding an API backdoor."""
        mfa_challenge_id = self.complete_email_otp(challenge_id, self.challenge_code_for_test(challenge_id), client_key=client_key)
        session = self.complete_login(mfa_challenge_id, self.challenge_totp_for_test(mfa_challenge_id), client_key=client_key)
        # The raw values are not recoverable from a digest, so use a normal test
        # flow in callers.  This method intentionally remains unused by routes.
        raise RuntimeError(f"session {session.session_id} created; use authenticate through the test client")

    def authenticate(self, token: str | None) -> tuple[PiSession, PiUser]:
        if not token:
            raise PiAuthError("AUTHENTICATION_REQUIRED")
        session = self.sessions.get(self._digest(token))
        if not session or session.expires_at <= _now():
            raise PiAuthError("SESSION_INVALID")
        user = next((candidate for candidate in self.users.values() if candidate.user_id == session.user_id and candidate.active), None)
        if not user:
            raise PiAuthError("SESSION_INVALID")
        return session, user

    def csrf_valid(self, session: PiSession, token: str | None) -> bool:
        return bool(token) and hmac.compare_digest(session.csrf_digest, self._digest(token or ""))

    def logout(self, session: PiSession, user: PiUser, *, client_key: str = "local") -> None:
        self.sessions.pop(session.token_digest, None)
        self._credentials.pop(session.session_id, None)
        self._audit("LOGOUT", user.username, client_key)

    @staticmethod
    def _profile_view(user: PiUser) -> dict[str, str]:
        return {
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "license_code": user.license_code,
            "license_class": user.license_class,
            "license_expiry": user.license_expiry,
        }

    def profile_for(self, user: PiUser) -> dict[str, str]:
        return self._profile_view(user)

    def start_profile_update(self, user: PiUser, current_password: str, changes: dict[str, str], *, current_session_id: str, client_key: str = "local") -> str:
        if not self._verify_password(user, current_password):
            self._audit("PROFILE_PASSWORD_FAILURE", user.username, client_key)
            raise PiAuthError("AUTHENTICATION_FAILED")
        if not user.email or not user.email_verified:
            raise PiAuthError("EMAIL_REQUIRED")
        allowed = {"username", "email", "new_password", "full_name", "license_code", "license_class", "license_expiry"}
        if set(changes) - allowed:
            raise PiAuthError("PROFILE_INVALID")
        normalized: dict[str, str] = {}
        username = self._key(changes.get("username", user.username))
        if len(username) < 3 or len(username) > 64:
            raise PiAuthError("PROFILE_INVALID")
        if username != user.username and username in self.users:
            raise PiAuthError("USERNAME_UNAVAILABLE")
        normalized["username"] = username
        email = self._key(changes.get("email", user.email))
        if len(email) < 5 or len(email) > 320 or "@" not in email:
            raise PiAuthError("PROFILE_INVALID")
        if email != user.email and any(candidate.email == email and candidate.user_id != user.user_id for candidate in self.users.values() if candidate.email):
            raise PiAuthError("EMAIL_UNAVAILABLE")
        normalized["email"] = email
        new_password = changes.get("new_password", "")
        if new_password and (len(new_password) < 12 or len(new_password) > 128):
            raise PiAuthError("PROFILE_INVALID")
        normalized["new_password"] = new_password
        for field, maximum in (("full_name", 200), ("license_code", 100), ("license_class", 50), ("license_expiry", 20)):
            value = str(changes.get(field, getattr(user, field))).strip()
            if len(value) > maximum:
                raise PiAuthError("PROFILE_INVALID")
            normalized[field] = value
        if normalized["license_code"] and normalized["license_class"] not in {"A", "B"}:
            raise PiAuthError("PROFILE_INVALID")
        if not normalized["license_code"] and normalized["license_class"]:
            raise PiAuthError("PROFILE_INVALID")
        for previous_id, previous in list(self.profile_challenges.items()):
            if previous.get("user_id") == user.user_id:
                self.profile_challenges.pop(previous_id, None)
                self._test_email_codes.pop(previous_id, None)
                self._test_profile_new_email_codes.pop(previous_id, None)
        code = f"{secrets.randbelow(1_000_000):06d}"
        challenge_id = secrets.token_urlsafe(18)
        expires = _now() + timedelta(minutes=10)
        self.profile_challenges[challenge_id] = {
            "user_id": user.user_id,
            "session_id": current_session_id,
            "changes": normalized,
            "expected_current": code,
            "expected_new": "",
            "stage": "CURRENT_EMAIL",
            "expires": expires,
            "current_attempts": 0,
            "new_attempts": 0,
        }
        self._test_email_codes[challenge_id] = code
        if self.email_sender is None:
            if not self.allow_inmemory_email:
                self.profile_challenges.pop(challenge_id, None)
                self._test_email_codes.pop(challenge_id, None)
                raise PiAuthError("EMAIL_DELIVERY_UNAVAILABLE")
            self._audit("PROFILE_OTP_QUEUED", user.username, client_key)
        else:
            try:
                self.email_sender(user.email, "PI_PROFILE_UPDATE_CURRENT", code)
            except Exception as exc:
                self.profile_challenges.pop(challenge_id, None)
                self._test_email_codes.pop(challenge_id, None)
                raise PiAuthError("EMAIL_DELIVERY_FAILED") from exc
        return challenge_id

    def complete_profile_update(self, challenge_id: str, code: str, *, current_session_id: str, client_key: str = "local") -> PiUser | dict[str, str]:
        item = self.profile_challenges.get(challenge_id)
        if not item or item["expires"] <= _now() or item.get("session_id") != current_session_id:
            raise PiAuthError("CHALLENGE_EXPIRED")
        stage = str(item.get("stage", "CURRENT_EMAIL"))
        attempts_key = "new_attempts" if stage == "NEW_EMAIL" else "current_attempts"
        attempts = int(item[attempts_key])
        if attempts >= 5:
            raise PiAuthError("RATE_LIMITED")
        expected = str(item.get("expected_new" if stage == "NEW_EMAIL" else "expected_current", ""))
        if not hmac.compare_digest(expected, str(code)):
            item[attempts_key] = attempts + 1
            raise PiAuthError("MFA_FAILED")
        user = next((candidate for candidate in self.users.values() if candidate.user_id == item["user_id"]), None)
        if not user:
            raise PiAuthError("AUTHENTICATION_FAILED")
        changes = dict(item["changes"])
        if stage == "CURRENT_EMAIL" and str(changes["email"]) != user.email:
            new_code = f"{secrets.randbelow(1_000_000):06d}"
            item["current_verified"] = True
            item["expected_new"] = new_code
            item["stage"] = "NEW_EMAIL"
            self._test_profile_new_email_codes[challenge_id] = new_code
            try:
                if self.email_sender is None:
                    if not self.allow_inmemory_email:
                        raise PiAuthError("EMAIL_DELIVERY_UNAVAILABLE")
                    self._audit("PROFILE_NEW_EMAIL_OTP_QUEUED", user.username, client_key)
                else:
                    self.email_sender(str(changes["email"]), "PI_PROFILE_UPDATE_NEW", new_code)
            except Exception as exc:
                self.profile_challenges.pop(challenge_id, None)
                self._test_email_codes.pop(challenge_id, None)
                self._test_profile_new_email_codes.pop(challenge_id, None)
                if isinstance(exc, PiAuthError):
                    raise
                raise PiAuthError("EMAIL_DELIVERY_FAILED") from exc
            local, separator, domain = str(changes["email"]).partition("@")
            masked = f"{local[:2]}***@{domain}" if separator else "email mới"
            return {"next_step": "NEW_EMAIL_OTP", "email_masked": masked}
        if stage == "NEW_EMAIL" and not item.get("current_verified"):
            raise PiAuthError("CHALLENGE_INVALID")
        old_key = user.username
        old_values = self._profile_view(user)
        old_password_hash = user.password_hash
        try:
            user.username = str(changes["username"])
            user.email = str(changes["email"])
            user.email_verified = True
            user.full_name = str(changes["full_name"])
            user.license_code = str(changes["license_code"])
            user.license_class = str(changes["license_class"])
            user.license_expiry = str(changes["license_expiry"])
            if changes["new_password"]:
                user.password_hash = PASSWORD_HASHER.hash(str(changes["new_password"]))
            if old_key != user.username:
                self.users.pop(old_key, None)
                self.users[user.username] = user
            self._save_user(user)
        except Exception as exc:
            if old_key != user.username:
                self.users.pop(user.username, None)
                self.users[old_key] = user
            user.username = old_values["username"]
            user.email = old_values["email"]
            user.email_verified = True
            user.full_name = old_values["full_name"]
            user.license_code = old_values["license_code"]
            user.license_class = old_values["license_class"]
            user.license_expiry = old_values["license_expiry"]
            user.password_hash = old_password_hash
            raise PiAuthError("PERSISTENCE_FAILED") from exc
        for digest, session in list(self.sessions.items()):
            if session.user_id == user.user_id and session.session_id != current_session_id:
                self.sessions.pop(digest, None)
                self._credentials.pop(session.session_id, None)
        self.profile_challenges.pop(challenge_id, None)
        self._test_email_codes.pop(challenge_id, None)
        self._test_profile_new_email_codes.pop(challenge_id, None)
        self._audit("PROFILE_UPDATED", user.username, client_key)
        return user

    def credentials_for_session(self, session: PiSession) -> tuple[str, str]:
        try:
            return self._credentials[session.session_id]
        except KeyError as exc:
            raise PiAuthError("SESSION_INVALID") from exc

    def _audit(self, event: str, username: str, client_key: str) -> None:
        self.audit_events.append({"event": event, "username": username, "client_key": client_key, "at": _now().isoformat()})

    def user_for_session(self, token: str) -> PiUser:
        return self.authenticate(token)[1]

    def request_admin(self, user: PiUser, reason: str) -> dict[str, str]:
        """Create one local Pi USER -> ADMIN request; never grants immediately."""

        reason = reason.strip()
        if user.role is PiRole.ADMIN:
            raise PiAuthError("ROLE_ALREADY_GRANTED")
        if len(reason) < 3 or len(reason) > 500:
            raise PiAuthError("INVALID_ROLE_REASON")
        if any(item["requester_id"] == user.user_id and item["status"] == "PENDING" for item in self.role_requests.values()):
            raise PiAuthError("ROLE_REQUEST_PENDING")
        request = {
            "request_id": secrets.token_urlsafe(12),
            "requester_id": user.user_id,
            "requester": user.username,
            "requested_role": PiRole.ADMIN.value,
            "reason": reason,
            "status": "PENDING",
            "created_at": _now().isoformat(),
        }
        self.role_requests[request["request_id"]] = request
        try:
            if self.store:
                self.store.save_role_request(request)
        except Exception as exc:
            # Keep the in-memory view aligned with the durable store.  A
            # failed role-request write must not look successful until the
            # next process restart.
            self.role_requests.pop(request["request_id"], None)
            raise PiAuthError("PERSISTENCE_FAILED") from exc
        self._audit("ROLE_REQUEST_CREATED", user.username, "local")
        return dict(request)

    def list_role_requests(self, actor: PiUser) -> list[dict[str, str]]:
        if actor.role is not PiRole.ADMIN:
            raise PiAuthError("ROLE_FORBIDDEN")
        return [dict(item) for item in self.role_requests.values()]

    def list_users(self, actor: PiUser) -> list[dict[str, str | bool | int]]:
        if actor.role is not PiRole.ADMIN:
            raise PiAuthError("ROLE_FORBIDDEN")
        session_counts: dict[str, int] = {}
        now = _now()
        for session in self.sessions.values():
            if session.expires_at > now:
                session_counts[session.user_id] = session_counts.get(session.user_id, 0) + 1
        return [
            {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "active": user.active,
                "email_verified": user.email_verified,
                "totp_active": user.totp_active,
                "active_sessions": session_counts.get(user.user_id, 0),
            }
            for user in self.users.values()
        ]

    def decide_role_request(self, actor: PiUser, request_id: str, decision: str) -> dict[str, str]:
        if actor.role is not PiRole.ADMIN:
            raise PiAuthError("ROLE_FORBIDDEN")
        if decision not in {"APPROVED", "REJECTED"}:
            raise PiAuthError("INVALID_ROLE_DECISION")
        item = self.role_requests.get(request_id)
        if not item or item["status"] != "PENDING":
            raise PiAuthError("ROLE_REQUEST_NOT_FOUND")
        previous_item = dict(item)
        target = None
        previous_role = None
        item["status"] = decision
        item["decided_by"] = actor.username
        item["decided_at"] = _now().isoformat()
        if decision == "APPROVED":
            target = next((candidate for candidate in self.users.values() if candidate.user_id == item["requester_id"]), None)
            if not target or not target.active:
                item["status"] = "REJECTED"
                item["decision_error"] = "REQUESTER_INACTIVE"
            else:
                previous_role = target.role
                target.role = PiRole.ADMIN
        try:
            if target is not None and previous_role is not None:
                self._save_user(target)
            if self.store:
                self.store.save_role_request(item)
        except Exception as exc:
            # Do not leave a role elevated or a request marked as decided
            # when either persistence operation fails.
            if target is not None and previous_role is not None:
                target.role = previous_role
                try:
                    self._save_user(target)
                except Exception:
                    pass
            item.clear()
            item.update(previous_item)
            raise PiAuthError("PERSISTENCE_FAILED") from exc
        self._audit("ROLE_REQUEST_DECIDED", actor.username, "local")
        return dict(item)
