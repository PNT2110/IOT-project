from __future__ import annotations

from sqlalchemy import select

from server.app.models import AuditEvent, SimulatedFlightRequest, WorkflowHistory


GEOMETRY = {"type": "Polygon", "coordinates": [[[30, 30], [30.1, 30], [30.1, 30.1], [30, 30.1], [30, 30]]]}
BODY = {"summary": "Synthetic local route", "scheduled_start_at": "2026-10-01T10:00:00+07:00", "scheduled_end_at": "2026-10-01T11:00:00+07:00", "geometry": GEOMETRY, "applicant_full_name": "Test Applicant", "license_code": "VN-TEST-001", "license_class": "A", "vehicle": "quadcopter-test", "gps_latitude": 21.03, "gps_longitude": 105.84, "gps_accuracy_m": 4.5}


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_canonical_pc_internal_flight_contract_is_first_class(app, actors):
    _, client = app
    guest = auth(actors["guest"]["token"])
    created = client.post("/api/v1/flight-requests", headers={**guest, "Idempotency-Key": "canonical-flight-1"}, json=BODY)
    assert created.status_code == 201
    item = created.json()["data"]
    assert item["authority_contract"] == "PC_INTERNAL_V1"
    listed = client.get("/api/v1/flight-requests", headers=guest)
    assert listed.status_code == 200
    assert any(candidate["id"] == item["id"] for candidate in listed.json()["data"]["items"])


def test_simulated_state_machine_labels_history_and_idempotency(app, actors):
    application, client = app
    guest = auth(actors["guest"]["token"])
    operator = auth(actors["operator"]["token"])
    created = client.post("/api/v1/simulated/flight-requests", headers={**guest, "Idempotency-Key": "flight-1"}, json=BODY)
    assert created.status_code == 201
    item = created.json()["data"]
    assert item["status"] == "DRAFT"
    assert item["simulated"] is True
    assert item["label"] == "PC INTERNAL DECISION — NOT A GOVERNMENT PERMIT"
    assert item["authority_contract"] == "PC_INTERNAL_V1"
    assert item["legal_status"] == "NOT_A_GOVERNMENT_PERMIT"
    replay = client.post("/api/v1/simulated/flight-requests", headers={**guest, "Idempotency-Key": "flight-1"}, json=BODY)
    assert replay.status_code == 201
    assert replay.json()["data"]["id"] == item["id"]
    changed_key = client.post("/api/v1/simulated/flight-requests", headers={**guest, "Idempotency-Key": "flight-1"}, json={**BODY, "summary": "Changed payload"})
    assert changed_key.status_code == 409

    submitted = client.post(f"/api/v1/simulated/flight-requests/{item['id']}/submit", headers={**guest, "If-Match": "1", "Idempotency-Key": "flight-submit-1"}, json={"reason": "Ready for synthetic review"})
    assert submitted.status_code == 200
    submitted_retry = client.post(f"/api/v1/simulated/flight-requests/{item['id']}/submit", headers={**guest, "If-Match": "1", "Idempotency-Key": "flight-submit-1"}, json={"reason": "Ready for synthetic review"})
    assert submitted_retry.status_code == 200
    assert submitted_retry.json()["data"]["id"] == item["id"]
    reviewed = client.post(f"/api/v1/simulated/flight-requests/{item['id']}/review", headers={**operator, "If-Match": "2", "Idempotency-Key": "flight-review-1"}, json={"reason": "Review started"})
    assert reviewed.status_code == 200
    reviewed_retry = client.post(f"/api/v1/simulated/flight-requests/{item['id']}/review", headers={**operator, "If-Match": "2", "Idempotency-Key": "flight-review-1"}, json={"reason": "Review started"})
    assert reviewed_retry.status_code == 200
    approved = client.post(f"/api/v1/simulated/flight-requests/{item['id']}/decision", headers={**operator, "If-Match": "3", "Idempotency-Key": "flight-decision-1"}, json={"decision": "APPROVED_SIMULATED", "reason": "Synthetic result only"})
    assert approved.status_code == 200
    approved_retry = client.post(f"/api/v1/simulated/flight-requests/{item['id']}/decision", headers={**operator, "If-Match": "3", "Idempotency-Key": "flight-decision-1"}, json={"decision": "APPROVED_SIMULATED", "reason": "Synthetic result only"})
    assert approved_retry.status_code == 200
    result = approved.json()["data"]
    assert result["status"] == "APPROVED_SIMULATED"
    assert result["simulated"] is True
    assert "PC INTERNAL" in result["label"]
    listed = client.get("/api/v1/simulated/flight-requests", headers=guest)
    assert listed.status_code == 200
    details = listed.json()["data"]["items"][0]["request_details"]
    assert details["applicant_full_name"] == "Test Applicant"
    assert details["license_class"] == "A"
    assert details["gps"]["latitude"] == 21.03
    history = client.get(f"/api/v1/history/SIMULATED_FLIGHT/{item['id']}", headers=guest)
    assert history.status_code == 200
    assert len(history.json()["data"]["items"]) >= 4
    assert all("password" not in str(event).lower() and "secret" not in str(event).lower() for event in history.json()["data"]["items"])
    with application.state.session_factory() as db:
        assert db.scalar(select(SimulatedFlightRequest).where(SimulatedFlightRequest.id == item["id"])).status == "APPROVED_SIMULATED"
        stored = db.scalar(select(SimulatedFlightRequest).where(SimulatedFlightRequest.id == item["id"]))
        assert "VN-TEST-001" not in stored.request_details_ciphertext
        assert len(db.scalars(select(AuditEvent).where(AuditEvent.object_id == item["id"])).all()) == 4
        assert len(db.scalars(select(WorkflowHistory).where(WorkflowHistory.object_id == item["id"])).all()) == 4


