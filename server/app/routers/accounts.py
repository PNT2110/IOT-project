from __future__ import annotations

from .deps import *  # noqa: F401,F403

router = APIRouter()


@router.get("/account-review/capabilities")
def account_review_capabilities(request: Request, db: Session = Depends(_db)):
    _, viewer, _ = _session(request, db)
    return ok(_effective_review_capabilities(db, viewer), request.state.request_id, _now_iso())


@router.get("/account-review/users")
def account_review_users(request: Request, db: Session = Depends(_db), status_filter: str | None = None, role: str | None = None, page: int = 1, page_size: int = 25):
    _, reviewer, _ = _require_account_status_reviewer(request, db)
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    query = select(User).order_by(User.created_at.desc())
    if status_filter:
        if status_filter not in {"PENDING", "ACTIVE", "REJECTED", "SUSPENDED"}:
            raise HTTPException(status_code=422, detail={"code": "INVALID_STATUS", "message_for_user": "Account status is invalid"})
        query = query.where(User.status == status_filter)
    if role:
        if role not in {"GUEST", "OPERATOR", "ADMIN", "OWNER"}:
            raise HTTPException(status_code=422, detail={"code": "INVALID_ROLE", "message_for_user": "Account role is invalid"})
        query = query.where(User.role == role)
    rows = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return ok({"items": [_account_view(item) for item in rows], "page": page, "page_size": page_size, "role_policy": "TWO_LEVEL", "effective_capabilities": _effective_review_capabilities(db, reviewer)}, request.state.request_id, _now_iso())


@router.get("/account-review/users/{user_id}")
def account_review_user(user_id: str, request: Request, db: Session = Depends(_db)):
    _, reviewer, _ = _require_account_status_reviewer(request, db)
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message_for_user": "Account not found"})
    history = db.scalars(select(WorkflowHistory).where(WorkflowHistory.object_type == "USER", WorkflowHistory.object_id == user.id).order_by(WorkflowHistory.created_at.desc()).limit(50)).all()
    return ok({"account": _account_view(user), "history": [_history_view(item) for item in history], "effective_capabilities": _effective_review_capabilities(db, reviewer)}, request.state.request_id, _now_iso())


