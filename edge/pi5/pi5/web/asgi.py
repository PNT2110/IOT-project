"""ASGI entry point for the Pi web app.

Wires the real camera, the ESP32 serial link, NetworkManager, the PC authority
client and the firmware updater from the environment, and starts the
background loops. Importing this module opens no listener; uvicorn does.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
import threading

from .app import PiWebConfig, create_pi_app
from .auth import PiAuthService, smtp_sender_from_env
from .authority import AuthorityClient, FlightAuthorityService
from .camera import V4L2CameraAdapter
from .firmware import FirmwareUpdater
from .runtime import validate_runtime_environment
from ..network.nm import NmcliAdapter
from ..telemetry.esp_command import EspFlightAuthorizationBridge
from ..telemetry.esp_link import EspLink

validate_runtime_environment(os.environ)

camera_device = os.environ.get("PI_CAMERA_DEVICE", "/dev/video0")
esp_link = EspLink.for_device(os.environ.get("PI_ESP_USB_DEVICE") or None)


def _gps() -> dict | None:
    sample = esp_link.read()
    if sample.get("fix_state") != "FIX" or sample.get("latitude") is None or sample.get("longitude") is None:
        return None
    gnss = (sample.get("device") or {}).get("gnss") or {}
    return {"lat": sample["latitude"], "lon": sample["longitude"], "fix_state": "FIX", "satellites": gnss.get("satellites")}


flight_requests = FlightAuthorityService(
    client=AuthorityClient.from_env(),
    bridge=EspFlightAuthorizationBridge(esp_link.send),
    gps=_gps,
    store_path=os.environ.get("PI_FLIGHT_DB_PATH") or None,
    vehicles=tuple(item.strip() for item in os.environ.get("PI_VEHICLES", "F450 PNT PVD").split(",") if item.strip()),
    window_minutes=int(os.environ.get("PI_FLIGHT_WINDOW_MIN", "60")),
)

app = create_pi_app(
    PiWebConfig(camera_device=camera_device, secure_cookies=os.environ.get("PI_COOKIE_SECURE", "true").strip().lower() != "false"),
    auth=PiAuthService.from_env(email_sender=smtp_sender_from_env()),
    camera=V4L2CameraAdapter(camera_device),
    telemetry=esp_link,
    flight_requests=flight_requests,
    esp_link=esp_link,
    network=NmcliAdapter(upstream_iface=os.environ.get("PI_UPSTREAM_IFACE", "wlan1"), ap_iface=os.environ.get("PI_AP_IFACE", "wlan0"), ap_ssid=os.environ.get("PI_AP_SSID") or None),
    firmware_updater=FirmwareUpdater.from_env(link=esp_link, arm_state=esp_link.arm_state),
)

_stop = threading.Event()


def _background() -> None:
    """Flight decisions every 5 s, ESP permission refresh every 30 s, map sync every 60 s."""
    ticks = 0
    while not _stop.wait(5):
        ticks += 1
        try:
            flight_requests.tick()
            if ticks % 6 == 0:
                flight_requests.refresh()
            if ticks % 12 == 1 and app.state.map_sync is not None:
                app.state.map_sync.sync(app.state.map_cache)
        except Exception:
            # A failed cycle must not end the loop; the next one retries.
            continue


@asynccontextmanager
async def _lifespan(_app):
    esp_link.start()
    threading.Thread(target=_background, name="pi-background", daemon=True).start()
    yield
    _stop.set()
    esp_link.stop()


app.router.lifespan_context = _lifespan
