from __future__ import annotations

from .deps import *  # noqa: F401,F403

router = APIRouter()


@router.post("/flight-requests", status_code=201)
@router.post("/simulated/flight-requests", status_code=201, include_in_schema=False)
def create_flight_request(body: SimulatedFlightCreateRequest, request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _, user, _ = _require_active_user(request, db)
    key = _require_idempotency_key(idempotency_key)
    digest = payload_digest({"action": "CREATE_SIMULATED_FLIGHT", "summary": body.summary, "start": _iso(body.scheduled_start_at), "end": _iso(body.scheduled_end_at), "geometry": body.geometry, "details": _flight_details(body)})
    replay = _idempotency_replay(db, actor_user_id=user.id, key=key, digest=digest)
    if replay:
        return ok(json.loads(replay.response_json), request.state.request_id, _now_iso())
    try:
        geometry = validate_polygon_geojson(body.geometry, settings.max_zone_bytes)
    except GeometryError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_GEOMETRY", "message_for_user": str(exc)}) from exc
    now = utcnow()
    item = SimulatedFlightRequest(submitter_user_id=user.id, summary=body.summary, scheduled_start_at=body.scheduled_start_at.astimezone(timezone.utc), scheduled_end_at=body.scheduled_end_at.astimezone(timezone.utc), simulated_geometry_json=json.dumps(geometry, separators=(",", ":")), status="DRAFT", version=1, simulated=True, source="USER_SIMULATED", created_at=now, updated_at=now)
    _store_flight_details(item, body, settings)
    db.add(item)
    db.flush()
    result = _flight_view(item)
    _remember_idempotency(db, actor_user_id=user.id, key=key, action="CREATE_SIMULATED_FLIGHT", object_type="SIMULATED_FLIGHT", object_id=item.id, digest=digest, data=result, status_code=201)
    record_audit(db, actor_user_id=user.id, action="FLIGHT_CREATE", object_type="SIMULATED_FLIGHT", object_id=item.id, outcome="SUCCESS", request_id=request.state.request_id, metadata={"to_status": "DRAFT", "simulated": True})
    record_history(db, actor_user_id=user.id, object_type="SIMULATED_FLIGHT", object_id=item.id, action="CREATE", from_state=None, to_state="DRAFT", from_version=None, to_version=1, reason=None, request_id=request.state.request_id, metadata={"simulated": True, "source": item.source})
    db.commit()
    return ok(result, request.state.request_id, _now_iso())


@router.get("/flight-requests")
@router.get("/simulated/flight-requests", include_in_schema=False)
def list_flight_requests(request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings), page: int = 1, page_size: int = 25, status_filter: str | None = None):
    _, user, _ = _require_active_user(request, db)
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    query = select(SimulatedFlightRequest).order_by(SimulatedFlightRequest.updated_at.desc())
    if user.role not in {"OPERATOR", "ADMIN", "OWNER"}:
        query = query.where(SimulatedFlightRequest.submitter_user_id == user.id)
    if status_filter:
        if status_filter not in {"DRAFT", "SUBMITTED", "UNDER_REVIEW", "NEEDS_INFORMATION", "REJECTED", "APPROVED_SIMULATED"}:
            raise HTTPException(status_code=422, detail={"code": "INVALID_STATUS", "message_for_user": "Workflow status is invalid"})
        query = query.where(SimulatedFlightRequest.status == status_filter)
    rows = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    names = {device.id: device.name for device in db.scalars(select(Device)).all()}
    return ok({"items": [_flight_view(item, settings, include_details=True, device_name=names.get(item.device_id)) for item in rows], "page": page, "page_size": page_size, "label": "SIMULATED — NOT A FLIGHT PERMIT"}, request.state.request_id, _now_iso())


@router.get("/flight-requests/{request_id}")
@router.get("/simulated/flight-requests/{request_id}", include_in_schema=False)
def get_flight_request(request_id: str, request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings)):
    _, user, _ = _require_active_user(request, db)
    item = db.get(SimulatedFlightRequest, request_id)
    if not item or (item.submitter_user_id != user.id and user.role not in {"OPERATOR", "ADMIN", "OWNER"}):
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message_for_user": "Request not found"})
    device = db.get(Device, item.device_id) if item.device_id else None
    return ok(_flight_view(item, settings, include_details=True, device_name=device.name if device else None), request.state.request_id, _now_iso())