def test_stale_reviewer_and_idor_are_rejected(app, actors):
    _, client = app
    guest = auth(actors["guest"]["token"])
    operator = auth(actors["operator"]["token"])
    other = auth(actors["other"]["token"])
    created = client.post("/api/v1/simulated/flight-requests", headers={**guest, "Idempotency-Key": "flight-2"}, json=BODY).json()["data"]
    assert client.post(f"/api/v1/simulated/flight-requests/{created['id']}/submit", headers={**guest, "If-Match": "1", "Idempotency-Key": "flight-2-submit"}, json={"reason": "Submit"}).status_code == 200
    first = client.post(f"/api/v1/simulated/flight-requests/{created['id']}/review", headers={**operator, "If-Match": "2", "Idempotency-Key": "flight-2-review"}, json={"reason": "Review"})
    assert first.status_code == 200
    second = client.post(f"/api/v1/simulated/flight-requests/{created['id']}/review", headers={**operator, "If-Match": "2", "Idempotency-Key": "flight-2-review-retry"}, json={"reason": "Concurrent review"})
    assert second.status_code == 409
    assert client.get(f"/api/v1/simulated/flight-requests/{created['id']}", headers=other).status_code == 404
    assert client.post(f"/api/v1/simulated/flight-requests/{created['id']}/decision", headers={**guest, "If-Match": "3", "Idempotency-Key": "self-decision"}, json={"decision": "REJECTED", "reason": "Self"}).status_code == 403


def test_submitter_cannot_start_review_on_own_request(app, actors):
    _, client = app
    operator = auth(actors["operator"]["token"])
    created = client.post("/api/v1/flight-requests", headers={**operator, "Idempotency-Key": "self-review-create"}, json=BODY).json()["data"]
    submitted = client.post(f"/api/v1/flight-requests/{created['id']}/submit", headers={**operator, "If-Match": "1", "Idempotency-Key": "self-review-submit"}, json={"reason": "Submit for review"})
    assert submitted.status_code == 200
    review = client.post(f"/api/v1/flight-requests/{created['id']}/review", headers={**operator, "If-Match": "2", "Idempotency-Key": "self-review-start"}, json={"reason": "Self review"})
    assert review.status_code == 403
    assert review.json()["error"]["code"] == "SELF_REVIEW_FORBIDDEN"


def test_create_idempotency_covers_encrypted_request_details(app, actors):
    _, client = app
    guest = auth(actors["guest"]["token"])
    first = client.post("/api/v1/simulated/flight-requests", headers={**guest, "Idempotency-Key": "flight-details-digest"}, json=BODY)
    assert first.status_code == 201
    changed = {**BODY, "license_code": "VN-OTHER-999"}
    replay = client.post("/api/v1/simulated/flight-requests", headers={**guest, "Idempotency-Key": "flight-details-digest"}, json=changed)
    assert replay.status_code == 409
    assert replay.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSE"


def test_flight_request_rejects_incomplete_identity_or_gps(app, actors):
    _, client = app
    guest = auth(actors["guest"]["token"])
    missing_identity = {**BODY, "license_code": ""}
    assert client.post("/api/v1/simulated/flight-requests", headers={**guest, "Idempotency-Key": "flight-invalid-identity"}, json=missing_identity).status_code == 422
    partial_gps = {**BODY, "gps_longitude": None}
    response = client.post("/api/v1/simulated/flight-requests", headers={**guest, "Idempotency-Key": "flight-invalid-gps"}, json=partial_gps)
    assert response.status_code == 422


def test_flight_request_rejects_unknown_license_class(app, actors):
    _, client = app
    guest = auth(actors["guest"]["token"])
    invalid_class = {**BODY, "license_class": "C"}
    response = client.post("/api/v1/simulated/flight-requests", headers={**guest, "Idempotency-Key": "flight-invalid-license-class"}, json=invalid_class)
    assert response.status_code == 422


def test_fake_pi_is_authenticated_read_only_and_offline_is_explicit(app, actors):
    _, client = app
    guest = auth(actors["guest"]["token"])
    assert client.get("/api/v1/pi/v1/map", headers=guest).status_code == 401
    blocked = client.get("/api/v1/pi/v1/map", headers={**guest, "X-Fake-Pi-Client": "wrong"})
    assert blocked.status_code == 401
    response = client.get("/api/v1/pi/v1/map?offline=true", headers={**guest, "X-Fake-Pi-Client": "scope02-test-client"})
    assert response.status_code == 200
    assert response.json()["data"]["stale"] is True
    status = client.get("/api/v1/pi/v1/status?offline=true", headers={**guest, "X-Fake-Pi-Client": "scope02-test-client"})
    assert status.status_code == 200
    assert status.json()["data"]["sync_state"] == "UNSYNCED"
    assert not any(path.endswith("/decision") and path.startswith("/api/v1/pi") for path in client.app.openapi()["paths"])
