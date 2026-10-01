"""Pi-local web app: identity, camera, map, telemetry, tuning, firmware
update and flight-permission requests.

Separate from ``server.app``: Pi accounts are local to the Pi. The only
command path to the ESP32 is the checked line protocol in
``pi5.telemetry.esp_command``; there is no arm, disarm or motor command.
"""

__all__ = ["PiWebConfig", "create_pi_app"]


def __getattr__(name: str):
    # Imported lazily: ``pi5.telemetry`` modules import ``pi5.web.models``, and
    # an eager import of the app here would make that a circular import.
    if name in __all__:
        from . import app

        return getattr(app, name)
    raise AttributeError(name)
