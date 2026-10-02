"""NetworkManager adapter for the Pi upstream Wi-Fi client.

The access point (a second interface on the same radio) is never touched from
here; a root dispatcher script keeps its channel in step with the client.
Every nmcli call uses an argument list, so SSIDs and passwords are never
interpreted by a shell.
"""
from __future__ import annotations

import re
import subprocess
from typing import Any, Callable

from .validation import validate_interface_name, validate_password, validate_ssid

_SPLIT = re.compile(r"(?<!\\):")


def _fields(line: str) -> list[str]:
    return [part.replace("\\:", ":").replace("\\\\", "\\") for part in _SPLIT.split(line)]


class NmcliAdapter:
    def __init__(self, run: Callable[..., Any] = subprocess.run, upstream_iface: str = "wlan1", ap_iface: str = "wlan0", ap_ssid: str | None = None) -> None:
        self._run = run
        self.upstream_iface = validate_interface_name(upstream_iface)
        self.ap_iface = validate_interface_name(ap_iface)
        self.ap_ssid = ap_ssid

    def _nmcli(self, *args: str, timeout: float = 20) -> tuple[int, str, str]:
        try:
            result = self._run(["nmcli", *args], capture_output=True, text=True, timeout=timeout, check=False)
        except (OSError, subprocess.SubprocessError):
            return 127, "", "nmcli unavailable"
        return result.returncode, result.stdout or "", result.stderr or ""

    def _ip(self, iface: str) -> str | None:
        code, out, _ = self._nmcli("-t", "-f", "IP4.ADDRESS", "device", "show", iface)
        if code != 0:
            return None
        for line in out.splitlines():
            value = line.partition(":")[2].strip()
            if value:
                return value.split("/")[0]
        return None

    def status(self) -> dict[str, Any]:
        """Upstream means the Wi-Fi client only. A wired link is a bench aid and
        is reported as ``wired`` without counting as the Pi's network."""
        result = {"upstream_connected": False, "iface": self.upstream_iface, "ssid": None, "ip": None, "wired": False}
        code, out, _ = self._nmcli("-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device", "status")
        if code != 0:
            return result
        for line in out.splitlines():
            parts = _fields(line)
            if len(parts) < 4:
                continue
            device, kind, state, connection = parts[0], parts[1], parts[2], parts[3]
            if device == self.upstream_iface and state == "connected":
                result.update(upstream_connected=True, ssid=connection or None, ip=self._ip(device))
            elif kind == "ethernet" and state == "connected":
                result["wired"] = True
        return result

    def scan(self) -> list[dict[str, Any]]:
        code, out, _ = self._nmcli("-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list", "ifname", self.upstream_iface, "--rescan", "yes", timeout=30)
        if code != 0:
            return []
        best: dict[str, dict[str, Any]] = {}
        for line in out.splitlines():
            parts = _fields(line)
            if len(parts) < 3 or not parts[0] or parts[0] == self.ap_ssid:
                continue
            try:
                signal = int(parts[1])
            except ValueError:
                continue
            security = parts[2].strip()
            if parts[0] not in best or signal > best[parts[0]]["signal"]:
                best[parts[0]] = {"ssid": parts[0], "signal": signal, "secure": bool(security) and security != "--"}
        return sorted(best.values(), key=lambda item: item["signal"], reverse=True)

    def connect(self, ssid: str, psk: str | None) -> dict[str, Any]:
        try:
            validate_ssid(ssid)
        except ValueError:
            return {"ok": False, "error": "INVALID_SSID"}
        args = ["device", "wifi", "connect", ssid]
        if psk:
            try:
                validate_password(psk)
            except ValueError:
                return {"ok": False, "error": "INVALID_PASSWORD"}
            args += ["password", psk]
        args += ["ifname", self.upstream_iface]
        code, _, err = self._nmcli(*args, timeout=45)
        if code == 0:
            return {"ok": True, "error": None}
        lowered = err.lower()
        if "secrets were required" in lowered or "802-11-wireless-security" in lowered:
            return {"ok": False, "error": "WRONG_PASSWORD"}
        if "not authorized" in lowered or "insufficient privileges" in lowered:
            # The service user lacks the polkit rule installed by ops/pi5/pi-setup.sh.
            return {"ok": False, "error": "NOT_AUTHORIZED"}
        if "no network with ssid" in lowered:
            return {"ok": False, "error": "NETWORK_NOT_FOUND"}
        return {"ok": False, "error": "CONNECT_FAILED"}
