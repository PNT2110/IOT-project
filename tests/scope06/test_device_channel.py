from __future__ import annotations

import time

import pytest
from sqlalchemy import select

from server.app.device_crypto import DeviceAuthError, open_sealed, seal
from server.app.models import Device, SimulatedFlightRequest
from server.app.security import utcnow

PAYLOAD = {
    "client_ref": "pi-req-0001",
    "applicant_full_name": "Nguyen Van A",
    "license_code": "UAV-123456",
    "flight_date": "2026-10-02",
    "flight_time": "09:30",
    "vehicle": "F450 PNT PVD",
    "pi_username": "pitan",
    "gps": {"lat": 10.7769, "lon": 106.7009, "fix_state": "VALID_FIX", "satellites": 9},
}


def submit(client, device, payload=PAYLOAD, now=None):
    return client.post("/api/v1/device/flight-requests", json=seal(device["key"], device["id"], payload, now or int(time.time())))


def status_of(client, device, request_id):
    return client.post(f"/api/v1/device/flight-requests/{request_id}/status", json=seal(device["key"], device["id"], {"request_id": request_id}, int(time.time())))


def decide(client, operator, request_id, decision, reason):
    version = client.get(f"/api/v1/flight-requests/{request_id}", headers=operator).json()["data"]["version"]
    return client.post(f"/api/v1/flight-requests/{request_id}/decision", headers={**operator, "If-Match": str(version), "Idempotency-Key": f"decide-{request_id}"}, json={"decision": decision, "reason": reason})


def test_seal_open_roundtrip():
    key = bytes(range(32))
    envelope = seal(key, "dev-1", {"a": 1, "b": "ấ"}, 1000)
    assert set(envelope) == {"device_id", "ts", "nonce", "ciphertext"}
    assert open_sealed(key, envelope, 1100) == {"a": 1, "b": "ấ"}


def test_known_vector():
    key = bytes(range(32))
    envelope = {"device_id": "dev-test-0001", "ts": 1790000000, "nonce": "ZGVmZ2hpamtsbW5v", "ciphertext": "Mzm9ChCMOOphEDqO-F9IjyekKzq7XMJQi_PaLZPKxiTxy3riCiauNN-Ook0S8-HwGq_HmkLf9-hLyg"}
    assert open_sealed(key, envelope, 1790000000) == {"client_ref": "ref-0001", "vehicle": "F450"}
    assert seal(key, "dev-test-0001", {"vehicle": "F450", "client_ref": "ref-0001"}, 1790000000, nonce=bytes(range(100, 112))) == envelope


def test_open_rejects_tamper_skew_and_wrong_key():
    key = bytes(range(32))
    envelope = seal(key, "dev-1", {"a": 1}, 1000)
    with pytest.raises(DeviceAuthError):
        open_sealed(key, {**envelope, "ts": 1001}, 1000)
    with pytest.raises(DeviceAuthError):
        open_sealed(key, envelope, 1301)
    assert open_sealed(key, envelope, 1300) == {"a": 1}
    with pytest.raises(DeviceAuthError):
        open_sealed(bytes(32), envelope, 1000)
    with pytest.raises(DeviceAuthError):
        open_sealed(key, {"device_id": "dev-1", "ts": "x", "nonce": "!!", "ciphertext": ""}, 1000)


def test_tampered_ciphertext_401(app, device):
    _, client = app
    envelope = seal(device["key"], device["id"], PAYLOAD, int(time.time()))
    envelope["ciphertext"] = ("A" if envelope["ciphertext"][0] != "A" else "B") + envelope["ciphertext"][1:]
    response = client.post("/api/v1/device/flight-requests", json=envelope)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "DEVICE_AUTH_FAILED"
    with app[0].state.session_factory() as db:
        assert db.scalar(select(SimulatedFlightRequest)) is None


def test_replayed_nonce_401(app, device):
    _, client = app
    envelope = seal(device["key"], device["id"], PAYLOAD, int(time.time()))
    assert client.post("/api/v1/device/flight-requests", json=envelope).status_code == 201
    assert client.post("/api/v1/device/flight-requests", json=envelope).status_code == 401


def test_clock_skew_301s_401(app, device):
    _, client = app
    assert submit(client, device, now=int(time.time()) - 302).status_code == 401
    assert submit(client, device, now=int(time.time()) + 302).status_code == 401


def test_revoked_or_unknown_device_401(app, device):
    application, client = app
    assert client.post("/api/v1/device/flight-requests", json=seal(device["key"], "no-such-device", PAYLOAD, int(time.time()))).status_code == 401
    with application.state.session_factory() as db:
        db.get(Device, device["id"]).revoked_at = utcnow()
        db.commit()
    assert submit(client, device).status_code == 401


def test_submit_then_pending_then_approved(app, device, operator):
    _, client = app
    created = submit(client, device)
    assert created.status_code == 201
    data = created.json()["data"]
    assert data["status"] == "PENDING"
    request_id = data["request_id"]
    assert status_of(client, device, request_id).json()["data"]["status"] == "PENDING"

    listed = client.get("/api/v1/flight-requests", headers=operator).json()["data"]["items"]
    item = next(candidate for candidate in listed if candidate["id"] == request_id)
    assert item["source"] == "PI_DEVICE"
    assert item["device_name"] == "pitan"
    details = item["request_details"]
    assert details["applicant_full_name"] == "Nguyen Van A"
    assert details["license_code"] == "UAV-123456"
    assert details["flight_date"] == "2026-10-02" and details["flight_time"] == "09:30"
    assert details["vehicle"] == "F450 PNT PVD"
    assert details["gps"]["lat"] == 10.7769

    assert decide(client, operator, request_id, "APPROVED_SIMULATED", "Đủ điều kiện").status_code == 200
    status = status_of(client, device, request_id).json()["data"]
    assert status["status"] == "APPROVED"
    assert status["reason"] == "Đủ điều kiện"
    assert status["decided_at"]


def test_rejected_returns_reason(app, device, operator):
    _, client = app
    request_id = submit(client, device).json()["data"]["request_id"]
    assert decide(client, operator, request_id, "REJECTED", "Trong vùng cấm bay").status_code == 200
    status = status_of(client, device, request_id).json()["data"]
    assert status["status"] == "REJECTED"
    assert status["reason"] == "Trong vùng cấm bay"


def test_duplicate_client_ref_same_id(app, device):
    _, client = app
    first = submit(client, device).json()["data"]["request_id"]
    second = submit(client, device)
    assert second.status_code == 201
    assert second.json()["data"]["request_id"] == first


def test_gps_null_accepted(app, device, operator):
    _, client = app
    created = submit(client, device, {**PAYLOAD, "gps": None})
    assert created.status_code == 201
    item = client.get(f"/api/v1/flight-requests/{created.json()['data']['request_id']}", headers=operator).json()["data"]
    assert item["request_details"]["gps"] is None


def test_invalid_payload_422(app, device):
    _, client = app
    assert submit(client, device, {**PAYLOAD, "flight_time": "25:99"}).status_code == 422
    assert submit(client, device, {**PAYLOAD, "client_ref": "pi-req-0002", "applicant_full_name": "  "}).status_code == 422


def test_other_device_cannot_read_404(app, device, other_device):
    _, client = app
    request_id = submit(client, device).json()["data"]["request_id"]
    assert status_of(client, other_device, request_id).status_code == 404


def test_public_cannot_list_device_requests(app, device):
    _, client = app
    submit(client, device)
    assert client.get("/api/v1/flight-requests").status_code == 401
