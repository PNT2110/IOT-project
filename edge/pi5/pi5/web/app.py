from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
import pyotp

from .auth import PiAuthError, PiAuthService, smtp_sender_from_env
from .cache import MapCache
from .camera import CameraAdapter, MockCameraAdapter
from .authority import FlightAuthorityService
from .extra_routes import register_extra_routes
from .firmware import FirmwareReadiness
from .models import PiRole, envelope, utcnow
from .pc_sync import PcMapSyncClient, PcMapSyncError
from .telemetry import MockTelemetrySource, TelemetrySource, build_3d_view


class PiRequestBodyError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code


@dataclass(frozen=True)
class PiWebConfig:
    bind_host: str = "127.0.0.1"
    port: int = 8080
    secure_cookies: bool = True
    camera_device: str = "/dev/video0"
    max_request_bytes: int = 1_000_000

    def validate(self) -> None:
        if self.bind_host in {"0.0.0.0", "::", ""}:
            raise ValueError("public or wildcard bind is forbidden for SCOPE-04")
        if self.bind_host not in {"127.0.0.1", "::1", "192.168.4.1"}:
            raise ValueError("bind host must be loopback or the approved local AP address")
        if not (1024 <= self.port <= 65535):
            raise ValueError("unprivileged local port is required")
        if self.max_request_bytes < 1024:
            raise ValueError("max request body size must be at least 1024 bytes")


