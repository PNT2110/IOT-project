from __future__ import annotations

from sqlalchemy import select

from server.app.models import AuditEvent, SessionRecord, User, WorkflowHistory


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_account_review_policy_status_version_and_session_revoke(app, actors):
    application, client = app
    owner = auth(actors["owner"]["token"])
    admin = auth(actors["admin"]["token"])
    operator = auth(actors["operator"]["token"])
    target = actors["other"]

    assert client.get("/api/v1/account-review/users", headers=operator).status_code == 403
    assert client.get("/api/v1/account-review/users", headers=admin).status_code == 200
    assert client.get("/api/v1/account-review/users", headers=owner).status_code == 200
    assert client.get(f"/api/v1/history/USER/{actors['owner']['id']}", headers=owner).status_code == 200
    self_review = client.post(f"/api/v1/account-review/users/{actors['owner']['id']}/status", headers={**owner, "If-Match": "1", "Idempotency-Key": "self-account"}, json={"status": "SUSPENDED", "reason": "self test"})
    assert self_review.status_code == 403

    changed = client.post(f"/api/v1/account-review/users/{target['id']}/status", headers={**owner, "If-Match": "1", "Idempotency-Key": "account-suspend-1"}, json={"status": "SUSPENDED", "reason": "review hold"})
    assert changed.status_code == 200
    assert changed.json()["data"]["account"]["status"] == "SUSPENDED"
    replay = client.post(f"/api/v1/account-review/users/{target['id']}/status", headers={**owner, "If-Match": "1", "Idempotency-Key": "account-suspend-1"}, json={"status": "SUSPENDED", "reason": "review hold"})
    assert replay.status_code == 200
    assert replay.json()["data"]["account"]["version"] == changed.json()["data"]["account"]["version"]
    assert client.get("/api/v1/auth/me", headers=auth(target["token"])).status_code == 401
    stale = client.post(f"/api/v1/account-review/users/{target['id']}/status", headers={**owner, "If-Match": "1", "Idempotency-Key": "account-suspend-2"}, json={"status": "ACTIVE", "reason": "stale"})
    assert stale.status_code == 409

    with application.state.session_factory() as db:
        assert db.scalar(select(User).where(User.id == target["id"])).status == "SUSPENDED"
        assert db.scalar(select(SessionRecord).where(SessionRecord.token_digest == __import__("server.app.security", fromlist=["digest_token"]).digest_token(application.state.settings.session_secret, target["token"]))).revoked_at is not None
        assert db.scalar(select(WorkflowHistory).where(WorkflowHistory.object_type == "USER", WorkflowHistory.object_id == target["id"])) is not None
        assert db.scalar(select(AuditEvent).where(AuditEvent.object_type == "USER", AuditEvent.object_id == target["id"])) is not None


def test_operator_can_edit_zones_but_cannot_review_accounts(app, actors):
    _, client = app
    operator = auth(actors["operator"]["token"])
    internal = client.get("/api/v1/internal/zones", headers=operator)
    assert internal.status_code == 200
    source_id = internal.json()["data"]["items"][0]["source_id"]
    geometry = {"type": "Polygon", "coordinates": [[[40, 40], [40.1, 40], [40.1, 40.1], [40, 40.1], [40, 40]]]}
    zone_headers = {**operator, "Idempotency-Key": "operator-zone-create-1"}
    created = client.post("/api/v1/internal/zones", headers=zone_headers, json={"name": "Operator zone", "geometry": geometry, "visibility": "INTERNAL", "classification": "RESTRICTED", "source_id": source_id})
    assert created.status_code == 201
    zone_id = created.json()["data"]["id"]
    created_retry = client.post("/api/v1/internal/zones", headers=zone_headers, json={"name": "Operator zone", "geometry": geometry, "visibility": "INTERNAL", "classification": "RESTRICTED", "source_id": source_id})
    assert created_retry.status_code == 201
    assert created_retry.json()["data"]["id"] == zone_id
    updated = client.patch(f"/api/v1/internal/zones/{zone_id}", headers={**operator, "If-Match": "1"}, json={"name": "Operator zone updated", "geometry": geometry, "visibility": "PUBLIC", "classification": "NO_FLY", "source_id": source_id, "version": 1})
    assert updated.status_code == 200
    deleted = client.delete(f"/api/v1/internal/zones/{zone_id}", headers={**operator, "If-Match": "2"})
    assert deleted.status_code == 200
    assert client.get("/api/v1/account-review/users", headers=operator).status_code == 403


def test_role_elevation_owner_review_duplicate_and_key_reuse(app, actors):
    _, client = app
    guest = auth(actors["guest"]["token"])
    owner = auth(actors["owner"]["token"])
    created = client.post("/api/v1/role-elevations", headers={**guest, "Idempotency-Key": "role-1"}, json={"requested_role": "ADMIN", "reason": "Need review access"})
    assert created.status_code == 200
    item = created.json()["data"]
    duplicate = client.post("/api/v1/role-elevations", headers={**guest, "Idempotency-Key": "role-1"}, json={"requested_role": "ADMIN", "reason": "Need review access"})
    assert duplicate.status_code == 200
    assert duplicate.json()["data"]["id"] == item["id"]
    mismatch = client.post("/api/v1/role-elevations", headers={**guest, "Idempotency-Key": "role-1"}, json={"requested_role": "OPERATOR", "reason": "Different"})
    assert mismatch.status_code == 409
    review = client.get("/api/v1/role-elevations/review", headers=owner)
    assert review.status_code == 200
    decided = client.post(f"/api/v1/role-elevations/{item['id']}/decision", headers={**owner, "If-Match": "1", "Idempotency-Key": "role-decision-1"}, json={"decision": "APPROVED", "reason": "Owner approved"})
    assert decided.status_code == 200
    assert client.get("/api/v1/role-elevations", headers=guest).status_code == 200
    with client.app.state.session_factory() as db:
        assert db.scalar(select(User).where(User.id == actors["guest"]["id"])).role == "ADMIN"


