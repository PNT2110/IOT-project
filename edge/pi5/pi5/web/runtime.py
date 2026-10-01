from __future__ import annotations

from collections.abc import Mapping
import os


def validate_runtime_environment(environ: Mapping[str, str] | None = None) -> None:
    """Fail closed when the ASGI entry point is explicitly run in production."""

    env = os.environ if environ is None else environ
    if env.get("APP_ENV", "development").strip().lower() != "production":
        return

    missing: list[str] = []
    https_terminated = env.get("PI_HTTPS_TERMINATED", "").strip().lower() in {"1", "true", "yes"}
    # The captive portal on the Pi's own access point is served over plain
    # HTTP; the operator states that by turning Secure cookies off explicitly.
    local_ap_http = env.get("PI_COOKIE_SECURE", "").strip().lower() == "false"
    if not https_terminated and not local_ap_http:
        missing.append("PI_HTTPS_TERMINATED=true, or PI_COOKIE_SECURE=false for the local access point")
    if not env.get("PI_SMTP_HOST", "").strip():
        missing.append("PI_SMTP_HOST")
    if not env.get("PI_SMTP_FROM", "").strip():
        missing.append("PI_SMTP_FROM")

    database_path = env.get("PI_AUTH_DB_PATH", "").strip()
    data_key = env.get("PI_DATA_KEY", "")
    if not database_path:
        missing.append("PI_AUTH_DB_PATH")
    elif not os.path.isabs(database_path):
        missing.append("PI_AUTH_DB_PATH must be absolute")
    if len(data_key) < 32:
        missing.append("PI_DATA_KEY (at least 32 characters)")

    smtp_username = env.get("PI_SMTP_USERNAME", "").strip()
    smtp_password = env.get("PI_SMTP_PASSWORD", "")
    if bool(smtp_username) != bool(smtp_password):
        missing.append("PI_SMTP_USERNAME and PI_SMTP_PASSWORD must be configured together")
    try:
        smtp_port = int(env.get("PI_SMTP_PORT", "587"))
        if not 1 <= smtp_port <= 65535:
            raise ValueError
    except ValueError:
        missing.append("PI_SMTP_PORT must be between 1 and 65535")

    if missing:
        raise RuntimeError(
            "Pi production startup requires durable encrypted account storage and working OTP mail settings; "
            "missing or incomplete: " + ", ".join(missing)
        )