def create_pi_app(
    config: PiWebConfig | None = None,
    *,
    auth: PiAuthService | None = None,
    camera: CameraAdapter | None = None,
    map_cache: MapCache | None = None,
    map_sync: PcMapSyncClient | None = None,
    telemetry: TelemetrySource | None = None,
    flight_requests: FlightAuthorityService | None = None,
    firmware_readiness: FirmwareReadiness | None = None,
    esp_link: Any | None = None,
    network: Any | None = None,
    firmware_updater: Any | None = None,
) -> FastAPI:
    config = config or PiWebConfig()
    config.validate()
    auth = auth or PiAuthService.from_env(email_sender=smtp_sender_from_env())
    camera = camera or MockCameraAdapter(device_path=config.camera_device)
    map_cache = map_cache or MapCache()
    map_sync = map_sync if map_sync is not None else PcMapSyncClient.from_env()
    telemetry = telemetry or MockTelemetrySource()
    flight_requests = flight_requests or FlightAuthorityService()
    if network is None:
        from ..network.nm import NmcliAdapter
        network = NmcliAdapter()
    firmware_readiness = firmware_readiness or FirmwareReadiness()

    app = FastAPI(
        title="SCOPE-04 Pi Local Web",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.mount("/assets", StaticFiles(directory=Path(__file__).with_name("static")), name="assets")
    ui_dir = Path(__file__).with_name("ui")
    app.mount("/ui", StaticFiles(directory=ui_dir), name="ui")
    app.state.auth = auth
    app.state.camera = camera
    app.state.map_cache = map_cache
    app.state.map_sync = map_sync
    app.state.telemetry = telemetry
    app.state.flight_requests = flight_requests
    app.state.firmware_readiness = firmware_readiness
    app.state.config = config
    app.state.esp_link = esp_link
    app.state.network = network
    app.state.firmware_updater = firmware_updater
    # user_id -> last authenticated request, for the "who is active" view.
    app.state.last_seen = {}

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                too_large = int(content_length) > config.max_request_bytes
            except ValueError:
                too_large = True
            if too_large:
                response = json_error(413, "REQUEST_TOO_LARGE", "Request body is too large")
                response.headers["Cache-Control"] = "no-store"
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["X-Frame-Options"] = "DENY"
                return response
        original_receive = request._receive
        received_bytes = 0

        async def limited_receive():
            nonlocal received_bytes
            message = await original_receive()
            if message.get("type") == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > config.max_request_bytes:
                    raise PiRequestBodyError("REQUEST_TOO_LARGE")
            return message

        request._receive = limited_receive
        try:
            response = await call_next(request)
        except PiRequestBodyError as exc:
            response = json_error(413, exc.code, "Request body is too large")
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        if "Content-Security-Policy" not in response.headers:
            response.headers["Content-Security-Policy"] = "default-src 'self'; connect-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        return response

    @app.exception_handler(PiRequestBodyError)
    async def invalid_body_handler(request: Request, exc: PiRequestBodyError) -> JSONResponse:
        # Keep malformed client input inside the versioned API envelope. Do
        # not echo parser details, body contents or offsets to the caller.
        message = "Request body must be valid JSON" if exc.code == "INVALID_JSON" else "Request body must be a JSON object"
        return JSONResponse(status_code=400, content=envelope(error={"code": exc.code, "message_for_user": message}))

    async def request_json_object(request: Request) -> dict[str, Any]:
        try:
            body = await request.json()
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise PiRequestBodyError("INVALID_JSON") from exc
        if not isinstance(body, dict):
            raise PiRequestBodyError("INVALID_BODY")
        return body

    def json_error(status: int, code: str, message: str) -> JSONResponse:
        return JSONResponse(status_code=status, content=envelope(error={"code": code, "message_for_user": message}))

    def bearer_or_cookie(request: Request) -> str | None:
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            return authorization[7:].strip()
        return request.cookies.get("pi_session")

    def identity(request: Request):
        try:
            session, user = auth.authenticate(bearer_or_cookie(request))
        except PiAuthError as exc:
            raise RuntimeError(exc.code) from exc
        app.state.last_seen[user.user_id] = utcnow()
        return session, user

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(ui_dir / "index.html", media_type="text/html; charset=utf-8")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return envelope({"service": "pi-local-web", "local_only": True, "read_only": True, "camera": camera.status().as_dict()})

    @app.post("/api/pi/v1/auth/challenge")
    async def challenge(request: Request) -> JSONResponse:
        body = await request_json_object(request)
        if body.get("terms_accepted") is not True:
            return json_error(400, "TERMS_REQUIRED", "Terms acceptance is required")
        try:
            challenge_id = auth.start_challenge(str(body.get("username", "")), str(body.get("password", "")), client_key=request.client.host if request.client else "local")
        except PiAuthError as exc:
            if exc.code == "EMAIL_SETUP_REQUIRED":
                return json_error(409, exc.code, "This account must configure an email before login")
            if exc.code == "EMAIL_DELIVERY_UNAVAILABLE":
                return json_error(503, exc.code, "Email delivery is not configured for this Pi account")
            if exc.code == "EMAIL_DELIVERY_FAILED":
                return json_error(503, exc.code, "Email delivery failed; no login challenge was created")
            return json_error(429 if exc.code == "RATE_LIMITED" else 401, exc.code, "Authentication failed")
        return JSONResponse(content=envelope({"challenge_id": challenge_id, "mfa_required": True}))

    @app.post("/api/pi/v1/auth/register")
    async def register(request: Request) -> JSONResponse:
        body = await request_json_object(request)
        if body.get("terms_accepted") is not True:
            return json_error(400, "TERMS_REQUIRED", "Terms acceptance is required")
        try:
            challenge_id = auth.register(str(body.get("username", "")), str(body.get("email", "")), str(body.get("password", "")), str(body.get("password_confirm", "")), client_key=request.client.host if request.client else "local")
        except PiAuthError as exc:
            if exc.code == "REGISTRATION_UNAVAILABLE":
                return json_error(409, exc.code, "Unable to create a Pi account")
            if exc.code == "EMAIL_DELIVERY_UNAVAILABLE":
                return json_error(503, exc.code, "Email delivery is not configured on this Pi")
            if exc.code == "EMAIL_DELIVERY_FAILED":
                return json_error(503, exc.code, "Email delivery failed; no account was created")
            if exc.code == "PERSISTENCE_FAILED":
                return json_error(503, exc.code, "Pi account storage is unavailable; no account was created")
            if exc.code == "RATE_LIMITED":
                return json_error(429, exc.code, "Too many registration attempts")
            return json_error(422, "REGISTRATION_INVALID", "Unable to create a Pi account")
        return JSONResponse(status_code=201, content=envelope({"challenge_id": challenge_id, "next_step": "VERIFY_EMAIL"}))

    @app.post("/api/pi/v1/auth/resend-registration-otp")
    async def resend_registration_otp(request: Request) -> JSONResponse:
        body = await request_json_object(request)
        try:
            challenge_id = auth.resend_registration_otp(str(body.get("challenge_id", "")), client_key=request.client.host if request.client else "local")
        except PiAuthError as exc:
            if exc.code == "EMAIL_DELIVERY_UNAVAILABLE":
                return json_error(503, exc.code, "Email delivery is not configured on this Pi")
            if exc.code == "EMAIL_DELIVERY_FAILED":
                return json_error(503, exc.code, "Email delivery failed; the previous code remains invalid")
            return json_error(429 if exc.code == "RATE_LIMITED" else 400, exc.code, "Unable to resend registration OTP")
        return JSONResponse(content=envelope({"challenge_id": challenge_id, "next_step": "VERIFY_EMAIL"}))

    @app.post("/api/pi/v1/auth/email/setup")
    async def setup_email(request: Request) -> JSONResponse:
        body = await request_json_object(request)
        if body.get("terms_accepted") is not True:
            return json_error(400, "TERMS_REQUIRED", "Terms acceptance is required")
        try:
            challenge_id = auth.start_email_setup(str(body.get("username", "")), str(body.get("password", "")), str(body.get("email", "")), client_key=request.client.host if request.client else "local")
        except PiAuthError as exc:
            if exc.code == "RATE_LIMITED":
                return json_error(429, exc.code, "Too many email setup attempts")
            if exc.code == "EMAIL_DELIVERY_UNAVAILABLE":
                return json_error(503, exc.code, "Email delivery is not configured for this Pi account")
            if exc.code == "EMAIL_DELIVERY_FAILED":
                return json_error(503, exc.code, "Email delivery failed; no email was saved")
            return json_error(409 if exc.code == "EMAIL_ALREADY_CONFIGURED" else 401 if exc.code == "AUTHENTICATION_FAILED" else 422, exc.code, "Email setup cannot be started")
        return JSONResponse(status_code=201, content=envelope({"challenge_id": challenge_id, "next_step": "VERIFY_EMAIL_SETUP"}))

    @app.post("/api/pi/v1/auth/email/resend")
    async def resend_setup_email(request: Request) -> JSONResponse:
        body = await request_json_object(request)
        try:
            challenge_id = auth.resend_email_setup_otp(str(body.get("challenge_id", "")), client_key=request.client.host if request.client else "local")
        except PiAuthError as exc:
            if exc.code == "EMAIL_DELIVERY_UNAVAILABLE":
                return json_error(503, exc.code, "Email delivery is not configured on this Pi")
            if exc.code == "EMAIL_DELIVERY_FAILED":
                return json_error(503, exc.code, "Email delivery failed; the previous code remains invalid")
            return json_error(429 if exc.code == "RATE_LIMITED" else 400, exc.code, "Unable to resend email setup OTP")
        return JSONResponse(content=envelope({"challenge_id": challenge_id, "next_step": "VERIFY_EMAIL_SETUP"}))

    @app.post("/api/pi/v1/auth/email/verify")
    async def verify_setup_email(request: Request) -> JSONResponse:
        body = await request_json_object(request)
        try:
            user = auth.verify_email_setup(str(body.get("challenge_id", "")), str(body.get("code", "")))
        except PiAuthError as exc:
            return json_error(503 if exc.code == "PERSISTENCE_FAILED" else 400, exc.code, "Email setup verification failed")
        return JSONResponse(content=envelope({"email_configured": True, "username": user.username, "next_step": "LOGIN"}))

    @app.post("/api/pi/v1/auth/verify-email")
    async def verify_email(request: Request) -> JSONResponse:
        body = await request_json_object(request)
        try:
            enrollment_token = auth.verify_registration_email(str(body.get("challenge_id", "")), str(body.get("code", "")))
        except PiAuthError as exc:
            return json_error(503 if exc.code == "PERSISTENCE_FAILED" else 400, exc.code, "Email verification failed")
        return JSONResponse(content=envelope({"enrollment_token": enrollment_token, "next_step": "TOTP_ENROLLMENT"}))

    @app.post("/api/pi/v1/auth/mfa/enroll")
    async def enroll_mfa(request: Request) -> JSONResponse:
        token = bearer_or_cookie(request)
        try:
            user, secret = auth.enrollment_details(token or "")
        except PiAuthError as exc:
            return json_error(401, exc.code, "MFA enrollment is not available")
        uri = pyotp.TOTP(secret).provisioning_uri(name=user.email or user.username, issuer_name="IOT Pi 5")
        return JSONResponse(content=envelope({"secret": secret, "otpauth_uri": uri, "warning": "Display once; save the 2FA secret securely"}))

    @app.post("/api/pi/v1/auth/mfa/confirm")
    async def confirm_mfa(request: Request) -> JSONResponse:
        token = bearer_or_cookie(request)
        body = await request_json_object(request)
        try:
            user = auth.confirm_registration_mfa(token or "", str(body.get("code", "")))
        except PiAuthError as exc:
            return json_error(429 if exc.code == "RATE_LIMITED" else 503 if exc.code == "PERSISTENCE_FAILED" else 400, exc.code, "MFA confirmation failed")
        return JSONResponse(content=envelope({"registered": True, "username": user.username, "role": user.role.value, "next_step": "LOGIN"}))

    @app.post("/api/pi/v1/auth/login")
    async def login(request: Request) -> JSONResponse:
        body = await request_json_object(request)
        try:
            if body.get("mfa_challenge_id"):
                session = auth.complete_login(str(body.get("mfa_challenge_id", "")), str(body.get("totp", "")), client_key=request.client.host if request.client else "local")
            else:
                mfa_challenge_id = auth.complete_email_otp(str(body.get("challenge_id", "")), str(body.get("otp", "")), client_key=request.client.host if request.client else "local")
                return JSONResponse(content=envelope({"next_step": "TOTP", "mfa_challenge_id": mfa_challenge_id}))
        except PiAuthError as exc:
            user_message = {
                "MFA_FAILED": "Mã xác thực không đúng. Hãy nhập mã OTP/2FA hiện tại.",
                "CHALLENGE_EXPIRED": "Mã xác thực đã hết hạn. Hãy quay lại đăng nhập để nhận mã mới.",
                "TOTP_REPLAY": "Mã 2FA này đã được sử dụng. Hãy lấy mã 2FA mới.",
                "RATE_LIMITED": "Bạn đã thử quá nhiều lần. Hãy chờ rồi thử lại.",
            }.get(exc.code, "Xác thực thất bại.")
            return json_error(429 if exc.code == "RATE_LIMITED" else 401, exc.code, user_message)
        session_token, csrf = auth.credentials_for_session(session)
        user = auth.authenticate(session_token)[1]
        response = JSONResponse(content=envelope({"authenticated": True, "role": user.role.value}))
        response.set_cookie("pi_session", session_token, httponly=True, secure=config.secure_cookies, samesite="strict", max_age=int(auth.session_ttl.total_seconds()))
        response.set_cookie("pi_csrf", csrf, httponly=False, secure=config.secure_cookies, samesite="strict", max_age=int(auth.session_ttl.total_seconds()))
        return response

    @app.post("/api/pi/v1/auth/resend-login-otp")
    async def resend_login_otp(request: Request) -> JSONResponse:
        body = await request_json_object(request)
        try:
            challenge_id = auth.resend_login_otp(str(body.get("challenge_id", "")), client_key=request.client.host if request.client else "local")
        except PiAuthError as exc:
            if exc.code == "EMAIL_DELIVERY_UNAVAILABLE":
                return json_error(503, exc.code, "Email delivery is not configured on this Pi")
            if exc.code == "EMAIL_DELIVERY_FAILED":
                return json_error(503, exc.code, "Email delivery failed; the previous code remains invalid")
            return json_error(429 if exc.code == "RATE_LIMITED" else 400, exc.code, "Unable to resend login OTP")
        return JSONResponse(content=envelope({"challenge_id": challenge_id, "next_step": "EMAIL_OTP"}))

    def csrf_required(request: Request, session: Any) -> bool:
        # A readable cookie is only a transport for the browser script. The
        # state-changing request must echo it in a header to satisfy the
        # double-submit check; accepting the cookie alone would re-open CSRF.
        return auth.csrf_valid(session, request.headers.get("x-csrf-token"))

    @app.get("/api/pi/v1/auth/me")
    async def me(request: Request) -> JSONResponse:
        try:
            session, user = identity(request)
        except RuntimeError as exc:
            return json_error(401, str(exc), "Authentication required")
        return JSONResponse(content=envelope({"user_id": user.user_id, "username": user.username, "role": user.role.value, "email_configured": bool(user.email), "session_expires_at": session.expires_at.isoformat()}))

    @app.get("/api/pi/v1/profile")
    async def get_profile(request: Request) -> JSONResponse:
        try:
            _, user = identity(request)
        except RuntimeError as exc:
            return json_error(401, str(exc), "Authentication required")
        return JSONResponse(content=envelope(auth.profile_for(user)))

    @app.post("/api/pi/v1/profile/challenge")
    async def profile_challenge(request: Request) -> JSONResponse:
        try:
            session, user = identity(request)
        except RuntimeError as exc:
            return json_error(401, str(exc), "Authentication required")
        if not csrf_required(request, session):
            return json_error(403, "CSRF_FAILED", "CSRF validation failed")
        body = await request_json_object(request)
        fields = ("username", "email", "new_password", "full_name", "license_code", "license_class", "license_expiry")
        changes = {field: str(body[field]) for field in fields if field in body and body[field] is not None}
        try:
            challenge_id = auth.start_profile_update(user, str(body.get("current_password", "")), changes, current_session_id=session.session_id, client_key=request.client.host if request.client else "local")
        except PiAuthError as exc:
            messages = {
                "AUTHENTICATION_FAILED": "Mật khẩu hiện tại không đúng.",
                "EMAIL_REQUIRED": "Tài khoản chưa có email xác thực để nhận OTP.",
                "USERNAME_UNAVAILABLE": "Tên người dùng đã được sử dụng.",
                "EMAIL_UNAVAILABLE": "Email đã được sử dụng.",
                "EMAIL_DELIVERY_UNAVAILABLE": "Chưa cấu hình gửi email OTP.",
                "EMAIL_DELIVERY_FAILED": "Không gửi được OTP; thay đổi chưa được lưu.",
                "PROFILE_INVALID": "Thông tin cập nhật không hợp lệ.",
            }
            code = 503 if exc.code in {"EMAIL_DELIVERY_UNAVAILABLE", "EMAIL_DELIVERY_FAILED"} else 409 if exc.code in {"USERNAME_UNAVAILABLE", "EMAIL_UNAVAILABLE"} else 422 if exc.code == "PROFILE_INVALID" else 401
            return json_error(code, exc.code, messages.get(exc.code, "Không thể bắt đầu cập nhật thông tin"))
        return JSONResponse(status_code=201, content=envelope({"challenge_id": challenge_id, "next_step": "VERIFY_PROFILE_OTP"}))

    @app.post("/api/pi/v1/profile/verify")
    async def verify_profile(request: Request) -> JSONResponse:
        try:
            session, user = identity(request)
        except RuntimeError as exc:
            return json_error(401, str(exc), "Authentication required")
        if not csrf_required(request, session):
            return json_error(403, "CSRF_FAILED", "CSRF validation failed")
        body = await request_json_object(request)
        try:
            result = auth.complete_profile_update(str(body.get("challenge_id", "")), str(body.get("otp", "")), current_session_id=session.session_id, client_key=request.client.host if request.client else "local")
        except PiAuthError as exc:
            messages = {
                "CHALLENGE_EXPIRED": "Mã OTP đã hết hạn. Hãy bắt đầu lại.",
                "MFA_FAILED": "Mã OTP không đúng.",
                "RATE_LIMITED": "Bạn đã nhập sai quá nhiều lần. Hãy bắt đầu lại sau.",
                "EMAIL_DELIVERY_UNAVAILABLE": "Chưa cấu hình email để gửi mã xác nhận địa chỉ mới.",
                "EMAIL_DELIVERY_FAILED": "Không gửi được mã tới email mới; thay đổi chưa được lưu.",
                "PERSISTENCE_FAILED": "Không thể lưu thay đổi; dữ liệu cũ vẫn được giữ nguyên.",
            }
            return json_error(503 if exc.code in {"PERSISTENCE_FAILED", "EMAIL_DELIVERY_UNAVAILABLE", "EMAIL_DELIVERY_FAILED"} else 429 if exc.code == "RATE_LIMITED" else 401, exc.code, messages.get(exc.code, "Không thể xác nhận thay đổi"))
        if isinstance(result, dict):
            return JSONResponse(content=envelope(result))
        return JSONResponse(content=envelope({"updated": True, "profile": auth.profile_for(result)}))

    @app.post("/api/pi/v1/auth/logout")
    async def logout(request: Request) -> JSONResponse:
        try:
            session, user = identity(request)
        except RuntimeError as exc:
            return json_error(401, str(exc), "Authentication required")
        if not csrf_required(request, session):
            return json_error(403, "CSRF_FAILED", "CSRF validation failed")
        auth.logout(session, user, client_key=request.client.host if request.client else "local")
        response = JSONResponse(content=envelope({"authenticated": False}))
        response.delete_cookie("pi_session")
        response.delete_cookie("pi_csrf")
        return response

    @app.post("/api/pi/v1/role-requests")
    async def create_role_request(request: Request) -> JSONResponse:
        result = await protected(request)
        if isinstance(result, JSONResponse):
            return result
        session, user = result
        if not csrf_required(request, session):
            return json_error(403, "CSRF_FAILED", "CSRF validation failed")
        body = await request_json_object(request)
        try:
            item = auth.request_admin(user, str(body.get("reason", "")))
        except PiAuthError as exc:
            if exc.code == "PERSISTENCE_FAILED":
                return json_error(503, exc.code, "Pi account storage is unavailable; the role request was not saved")
            return json_error(409 if exc.code.endswith("PENDING") or exc.code.endswith("GRANTED") else 422, exc.code, "Role request cannot be created")
        return JSONResponse(status_code=201, content=envelope(item))

    @app.get("/api/pi/v1/role-requests")
    async def get_role_requests(request: Request) -> JSONResponse:
        result = await protected(request)
        if isinstance(result, JSONResponse):
            return result
        _, user = result
        try:
            return JSONResponse(content=envelope(auth.list_role_requests(user)))
        except PiAuthError:
            return json_error(403, "ROLE_FORBIDDEN", "Admin role required")

    @app.get("/api/pi/v1/admin/users")
    async def admin_users(request: Request) -> JSONResponse:
        result = await protected(request)
        if isinstance(result, JSONResponse):
            return result
        _, user = result
        try:
            return JSONResponse(content=envelope(auth.list_users(user)))
        except PiAuthError:
            return json_error(403, "ROLE_FORBIDDEN", "Admin role required")

    @app.post("/api/pi/v1/role-requests/{request_id}/decision")
    async def decide_role_request(request_id: str, request: Request) -> JSONResponse:
        result = await protected(request)
        if isinstance(result, JSONResponse):
            return result
        session, user = result
        if not csrf_required(request, session):
            return json_error(403, "CSRF_FAILED", "CSRF validation failed")
        body = await request_json_object(request)
        try:
            item = auth.decide_role_request(user, request_id, str(body.get("decision", "")))
        except PiAuthError as exc:
            if exc.code == "PERSISTENCE_FAILED":
                return json_error(503, exc.code, "Pi account storage is unavailable; the role decision was not saved")
            return json_error(403 if exc.code == "ROLE_FORBIDDEN" else 409, exc.code, "Role request cannot be decided")
        return JSONResponse(content=envelope(item))

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
        return Response(
            content=frame.payload,
            media_type=frame.content_type,
            headers={
                "Cache-Control": "no-store",
                "X-Camera-Sequence": str(frame.sequence),
            },
        )

    @app.get("/api/pi/v1/map/cache")
    async def map_cache_status(request: Request) -> JSONResponse:
        result = await protected(request)
        if isinstance(result, JSONResponse):
            return result
        _, user = result
        if user.role is not PiRole.ADMIN:
            return json_error(403, "ROLE_FORBIDDEN", "Admin role required")
        return JSONResponse(content=envelope(map_cache.read()))

    @app.post("/api/pi/v1/map/sync")
    async def map_sync_route(request: Request) -> JSONResponse:
        result = await protected(request)
        if isinstance(result, JSONResponse):
            return result
        session, user = result
        if user.role is not PiRole.ADMIN:
            return json_error(403, "ROLE_FORBIDDEN", "Admin role required")
        if not csrf_required(request, session):
            return json_error(403, "CSRF_FAILED", "CSRF validation failed")
        if map_sync is None:
            return json_error(503, "PC_MAP_SYNC_UNAVAILABLE", "Chưa cấu hình đồng bộ bản đồ từ PC")
        try:
            return JSONResponse(content=envelope(map_sync.sync(map_cache)))
        except PcMapSyncError:
            return json_error(502, "PC_MAP_SYNC_FAILED", "Không đồng bộ được bản đồ từ PC; dữ liệu cache cũ vẫn được giữ an toàn")

    @app.get("/api/pi/v1/telemetry")
    async def telemetry_status(request: Request) -> JSONResponse:
        result = await protected(request)
        if isinstance(result, JSONResponse):
            return result
        _, user = result
        if user.role is not PiRole.ADMIN:
            return json_error(403, "ROLE_FORBIDDEN", "Admin role required")
        return JSONResponse(content=envelope(telemetry.read()))

    @app.get("/api/pi/v1/3d")
    async def three_d(request: Request) -> JSONResponse:
        result = await protected(request)
        if isinstance(result, JSONResponse):
            return result
        _, user = result
        if user.role is not PiRole.ADMIN:
            return json_error(403, "ROLE_FORBIDDEN", "Admin role required")
        return JSONResponse(content=envelope(build_3d_view(telemetry.read())))

    @app.get("/api/pi/v1/firmware/status")
    async def firmware_status(request: Request) -> JSONResponse:
        result = await protected(request)
        if isinstance(result, JSONResponse):
            return result
        _, user = result
        if user.role is not PiRole.ADMIN:
            return json_error(403, "ROLE_FORBIDDEN", "Admin role required")
        return JSONResponse(content=envelope(firmware_readiness.read()))

    register_extra_routes(app, protected=protected, csrf_required=csrf_required, request_json_object=request_json_object, json_error=json_error)
    return app