def test_pending_account_cannot_request_role_or_workflow(app, actors):
    application, client = app
    with application.state.session_factory() as db:
        user = db.get(User, actors["guest"]["id"])
        user.status = "PENDING"
        user.version += 1
        db.commit()
    response = client.post("/api/v1/role-elevations", headers={**auth(actors["guest"]["token"]), "Idempotency-Key": "pending-role"}, json={"requested_role": "ADMIN", "reason": "Should be blocked"})
    assert response.status_code == 403


def _make_pending(application, user_id):
    from server.app.security import utcnow
    with application.state.session_factory() as db:
        user = db.get(User, user_id)
        user.status = "PENDING"
        user.role = "GUEST"
        user.email_verified_at = utcnow()
        user.credential.totp_active = True
        db.commit()


def test_admin_approves_with_role_operator(app, actors):
    application, client = app
    admin = auth(actors["admin"]["token"])
    _make_pending(application, actors["other"]["id"])
    approved = client.post(f"/api/v1/account-review/users/{actors['other']['id']}/status", headers={**admin, "If-Match": "1", "Idempotency-Key": "approve-op"}, json={"status": "ACTIVE", "role": "OPERATOR", "reason": "approved"})
    assert approved.status_code == 200
    assert approved.json()["data"]["account"]["status"] == "ACTIVE"
    assert approved.json()["data"]["account"]["role"] == "OPERATOR"


def test_approve_without_role_rejected(app, actors):
    application, client = app
    admin = auth(actors["admin"]["token"])
    _make_pending(application, actors["other"]["id"])
    response = client.post(f"/api/v1/account-review/users/{actors['other']['id']}/status", headers={**admin, "If-Match": "1", "Idempotency-Key": "approve-norole"}, json={"status": "ACTIVE", "reason": "approved"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ROLE_REQUIRED"


def test_admin_rejects_pending_account(app, actors):
    application, client = app
    admin = auth(actors["admin"]["token"])
    _make_pending(application, actors["other"]["id"])
    response = client.post(f"/api/v1/account-review/users/{actors['other']['id']}/status", headers={**admin, "If-Match": "1", "Idempotency-Key": "reject-1"}, json={"status": "REJECTED", "reason": "not eligible"})
    assert response.status_code == 200
    assert response.json()["data"]["account"]["status"] == "REJECTED"


def test_operator_cannot_list_or_approve_accounts(app, actors):
    application, client = app
    operator = auth(actors["operator"]["token"])
    _make_pending(application, actors["other"]["id"])
    assert client.get("/api/v1/account-review/users", headers=operator).status_code == 403
    assert client.post(f"/api/v1/account-review/users/{actors['other']['id']}/status", headers={**operator, "If-Match": "1", "Idempotency-Key": "op-approve"}, json={"status": "ACTIVE", "role": "OPERATOR", "reason": "nope"}).status_code == 403
    assert client.post(f"/api/v1/account-review/users/{actors['other']['id']}/role", headers=operator, json={"role": "ADMIN"}).status_code == 403


def test_admin_promotes_operator_to_admin(app, actors):
    application, client = app
    admin = auth(actors["admin"]["token"])
    promoted = client.post(f"/api/v1/account-review/users/{actors['operator']['id']}/role", headers=admin, json={"role": "ADMIN"})
    assert promoted.status_code == 200
    assert promoted.json()["data"]["account"]["role"] == "ADMIN"
    assert promoted.json()["data"]["account"]["version"] == 2
    demoted = client.post(f"/api/v1/account-review/users/{actors['operator']['id']}/role", headers=admin, json={"role": "OPERATOR"})
    assert demoted.json()["data"]["account"]["role"] == "OPERATOR"
    with application.state.session_factory() as db:
        assert db.scalar(select(AuditEvent).where(AuditEvent.action == "ACCOUNT_ROLE_CHANGE", AuditEvent.object_id == actors["operator"]["id"])) is not None


def test_admin_cannot_change_owner(app, actors):
    _, client = app
    admin = auth(actors["admin"]["token"])
    assert client.post(f"/api/v1/account-review/users/{actors['owner']['id']}/role", headers=admin, json={"role": "OPERATOR"}).status_code == 403
    assert client.post(f"/api/v1/account-review/users/{actors['owner']['id']}/status", headers={**admin, "If-Match": "1", "Idempotency-Key": "suspend-owner"}, json={"status": "SUSPENDED", "reason": "nope"}).status_code == 403
    assert client.post(f"/api/v1/account-review/users/{actors['admin']['id']}/role", headers=admin, json={"role": "OPERATOR"}).status_code == 403
