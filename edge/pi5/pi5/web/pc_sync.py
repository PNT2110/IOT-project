from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .cache import MapCache
from .models import CacheProvenance, utcnow


class PcMapSyncError(Exception):
    """A safe, read-only PC map synchronization failure."""


@dataclass(frozen=True)
class PcMapSyncConfig:
    base_url: str
    timeout_seconds: float = 5.0
    stale_after_seconds: int = 300
    max_response_bytes: int = 1_000_000

    def validate(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("PC map sync requires an explicit HTTPS base URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("PC map sync URL must not contain credentials or query data")
        if not (0.5 <= self.timeout_seconds <= 30):
            raise ValueError("PC map sync timeout must be between 0.5 and 30 seconds")
        if not (30 <= self.stale_after_seconds <= 86_400):
            raise ValueError("PC map stale-after must be between 30 seconds and 24 hours")
        if not (16_384 <= self.max_response_bytes <= 10_000_000):
            raise ValueError("PC map response limit is invalid")


class PcMapSyncClient:
    """Fetch the PC public-zone contract without exposing mutation on the Pi."""

    def __init__(self, config: PcMapSyncConfig, *, opener: Callable[..., Any] = urlopen) -> None:
        config.validate()
        self.config = config
        self.opener = opener

    @classmethod
    def from_env(cls) -> "PcMapSyncClient | None":
        base_url = os.getenv("PI_PC_MAP_URL", "").strip()
        if not base_url:
            return None
        return cls(
            PcMapSyncConfig(
                base_url=base_url,
                timeout_seconds=float(os.getenv("PI_PC_MAP_TIMEOUT_SECONDS", "5")),
                stale_after_seconds=int(os.getenv("PI_PC_MAP_STALE_AFTER_SECONDS", "300")),
                max_response_bytes=int(os.getenv("PI_PC_MAP_MAX_RESPONSE_BYTES", "1000000")),
            )
        )

    def sync(self, cache: MapCache) -> dict[str, Any]:
        endpoint = self.config.base_url.rstrip("/") + "/api/v1/public/zones"
        request = Request(endpoint, headers={"Accept": "application/json", "User-Agent": "IOT-Pi-MapSync/1"}, method="GET")
        try:
            with self.opener(request, timeout=self.config.timeout_seconds) as response:
                status = int(getattr(response, "status", 200))
                raw = response.read(self.config.max_response_bytes + 1)
        except Exception as exc:
            cache.invalidate("PC map sync failed")
            raise PcMapSyncError("PC map sync failed") from exc
        if status < 200 or status >= 300:
            cache.invalidate("PC map endpoint returned an error")
            raise PcMapSyncError("PC map endpoint returned an error")
        if len(raw) > self.config.max_response_bytes:
            cache.invalidate("PC map response is too large")
            raise PcMapSyncError("PC map response is too large")
        try:
            envelope = json.loads(raw.decode("utf-8"))
            data = envelope["data"]
            items = data["items"]
            if envelope.get("schema_version") != "v1" or not isinstance(data, dict) or not isinstance(items, list):
                raise ValueError("invalid PC map envelope")
            for item in items:
                if not isinstance(item, dict) or not isinstance(item.get("geometry"), dict):
                    raise ValueError("invalid PC zone item")
        except (UnicodeDecodeError, ValueError, KeyError, TypeError) as exc:
            cache.invalidate("PC map response is invalid")
            raise PcMapSyncError("PC map response is invalid") from exc
        fetched_at = utcnow()
        provenance = CacheProvenance(
            source=endpoint,
            source_type="PC_PUBLIC_API",
            fetched_at=fetched_at,
            generated_at=None,
            cache_version=str(envelope.get("schema_version", "v1")),
            stale_after=fetched_at + timedelta(seconds=self.config.stale_after_seconds),
            license="PC_OPERATOR_POLICY",
            is_stale=False,
        )
        cache.load_remote(data, provenance)
        return cache.read()
