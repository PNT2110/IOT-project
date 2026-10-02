from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PI_ROOT = Path(__file__).resolve().parents[2] / "edge" / "pi5"
if str(PI_ROOT) not in sys.path:
    sys.path.insert(0, str(PI_ROOT))

from pi5.telemetry.esp_command import EspFlightAuthorizationBridge  # noqa: E402
from pi5.web import device_crypto as pi_crypto  # noqa: E402
from pi5.web.authority import AuthorityClient, AuthorityError, FlightAuthorityService, FlightRequestError  # noqa: E402
from server.app import device_crypto as pc_crypto  # noqa: E402

VN = timezone(timedelta(hours=7))
USER = SimpleNamespace(user_id="u1", username="pitan")
BODY = {"full_name": "Nguyen Van A", "license_code": "UAV-123456", "flight_date": "2026-10-02", "flight_time": "09:30", "flight_end_time": "10:10", "vehicle": "F450 PNT PVD"}


class FakeAuthority:
    def __init__(self):
        self.online = True
        self.submitted: list[dict] = []
        self.decisions: dict[str, dict] = {}

    def submit(self, payload: dict) -> str:
        if not self.online:
            raise AuthorityError("PC unreachable")
        self.submitted.append(payload)
        return f"remote-{payload['client_ref']}"

    def status(self, request_id: str) -> dict:
        if not self.online:
            raise AuthorityError("PC unreachable")
        return self.decisions.get(request_id, {"status": "PENDING", "reason": None, "decided_at": None})


def make(now: datetime, gps=None, tmp_path=None):
    clock = {"now": now}
    lines: list[bytes] = []
    bridge = EspFlightAuthorizationBridge(lines.append, clock=lambda: clock["now"])
    authority = FakeAuthority()
    service = FlightAuthorityService(
        client=authority,
        bridge=bridge,
        gps=lambda: gps,
        store_path=str(tmp_path / "flights.sqlite3") if tmp_path else None,
        clock=lambda: clock["now"],
    )
    return service, authority, lines, clock


def test_pi_seal_matches_server_vector():
    key = bytes(range(32))
    envelope = {"device_id": "dev-test-0001", "ts": 1790000000, "nonce": "ZGVmZ2hpamtsbW5v", "ciphertext": "Mzm9ChCMOOphEDqO-F9IjyekKzq7XMJQi_PaLZPKxiTxy3riCiauNN-Ook0S8-HwGq_HmkLf9-hLyg"}
    assert pi_crypto.seal(key, "dev-test-0001", {"client_ref": "ref-0001", "vehicle": "F450"}, 1790000000, nonce=bytes(range(100, 112))) == envelope
    assert pc_crypto.open_sealed(key, pi_crypto.seal(key, "d", {"x": "ấ"}, 50), 60) == {"x": "ấ"}


def test_boot_sends_deny():
    service, _, lines, _ = make(datetime(2026, 10, 2, 2, 0, tzinfo=timezone.utc))
    service.tick()
    assert lines and lines[-1].startswith(b"$AUTH,DENY,")


def test_flight_submit_without_gps_sends_null():
    service, authority, _, _ = make(datetime(2026, 10, 2, 2, 0, tzinfo=timezone.utc), gps=None)
    item = service.create(USER, BODY)
    assert item["status"] == "PENDING"
    assert item["gps"] is None
    sent = authority.submitted[0]
    assert sent["gps"] is None
    assert sent["applicant_full_name"] == "Nguyen Van A"
    assert sent["license_code"] == "UAV-123456"
    assert sent["flight_date"] == "2026-10-02" and sent["flight_time"] == "09:30" and sent["flight_end_time"] == "10:10"
    assert sent["vehicle"] == "F450 PNT PVD" and sent["pi_username"] == "pitan"
    assert sent["client_ref"] == item["request_id"]


def test_flight_submit_includes_gps_from_esp():
    gps = {"lat": 10.7769, "lon": 106.7009, "fix_state": "FIX", "satellites": 9}
    service, authority, _, _ = make(datetime(2026, 10, 2, 2, 0, tzinfo=timezone.utc), gps=gps)
    service.create(USER, BODY)
    assert authority.submitted[0]["gps"] == gps


def test_flight_submit_pc_unreachable_stays_pending_send_and_retries():
    service, authority, lines, _ = make(datetime(2026, 10, 2, 2, 0, tzinfo=timezone.utc))
    authority.online = False
    item = service.create(USER, BODY)
    assert item["status"] == "PENDING_SEND"
    service.tick()
    assert service.list_for(USER)[0]["status"] == "PENDING_SEND"
    assert all(line.startswith(b"$AUTH,DENY,") for line in lines)
    authority.online = True
    service.tick()
    assert service.list_for(USER)[0]["status"] == "PENDING"
    assert len(authority.submitted) == 1


