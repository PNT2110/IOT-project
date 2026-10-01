"""Pi routes beyond identity: network setup, camera stream, map tiles,
tuning, active users, firmware update and flight-permission requests."""
from __future__ import annotations

import os
from pathlib import Path
import re
import threading
from typing import Any, Callable
from urllib.request import Request as UrlRequest, urlopen

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response, StreamingResponse

from ..telemetry.esp_command import EspCommandError, set_max_altitude, set_pid
from ..telemetry.esp_link import EspLinkError
from .authority import FlightRequestError
from .firmware import FirmwareUpdateError
from .models import PiRole, envelope, utcnow

PORTAL_URL = "http://192.168.4.1/"
CAPTIVE_PROBES = ("/generate_204", "/gen_204", "/hotspot-detect.html", "/connecttest.txt", "/ncsi.txt", "/redirect", "/canonical.html", "/success.txt")
ACTIVE_SECONDS = 300
TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"


def _fetch_tile(url: str) -> bytes:
    request = UrlRequest(url, headers={"User-Agent": "IOT-Pi-DroneZoneCheck/1 (local map cache)"})
    with urlopen(request, timeout=10) as response:
        return response.read(1_000_000)


def register_extra_routes(
    app: FastAPI,
    *,
    protected: Callable[..., Any],
    csrf_required: Callable[..., bool],
    request_json_object: Callable[..., Any],
    json_error: Callable[..., JSONResponse],
    fetch_tile: Callable[[str], bytes] = _fetch_tile,
) -> None:
    state = app.state

    async def admin(request: Request, *, write: bool = False):
        result = await protected(request)
        if isinstance(result, JSONResponse):
            return result
        session, user = result
        if user.role is not PiRole.ADMIN:
            return json_error(403, "ROLE_FORBIDDEN", "Admin role required")
        if write and not csrf_required(request, session):
            return json_error(403, "CSRF_FAILED", "CSRF validation failed")
        return session, user

    # ---- captive portal and upstream Wi-Fi (screen 1)

    for probe in CAPTIVE_PROBES:
        app.add_api_route(probe, lambda: RedirectResponse(PORTAL_URL, status_code=302), methods=["GET"], include_in_schema=False)

    @app.get("/api/pi/v1/network/status")
    async def network_status() -> JSONResponse:
        return JSONResponse(content=envelope(state.network.status()))

    async def network_gate(request: Request, *, write: bool) -> JSONResponse | None:
        # Before the Pi has an upstream network the setup screen precedes
        # login, so scan/connect are open; afterwards only an admin may change it.
        if not state.network.status().get("upstream_connected"):
            return None
        result = await admin(request, write=write)
        return result if isinstance(result, JSONResponse) else None

    @app.get("/api/pi/v1/network/scan")
    async def network_scan(request: Request) -> JSONResponse:
        denied = await network_gate(request, write=False)
        if denied is not None:
            return denied
        return JSONResponse(content=envelope(state.network.scan()))

    @app.post("/api/pi/v1/network/connect")
    async def network_connect(request: Request) -> JSONResponse:
        denied = await network_gate(request, write=True)
        if denied is not None:
            return denied
        body = await request_json_object(request)
        password = body.get("password")
        result = state.network.connect(str(body.get("ssid", "")), str(password) if password else None)
        return JSONResponse(content=envelope(result))

    # ---- camera stream

    @app.get("/api/pi/v1/camera/mjpeg")
    async def camera_mjpeg(request: Request) -> Response:
        result = await protected(request)
        if isinstance(result, JSONResponse):
            return result
        frames = getattr(state.camera, "mjpeg_frames", None)
        if frames is None:
            return json_error(503, "CAMERA_STREAM_UNAVAILABLE", "Camera stream is not available")

        def body():
            for frame in frames():
                yield b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(frame)).encode() + b"\r\n\r\n" + frame + b"\r\n"

        return StreamingResponse(body(), media_type="multipart/x-mixed-replace; boundary=frame")

    # ---- map tiles (AP clients have no Internet of their own)

    tile_lock = threading.Lock()

    @app.get("/api/pi/v1/tiles/{z}/{x}/{y}.png")
    async def map_tile(z: int, x: int, y: int, request: Request) -> Response:
        result = await protected(request)
        if isinstance(result, JSONResponse):
            return result
        if not (0 <= z <= 19 and 0 <= x < 2 ** z and 0 <= y < 2 ** z):
            return json_error(404, "TILE_NOT_FOUND", "Tile not found")
        cache_dir = Path(os.environ.get("PI_TILE_CACHE_DIR", "/tmp/iot-tiles"))
        path = cache_dir / str(z) / str(x) / f"{y}.png"
        try:
            data = path.read_bytes()
        except OSError:
            try:
                data = fetch_tile(TILE_URL.format(z=z, x=x, y=y))
            except Exception:
                return json_error(502, "TILE_UNAVAILABLE", "Map tile is not available")
            if not data.startswith(b"\x89PNG"):
                return json_error(502, "TILE_UNAVAILABLE", "Map tile is not available")
            with tile_lock:
                try:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                except OSError:
                    pass
        return Response(content=data, media_type="image/png", headers={"Cache-Control": "private, max-age=86400"})

    # ---- tuning

    async def send_tuning(request: Request, build: Callable[[dict], bytes]) -> JSONResponse:
        result = await admin(request, write=True)
        if isinstance(result, JSONResponse):
            return result
        body = await request_json_object(request)
        try:
            line = build(body)
        except (EspCommandError, TypeError, ValueError):
            return json_error(422, "TUNING_INVALID", "Giá trị tinh chỉnh không hợp lệ")
        link = state.esp_link
        if link is None:
            return json_error(503, "ESP_NOT_CONNECTED", "Chưa kết nối ESP32")
        if link.arm_state() == "ARMED":
            return json_error(409, "DRONE_ARMED", "Không đổi thông số khi drone đang ARM")
        try:
            link.send(line)
        except EspLinkError as exc:
            return json_error(503, "ESP_NOT_CONNECTED" if str(exc) != "ESP_LINK_PAUSED" else "ESP_LINK_PAUSED", "Chưa gửi được lệnh tới ESP32")
        return JSONResponse(content=envelope({"sent": line.decode("ascii").strip()}))

    def number(value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("number required")
        return value

    @app.post("/api/pi/v1/tuning/pid")
    async def tuning_pid(request: Request) -> JSONResponse:
        return await send_tuning(request, lambda body: set_pid(str(body.get("axis", "")), number(body.get("kp")), number(body.get("ki")), number(body.get("kd"))))

    @app.post("/api/pi/v1/tuning/max-altitude")
    async def tuning_max_altitude(request: Request) -> JSONResponse:
        return await send_tuning(request, lambda body: set_max_altitude(number(body.get("meters"))))

    @app.get("/api/pi/v1/esp/commands")
    async def esp_commands(request: Request) -> JSONResponse:
        result = await admin(request)
        if isinstance(result, JSONResponse):
            return result
        link = state.esp_link
        return JSONResponse(content=envelope([{"at": at, "line": line} for at, line in (link.sent if link else [])]))

    # ---- active users

    @app.get("/api/pi/v1/admin/active")
    async def admin_active(request: Request) -> JSONResponse:
        result = await admin(request)
        if isinstance(result, JSONResponse):
            return result
        _, actor = result
        now = utcnow()
        recent = {user_id: seen for user_id, seen in state.last_seen.items() if (now - seen).total_seconds() <= ACTIVE_SECONDS}
        users = [{"user_id": item["user_id"], "username": item["username"], "role": item["role"], "last_seen": recent[item["user_id"]].isoformat()} for item in state.auth.list_users(actor) if item["user_id"] in recent]
        return JSONResponse(content=envelope(users))

    # ---- firmware update

    def firmware_error(exc: FirmwareUpdateError) -> JSONResponse:
        status = {"FIRMWARE_REPO_NOT_CONFIGURED": 503, "FIRMWARE_RELEASE_UNAVAILABLE": 502, "ESP_NOT_CONNECTED": 503, "DRONE_ARMED": 409, "VERSION_MISMATCH": 409}.get(exc.code, 400)
        message = {"FIRMWARE_REPO_NOT_CONFIGURED": "Chưa cấu hình kho firmware của nhà sản xuất", "FIRMWARE_RELEASE_UNAVAILABLE": "Không lấy được bản phát hành firmware", "ESP_NOT_CONNECTED": "Chưa kết nối ESP32", "DRONE_ARMED": "Không nạp firmware khi drone đang ARM", "VERSION_MISMATCH": "Đã có bản phát hành khác; hãy kiểm tra lại"}.get(exc.code, "Không cập nhật được firmware")
        return json_error(status, exc.code, message)

    @app.get("/api/pi/v1/firmware/latest")
    async def firmware_latest(request: Request) -> JSONResponse:
        result = await admin(request)
        if isinstance(result, JSONResponse):
            return result
        if state.firmware_updater is None:
            return firmware_error(FirmwareUpdateError("FIRMWARE_REPO_NOT_CONFIGURED"))
        try:
            return JSONResponse(content=envelope(state.firmware_updater.latest()))
        except FirmwareUpdateError as exc:
            return firmware_error(exc)

    @app.post("/api/pi/v1/firmware/flash")
    async def firmware_flash(request: Request) -> JSONResponse:
        result = await admin(request, write=True)
        if isinstance(result, JSONResponse):
            return result
        body = await request_json_object(request)
        if state.firmware_updater is None:
            return firmware_error(FirmwareUpdateError("FIRMWARE_REPO_NOT_CONFIGURED"))
        try:
            job = state.firmware_updater.flash(str(body.get("version", "")))
        except FirmwareUpdateError as exc:
            return firmware_error(exc)
        return JSONResponse(status_code=202, content=envelope(job))

    @app.get("/api/pi/v1/firmware/jobs/{job_id}")
    async def firmware_job(job_id: str, request: Request) -> JSONResponse:
        result = await admin(request)
        if isinstance(result, JSONResponse):
            return result
        job = state.firmware_updater.job(job_id) if state.firmware_updater and re.fullmatch(r"[0-9a-f]{16}", job_id) else None
        if job is None:
            return json_error(404, "NOT_FOUND", "Job not found")
        return JSONResponse(content=envelope(job))

    # ---- flight permission

    @app.get("/api/pi/v1/flight-options")
    async def flight_options(request: Request) -> JSONResponse:
        result = await admin(request)
        if isinstance(result, JSONResponse):
            return result
        return JSONResponse(content=envelope({"vehicles": list(state.flight_requests.vehicles)}))

    @app.get("/api/pi/v1/flight-requests")
    async def list_flight_requests(request: Request) -> JSONResponse:
        result = await admin(request)
        if isinstance(result, JSONResponse):
            return result
        _, user = result
        return JSONResponse(content=envelope(state.flight_requests.list_for(user)))

    @app.post("/api/pi/v1/flight-requests", status_code=201)
    async def create_flight_request(request: Request) -> JSONResponse:
        result = await admin(request, write=True)
        if isinstance(result, JSONResponse):
            return result
        _, user = result
        body = await request_json_object(request)
        try:
            item = state.flight_requests.create(user, body)
        except FlightRequestError as exc:
            return json_error(422, exc.code, "Thông tin xin cấp phép bay không hợp lệ")
        return JSONResponse(status_code=201, content=envelope(item))
