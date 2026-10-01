from __future__ import annotations

from .deps import *  # noqa: F401,F403

router = APIRouter()


@router.get("/public/zones")
def public_zones(request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings)):
    query = select(Zone).where(Zone.visibility == "PUBLIC", Zone.deleted_at.is_(None))
    # Keep legacy fixture provenance out of the public response in
    # production mode, while preserving fixtures for isolated test mode.
    if settings.public_mode:
        query = query.join(ZoneSource, Zone.source_id == ZoneSource.id).where(func.upper(ZoneSource.publisher) != "TEST_FIXTURE")
    rows = db.scalars(query.order_by(Zone.name)).all()
    data = [{"id": z.id, "name": z.name, "geometry": json.loads(z.geometry_json), "visibility": "PUBLIC", "classification": z.classification, "version": z.version, "retrieved_at": z.retrieved_at.isoformat()} for z in rows]
    return ok({"items": data, "count": len(data), "label": "SIMULATED — NOT OFFICIAL AIRSPACE DATA"}, request.state.request_id, _now_iso())


@router.get("/internal/zones")
def internal_zones(request: Request, db: Session = Depends(_db)):
    _require_map_read(request, db)
    rows = db.scalars(select(Zone).where(Zone.deleted_at.is_(None)).order_by(Zone.name)).all()
    data = [{"id": z.id, "name": z.name, "geometry": json.loads(z.geometry_json), "visibility": z.visibility, "classification": z.classification, "source_id": z.source_id, "version": z.version, "retrieved_at": z.retrieved_at.isoformat()} for z in rows]
    return ok({"items": data, "count": len(data), "label": "SIMULATED — NOT OFFICIAL AIRSPACE DATA"}, request.state.request_id, _now_iso())


@router.get("/internal/zone-sources")
def list_zone_sources(request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings)):
    _require_map_read(request, db)
    query = select(ZoneSource).order_by(ZoneSource.retrieved_at.desc())
    if settings.public_mode:
        query = query.where(func.upper(ZoneSource.publisher) != "TEST_FIXTURE")
    rows = db.scalars(query).all()
    items = [{"id": item.id, "publisher": item.publisher, "source_type": item.source_type, "license_name": item.license_name, "checksum": item.checksum, "retrieved_at": item.retrieved_at.isoformat()} for item in rows]
    return ok({"items": items}, request.state.request_id, _now_iso())