@router.patch("/flight-requests/{request_id}")
@router.patch("/simulated/flight-requests/{request_id}", include_in_schema=False)
def edit_flight_request(request_id: str, body: SimulatedFlightCreateRequest, request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings), if_match: str | None = Header(default=None, alias="If-Match"), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _, user, _ = _require_active_user(request, db)
    item = db.get(SimulatedFlightRequest, request_id)
    if not item or item.submitter_user_id != user.id:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message_for_user": "Request not found"})
    expected = _parse_if_match(if_match)
    key = _require_idempotency_key(idempotency_key) if idempotency_key is not None else None
    digest = payload_digest({"action": "EDIT_SIMULATED_FLIGHT", "request_id": request_id, "version": expected, "summary": body.summary, "scheduled_start_at": body.scheduled_start_at.isoformat(), "scheduled_end_at": body.scheduled_end_at.isoformat(), "geometry": body.geometry, "applicant_full_name": body.applicant_full_name, "license_code": body.license_code, "license_class": body.license_class, "vehicle": body.vehicle, "gps_latitude": body.gps_latitude, "gps_longitude": body.gps_longitude, "gps_accuracy_m": body.gps_accuracy_m}) if key else None
    if key and digest:
        replay = _idempotency_replay(db, actor_user_id=user.id, key=key, digest=digest)
        if replay:
            return ok(json.loads(replay.response_json), request.state.request_id, _now_iso())
    if expected != item.version:
        raise HTTPException(status_code=409, detail={"code": "VERSION_CONFLICT", "message_for_user": "Request has changed; reload before retrying"})
    if item.status not in {"DRAFT", "NEEDS_INFORMATION"}:
        raise HTTPException(status_code=409, detail={"code": "INVALID_TRANSITION", "message_for_user": "Only draft or information-requested items can be edited"})
    try:
        geometry = validate_polygon_geojson(body.geometry, settings.max_zone_bytes)
    except GeometryError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_GEOMETRY", "message_for_user": str(exc)}) from exc
    old_version = item.version
    item.summary = body.summary
    item.scheduled_start_at = body.scheduled_start_at.astimezone(timezone.utc)
    item.scheduled_end_at = body.scheduled_end_at.astimezone(timezone.utc)
    item.simulated_geometry_json = json.dumps(geometry, separators=(",", ":"))
    _store_flight_details(item, body, settings)
    item.version += 1
    item.updated_at = utcnow()
    result = _flight_view(item)
    if key and digest:
        _remember_idempotency(db, actor_user_id=user.id, key=key, action="EDIT_SIMULATED_FLIGHT", object_type="SIMULATED_FLIGHT", object_id=item.id, digest=digest, data=result)
    record_audit(db, actor_user_id=user.id, action="FLIGHT_EDIT", object_type="SIMULATED_FLIGHT", object_id=item.id, outcome="SUCCESS", request_id=request.state.request_id, metadata={"from_version": old_version, "to_version": item.version, "simulated": True})
    record_history(db, actor_user_id=user.id, object_type="SIMULATED_FLIGHT", object_id=item.id, action="EDIT", from_state=item.status, to_state=item.status, from_version=old_version, to_version=item.version, reason=None, request_id=request.state.request_id, metadata={"simulated": True})
    db.commit()
    return ok(result, request.state.request_id, _now_iso())


