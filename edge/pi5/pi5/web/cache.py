from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import CacheProvenance, CacheState


class MapCache:
    """Read-only map cache; network fetching is isolated in ``pc_sync``."""

    def __init__(self) -> None:
        self.payload: dict[str, Any] | None = None
        self.provenance: CacheProvenance | None = None
        self.state = CacheState.UNAVAILABLE
        self.error: str | None = None

    def load_fixture(self, payload: dict[str, Any], provenance: CacheProvenance) -> None:
        self.load_remote(payload, provenance)

    def load_remote(self, payload: dict[str, Any], provenance: CacheProvenance) -> None:
        if not isinstance(payload, dict) or not provenance.cache_version:
            self.state, self.error = CacheState.CORRUPT, "invalid cache fixture"
            return
        self.payload, self.provenance, self.error = payload, provenance, None
        self.state = CacheState.STALE if provenance.is_stale or (provenance.stale_after and provenance.stale_after <= datetime.now(timezone.utc)) else CacheState.AVAILABLE

    def invalidate(self, reason: str = "cache invalidated") -> None:
        self.state, self.error = CacheState.UNAVAILABLE, reason

    def read(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "payload": self.payload,
            "provenance": self.provenance.as_dict() if self.provenance else None,
            "error": self.error,
            "label": "STALE" if self.state == CacheState.STALE else ("UNAVAILABLE" if self.state != CacheState.AVAILABLE else "CACHED"),
        }
