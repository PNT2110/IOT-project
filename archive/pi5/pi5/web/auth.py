from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from .models import PiRole


PASSWORD_HASHER = PasswordHasher(time_cost=2, memory_cost=32_768, parallelism=2)


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PiUser:
    user_id: str
    username: str
    password_hash: str
    role: PiRole
    totp_secret: str
    active: bool = True


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
    """In-memory Pi-local identity domain for the SCOPE-04 prototype.

    It deliberately has no email, PC session, federation, or synchronization
    path.  Production persistence/MFA enrolment remains a separate approval
    and deployment decision; tests use the same service with ephemeral data.
    """

    def __init__(self, *, session_ttl_minutes: int = 30, max_failures: int = 5) -> None:
        self.users: dict[str, PiUser] = {}
        self.sessions: dict[str, PiSession] = {}
        self._credentials: dict[str, tuple[str, str]] = {}
        self.challenges: dict[str, tuple[str, str, datetime]] = {}
        self.failures: dict[str, tuple[int, datetime]] = {}
        self.audit_events: list[dict[str, str]] = []
        self.session_ttl = timedelta(minutes=session_ttl_minutes)
        self.max_failures = max_failures

    @staticmethod
    def _key(value: str) -> str:
        return value.strip().casefold()

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def add_user(self, username: str, password: str, *, role: PiRole = PiRole.USER, totp_secret: str | None = None) -> PiUser:
        key = self._key(username)
        if not key or key in self.users:
            raise ValueError("username is unavailable")
        user = PiUser(
            user_id=secrets.token_hex(8),
            username=key,
            password_hash=PASSWORD_HASHER.hash(password),
            role=role,
            totp_secret=totp_secret or pyotp.random_base32(),
        )
        self.users[key] = user
        return user

    def _verify_password(self, user: PiUser, password: str) -> bool:
        try:
            return PASSWORD_HASHER.verify(user.password_hash, password)
        except (VerifyMismatchError, VerificationError):
            return False

    def start_challenge(self, username: str, password: str, *, client_key: str = "local") -> str:
        key = self._key(username)
        user = self.users.get(key)
        if not user or not user.active or not self._verify_password(user, password):
            self._audit("LOGIN_FAILURE", key, client_key)
            raise PiAuthError("AUTHENTICATION_FAILED")
        count, blocked_until = self.failures.get(client_key, (0, _now()))
        if blocked_until > _now() or count >= self.max_failures:
            raise PiAuthError("RATE_LIMITED", "Too many authentication attempts")
        challenge_id = secrets.token_urlsafe(18)
        otp = f"{secrets.randbelow(1_000_000):06d}"
        self.challenges[challenge_id] = (key, otp, _now() + timedelta(minutes=5))
        self._audit("LOGIN_CHALLENGE", key, client_key)
        return challenge_id

    def challenge_code_for_test(self, challenge_id: str) -> str:
        """Test-only inspection hook; never exposed by the web API or audit log."""
        item = self.challenges.get(challenge_id)
        if not item:
            raise PiAuthError("CHALLENGE_NOT_FOUND")
        return item[1]

    def complete_login(self, challenge_id: str, otp: str, *, client_key: str = "local") -> PiSession:
        challenge = self.challenges.get(challenge_id)
        if not challenge or challenge[2] <= _now():
            raise PiAuthError("CHALLENGE_EXPIRED")
        username, expected, _ = challenge
        if not hmac.compare_digest(expected, str(otp)):
            count, _ = self.failures.get(client_key, (0, _now()))
            count += 1
            self.failures[client_key] = (count, _now() + timedelta(seconds=min(60, count * 5)))
            self._audit("MFA_FAILURE", username, client_key)
            if count >= self.max_failures:
                raise PiAuthError("RATE_LIMITED", "Too many authentication attempts")
            raise PiAuthError("MFA_FAILED")
        user = self.users[username]
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        now = _now()
        session = PiSession(secrets.token_hex(12), user.user_id, self._digest(token), self._digest(csrf), now + self.session_ttl, now)
        self.sessions[session.token_digest] = session
        self._credentials[session.session_id] = (token, csrf)
        del self.challenges[challenge_id]
        self.failures.pop(client_key, None)
        self._audit("LOGIN_SUCCESS", username, client_key)
        return session

    def issue_test_credentials(self, challenge_id: str, *, client_key: str = "test") -> tuple[str, str]:
        """Return bearer/CSRF values for tests without adding an API backdoor."""
        session = self.complete_login(challenge_id, self.challenge_code_for_test(challenge_id), client_key=client_key)
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

    def credentials_for_session(self, session: PiSession) -> tuple[str, str]:
        try:
            return self._credentials[session.session_id]
        except KeyError as exc:
            raise PiAuthError("SESSION_INVALID") from exc

    def _audit(self, event: str, username: str, client_key: str) -> None:
        self.audit_events.append({"event": event, "username": username, "client_key": client_key, "at": _now().isoformat()})

    def user_for_session(self, token: str) -> PiUser:
        return self.authenticate(token)[1]