@router.post("/flight-requests/{request_id}/submit")
@router.post("/simulated/flight-requests/{request_id}/submit", include_in_schema=False)
def submit_flight_request(request_id: str, body: SimulatedFlightActionRequest, request: Request, db: Session = Depends(_db), if_match: str | None = Header(default=None, alias="If-Match"), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _, user, _ = _require_active_user(request, db)
    item = db.get(SimulatedFlightRequest, request_id)
    if not item or item.submitter_user_id != user.id:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message_for_user": "Request not found"})
    key = _require_idempotency_key(idempotency_key)
    expected = _parse_if_match(if_match)
    digest = payload_digest({"action": "SUBMIT_SIMULATED_FLIGHT", "request_id": request_id, "version": expected, "reason": body.reason})
    replay = _idempotency_replay(db, actor_user_id=user.id, key=key, digest=digest)
    if replay:
        return ok(json.loads(replay.response_json), request.state.request_id, _now_iso())
    if expected != item.version:
        raise HTTPException(status_code=409, detail={"code": "VERSION_CONFLICT", "message_for_user": "Request has changed; reload before retrying"})
    if item.status not in {"DRAFT", "NEEDS_INFORMATION"}:
        raise HTTPException(status_code=409, detail={"code": "INVALID_TRANSITION", "message_for_user": "Request cannot be submitted from this state"})
    old_state, old_version = item.status, item.version
    item.status = "SUBMITTED"
    item.version += 1
    item.updated_at = utcnow()
    result = _flight_view(item)
    _remember_idempotency(db, actor_user_id=user.id, key=key, action="SUBMIT_SIMULATED_FLIGHT", object_type="SIMULATED_FLIGHT", object_id=item.id, digest=digest, data=result)
    record_audit(db, actor_user_id=user.id, action="FLIGHT_SUBMIT", object_type="SIMULATED_FLIGHT", object_id=item.id, outcome="SUCCESS", request_id=request.state.request_id, metadata={"from_status": old_state, "to_status": item.status, "simulated": True})
    record_history(db, actor_user_id=user.id, object_type="SIMULATED_FLIGHT", object_id=item.id, action="SUBMIT", from_state=old_state, to_state=item.status, from_version=old_version, to_version=item.version, reason=body.reason, request_id=request.state.request_id, metadata={"simulated": True})
    db.commit()
    return ok(result, request.state.request_id, _now_iso())


@router.post("/flight-requests/{request_id}/review")
@router.post("/simulated/flight-requests/{request_id}/review", include_in_schema=False)
def review_flight_request(request_id: str, body: SimulatedFlightActionRequest, request: Request, db: Session = Depends(_db), if_match: str | None = Header(default=None, alias="If-Match"), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _, reviewer, _ = _require_workflow_reviewer(request, db)
    item = db.get(SimulatedFlightRequest, request_id)
    if not item:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message_for_user": "Request not found"})
    if item.submitter_user_id == reviewer.id:
        raise HTTPException(status_code=403, detail={"code": "SELF_REVIEW_FORBIDDEN", "message_for_user": "A submitter cannot review its own request"})
    key = _require_idempotency_key(idempotency_key)
    expected = _parse_if_match(if_match)
    digest = payload_digest({"action": "START_REVIEW", "request_id": request_id, "version": expected, "reason": body.reason})
    replay = _idempotency_replay(db, actor_user_id=reviewer.id, key=key, digest=digest)
    if replay:
        return ok(json.loads(replay.response_json), request.state.request_id, _now_iso())
    if expected != item.version:
        raise HTTPException(status_code=409, detail={"code": "VERSION_CONFLICT", "message_for_user": "Request has changed; reload before retrying"})
    if item.status != "SUBMITTED":
        raise HTTPException(status_code=409, detail={"code": "INVALID_TRANSITION", "message_for_user": "Only submitted requests can enter review"})
    old_version = item.version
    item.status = "UNDER_REVIEW"
    item.version += 1
    item.updated_at = utcnow()
    result = _flight_view(item)
    _remember_idempotency(db, actor_user_id=reviewer.id, key=key, action="START_REVIEW", object_type="SIMULATED_FLIGHT", object_id=item.id, digest=digest, data=result)
    record_audit(db, actor_user_id=reviewer.id, action="FLIGHT_REVIEW_START", object_type="SIMULATED_FLIGHT", object_id=item.id, outcome="SUCCESS", request_id=request.state.request_id, metadata={"from_status": "SUBMITTED", "to_status": item.status, "simulated": True})
    record_history(db, actor_user_id=reviewer.id, object_type="SIMULATED_FLIGHT", object_id=item.id, action="REVIEW_START", from_state="SUBMITTED", to_state=item.status, from_version=old_version, to_version=item.version, reason=body.reason, request_id=request.state.request_id, metadata={"simulated": True})
    db.commit()
    return ok(result, request.state.request_id, _now_iso())


@router.post("/flight-requests/{request_id}/decision")
@router.post("/simulated/flight-requests/{request_id}/decision", include_in_schema=False)
def decide_flight_request(request_id: str, body: SimulatedFlightDecisionRequest, request: Request, db: Session = Depends(_db), if_match: str | None = Header(default=None, alias="If-Match"), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _, reviewer, _ = _require_workflow_reviewer(request, db)
    item = db.get(SimulatedFlightRequest, request_id)
    if not item:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message_for_user": "Request not found"})
    if item.submitter_user_id == reviewer.id:
        raise HTTPException(status_code=403, detail={"code": "SELF_REVIEW_FORBIDDEN", "message_for_user": "A submitter cannot review its own request"})
    key = _require_idempotency_key(idempotency_key)
    expected = _parse_if_match(if_match)
    digest = payload_digest({"action": "DECIDE_SIMULATED_FLIGHT", "request_id": request_id, "version": expected, "decision": body.decision, "reason": body.reason})
    replay = _idempotency_replay(db, actor_user_id=reviewer.id, key=key, digest=digest)
    if replay:
        return ok(json.loads(replay.response_json), request.state.request_id, _now_iso())
    if expected != item.version:
        raise HTTPException(status_code=409, detail={"code": "VERSION_CONFLICT", "message_for_user": "Request has changed; reload before retrying"})
    # Pi device requests are decided in one step; PC web requests still pass
    # through the explicit review state first.
    decidable = {"UNDER_REVIEW", "SUBMITTED"} if item.device_id else {"UNDER_REVIEW"}
    if item.status not in decidable:
        raise HTTPException(status_code=409, detail={"code": "INVALID_TRANSITION", "message_for_user": "Only requests under review can receive a decision"})
    old_state, old_version = item.status, item.version
    item.status = body.decision
    item.version += 1
    item.updated_at = utcnow()
    result = _flight_view(item)
    _remember_idempotency(db, actor_user_id=reviewer.id, key=key, action="DECIDE_SIMULATED_FLIGHT", object_type="SIMULATED_FLIGHT", object_id=item.id, digest=digest, data=result)
    record_audit(db, actor_user_id=reviewer.id, action="FLIGHT_DECISION", object_type="SIMULATED_FLIGHT", object_id=item.id, outcome="SUCCESS", request_id=request.state.request_id, metadata={"from_status": old_state, "to_status": item.status, "simulated": True})
    record_history(db, actor_user_id=reviewer.id, object_type="SIMULATED_FLIGHT", object_id=item.id, action="DECISION", from_state=old_state, to_state=item.status, from_version=old_version, to_version=item.version, reason=body.reason, request_id=request.state.request_id, metadata={"simulated": True, "label": "SIMULATED — NOT A FLIGHT PERMIT"})
    db.commit()
    return ok(result, request.state.request_id, _now_iso())
