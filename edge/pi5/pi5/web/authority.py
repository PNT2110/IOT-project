"""Flight-permission requests: Pi -> PC authority -> ESP32 arm permission.

Contract: contracts/v1/DEVICE_FLIGHT_CONTRACT.md. The Pi only ever grants or
revokes the *permission* to arm (``$AUTH,ALLOW`` / ``$AUTH,DENY``); it has no
arm, disarm or motor command.
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import json
import os
import re
import secrets
import sqlite3
import threading
import time
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ..telemetry.esp_command import EspFlightAuthorizationBridge
from .device_crypto import seal

# Flight date and time on the form are Vietnam local time.
LOCAL_TZ = timezone(timedelta(hours=7))
DEFAULT_VEHICLES = ("F450 PNT PVD",)
MAX_RESPONSE_BYTES = 65_536


class AuthorityError(Exception):
    """The PC authority could not be reached or returned an unusable answer."""


class FlightRequestError(Exception):
    def __init__(self, code: str = "FLIGHT_REQUEST_INVALID") -> None:
        super().__init__(code)
        self.code = code


class AuthorityClient:
    def __init__(self, base_url: str, device_id: str, key: bytes, *, opener: Callable[..., Any] = urlopen, clock: Callable[[], float] = time.time, timeout: float = 8.0) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("PC authority requires an explicit HTTPS base URL")
        if len(key) != 32 or not device_id:
            raise ValueError("PC authority requires a device id and a 32-byte key")
        self.base_url = base_url.rstrip("/")
        self.device_id = device_id
        self._key = key
        self._opener = opener
        self._clock = clock
        self._timeout = timeout

    @classmethod
    def from_env(cls) -> "AuthorityClient | None":
        base_url = os.getenv("PI_PC_MAP_URL", "").strip()
        device_id = os.getenv("PI_DEVICE_ID", "").strip()
        key = os.getenv("PI_DEVICE_KEY", "").strip()
        if not (base_url and device_id and key):
            return None
        return cls(base_url, device_id, base64.urlsafe_b64decode(key + "=" * (-len(key) % 4)))

    def _post(self, path: str, payload: dict) -> dict:
        envelope = seal(self._key, self.device_id, payload, int(self._clock()))
        request = Request(self.base_url + path, data=json.dumps(envelope).encode(), headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "IOT-Pi-Authority/1"}, method="POST")
        try:
            with self._opener(request, timeout=self._timeout) as response:
                status = int(getattr(response, "status", 200))
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if status < 200 or status >= 300 or len(raw) > MAX_RESPONSE_BYTES:
                raise AuthorityError("PC authority returned an error")
            data = json.loads(raw.decode("utf-8"))["data"]
            if not isinstance(data, dict):
                raise AuthorityError("PC authority returned an invalid body")
            return data
        except AuthorityError:
            raise
        except Exception as exc:
            raise AuthorityError("PC authority request failed") from exc

    def submit(self, payload: dict) -> str:
        data = self._post("/api/v1/device/flight-requests", payload)
        request_id = data.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            raise AuthorityError("PC authority returned no request id")
        return request_id

    def status(self, request_id: str) -> dict:
        if not re.fullmatch(r"[A-Za-z0-9-]{1,64}", request_id):
            raise AuthorityError("invalid request id")
        return self._post(f"/api/v1/device/flight-requests/{request_id}/status", {"request_id": request_id})


class FlightAuthorityService:
    """Stores requests, talks to the PC, and drives the ESP arm permission."""

    def __init__(
        self,
        *,
        client: Any | None = None,
        bridge: EspFlightAuthorizationBridge | None = None,
        gps: Callable[[], dict | None] = lambda: None,
        store_path: str | None = None,
        vehicles: tuple[str, ...] = DEFAULT_VEHICLES,
        window_minutes: int = 60,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._client = client
        self._bridge = bridge
        self._gps = gps
        self.vehicles = tuple(vehicles)
        self._window = timedelta(minutes=window_minutes)
        self._clock = clock
        self._lock = threading.RLock()
        self._applied: tuple[str, str, str | None] | None = None
        self._db = sqlite3.connect(store_path or ":memory:", check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS flight_requests (request_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, body TEXT NOT NULL)")
        self._db.commit()

    # ---- storage

    def _all(self) -> list[dict[str, Any]]:
        rows = self._db.execute("SELECT body FROM flight_requests ORDER BY created_at DESC").fetchall()
        return [json.loads(row[0]) for row in rows]

    def _save(self, item: dict[str, Any]) -> None:
        self._db.execute("INSERT OR REPLACE INTO flight_requests (request_id, created_at, body) VALUES (?, ?, ?)", (item["request_id"], item["created_at"], json.dumps(item)))
        self._db.commit()

    # ---- request lifecycle

    @staticmethod
    def _text(body: dict[str, Any], name: str, maximum: int) -> str:
        value = str(body.get(name, "")).strip()
        if not 1 <= len(value) <= maximum:
            raise FlightRequestError()
        return value

    def _window_of(self, item: dict[str, Any]) -> tuple[datetime, datetime]:
        def at(clock: str) -> datetime:
            return datetime.strptime(f"{item['flight_date']} {clock}", "%Y-%m-%d %H:%M").replace(tzinfo=LOCAL_TZ).astimezone(timezone.utc)

        start = at(item["flight_time"])
        # Requests stored before the end time existed fall back to the fixed window.
        return start, at(item["flight_end_time"]) if item.get("flight_end_time") else start + self._window

    def _view(self, item: dict[str, Any]) -> dict[str, Any]:
        start, end = self._window_of(item)
        allowed = item["status"] == "APPROVED" and start <= self._clock() < end
        return {**item, "valid_from": start.isoformat(), "valid_until": end.isoformat(), "arm_permission": "ALLOWED" if allowed else "BLOCKED"}

    def create(self, user: Any, body: dict[str, Any]) -> dict[str, Any]:
        full_name = self._text(body, "full_name", 160)
        license_code = self._text(body, "license_code", 80)
        flight_date = self._text(body, "flight_date", 10)
        flight_time = self._text(body, "flight_time", 5)
        flight_end_time = self._text(body, "flight_end_time", 5)
        vehicle = self._text(body, "vehicle", 80)
        clock = r"([01]\d|2[0-3]):[0-5]\d"
        if vehicle not in self.vehicles or not re.fullmatch(clock, flight_time) or not re.fullmatch(clock, flight_end_time) or flight_end_time <= flight_time:
            raise FlightRequestError()
        try:
            datetime.strptime(flight_date, "%Y-%m-%d")
        except ValueError as exc:
            raise FlightRequestError() from exc
        gps = self._gps()
        item = {
            "request_id": "pi-" + secrets.token_hex(12),
            "requester_id": user.user_id,
            "requester": user.username,
            "full_name": full_name,
            "license_code": license_code,
            "flight_date": flight_date,
            "flight_time": flight_time,
            "flight_end_time": flight_end_time,
            "vehicle": vehicle,
            "gps": gps,
            "status": "PENDING_SEND",
            "remote_id": None,
            "reason": None,
            "decided_at": None,
            "created_at": self._clock().isoformat(),
        }
        with self._lock:
            self._save(item)
            self._send(item)
            return self._view(item)

    def _send(self, item: dict[str, Any]) -> None:
        if self._client is None:
            return
        payload = {
            "client_ref": item["request_id"],
            "applicant_full_name": item["full_name"],
            "license_code": item["license_code"],
            "flight_date": item["flight_date"],
            "flight_time": item["flight_time"],
            "flight_end_time": item.get("flight_end_time"),
            "vehicle": item["vehicle"],
            "pi_username": item["requester"],
            "gps": item["gps"],
        }
        try:
            item["remote_id"] = self._client.submit(payload)
        except AuthorityError:
            return
        item["status"] = "PENDING"
        self._save(item)

    def _poll(self, item: dict[str, Any]) -> None:
        try:
            answer = self._client.status(item["remote_id"])
        except AuthorityError:
            return
        if answer.get("status") in {"APPROVED", "REJECTED"}:
            item["status"] = answer["status"]
            item["reason"] = answer.get("reason")
            item["decided_at"] = answer.get("decided_at")
            self._save(item)

    def list_for(self, user: Any) -> list[dict[str, Any]]:
        with self._lock:
            return [self._view(item) for item in self._all() if item["requester_id"] == user.user_id]

    def tick(self) -> None:
        """Retry sends, poll decisions, and keep the ESP permission in step."""
        with self._lock:
            items = self._all()
            if self._client is not None:
                for item in items:
                    if item["status"] == "PENDING_SEND":
                        self._send(item)
                    elif item["status"] == "PENDING":
                        self._poll(item)
            self._apply(items)

    def _apply(self, items: list[dict[str, Any]]) -> None:
        if self._bridge is None:
            return
        now = self._clock()
        live = next((item for item in items if item["status"] == "APPROVED" and self._window_of(item)[0] <= now < self._window_of(item)[1]), None)
        if live is not None:
            wanted = (live["request_id"], "APPROVED", self._window_of(live)[1].isoformat())
        else:
            latest = items[0]["request_id"] if items else "NONE"
            wanted = (latest, "REJECTED", None)
        if wanted == self._applied:
            return
        try:
            self._bridge.apply_decision(wanted[0], wanted[1], self._window_of(live)[1] if live is not None else None)
        except Exception:
            # ESP unplugged or flashing: stay unapplied so the next tick retries.
            self._applied = None
            return
        self._applied = wanted

    def refresh(self) -> None:
        """Re-send the current permission (the ESP forgets it on reboot)."""
        if self._bridge is None:
            return
        with self._lock:
            try:
                self._bridge.refresh()
            except Exception:
                self._applied = None
