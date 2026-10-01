from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import pyotp

from .auth import SESSION_COOKIE, login_limiter, require_admin, require_csrf, session_user, verify_admin_totp
from .config import settings
from .db import db
from .geofence import geofence
from .models import CameraStatus, LoginRequest, LoginResponse
from .serial_io import command_dispatcher, coordinator, esp_worker, gps_worker, simulated_telemetry, state
from .zone_sync import sync_zones

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)


async def telemetry_loop() -> None:
    while True:
        frame = state.snapshot()
        frame.geofence = geofence.evaluate(frame.gps)
        with state._lock:
            state.frame.geofence = frame.geofence
        await asyncio.sleep(0.2)


async def recorder_loop() -> None:
    """Persist live hardware telemetry at 1 Hz and enforce retention hourly."""
    ticks = 0
    while True:
        frame = state.snapshot()
        if frame.gps_connected or frame.esp_connected:
            with db.connect() as conn:
                conn.execute(
                    "INSERT INTO telemetry_samples(created_at,payload_json) VALUES (?,?)",
                    (datetime.now(timezone.utc).isoformat(), frame.model_dump_json()),
                )
        ticks += 1
        if ticks >= 3600:
            db.cleanup(settings.retention_days, settings.retention_bytes)
            ticks = 0
        await asyncio.sleep(1)


def geofence_sync_is_fresh() -> bool:
    with db.connect() as conn:
        row = conn.execute("SELECT fetched_at,feature_count,status FROM map_sync WHERE id=1").fetchone()
    if not row or row["status"] != "ready" or int(row["feature_count"]) <= 0 or not row["fetched_at"]:
        return False
    try:
        fetched_at = datetime.fromisoformat(row["fetched_at"])
    except ValueError:
        return False
    return datetime.now(timezone.utc) - fetched_at.astimezone(timezone.utc) <= timedelta(hours=24)


async def safety_command_loop() -> None:
    gps_lost_since: float | None = None
    triggered = False
    while True:
        await asyncio.sleep(0.1)
        frame = state.snapshot()
        if not settings.enable_real_flight_commands or not frame.armed:
            gps_lost_since = None
            triggered = False
            continue
        now = asyncio.get_running_loop().time()
        if frame.gps_connected and frame.gps.valid and not frame.gps.stale:
            gps_lost_since = None
        elif gps_lost_since is None:
            gps_lost_since = now
        reason = None
        if frame.geofence.status == "breach":
            reason = "GEOFENCE_BREACH"
        elif gps_lost_since is not None and now - gps_lost_since >= settings.gps_stale_seconds:
            reason = "GPS_LOST"
        if reason and not triggered:
            triggered = True
            command, ack, attempts = await command_dispatcher.land(reason)
            db.audit(
                "automatic_land_ack" if ack and ack.accepted else "automatic_land_failed",
                detail=f"id={command.id};reason={reason};attempts={attempts}",
            )


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    db.initialize()
    geofence.load()
    coordinator.reset()
    gps_worker.start()
    esp_worker.start()
    tasks = [
        asyncio.create_task(telemetry_loop()),
        asyncio.create_task(recorder_loop()),
        asyncio.create_task(safety_command_loop()),
        asyncio.create_task(simulated_telemetry()),
    ]
    yield
    for task in tasks:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    gps_worker.stop()
    esp_worker.stop()
    coordinator.reset()


app = FastAPI(title="IOT Drone Station", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self' ws: wss:; worker-src 'self' blob:; media-src 'self' blob:"
    )
    if settings.cookie_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    if response.headers.get("content-type", "").startswith("text/html"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "version": app.version}


@app.post("/api/v1/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response):
    remote = request.client.host if request.client else "unknown"
    if not login_limiter.allow(remote):
        raise HTTPException(status_code=429, detail="Thử lại sau")
    user = db.authenticate(payload.username, payload.password)
    if not user or not verify_admin_totp(user, payload.totp):
        db.audit("login_failed", payload.username, remote_addr=remote)
        raise HTTPException(status_code=401, detail="Sai tài khoản, mật khẩu hoặc OTP")
    token, csrf = db.create_session(user["id"], settings.session_hours)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        max_age=settings.session_hours * 3600,
        path="/",
    )
    db.audit("login_success", user["username"], remote_addr=remote)
    return LoginResponse(username=user["username"], role=user["role"], csrf_token=csrf)


