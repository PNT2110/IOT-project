from __future__ import annotations

import pytest

from pi5.cli import provision_first_admin
from pi5.web.auth import PiAuthService
from pi5.web.models import PiRole
from pi5.web.persistence import PiUserStore
from pi5.web.runtime import validate_runtime_environment


def test_production_runtime_requires_smtp_and_encrypted_persistent_accounts(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="PI_SMTP_HOST"):
        validate_runtime_environment({"APP_ENV": "production"})

    valid = {
        "APP_ENV": "production",
        "PI_HTTPS_TERMINATED": "true",
        "PI_SMTP_HOST": "smtp.example.invalid",
        "PI_SMTP_FROM": "noreply@example.invalid",
        "PI_AUTH_DB_PATH": str(tmp_path / "pi-users.sqlite3"),
        "PI_DATA_KEY": "k" * 40,
    }
    validate_runtime_environment(valid)
    validate_runtime_environment({"APP_ENV": "development"})


def test_production_runtime_rejects_partial_smtp_credentials(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="configured together"):
        validate_runtime_environment(
            {
                "APP_ENV": "production",
                "PI_HTTPS_TERMINATED": "true",
                "PI_SMTP_HOST": "smtp.example.invalid",
                "PI_SMTP_FROM": "noreply@example.invalid",
                "PI_SMTP_USERNAME": "account",
                "PI_AUTH_DB_PATH": str(tmp_path / "pi-users.sqlite3"),
                "PI_DATA_KEY": "k" * 40,
            }
        )


def test_production_runtime_requires_https_termination(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="PI_HTTPS_TERMINATED"):
        validate_runtime_environment(
            {
                "APP_ENV": "production",
                "PI_SMTP_HOST": "smtp.example.invalid",
                "PI_SMTP_FROM": "noreply@example.invalid",
                "PI_AUTH_DB_PATH": str(tmp_path / "pi-users.sqlite3"),
                "PI_DATA_KEY": "k" * 40,
            }
        )


def test_first_pi_admin_bootstrap_is_durable_and_one_time(tmp_path) -> None:
    store = PiUserStore(str(tmp_path / "accounts.sqlite3"), "test-key-" + "x" * 40)
    user = provision_first_admin(
        store,
        "Primary-Admin",
        "QA-only-password-2026!",
        totp_secret="JBSWY3DPEHPK3PXP",
    )

    restored = PiAuthService(store=PiUserStore(str(store.path), "test-key-" + "x" * 40))
    assert restored.users[user.username].role is PiRole.ADMIN
    assert restored.users[user.username].email == ""
    assert restored.users[user.username].totp_secret == "JBSWY3DPEHPK3PXP"
    with pytest.raises(ValueError, match="empty Pi account store"):
        provision_first_admin(store, "another-admin", "QA-only-password-2026!")
