"""Pi device channel: sealed flight requests in, decisions out."""
from __future__ import annotations

import base64
from datetime import time as clock_time

from pydantic import ValidationError

from ..device_crypto import DeviceAuthError, open_sealed
from ..models import Device
from ..schemas import DeviceEnvelope, DeviceFlightPayload, TelemetryPayload
from .deps import *  # noqa: F401,F403

router = APIRouter()

NONCE_TTL_SECONDS = 600
# Flight date/time on the form are Vietnam local time.
LOCAL_TZ = timezone(timedelta(hours=7))
DEVICE_STATUS = {"APPROVED_SIMULATED": "APPROVED", "REJECTED": "REJECTED"}


def _auth_failed() -> HTTPException:
    return HTTPException(status_code=401, detail={"code": "DEVICE_AUTH_FAILED", "message_for_user": "Device authentication failed"})


def _open(request: Request, db: Session, envelope: DeviceEnvelope) -> tuple[Device, dict]:
    settings = request.app.state.settings
    device = db.get(Device, envelope.device_id)
    if not device or device.revoked_at:
        raise _auth_failed()
    now = int(time.time())
    try:
        key = base64.urlsafe_b64decode(decrypt_secret(settings.session_secret, device.key_encrypted))
        payload = open_sealed(key, envelope.model_dump(), now)
    except DeviceAuthError as exc:
        raise _auth_failed() from exc
    seen = request.app.state.device_nonces
    for stale in [item for item, expires in seen.items() if expires <= now]:
        seen.pop(stale, None)
    replay_key = (device.id, envelope.nonce)
    if replay_key in seen:
        raise _auth_failed()
    seen[replay_key] = now + NONCE_TTL_SECONDS
    return device, payload


@router.post("/device/flight-requests", status_code=201)
def device_submit_flight_request(envelope: DeviceEnvelope, request: Request, db: Session = Depends(_db), settings: Settings = Depends(_settings)):
    device, raw = _open(request, db, envelope)
    try:
        body = DeviceFlightPayload.model_validate(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message_for_user": "Flight request fields are invalid"}) from exc
    existing = db.scalar(select(SimulatedFlightRequest).where(SimulatedFlightRequest.device_id == device.id, SimulatedFlightRequest.client_ref == body.client_ref))
    if existing:
        return ok({"request_id": existing.id, "status": DEVICE_STATUS.get(existing.status, "PENDING")}, request.state.request_id, _now_iso())
    hour, minute = (int(part) for part in body.flight_time.split(":"))
    start = datetime.combine(body.flight_date, clock_time(hour, minute), tzinfo=LOCAL_TZ).astimezone(timezone.utc)
    if body.flight_end_time:
        end_hour, end_minute = (int(part) for part in body.flight_end_time.split(":"))
        end = datetime.combine(body.flight_date, clock_time(end_hour, end_minute), tzinfo=LOCAL_TZ).astimezone(timezone.utc)
    else:
        end = start + timedelta(hours=1)
    details = body.model_dump(mode="json", exclude={"client_ref"})
    now = utcnow()
    item = SimulatedFlightRequest(
        submitter_user_id=None,
        device_id=device.id,
        client_ref=body.client_ref,
        summary=f"{body.vehicle} — {body.applicant_full_name}"[:240],
        scheduled_start_at=start,
        scheduled_end_at=end,
        simulated_geometry_json="null",
        status="SUBMITTED",
        version=1,
        simulated=True,
        source="PI_DEVICE",
        request_details_ciphertext=encrypt_secret(settings.session_secret, json.dumps(details, separators=(",", ":"))),
        request_payload_digest=payload_digest(details),
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    try:
        db.flush()
    except IntegrityError:
        # Two retries of the same client_ref raced; return the winner.
        db.rollback()
        existing = db.scalar(select(SimulatedFlightRequest).where(SimulatedFlightRequest.device_id == device.id, SimulatedFlightRequest.client_ref == body.client_ref))
        return ok({"request_id": existing.id, "status": DEVICE_STATUS.get(existing.status, "PENDING")}, request.state.request_id, _now_iso())
    record_audit(db, actor_user_id=None, action="DEVICE_FLIGHT_SUBMIT", object_type="SIMULATED_FLIGHT", object_id=item.id, outcome="SUCCESS", request_id=request.state.request_id, metadata={"device_id": device.id, "to_status": "SUBMITTED"})
    record_history(db, actor_user_id=None, object_type="SIMULATED_FLIGHT", object_id=item.id, action="SUBMIT", from_state=None, to_state="SUBMITTED", from_version=None, to_version=1, reason=None, request_id=request.state.request_id, metadata={"source": "PI_DEVICE"})
    db.commit()
    return ok({"request_id": item.id, "status": "PENDING"}, request.state.request_id, _now_iso())


@router.post("/device/flight-requests/{request_id}/status")
def device_flight_request_status(request_id: str, envelope: DeviceEnvelope, request: Request, db: Session = Depends(_db)):
    device, payload = _open(request, db, envelope)
    item = db.get(SimulatedFlightRequest, request_id)
    if not item or item.device_id != device.id or payload.get("request_id") != request_id:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message_for_user": "Request not found"})
    status_value = DEVICE_STATUS.get(item.status, "PENDING")
    reason = decided_at = None
    if status_value != "PENDING":
        decision = db.scalar(select(WorkflowHistory).where(WorkflowHistory.object_type == "SIMULATED_FLIGHT", WorkflowHistory.object_id == item.id, WorkflowHistory.action == "DECISION").order_by(WorkflowHistory.created_at.desc()))
        reason = decision.reason if decision else None
        decided_at = _iso(item.updated_at)
    return ok({"request_id": item.id, "status": status_value, "reason": reason, "decided_at": decided_at}, request.state.request_id, _now_iso())


@router.post("/device/telemetry", status_code=200)
def device_push_telemetry(
    envelope: DeviceEnvelope,
    request: Request,
    db: Session = Depends(_db),
):
    device, raw = _open(request, db, envelope)
    try:
        sample = TelemetryPayload.model_validate(raw)
        data = sample.model_dump()
    except ValidationError:
        data = dict(raw) if isinstance(raw, dict) else {}
    data["device_id"] = device.id
    data["device_name"] = device.name
    data["received_at"] = utcnow().isoformat()
    if not hasattr(request.app.state, "latest_telemetry"):
        request.app.state.latest_telemetry = {}
    request.app.state.latest_telemetry[device.id] = data
    request.app.state.latest_telemetry["__latest__"] = data
    return ok({"stored": True, "device_id": device.id}, request.state.request_id, _now_iso())


