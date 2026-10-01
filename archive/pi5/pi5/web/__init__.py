"""SCOPE-04 Pi-local web foundation.

This package is intentionally separate from ``server.app``.  It contains
local-only, read-only adapters and an offline-first web surface; it has no
PC identity federation and no actuator command channel.
"""

from .app import PiWebConfig, create_pi_app

__all__ = ["PiWebConfig", "create_pi_app"]