@router.post("/account-review/users/{user_id}/status")
def account_review_status(user_id: str, body: AccountStatusRequest, request: Request, db: Session = Depends(_db), if_match: str | None = Header(default=None, alias="If-Match"), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _, reviewer, _ = _require_account_status_reviewer(request, db)
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message_for_user": "Account not found"})
    if target.id == reviewer.id:
        raise HTTPException(status_code=403, detail={"code": "SELF_REVIEW_FORBIDDEN", "message_for_user": "An account cannot review itself"})
    expected = _parse_if_match(if_match)
    key = _require_idempotency_key(idempotency_key)
    digest = payload_digest({"action": "ACCOUNT_STATUS_CHANGE", "user_id": target.id, "version": expected, "status": body.status, "role": body.role, "reason": body.reason})
    replay = _idempotency_replay(db, actor_user_id=reviewer.id, key=key, digest=digest)
    if replay:
        return ok(json.loads(replay.response_json), request.state.request_id, _now_iso())
    if target.role == "OWNER":
        raise HTTPException(status_code=403, detail={"code": "OWNER_PROTECTED", "message_for_user": "The main account cannot be changed here"})
    if body.status == "ACTIVE" and target.status == "PENDING" and body.role is None:
        raise HTTPException(status_code=422, detail={"code": "ROLE_REQUIRED", "message_for_user": "Choose level 1 (Admin) or level 2 (Operator) when approving an account"})
    if body.status == "ACTIVE" and (not target.email_verified_at or not target.credential or not target.credential.totp_active):
        raise HTTPException(status_code=409, detail={"code": "ACCOUNT_NOT_READY", "message_for_user": "Email verification and MFA setup must be complete before activation"})
    if expected != target.version:
        raise HTTPException(status_code=409, detail={"code": "VERSION_CONFLICT", "message_for_user": "Account has changed; reload before retrying"})
    transitions = {"PENDING": {"ACTIVE", "REJECTED"}, "ACTIVE": {"SUSPENDED", "REJECTED"}, "SUSPENDED": {"ACTIVE"}, "REJECTED": set()}
    if body.status not in transitions.get(target.status, set()):
        raise HTTPException(status_code=409, detail={"code": "INVALID_TRANSITION", "message_for_user": "Account status transition is not allowed"})
    old_status = target.status
    old_version = target.version
    now = utcnow()
    target.status = body.status
    if body.status == "ACTIVE" and old_status == "PENDING":
        target.role = body.role
    target.version += 1
    target.updated_at = now
    if body.status in {"REJECTED", "SUSPENDED"}:
        for session in db.scalars(select(SessionRecord).where(SessionRecord.user_id == target.id, SessionRecord.revoked_at.is_(None))).all():
            session.revoked_at = now
    result = {"account": _account_view(target), "label": "SIMULATED — NOT A FLIGHT PERMIT"}
    _remember_idempotency(db, actor_user_id=reviewer.id, key=key, action="ACCOUNT_STATUS_CHANGE", object_type="USER", object_id=target.id, digest=digest, data=result)
    record_audit(db, actor_user_id=reviewer.id, action="ACCOUNT_STATUS_CHANGE", object_type="USER", object_id=target.id, outcome="SUCCESS", request_id=request.state.request_id, metadata={"from_status": old_status, "to_status": body.status})
    record_history(db, actor_user_id=reviewer.id, object_type="USER", object_id=target.id, action="ACCOUNT_STATUS_CHANGE", from_state=old_status, to_state=body.status, from_version=old_version, to_version=target.version, reason=body.reason, request_id=request.state.request_id)
    db.commit()
    return ok(result, request.state.request_id, _now_iso())


@router.post("/account-review/users/{user_id}/role")
def account_review_role(user_id: str, body: AccountRoleRequest, request: Request, db: Session = Depends(_db)):
    _, reviewer, _ = _require_account_status_reviewer(request, db)
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message_for_user": "Account not found"})
    if target.id == reviewer.id:
        raise HTTPException(status_code=403, detail={"code": "SELF_REVIEW_FORBIDDEN", "message_for_user": "An account cannot review itself"})
    if target.role == "OWNER":
        raise HTTPException(status_code=403, detail={"code": "OWNER_PROTECTED", "message_for_user": "The main account cannot be changed here"})
    if target.status != "ACTIVE":
        raise HTTPException(status_code=409, detail={"code": "ACCOUNT_NOT_ACTIVE", "message_for_user": "Only active accounts can change level"})
    old_role, old_version = target.role, target.version
    if old_role != body.role:
        target.role = body.role
        target.version += 1
        target.updated_at = utcnow()
        record_audit(db, actor_user_id=reviewer.id, action="ACCOUNT_ROLE_CHANGE", object_type="USER", object_id=target.id, outcome="SUCCESS", request_id=request.state.request_id, metadata={"from_role": old_role, "to_role": body.role})
        record_history(db, actor_user_id=reviewer.id, object_type="USER", object_id=target.id, action="ACCOUNT_ROLE_CHANGE", from_state=old_role, to_state=body.role, from_version=old_version, to_version=target.version, reason=body.reason, request_id=request.state.request_id)
        db.commit()
    return ok({"account": _account_view(target)}, request.state.request_id, _now_iso())


@router.post("/role-elevations")
def create_role_elevation(body: RoleElevationCreateRequest, request: Request, db: Session = Depends(_db), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _, requester, _ = _require_active_user(request, db)
    if requester.role in {"ADMIN", "OWNER"} or (requester.role == "OPERATOR" and body.requested_role != "ADMIN"):
        raise HTTPException(status_code=409, detail={"code": "ROLE_REQUEST_NOT_NEEDED", "message_for_user": "This role request is not available for the current role"})
    key = _require_idempotency_key(idempotency_key)
    digest = payload_digest({"action": "CREATE_ROLE_ELEVATION", "requested_role": body.requested_role, "reason": body.reason})
    replay = _idempotency_replay(db, actor_user_id=requester.id, key=key, digest=digest)
    if replay:
        return ok(json.loads(replay.response_json), request.state.request_id, _now_iso())
    open_request = db.scalar(select(RoleElevationRequest).where(RoleElevationRequest.requester_user_id == requester.id, RoleElevationRequest.requested_role == body.requested_role, RoleElevationRequest.status == "PENDING"))
    if open_request:
        raise HTTPException(status_code=409, detail={"code": "DUPLICATE_OPEN_REQUEST", "message_for_user": "An open request for this role already exists"})
    now = utcnow()
    item = RoleElevationRequest(requester_user_id=requester.id, requested_role=body.requested_role, status="PENDING", reason=body.reason, version=1, created_at=now, updated_at=now)
    db.add(item)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "DUPLICATE_OPEN_REQUEST", "message_for_user": "An open request for this role already exists"}) from exc
    result = _elevation_view(item)
    _remember_idempotency(db, actor_user_id=requester.id, key=key, action="CREATE_ROLE_ELEVATION", object_type="ROLE_ELEVATION", object_id=item.id, digest=digest, data=result, status_code=201)
    record_audit(db, actor_user_id=requester.id, action="ROLE_ELEVATION_CREATE", object_type="ROLE_ELEVATION", object_id=item.id, outcome="SUCCESS", request_id=request.state.request_id, metadata={"requested_role": item.requested_role})
    record_history(db, actor_user_id=requester.id, object_type="ROLE_ELEVATION", object_id=item.id, action="CREATE", from_state=None, to_state="PENDING", from_version=None, to_version=1, reason=body.reason, request_id=request.state.request_id, metadata={"requested_role": item.requested_role})
    db.commit()
    return ok(result, request.state.request_id, _now_iso())