@app.post("/api/v1/auth/logout")
def logout(request: Request, response: Response, user=Depends(require_csrf)):
    db.delete_session(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/")
    db.audit("logout", user["username"], remote_addr=request.client.host if request.client else None)
    return {"ok": True}


@app.get("/api/v1/auth/me", response_model=LoginResponse)
def me(user=Depends(session_user)):
    return LoginResponse(username=user["username"], role=user["role"], csrf_token=user["csrf_token"])


@app.get("/api/v1/camera/status", response_model=CameraStatus)
def camera_status(_=Depends(session_user)):
    return CameraStatus()


@app.get("/api/v1/status")
def system_status(_=Depends(require_admin)):
    frame = state.snapshot()
    return {
        "gps_connected": frame.gps_connected,
        "esp_connected": frame.esp_connected,
        "geofence_ready": frame.geofence.data_ready,
        "map_ready": settings.map_path.exists(),
        "real_commands_enabled": settings.enable_real_flight_commands,
        "raw_esp_lines": len(state.raw_esp),
        "gps_port": coordinator.assigned.get("gps"),
        "esp_port": coordinator.assigned.get("esp"),
    }


@app.get("/api/v1/telemetry/latest")
def latest_telemetry(_=Depends(require_admin)):
    return state.snapshot()


@app.get("/api/v1/serial/raw")
def raw_serial(_=Depends(require_admin)):
    return {"lines": list(state.raw_esp)}


@app.get("/api/v1/preflight")
def preflight(_=Depends(require_admin)):
    frame = state.snapshot()
    zone_sync_fresh = geofence_sync_is_fresh()
    checks = {
        "gps": frame.gps_connected and frame.gps.valid and not frame.gps.stale,
        "esp": frame.esp_connected,
        "geofence": frame.geofence.data_ready and zone_sync_fresh,
        "geofence_sync_fresh": zone_sync_fresh,
        "map": settings.map_path.exists(),
        "firmware_commands": settings.enable_real_flight_commands,
    }
    return {"ready": all(checks.values()), "checks": checks, "geofence": frame.geofence}


@app.get("/api/v1/map-pack/status")
def map_status(_=Depends(require_admin)):
    path = settings.map_path
    return {
        "ready": path.exists(),
        "path": path.name,
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "region": "TPHCM mới + Côn Đảo",
        "max_zoom": 15,
    }


@app.get("/api/v1/map-pack/file")
def map_file(_=Depends(require_admin)):
    if not settings.map_path.exists():
        raise HTTPException(status_code=404, detail="Map pack chưa được tải")
    return FileResponse(settings.map_path, media_type="application/vnd.pmtiles", filename="hcm.pmtiles")


@app.get("/api/v1/geofence/zones")
def geofence_zones(_=Depends(require_admin)):
    if not settings.zones_path.exists():
        return {"type": "FeatureCollection", "features": []}
    return json.loads(settings.zones_path.read_text(encoding="utf-8"))


@app.post("/api/v1/geofence/sync")
def geofence_sync(user=Depends(require_csrf)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin được phép")
    try:
        result = sync_zones()
        geofence.load()
        db.audit("geofence_sync", user["username"], result["checksum"])
        return result
    except Exception as exc:
        log.exception("Geofence sync failed")
        with db.connect() as conn:
            conn.execute("UPDATE map_sync SET status='failed' WHERE id=1")
        raise HTTPException(status_code=502, detail="Không đồng bộ được dữ liệu vùng cấm") from exc


@app.get("/api/v1/flights")
def flights(_=Depends(require_admin)):
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT created_at,payload_json FROM telemetry_samples ORDER BY id DESC LIMIT 100"
        ).fetchall()
    return [{"created_at": row["created_at"], "telemetry": json.loads(row["payload_json"])} for row in rows]


@app.post("/api/v1/commands/land")
async def land(request: Request, user=Depends(require_csrf)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin được phép")
    if not settings.enable_real_flight_commands:
        db.audit("land_blocked", user["username"], "Firmware capability chưa được mở")
        raise HTTPException(status_code=423, detail="Lệnh bay thật đang bị khóa an toàn")
    frame, ack, attempts = await command_dispatcher.land("ADMIN")
    if attempts == 1 and ack is None and not state.snapshot().esp_connected:
        raise HTTPException(status_code=503, detail="ESP chưa kết nối")
    if ack is None:
        db.audit("land_timeout", user["username"], str(frame.id), request.client.host if request.client else None)
        raise HTTPException(status_code=504, detail="ESP không ACK sau 3 lần thử")
    db.audit("land_ack", user["username"], str(frame.id), request.client.host if request.client else None)
    return {"command": frame, "ack": ack, "attempts": attempts}


@app.websocket("/ws/telemetry")
async def telemetry_ws(websocket: WebSocket):
    session = db.get_session(websocket.cookies.get(SESSION_COOKIE))
    if not session or session["role"] != "admin":
        await websocket.close(code=4403)
        return
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(state.snapshot().model_dump(mode="json"))
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        return


static_dir = settings.static_dir.resolve()
if static_dir.exists():
    map_assets = settings.data_dir / "map-assets"
    if map_assets.exists():
        app.mount("/map-assets", StaticFiles(directory=map_assets), name="map-assets")
    assets = static_dir / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        requested = static_dir / path
        if path and requested.is_file() and static_dir in requested.resolve().parents:
            return FileResponse(requested)
        return FileResponse(static_dir / "index.html")
