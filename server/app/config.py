from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def validate_allowed_origins(origins: tuple[str, ...]) -> tuple[str, ...]:
    if not origins:
        raise RuntimeError("ALLOWED_ORIGINS must contain at least one explicit origin")
    if "*" in origins:
        raise RuntimeError("ALLOWED_ORIGINS must not contain '*' when credentialed cookies are enabled")
    return origins


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    session_secret: str
    cookie_secure: bool
    allowed_origins: tuple[str, ...]
    host: str
    port: int
    fake_mail_outbox: str | None = None
    session_ttl_minutes: int = 60
    challenge_ttl_minutes: int = 10
    terms_version: str = "terms-v1"
    max_zone_bytes: int = 200_000
    max_request_bytes: int = 1_000_000
    # Test fixtures are opt-in for a deployed/public process. Test fixtures
    # remain enabled by default for the isolated Settings objects in tests.
    seed_demo_data: bool = True
    public_mode: bool = False
    airspace_source_url: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    auth_rate_limit_window_seconds: int = 900
    auth_rate_limit_max_attempts: int = 10
    auth_rate_limit_max_entries: int = 10_000
    registration_rate_limit_max_attempts: int = 20
    auth_challenge_rate_limit_max_attempts: int = 5
    enable_test_adapters: bool = False


def load_settings() -> Settings:
    env = os.getenv("APP_ENV", "development")
    secret = os.getenv("SESSION_SECRET")
    if not secret:
        raise RuntimeError("SESSION_SECRET is required; provide it via the environment")
    database_url = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'server' / 'data' / 'app.db'}")
    allowed_origins = validate_allowed_origins(tuple(_csv(os.getenv("ALLOWED_ORIGINS", "https://localhost:5173"))))
    return Settings(
        app_env=env,
        database_url=database_url,
        session_secret=secret,
        cookie_secure=os.getenv("COOKIE_SECURE", "true").lower() == "true",
        allowed_origins=allowed_origins,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8765")),
        fake_mail_outbox=os.getenv("FAKE_MAIL_OUTBOX") or None,
        terms_version=os.getenv("TERMS_VERSION", "terms-v1").strip() or "terms-v1",
        max_request_bytes=int(os.getenv("MAX_REQUEST_BYTES", "1000000")),
        seed_demo_data=os.getenv("SEED_DEMO_DATA", "false").lower() == "true",
        public_mode=os.getenv("PUBLIC_MODE", "false").lower() == "true",
        airspace_source_url=os.getenv("AIRSPACE_SOURCE_URL") or None,
        smtp_host=os.getenv("SMTP_HOST") or None,
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_username=os.getenv("SMTP_USERNAME") or None,
        smtp_password=os.getenv("SMTP_PASSWORD") or None,
        smtp_from=os.getenv("SMTP_FROM") or None,
        auth_rate_limit_window_seconds=int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "900")),
        auth_rate_limit_max_attempts=int(os.getenv("AUTH_RATE_LIMIT_MAX_ATTEMPTS", "10")),
        auth_rate_limit_max_entries=int(os.getenv("AUTH_RATE_LIMIT_MAX_ENTRIES", "10000")),
        registration_rate_limit_max_attempts=int(os.getenv("REGISTRATION_RATE_LIMIT_MAX_ATTEMPTS", "20")),
        auth_challenge_rate_limit_max_attempts=int(os.getenv("AUTH_CHALLENGE_RATE_LIMIT_MAX_ATTEMPTS", "5")),
        enable_test_adapters=os.getenv("ENABLE_TEST_ADAPTERS", "false").lower() == "true",
    )
