from __future__ import annotations

import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text

from .api import build_router
from .config import Settings, load_settings, validate_allowed_origins
from .db import make_engine, make_session_factory
from .mail import email_sender_for_settings
from .models import Base
from .services import seed_demo_zones


logger = logging.getLogger(__name__)


class RequestBodyTooLarge(Exception):
    """Raised while receiving a chunked request that exceeds the configured cap."""


def create_app(settings: Settings | None = None, *, initialize_schema: bool = False) -> FastAPI:
    settings = settings or load_settings()
    validate_allowed_origins(settings.allowed_origins)
    if settings.max_request_bytes < 1024:
        raise RuntimeError("MAX_REQUEST_BYTES must be at least 1024 bytes")
    if settings.public_mode and not settings.cookie_secure:
        raise RuntimeError("COOKIE_SECURE must be enabled in public mode")
    if settings.public_mode and settings.seed_demo_data:
        raise RuntimeError("SEED_DEMO_DATA must be disabled in public mode")
    if settings.public_mode and settings.app_env.lower() in {"development", "test"}:
        raise RuntimeError("PUBLIC_MODE requires a non-development APP_ENV")
    if settings.public_mode and (not settings.smtp_host or not settings.smtp_from):
        raise RuntimeError("PUBLIC_MODE requires SMTP_HOST and SMTP_FROM")
    if not settings.terms_version.strip():
        raise RuntimeError("TERMS_VERSION must not be empty")
    for name in ("session_ttl_minutes", "challenge_ttl_minutes", "auth_rate_limit_window_seconds", "auth_rate_limit_max_attempts", "auth_rate_limit_max_entries", "registration_rate_limit_max_attempts", "auth_challenge_rate_limit_max_attempts"):
        if getattr(settings, name) <= 0:
            raise RuntimeError(f"{name} must be positive")
    engine = make_engine(settings.database_url)
    factory = make_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if initialize_schema:
            Base.metadata.create_all(engine)
        # Establish a real database connection during startup. A previous
        # broad exception handler let a broken/missing production database
        # continue serving a green process that could only fail later on API
        # requests. Normal deployments must run Alembic before starting.
        if not initialize_schema and not inspect(engine).has_table("users"):
            raise RuntimeError("Database schema is missing; run alembic upgrade head before starting the server")
        with factory() as db:
            db.execute(text("SELECT 1"))
            if settings.seed_demo_data:
                seed_demo_zones(db)
        yield
        engine.dispose()

    app = FastAPI(
        title="IOT Airspace Control — PC Server",
        version="0.2.0",
        lifespan=lifespan,
        docs_url=None if settings.public_mode else "/docs",
        redoc_url=None if settings.public_mode else "/redoc",
        openapi_url=None if settings.public_mode else "/openapi.json",
    )
    app.state.settings = settings
    app.state.session_factory = factory
    app.state.fake_mail = email_sender_for_settings(settings)
    app.state.factor_failures = {}
    app.state.auth_failures = {}
    app.state.registration_failures = {}
    app.state.auth_challenge_failures = {}
    app.state.device_nonces = {}
    app.state.latest_telemetry = {}
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.allowed_origins), allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type", "If-Match", "Idempotency-Key", "X-CSRF-Token", "X-Request-ID"])

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        supplied_request_id = request.headers.get("X-Request-ID", "").strip()
        try:
            request.state.request_id = str(uuid.UUID(supplied_request_id)) if supplied_request_id else str(uuid.uuid4())
        except ValueError:
            request.state.request_id = str(uuid.uuid4())
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                too_large = int(content_length) > settings.max_request_bytes
            except ValueError:
                too_large = True
            if too_large:
                response = JSONResponse(status_code=413, content={"schema_version": "v1", "request_id": request.state.request_id, "data": None, "error": {"code": "REQUEST_TOO_LARGE", "message_for_user": "Request body is too large"}, "observed_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()})
                response.headers["X-Request-ID"] = request.state.request_id
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
                if received_bytes > settings.max_request_bytes:
                    raise RequestBodyTooLarge
            return message

        request._receive = limited_receive
        try:
            response = await call_next(request)
        except RequestBodyTooLarge:
            response = JSONResponse(status_code=413, content={"schema_version": "v1", "request_id": request.state.request_id, "data": None, "error": {"code": "REQUEST_TOO_LARGE", "message_for_user": "Request body is too large"}, "observed_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()})
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        if settings.public_mode and settings.cookie_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if not request.url.path.startswith(("/docs", "/redoc")):
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        if request.url.path.startswith("/api/v1"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": "HTTP_ERROR", "message_for_user": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content={"schema_version": "v1", "request_id": getattr(request.state, "request_id", ""), "data": None, "error": detail, "observed_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()})

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(status_code=422, content={"schema_version": "v1", "request_id": getattr(request.state, "request_id", ""), "data": None, "error": {"code": "VALIDATION_ERROR", "message_for_user": str(exc)}, "observed_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()})

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(request: Request, exc: RequestValidationError):
        invalid_fields = {
            str(error["loc"][-1])
            for error in exc.errors()
            if error.get("loc")
        }
        if "email" in invalid_fields:
            message = "Email không hợp lệ. Hãy kiểm tra lại địa chỉ email."
        elif invalid_fields.intersection({"password", "password_confirm"}):
            message = "Mật khẩu không hợp lệ hoặc xác nhận mật khẩu không khớp."
        else:
            message = "Thông tin chưa hợp lệ. Hãy kiểm tra các trường bắt buộc."
        return JSONResponse(status_code=422, content={"schema_version": "v1", "request_id": getattr(request.state, "request_id", ""), "data": None, "error": {"code": "VALIDATION_ERROR", "message_for_user": message}, "observed_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Keep unexpected implementation/DB errors out of the public response
        # while retaining a server-side traceback tied to the request ID.
        logger.exception("Unhandled request error request_id=%s", getattr(request.state, "request_id", ""), exc_info=exc)
        return JSONResponse(status_code=500, content={"schema_version": "v1", "request_id": getattr(request.state, "request_id", ""), "data": None, "error": {"code": "INTERNAL_ERROR", "message_for_user": "An internal server error occurred"}, "observed_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()})

    from .routers import telemetry

    app.include_router(build_router())
    app.include_router(telemetry.router, prefix="/api/v1")
    return app


# Uvicorn loads this object after the operator supplies SESSION_SECRET. Keeping
# import-time configuration lazy allows isolated unit tests to use create_app()
# with an explicit Settings object without manufacturing a default secret.
app = create_app() if __import__("os").getenv("SESSION_SECRET") else None