def test_approved_sends_auth_allow_only_inside_flight_window():
    # 09:30-10:10 Vietnam time is 02:30-03:10 UTC.
    service, authority, lines, clock = make(datetime(2026, 10, 2, 2, 0, tzinfo=timezone.utc))
    item = service.create(USER, BODY)
    authority.decisions[f"remote-{item['request_id']}"] = {"status": "APPROVED", "reason": "Đủ điều kiện", "decided_at": "2026-10-02T02:05:00+00:00"}
    service.tick()
    current = service.list_for(USER)[0]
    assert current["status"] == "APPROVED" and current["reason"] == "Đủ điều kiện"
    assert current["arm_permission"] == "BLOCKED"
    assert lines[-1].startswith(b"$AUTH,DENY,")

    clock["now"] = datetime(2026, 10, 2, 2, 31, tzinfo=timezone.utc)
    service.tick()
    assert lines[-1].startswith(b"$AUTH,ALLOW,2340,")
    assert service.list_for(USER)[0]["arm_permission"] == "ALLOWED"

    clock["now"] = datetime(2026, 10, 2, 3, 10, tzinfo=timezone.utc)
    service.tick()
    assert lines[-1].startswith(b"$AUTH,DENY,")
    assert service.list_for(USER)[0]["arm_permission"] == "BLOCKED"


def test_rejected_sends_auth_deny():
    service, authority, lines, clock = make(datetime(2026, 10, 2, 2, 31, tzinfo=timezone.utc))
    item = service.create(USER, BODY)
    authority.decisions[f"remote-{item['request_id']}"] = {"status": "REJECTED", "reason": "Trong vùng cấm bay", "decided_at": "x"}
    service.tick()
    current = service.list_for(USER)[0]
    assert current["status"] == "REJECTED" and current["reason"] == "Trong vùng cấm bay"
    assert lines[-1].startswith(b"$AUTH,DENY,")
    assert not any(line.startswith(b"$AUTH,ALLOW") for line in lines)


def test_esp_write_failure_is_retried_next_tick():
    clock = {"now": datetime(2026, 10, 2, 2, 31, tzinfo=timezone.utc)}
    lines: list[bytes] = []
    failing = {"on": True}

    def write(line: bytes) -> None:
        if failing["on"]:
            raise OSError("unplugged")
        lines.append(line)

    service = FlightAuthorityService(client=FakeAuthority(), bridge=EspFlightAuthorizationBridge(write, clock=lambda: clock["now"]), gps=lambda: None, clock=lambda: clock["now"])
    service.tick()
    assert lines == []
    failing["on"] = False
    service.tick()
    assert lines and lines[-1].startswith(b"$AUTH,DENY,")


def test_requests_survive_restart(tmp_path):
    now = datetime(2026, 10, 2, 2, 31, tzinfo=timezone.utc)
    service, authority, _, _ = make(now, tmp_path=tmp_path)
    item = service.create(USER, BODY)
    authority.decisions[f"remote-{item['request_id']}"] = {"status": "APPROVED", "reason": "ok", "decided_at": "x"}
    service.tick()
    restarted, _, lines, _ = make(now, tmp_path=tmp_path)
    restarted.tick()
    assert restarted.list_for(USER)[0]["status"] == "APPROVED"
    assert lines[-1].startswith(b"$AUTH,ALLOW,")


@pytest.mark.parametrize("change", [{"full_name": " "}, {"license_code": ""}, {"flight_date": "02/10/2026"}, {"flight_time": "25:00"}, {"flight_end_time": "09:30"}, {"flight_end_time": "09:00"}, {"flight_end_time": ""}, {"vehicle": "Unknown craft"}])
def test_invalid_request_rejected(change):
    service, authority, _, _ = make(datetime(2026, 10, 2, 2, 0, tzinfo=timezone.utc))
    with pytest.raises(FlightRequestError):
        service.create(USER, {**BODY, **change})
    assert authority.submitted == []


def test_authority_client_seals_and_requires_https():
    with pytest.raises(ValueError):
        AuthorityClient("http://pc.example.test", "dev", bytes(32))
    seen = {}

    class Response:
        status = 201
        def __init__(self, body): self._body = body
        def read(self, _limit=None): return self._body
        def __enter__(self): return self
        def __exit__(self, *args): return False

    def opener(request, timeout):
        seen["url"] = request.full_url
        seen["envelope"] = json.loads(request.data)
        return Response(json.dumps({"data": {"request_id": "r-1", "status": "PENDING"}, "error": None}).encode())

    key = bytes(range(32))
    client = AuthorityClient("https://pc.example.test/", "dev-1", key, opener=opener, clock=lambda: 1000)
    assert client.submit({"client_ref": "abcdefgh"}) == "r-1"
    assert seen["url"] == "https://pc.example.test/api/v1/device/flight-requests"
    assert pc_crypto.open_sealed(key, seen["envelope"], 1000) == {"client_ref": "abcdefgh"}

    def failing(request, timeout):
        raise OSError("down")
    with pytest.raises(AuthorityError):
        AuthorityClient("https://pc.example.test", "dev-1", key, opener=failing).submit({"client_ref": "abcdefgh"})
