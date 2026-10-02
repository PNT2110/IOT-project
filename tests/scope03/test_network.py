from __future__ import annotations

from types import SimpleNamespace

from pi5.network.nm import NmcliAdapter


class FakeRun:
    def __init__(self, outputs: dict[str, tuple[int, str, str]]):
        self.outputs = outputs
        self.calls: list[list[str]] = []

    def __call__(self, args, **kwargs):
        self.calls.append(list(args))
        joined = " ".join(args)
        for needle, (code, out, err) in self.outputs.items():
            if needle in joined:
                return SimpleNamespace(returncode=code, stdout=out, stderr=err)
        return SimpleNamespace(returncode=0, stdout="", stderr="")


def test_status_parses_nmcli():
    run = FakeRun({
        "device status": (0, "wlan0:wifi:connected:F450\nwlan1:wifi:connected:Home\\:5G\neth0:ethernet:unavailable:--\nlo:loopback:connected (externally):lo\n", ""),
        "device show wlan1": (0, "IP4.ADDRESS[1]:192.168.1.50/24\n", ""),
    })
    status = NmcliAdapter(run=run, upstream_iface="wlan1", ap_iface="wlan0").status()
    assert status == {"upstream_connected": True, "iface": "wlan1", "ssid": "Home:5G", "ip": "192.168.1.50", "wired": False}


def test_status_ignores_ethernet_and_reports_it_separately():
    offline = FakeRun({"device status": (0, "ap0:wifi:connected:F450\nwlan1:wifi:disconnected:--\n", "")})
    assert NmcliAdapter(run=offline).status() == {"upstream_connected": False, "iface": "wlan1", "ssid": None, "ip": None, "wired": False}
    wired = FakeRun({"device status": (0, "ap0:wifi:connected:F450\nwlan1:wifi:disconnected:--\neth0:ethernet:connected:Wired connection 1\n", "")})
    assert NmcliAdapter(run=wired).status() == {"upstream_connected": False, "iface": "wlan1", "ssid": None, "ip": None, "wired": True}


def test_status_survives_missing_nmcli():
    def run(args, **kwargs):
        raise FileNotFoundError("nmcli")
    assert NmcliAdapter(run=run).status()["upstream_connected"] is False


def test_scan_dedupes_and_sorts_by_signal():
    run = FakeRun({"wifi list": (0, "Home:40:WPA2\nCafe\\:Free:80:\nHome:72:WPA2\n:55:WPA2\nF450:99:WPA2\n", "")})
    networks = NmcliAdapter(run=run, ap_ssid="F450").scan()
    assert networks == [
        {"ssid": "Cafe:Free", "signal": 80, "secure": False},
        {"ssid": "Home", "signal": 72, "secure": True},
    ]


def test_connect_rejects_bad_ssid_and_short_password():
    run = FakeRun({})
    adapter = NmcliAdapter(run=run)
    assert adapter.connect("", "password123") == {"ok": False, "error": "INVALID_SSID"}
    assert adapter.connect("Home", "short") == {"ok": False, "error": "INVALID_PASSWORD"}
    assert run.calls == []


def test_connect_passes_arguments_without_shell():
    run = FakeRun({"wifi connect": (0, "Device 'wlan1' successfully activated", "")})
    adapter = NmcliAdapter(run=run, upstream_iface="wlan1")
    assert adapter.connect("Home; rm -rf /", "password 123") == {"ok": True, "error": None}
    assert run.calls[-1] == ["nmcli", "device", "wifi", "connect", "Home; rm -rf /", "password", "password 123", "ifname", "wlan1"]
    assert adapter.connect("Open Net", None) == {"ok": True, "error": None}
    assert run.calls[-1] == ["nmcli", "device", "wifi", "connect", "Open Net", "ifname", "wlan1"]


def test_connect_wrong_password_returns_error():
    run = FakeRun({"wifi connect": (4, "", "Error: Connection activation failed: (7) Secrets were required, but not provided.")})
    assert NmcliAdapter(run=run).connect("Home", "wrongpass1") == {"ok": False, "error": "WRONG_PASSWORD"}
    missing = FakeRun({"wifi connect": (10, "", "Error: No network with SSID 'Home' found.")})
    assert NmcliAdapter(run=missing).connect("Home", "password123") == {"ok": False, "error": "NETWORK_NOT_FOUND"}
    denied = FakeRun({"wifi connect": (4, "", "Error: Failed to add/activate new connection: Not authorized to control networking.")})
    assert NmcliAdapter(run=denied).connect("Home", "password123") == {"ok": False, "error": "NOT_AUTHORIZED"}
    other = FakeRun({"wifi connect": (1, "", "Error: something else")})
    assert NmcliAdapter(run=other).connect("Home", "password123") == {"ok": False, "error": "CONNECT_FAILED"}
