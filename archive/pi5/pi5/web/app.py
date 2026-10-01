from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from .auth import PiAuthError, PiAuthService
from .cache import MapCache
from .camera import CameraAdapter, MockCameraAdapter
from .models import PiRole, envelope
from .telemetry import MockTelemetrySource, build_3d_view


@dataclass(frozen=True)
class PiWebConfig:
    bind_host: str = "127.0.0.1"
    port: int = 8080
    secure_cookies: bool = True
    camera_device: str = "/dev/video0"

    def validate(self) -> None:
        if self.bind_host in {"0.0.0.0", "::", ""}:
            raise ValueError("public or wildcard bind is forbidden for SCOPE-04")
        if self.bind_host not in {"127.0.0.1", "::1", "192.168.4.1"}:
            raise ValueError("bind host must be loopback or the approved local AP address")
        if not (1024 <= self.port <= 65535):
            raise ValueError("unprivileged local port is required")


PAGE = """<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Pi Local Web</title></head>
<body><main><h1>Pi Local Web</h1><p>Read-only local dashboard.</p>
<p data-state='camera'>CAMERA: UNAVAILABLE</p><p data-state='telemetry'>TELEMETRY: MOCK / STALE / UNAVAILABLE</p>
<p data-state='map'>MAP: CACHED / STALE / UNAVAILABLE</p><p data-state='three-d'>3D: disabled until orientation is available</p>
<p>No actuator controls are exposed.</p></main></body></html>"""


def create_pi_app(
    config: PiWebConfig | None = None,
    *,
    auth: PiAuthService | None = None,
    camera: CameraAdapter | None = None,
    map_cache: MapCache | None = None,
    telemetry: MockTelemetrySource | None = None,
) -> FastAPI:
    config = config or PiWebConfig()
    config.validate()
    auth = auth or PiAuthService()
    camera = camera or MockCameraAdapter(device_path=config.camera_device)
    map_cache = map_cache or MapCache()
    telemetry = telemetry or MockTelemetrySource()

    app = FastAPI(title="SCOPE-04 Pi Local Web", version="0.1.0", docs_url=None, redoc_url=None)
    app.state.auth = auth
    app.state.camera = camera
    app.state.map_cache = map_cache
    app.state.telemetry = telemetry
    app.state.config = config

    def json_error(status: int, code: str, message: str) -> JSONResponse:
        return JSONResponse(status_code=status, content=envelope(error={"code": code, "message_for_user": message}))

    def bearer_or_cookie(request: Request) -> str | None:
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            return authorization[7:].strip()
        return request.cookies.get("pi_session")

    def identity(request: Request):
        try:
            return auth.authenticate(bearer_or_cookie(request))
        except PiAuthError as exc:
            raise RuntimeError(exc.code) from exc

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return PAGE

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return envelope({"service": "pi-local-web", "local_only": True, "read_only": True, "camera": camera.status().as_dict()})

    @app.post("/api/pi/v1/auth/challenge")
    async def challenge(request: Request) -> JSONResponse:
        body = await request.json()
        try:
            challenge_id = auth.start_challenge(str(body.get("username", "")), str(body.get("password", "")), client_key=request.client.host if request.client else "local")
        except PiAuthError as exc:
            return json_error(429 if exc.code == "RATE_LIMITED" else 401, exc.code, "Authentication failed")
        return JSONResponse(content=envelope({"challenge_id": challenge_id, "mfa_required": True}))

    @app.post("/api/pi/v1/auth/login")
    async def login(request: Request) -> JSONResponse:
        body = await request.json()
        try:
            session = auth.complete_login(str(body.get("challenge_id", "")), str(body.get("otp", "")), client_key=request.client.host if request.client else "local")
        except PiAuthError as exc:
            return json_error(429 if exc.code == "RATE_LIMITED" else 401, exc.code, "Authentication failed")
        session_token, csrf = auth.credentials_for_session(session)
        user = auth.authenticate(session_token)[1]
        response = JSONResponse(content=envelope({"authenticated": True, "role": user.role.value}))
        response.set_cookie("pi_session", session_token, httponly=True, secure=config.secure_cookies, samesite="strict", max_age=int(auth.session_ttl.total_seconds()))
        response.set_cookie("pi_csrf", csrf, httponly=False, secure=config.secure_cookies, samesite="strict", max_age=int(auth.session_ttl.total_seconds()))
        return response

    @app.get("/api/pi/v1/auth/me")
    async def me(request: Request) -> JSONResponse:
        try:
            session, user = identity(request)
        except RuntimeError as exc:
            return json_error(401, str(exc), "Authentication required")
        return JSONResponse(content=envelope({"user_id": user.user_id, "username": user.username, "role": user.role.value, "session_expires_at": session.expires_at.isoformat()}))

    @app.post("/api/pi/v1/auth/logout")
    async def logout(request: Request) -> JSONResponse:
        try:
            session, user = identity(request)
        except RuntimeError as exc:
            return json_error(401, str(exc), "Authentication required")
        if not auth.csrf_valid(session, request.headers.get("x-csrf-token") or request.cookies.get("pi_csrf")):
            return json_error(403, "CSRF_FAILED", "CSRF validation failed")
        auth.logout(session, user, client_key=request.client.host if request.client else "local")
        response = JSONResponse(content=envelope({"authenticated": False}))
        response.delete_cookie("pi_session")
        response.delete_cookie("pi_csrf")
        return response

    async def protected(request: Request) -> tuple[Any, Any] | JSONResponse:
        try:
            return identity(request)
        except RuntimeError as exc:
            return json_error(401, str(exc), "Authentication required")

    @app.get("/api/pi/v1/camera/status")
    async def camera_status(request: Request) -> JSONResponse:
        result = await protected(request)
        if isinstance(result, JSONResponse):
            return result
        return JSONResponse(content=envelope(camera.status().as_dict()))

    @app.get("/api/pi/v1/camera/stream")
    async def camera_stream(request: Request) -> Response:
        result = await protected(request)
        if isinstance(result, JSONResponse):
            return result
        camera.start()
        frame = camera.read_frame()
        if frame is None:
            status = camera.status()
            if getattr(camera, "last_error", None):
                state, error_code, detail = camera.last_error
                return json_error(503, error_code.value, detail)
            return json_error(503, status.error_code.value if status.error_code else "FRAME_UNAVAILABLE", status.detail or status.state.value)
        return Response(content=frame.payload, media_type=frame.content_type, headers={"X-Camera-Sequence": str(frame.sequence)})

    @app.get("/api/pi/v1/map/cache")
    async def map_cache_status(request: Request) -> JSONResponse:
        result = await protected(request)
        if isinstance(result, JSONResponse):
            return result
        return JSONResponse(content=envelope(map_cache.read()))

    @app.get("/api/pi/v1/telemetry")
    async def telemetry_status(request: Request) -> JSONResponse:
        result = await protected(request)
        if isinstance(result, JSONResponse):
            return result
        return JSONResponse(content=envelope(telemetry.read()))

    @app.get("/api/pi/v1/3d")
    async def three_d(request: Request) -> JSONResponse:
        result = await protected(request)
        if isinstance(result, JSONResponse):
            return result
        return JSONResponse(content=envelope(build_3d_view(telemetry.read())))

    return app
