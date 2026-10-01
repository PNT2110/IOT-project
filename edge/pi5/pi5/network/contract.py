from __future__ import annotations

from typing import Any

from .models import NetworkStatus


def status_contract(status: NetworkStatus) -> dict[str, Any]:
    """Return the versioned redacted PC-mock contract; never includes credentials."""
    return status.as_dict()
