from __future__ import annotations

from .deps import *  # noqa: F401,F403

router = APIRouter()


@router.get("/health")
def health(request: Request, db: Session = Depends(_db)):
    settings = request.app.state.settings
    source_metadata_configured = db.scalar(select(ZoneSource.id).where(func.upper(ZoneSource.publisher) != "TEST_FIXTURE").limit(1)) is not None
    official_public_data_available = db.scalar(
        select(Zone.id)
        .join(ZoneSource, Zone.source_id == ZoneSource.id)
        .where(
            Zone.visibility == "PUBLIC",
            Zone.deleted_at.is_(None),
            ZoneSource.source_type.in_(("OFFICIAL_GEOJSON", "OFFICIAL_API")),
            func.upper(ZoneSource.publisher) != "TEST_FIXTURE",
        )
        .limit(1)
    ) is not None
    return ok({
        "status": "ok",
        "environment": settings.app_env,
        "local_only": not settings.public_mode,
        "runtime_mode": "PUBLIC" if settings.public_mode else "LOCAL",
        # Keep the legacy field, but only count persisted source metadata;
        # AIRSPACE_SOURCE_URL is not an ingestor and must not look live.
        "airspace_source_configured": source_metadata_configured,
        "official_airspace_data_available": official_public_data_available,
        "official_airspace_sync_state": "NOT_IMPLEMENTED",
        "terms_version": settings.terms_version,
    }, request.state.request_id, _now_iso())


@router.get("/history/{object_type}/{object_id}")
def history(object_type: str, object_id: str, request: Request, db: Session = Depends(_db), page: int = 1, page_size: int = 50):
    _, user, _ = _session(request, db)
    allowed = False
    if object_type == "USER":
        target = db.get(User, object_id)
        allowed = bool(target and user.status == "ACTIVE" and user.role in {"OWNER", "ADMIN"})
    elif object_type == "ROLE_ELEVATION":
        item = db.get(RoleElevationRequest, object_id)
        allowed = bool(item and (item.requester_user_id == user.id or (user.role == "OWNER" and user.status == "ACTIVE")))
    elif object_type == "SIMULATED_FLIGHT":
        item = db.get(SimulatedFlightRequest, object_id)
        allowed = bool(item and (item.submitter_user_id == user.id or (user.role in {"OPERATOR", "ADMIN", "OWNER"} and user.status == "ACTIVE")))
    if not allowed:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message_for_user": "History not found"})
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    rows = db.scalars(select(WorkflowHistory).where(WorkflowHistory.object_type == object_type, WorkflowHistory.object_id == object_id).order_by(WorkflowHistory.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return ok({"items": [_history_view(item) for item in rows], "page": page, "page_size": page_size, "redacted": True}, request.state.request_id, _now_iso())


@router.get("/audit")
def audit_events(request: Request, db: Session = Depends(_db), object_type: str | None = None, object_id: str | None = None, page: int = 1, page_size: int = 50):
    _require_owner(request, db)
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    query = select(AuditEvent).order_by(AuditEvent.created_at.desc())
    if object_type:
        query = query.where(AuditEvent.object_type == object_type)
    if object_id:
        query = query.where(AuditEvent.object_id == object_id)
    rows = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    data = [{"id": item.id, "actor_user_id": item.actor_user_id, "action": item.action, "object_type": item.object_type, "object_id": item.object_id, "outcome": item.outcome, "request_id": item.request_id, "metadata": json.loads(item.metadata_redacted or "{}"), "created_at": _iso(item.created_at)} for item in rows]
    return ok({"items": data, "page": page, "page_size": page_size, "redacted": True}, request.state.request_id, _now_iso())


@router.get("/pi/v1/map")
def fake_pi_map(request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings), fake_pi_client: str | None = Header(default=None, alias="X-Fake-Pi-Client"), offline: bool = False):
    if settings.public_mode or not settings.enable_test_adapters:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message_for_user": "Adapter is not available in public mode"})
    _require_active_user(request, db)
    if fake_pi_client != "scope02-test-client":
        raise HTTPException(status_code=401, detail={"code": "PI_CLIENT_AUTH_REQUIRED", "message_for_user": "Fake Pi client identity is required"})
    rows = db.scalars(select(Zone).where(Zone.visibility == "PUBLIC", Zone.deleted_at.is_(None)).order_by(Zone.name)).all()
    return ok({"adapter_version": "v1", "simulated": True, "label": "SIMULATED — NOT A FLIGHT PERMIT", "source": "TEST_FIXTURE", "sync_state": "UNSYNCED" if offline else "SYNCED", "stale": offline, "items": [{"id": z.id, "name": z.name, "geometry": json.loads(z.geometry_json), "simulated": True, "source": "TEST_FIXTURE"} for z in rows]}, request.state.request_id, _now_iso())


@router.get("/pi/v1/status")
def fake_pi_status(request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings), fake_pi_client: str | None = Header(default=None, alias="X-Fake-Pi-Client"), offline: bool = False):
    if settings.public_mode or not settings.enable_test_adapters:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message_for_user": "Adapter is not available in public mode"})
    _, user, _ = _require_active_user(request, db)
    if fake_pi_client != "scope02-test-client":
        raise HTTPException(status_code=401, detail={"code": "PI_CLIENT_AUTH_REQUIRED", "message_for_user": "Fake Pi client identity is required"})
    query = select(SimulatedFlightRequest).order_by(SimulatedFlightRequest.updated_at.desc())
    if user.role not in {"OPERATOR", "ADMIN", "OWNER"}:
        query = query.where(SimulatedFlightRequest.submitter_user_id == user.id)
    rows = db.scalars(query.limit(100)).all()
    return ok({"adapter_version": "v1", "simulated": True, "label": "SIMULATED — NOT A FLIGHT PERMIT", "sync_state": "UNSYNCED" if offline else "SYNCED", "stale": offline, "central_server_reachable": not offline, "items": [{"id": item.id, "status": item.status, "simulated": True, "label": "SIMULATED — NOT A FLIGHT PERMIT", "source": item.source, "version": item.version} for item in rows]}, request.state.request_id, _now_iso())
