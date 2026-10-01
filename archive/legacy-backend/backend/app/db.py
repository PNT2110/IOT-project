from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from .config import settings


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin','user')),
    totp_secret TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    csrf_token TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    username TEXT,
    action TEXT NOT NULL,
    detail TEXT,
    remote_addr TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_log(created_at);
CREATE TABLE IF NOT EXISTS telemetry_samples (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_telemetry_created_at ON telemetry_samples(created_at);
CREATE TABLE IF NOT EXISTS map_sync (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    source_url TEXT,
    fetched_at TEXT,
    checksum TEXT,
    feature_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'missing'
);
INSERT OR IGNORE INTO map_sync(id, status) VALUES (1, 'missing');
"""


class Database:
    def __init__(self, path: Path | None = None):
        self.path = path or settings.db_path
        self._lock = threading.Lock()
        self.password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            conn.execute("PRAGMA optimize")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def create_user(self, username: str, password: str, role: str, totp_secret: str | None = None) -> None:
        if role not in {"admin", "user"}:
            raise ValueError("role must be admin or user")
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO users(username,password_hash,role,totp_secret,created_at) VALUES (?,?,?,?,?)",
                (username, self.password_hasher.hash(password), role, totp_secret, now),
            )

    def set_password(self, username: str, password: str) -> None:
        with self.connect() as conn:
            result = conn.execute(
                "UPDATE users SET password_hash=?,failed_attempts=0,locked_until=NULL WHERE username=?",
                (self.password_hasher.hash(password), username),
            )
            if result.rowcount != 1:
                raise ValueError("Không tìm thấy user")
            conn.execute("DELETE FROM sessions WHERE user_id=(SELECT id FROM users WHERE username=?)", (username,))

    def set_totp_secret(self, username: str, secret: str) -> None:
        with self.connect() as conn:
            result = conn.execute(
                "UPDATE users SET totp_secret=? WHERE username=? AND role='admin'",
                (secret, username),
            )
            if result.rowcount != 1:
                raise ValueError("Không tìm thấy admin")
            conn.execute("DELETE FROM sessions WHERE user_id=(SELECT id FROM users WHERE username=?)", (username,))

    def authenticate(self, username: str, password: str) -> sqlite3.Row | None:
        now = datetime.now(timezone.utc)
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE username=? AND enabled=1", (username,)).fetchone()
            if not row:
                return None
            if row["locked_until"] and datetime.fromisoformat(row["locked_until"]) > now:
                return None
            try:
                self.password_hasher.verify(row["password_hash"], password)
            except VerifyMismatchError:
                attempts = int(row["failed_attempts"]) + 1
                locked_until = (now + timedelta(minutes=15)).isoformat() if attempts >= 5 else None
                conn.execute(
                    "UPDATE users SET failed_attempts=?, locked_until=? WHERE id=?",
                    (0 if locked_until else attempts, locked_until, row["id"]),
                )
                return None
            conn.execute("UPDATE users SET failed_attempts=0, locked_until=NULL WHERE id=?", (row["id"],))
            return row

    def create_session(self, user_id: int, hours: int) -> tuple[str, str]:
        token = secrets.token_urlsafe(48)
        csrf = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=hours)
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO sessions(token_hash,user_id,csrf_token,expires_at,created_at) VALUES (?,?,?,?,?)",
                (self._token_hash(token), user_id, csrf, expires.isoformat(), now.isoformat()),
            )
        return token, csrf

    def get_session(self, token: str | None) -> sqlite3.Row | None:
        if not token:
            return None
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as conn:
            return conn.execute(
                """SELECT users.id,users.username,users.role,users.totp_secret,sessions.csrf_token,sessions.expires_at
                   FROM sessions JOIN users ON users.id=sessions.user_id
                   WHERE sessions.token_hash=? AND sessions.expires_at>? AND users.enabled=1""",
                (self._token_hash(token), now),
            ).fetchone()

    def delete_session(self, token: str | None) -> None:
        if not token:
            return
        with self.connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash=?", (self._token_hash(token),))

    def audit(self, action: str, username: str | None = None, detail: str | None = None, remote_addr: str | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO audit_log(created_at,username,action,detail,remote_addr) VALUES (?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(), username, action, detail, remote_addr),
            )

    def cleanup(self, retention_days: int, retention_bytes: int) -> None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
        with self.connect() as conn:
            conn.execute("DELETE FROM sessions WHERE expires_at<=?", (datetime.now(timezone.utc).isoformat(),))
            conn.execute("DELETE FROM telemetry_samples WHERE created_at<?", (cutoff,))
        if self.path.exists() and self.path.stat().st_size > retention_bytes:
            with self.connect() as conn:
                while self.path.stat().st_size > retention_bytes:
                    rows = conn.execute("SELECT id FROM telemetry_samples ORDER BY id LIMIT 10000").fetchall()
                    if not rows:
                        break
                    conn.execute("DELETE FROM telemetry_samples WHERE id<=?", (rows[-1]["id"],))
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()


db = Database()