@router.post("/internal/zone-sources", status_code=201)
def create_zone_source(body: ZoneSourceCreateRequest, request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _, owner, _ = _require_owner(request, db)
    if settings.public_mode and body.publisher.strip().upper() == "TEST_FIXTURE":
        raise HTTPException(status_code=422, detail={"code": "TEST_SOURCE_FORBIDDEN", "message_for_user": "Test data sources cannot be created in public mode"})
    key = _require_idempotency_key(idempotency_key) if idempotency_key is not None else None
    digest = payload_digest({"action": "CREATE_ZONE_SOURCE", "publisher": body.publisher, "source_type": body.source_type, "license_name": body.license_name, "checksum": body.checksum}) if key else None
    if key and digest:
        replay = _idempotency_replay(db, actor_user_id=owner.id, key=key, digest=digest)
        if replay:
            return ok(json.loads(replay.response_json), request.state.request_id, _now_iso())
    now = utcnow()
    source = ZoneSource(publisher=body.publisher, source_type=body.source_type, license_name=body.license_name, checksum=body.checksum, retrieved_at=now)
    db.add(source)
    db.flush()
    result = {"id": source.id, "publisher": source.publisher, "source_type": source.source_type, "license_name": source.license_name, "checksum": source.checksum, "retrieved_at": source.retrieved_at.isoformat()}
    if key and digest:
        _remember_idempotency(db, actor_user_id=owner.id, key=key, action="CREATE_ZONE_SOURCE", object_type="ZONE_SOURCE", object_id=source.id, digest=digest, data=result, status_code=201)
    record_audit(db, actor_user_id=owner.id, action="CREATE", object_type="ZONE_SOURCE", object_id=source.id, outcome="SUCCESS", request_id=request.state.request_id, metadata={"source_type": source.source_type, "publisher": source.publisher})
    db.commit()
    return ok(result, request.state.request_id, _now_iso())


@router.post("/internal/zones", status_code=201)
def create_zone(body: ZoneCreateRequest, request: Request, db: Session = Depends(_db), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _, user, _ = _require_map_write(request, db)
    key = _require_idempotency_key(idempotency_key) if idempotency_key is not None else None
    digest = payload_digest({"action": "CREATE_ZONE", "name": body.name, "geometry": body.geometry, "visibility": body.visibility, "classification": body.classification, "source_id": body.source_id}) if key else None
    if key and digest:
        replay = _idempotency_replay(db, actor_user_id=user.id, key=key, digest=digest)
        if replay:
            return ok(json.loads(replay.response_json), request.state.request_id, _now_iso())
    try:
        geometry = validate_polygon_geojson(body.geometry, request.app.state.settings.max_zone_bytes)
    except GeometryError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_GEOMETRY", "message_for_user": str(exc)}) from exc
    source = db.get(ZoneSource, body.source_id)
    if not source or (request.app.state.settings.public_mode and source.publisher.strip().upper() == "TEST_FIXTURE"):
        raise HTTPException(status_code=422, detail={"code": "SOURCE_NOT_FOUND", "message_for_user": "Zone source does not exist"})
    now = utcnow()
    zone = Zone(name=body.name, source_id=source.id, geometry_json=json.dumps(geometry, separators=(",", ":")), visibility=body.visibility, classification=body.classification, version=1, retrieved_at=now, created_at=now, updated_at=now)
    db.add(zone)
    db.flush()
    result = {"id": zone.id, "version": zone.version}
    if key and digest:
        _remember_idempotency(db, actor_user_id=user.id, key=key, action="CREATE_ZONE", object_type="ZONE", object_id=zone.id, digest=digest, data=result, status_code=201)
    record_audit(db, actor_user_id=user.id, action="CREATE", object_type="ZONE", object_id=zone.id, outcome="SUCCESS", request_id=request.state.request_id, metadata={"version": 1, "visibility": zone.visibility})
    db.commit()
    return ok(result, request.state.request_id, _now_iso())


@router.patch("/internal/zones/{zone_id}")
def update_zone(zone_id: str, body: ZoneUpdateRequest, request: Request, db: Session = Depends(_db), if_match: str | None = Header(default=None, alias="If-Match"), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _, user, _ = _require_map_write(request, db)
    expected = _parse_if_match(if_match, required=False)
    if expected is None:
        expected = body.version
    key = _require_idempotency_key(idempotency_key) if idempotency_key is not None else None
    digest = payload_digest({"action": "UPDATE_ZONE", "zone_id": zone_id, "version": expected, "name": body.name, "geometry": body.geometry, "visibility": body.visibility, "classification": body.classification, "source_id": body.source_id}) if key else None
    if key and digest:
        replay = _idempotency_replay(db, actor_user_id=user.id, key=key, digest=digest)
        if replay:
            return ok(json.loads(replay.response_json), request.state.request_id, _now_iso())
    zone = db.get(Zone, zone_id)
    if not zone or zone.deleted_at:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message_for_user": "Zone not found"})
    if expected != zone.version:
        raise HTTPException(status_code=409, detail={"code": "VERSION_CONFLICT", "message_for_user": "Zone version has changed"})
    try:
        geometry = validate_polygon_geojson(body.geometry, request.app.state.settings.max_zone_bytes)
    except (GeometryError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_GEOMETRY", "message_for_user": str(exc)}) from exc
    source = db.get(ZoneSource, body.source_id)
    if not source or (request.app.state.settings.public_mode and source.publisher.strip().upper() == "TEST_FIXTURE"):
        raise HTTPException(status_code=422, detail={"code": "SOURCE_NOT_FOUND", "message_for_user": "Zone source does not exist"})
    zone.name = body.name
    zone.geometry_json = json.dumps(geometry, separators=(",", ":"))
    zone.visibility = body.visibility
    zone.classification = body.classification
    zone.source_id = body.source_id
    zone.version += 1
    zone.updated_at = utcnow()
    result = {"id": zone.id, "version": zone.version}
    if key and digest:
        _remember_idempotency(db, actor_user_id=user.id, key=key, action="UPDATE_ZONE", object_type="ZONE", object_id=zone.id, digest=digest, data=result)
    record_audit(db, actor_user_id=user.id, action="UPDATE", object_type="ZONE", object_id=zone.id, outcome="SUCCESS", request_id=request.state.request_id, metadata={"from_version": expected, "to_version": zone.version})
    db.commit()
    return ok(result, request.state.request_id, _now_iso())


@router.delete("/internal/zones/{zone_id}")
def delete_zone(zone_id: str, request: Request, db: Session = Depends(_db), if_match: str | None = Header(default=None, alias="If-Match"), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _, user, _ = _require_map_write(request, db)
    expected = _parse_if_match(if_match)
    key = _require_idempotency_key(idempotency_key) if idempotency_key is not None else None
    digest = payload_digest({"action": "DELETE_ZONE", "zone_id": zone_id, "version": expected}) if key else None
    if key and digest:
        replay = _idempotency_replay(db, actor_user_id=user.id, key=key, digest=digest)
        if replay:
            return ok(json.loads(replay.response_json), request.state.request_id, _now_iso())
    zone = db.get(Zone, zone_id)
    if not zone or zone.deleted_at:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message_for_user": "Zone not found"})
    if expected != zone.version:
        raise HTTPException(status_code=409, detail={"code": "VERSION_CONFLICT", "message_for_user": "Zone version has changed"})
    zone.deleted_at = utcnow()
    zone.version += 1
    result = {"id": zone.id, "deleted": True, "version": zone.version}
    if key and digest:
        _remember_idempotency(db, actor_user_id=user.id, key=key, action="DELETE_ZONE", object_type="ZONE", object_id=zone.id, digest=digest, data=result)
    record_audit(db, actor_user_id=user.id, action="DELETE", object_type="ZONE", object_id=zone.id, outcome="SUCCESS", request_id=request.state.request_id, metadata={"from_version": expected, "to_version": zone.version})
    db.commit()
    return ok(result, request.state.request_id, _now_iso())
