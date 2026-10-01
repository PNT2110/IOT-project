from __future__ import annotations

import base64
import hashlib
import os
import secrets
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .models import PiRole


def _key_bytes(value: str) -> bytes:
    raw = value.encode("utf-8")
    if len(raw) < 32:
        raise ValueError("PI_DATA_KEY must contain at least 32 characters")
    return hashlib.sha256(b"scope04-pi-data-v2:" + raw).digest()


def _protect(value: str, master_key: bytes) -> str:
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(master_key).encrypt(nonce, value.encode("utf-8"), b"scope04-pi-totp-v2")
    return base64.urlsafe_b64encode(b"\x02" + nonce + ciphertext).decode("ascii")


def _unprotect(value: str, master_key: bytes) -> str:
    packed = base64.urlsafe_b64decode(value.encode("ascii"))
    if len(packed) < 1 + 12 + 16 or packed[0] != 2:
        raise ValueError("invalid protected secret")
    nonce, ciphertext = packed[1:13], packed[13:]
    return AESGCM(master_key).decrypt(nonce, ciphertext, b"scope04-pi-totp-v2").decode("utf-8")


class PiUserStore:
    """Small SQLite persistence boundary for Pi identity and role requests."""

    def __init__(self, path: str, data_key: str) -> None:
        self.path = Path(path)
        self.master_key = _key_bytes(data_key)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch(mode=0o600)
        os.chmod(self.path, 0o600)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS pi_users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('USER','ADMIN')),
                    totp_secret TEXT NOT NULL,
                    active INTEGER NOT NULL,
                    email_verified INTEGER NOT NULL,
                    totp_active INTEGER NOT NULL,
                    full_name TEXT NOT NULL DEFAULT '',
                    license_code TEXT NOT NULL DEFAULT '',
                    license_class TEXT NOT NULL DEFAULT '',
                    license_expiry TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS pi_role_requests (
                    request_id TEXT PRIMARY KEY,
                    requester_id TEXT NOT NULL,
                    requester TEXT NOT NULL,
                    requested_role TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    decided_by TEXT,
                    decided_at TEXT,
                    decision_error TEXT
                );
                """
            )
            columns = {row["name"] for row in db.execute("PRAGMA table_info(pi_users)").fetchall()}
            for name in ("full_name", "license_code", "license_class", "license_expiry"):
                if name not in columns:
                    db.execute(f"ALTER TABLE pi_users ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")

    def load_users(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as db:
            rows = db.execute("SELECT * FROM pi_users ORDER BY created_at").fetchall()
        result = []
        for row in rows:
            result.append(
                {
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "email": row["email"] or "",
                    "password_hash": row["password_hash"],
                    "role": PiRole(row["role"]),
                    "totp_secret": _unprotect(row["totp_secret"], self.master_key),
                    "active": bool(row["active"]),
                    "email_verified": bool(row["email_verified"]),
                    "totp_active": bool(row["totp_active"]),
                    "full_name": _unprotect(row["full_name"], self.master_key) if row["full_name"] else "",
                    "license_code": _unprotect(row["license_code"], self.master_key) if row["license_code"] else "",
                    "license_class": _unprotect(row["license_class"], self.master_key) if row["license_class"] else "",
                    "license_expiry": _unprotect(row["license_expiry"], self.master_key) if row["license_expiry"] else "",
                }
            )
        return result

    def save_user(self, user: Any) -> None:
        with self._lock, self._connect() as db:
            db.execute(
                """INSERT INTO pi_users
                (user_id, username, email, password_hash, role, totp_secret, active, email_verified, totp_active, full_name, license_code, license_class, license_expiry, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                  username=excluded.username, email=excluded.email, password_hash=excluded.password_hash,
                  role=excluded.role, totp_secret=excluded.totp_secret, active=excluded.active,
                  email_verified=excluded.email_verified, totp_active=excluded.totp_active,
                  full_name=excluded.full_name, license_code=excluded.license_code,
                  license_class=excluded.license_class, license_expiry=excluded.license_expiry""",
                (
                    user.user_id,
                    user.username,
                    user.email or None,
                    user.password_hash,
                    user.role.value,
                    _protect(user.totp_secret, self.master_key),
                    int(user.active),
                    int(user.email_verified),
                    int(user.totp_active),
                    _protect(user.full_name, self.master_key) if user.full_name else "",
                    _protect(user.license_code, self.master_key) if user.license_code else "",
                    _protect(user.license_class, self.master_key) if user.license_class else "",
                    _protect(user.license_expiry, self.master_key) if user.license_expiry else "",
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def delete_user(self, username: str) -> None:
        with self._lock, self._connect() as db:
            db.execute("DELETE FROM pi_users WHERE username = ?", (username,))

    def load_role_requests(self) -> list[dict[str, str]]:
        with self._lock, self._connect() as db:
            rows = db.execute("SELECT * FROM pi_role_requests ORDER BY created_at").fetchall()
        return [dict(row) for row in rows]

    def save_role_request(self, item: dict[str, str]) -> None:
        with self._lock, self._connect() as db:
            db.execute(
                """INSERT INTO pi_role_requests
                (request_id, requester_id, requester, requested_role, reason, status, created_at, decided_by, decided_at, decision_error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(request_id) DO UPDATE SET status=excluded.status, decided_by=excluded.decided_by,
                  decided_at=excluded.decided_at, decision_error=excluded.decision_error""",
                (
                    item["request_id"], item["requester_id"], item["requester"], item["requested_role"],
                    item["reason"], item["status"], item["created_at"], item.get("decided_by"),
                    item.get("decided_at"), item.get("decision_error"),
                ),
            )


def store_from_env() -> PiUserStore | None:
    path = os.getenv("PI_AUTH_DB_PATH")
    data_key = os.getenv("PI_DATA_KEY")
    if not path and not data_key:
        return None
    if not path or not data_key:
        raise RuntimeError("PI_AUTH_DB_PATH and PI_DATA_KEY must be configured together")
    return PiUserStore(path, data_key)
