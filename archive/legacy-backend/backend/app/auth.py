from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Annotated

import pyotp
from fastapi import Cookie, Depends, Header, HTTPException, Request, status

from .db import db

SESSION_COOKIE = "drone_session"


class LoginLimiter:
    def __init__(self, limit: int = 10, window_seconds: int = 60):
        self.limit = limit
        self.window = window_seconds
        self.attempts: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        queue = self.attempts[key]
        while queue and queue[0] < now - self.window:
            queue.popleft()
        if len(queue) >= self.limit:
            return False
        queue.append(now)
        return True


login_limiter = LoginLimiter()


def session_user(drone_session: Annotated[str | None, Cookie()] = None):
    row = db.get_session(drone_session)
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chưa đăng nhập")
    return row


def require_admin(user=Depends(session_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chỉ admin được phép")
    return user


def require_csrf(
    user=Depends(session_user),
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
):
    if not csrf_token or csrf_token != user["csrf_token"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token không hợp lệ")
    return user


def verify_admin_totp(user, token: str | None) -> bool:
    if user["role"] != "admin":
        return True
    secret = user["totp_secret"]
    return bool(secret and token and pyotp.TOTP(secret).verify(token, valid_window=1))