@router.get("/role-elevations")
def list_role_elevations(request: Request, db: Session = Depends(_db)):
    _, requester, _ = _session(request, db)
    rows = db.scalars(select(RoleElevationRequest).where(RoleElevationRequest.requester_user_id == requester.id).order_by(RoleElevationRequest.created_at.desc()).limit(100)).all()
    return ok({"items": [_elevation_view(item) for item in rows]}, request.state.request_id, _now_iso())


@router.get("/role-elevations/review")
def review_role_elevations(request: Request, db: Session = Depends(_db)):
    _, reviewer, _ = _require_role_reviewer(request, db)
    query = select(RoleElevationRequest).where(RoleElevationRequest.status == "PENDING")
    rows = db.scalars(query.order_by(RoleElevationRequest.created_at)).all()
    return ok({"items": [_elevation_view(item, db.get(User, item.requester_user_id)) for item in rows], "policy": "TWO_LEVEL", "effective_capabilities": _effective_review_capabilities(db, reviewer)}, request.state.request_id, _now_iso())


@router.post("/role-elevations/{request_id}/decision")
def decide_role_elevation(request_id: str, body: RoleElevationDecisionRequest, request: Request, db: Session = Depends(_db), if_match: str | None = Header(default=None, alias="If-Match"), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _, reviewer, _ = _require_role_reviewer(request, db)
    item = db.get(RoleElevationRequest, request_id)
    if not item:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message_for_user": "Role request not found"})
    if item.requester_user_id == reviewer.id:
        raise HTTPException(status_code=403, detail={"code": "SELF_REVIEW_FORBIDDEN", "message_for_user": "A role request cannot review itself"})
    expected = _parse_if_match(if_match)
    key = _require_idempotency_key(idempotency_key)
    digest = payload_digest({"action": "DECIDE_ROLE_ELEVATION", "request_id": request_id, "version": expected, "decision": body.decision, "reason": body.reason})
    replay = _idempotency_replay(db, actor_user_id=reviewer.id, key=key, digest=digest)
    if replay:
        return ok(json.loads(replay.response_json), request.state.request_id, _now_iso())
    if expected != item.version:
        raise HTTPException(status_code=409, detail={"code": "VERSION_CONFLICT", "message_for_user": "Role request has changed; reload before retrying"})
    if item.status != "PENDING":
        raise HTTPException(status_code=409, detail={"code": "INVALID_TRANSITION", "message_for_user": "Role request is no longer open"})
    target = db.get(User, item.requester_user_id)
    if not target or target.status != "ACTIVE":
        raise HTTPException(status_code=409, detail={"code": "ACCOUNT_NOT_ACTIVE", "message_for_user": "Requester account is not active"})
    old_state, old_version = item.status, item.version
    item.status = body.decision
    item.reviewer_user_id = reviewer.id
    item.reviewer_reason = body.reason
    item.reviewed_at = utcnow()
    item.version += 1
    item.updated_at = utcnow()
    if body.decision == "APPROVED":
        target.role = item.requested_role
        target.version += 1
        target.updated_at = utcnow()
    result = _elevation_view(item)
    _remember_idempotency(db, actor_user_id=reviewer.id, key=key, action="DECIDE_ROLE_ELEVATION", object_type="ROLE_ELEVATION", object_id=item.id, digest=digest, data=result)
    record_audit(db, actor_user_id=reviewer.id, action="ROLE_ELEVATION_DECISION", object_type="ROLE_ELEVATION", object_id=item.id, outcome="SUCCESS", request_id=request.state.request_id, metadata={"from_status": old_state, "to_status": item.status, "requested_role": item.requested_role})
    record_history(db, actor_user_id=reviewer.id, object_type="ROLE_ELEVATION", object_id=item.id, action="DECISION", from_state=old_state, to_state=item.status, from_version=old_version, to_version=item.version, reason=body.reason, request_id=request.state.request_id, metadata={"requested_role": item.requested_role})
    db.commit()
    return ok(result, request.state.request_id, _now_iso())
