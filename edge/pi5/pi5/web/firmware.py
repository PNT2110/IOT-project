"""ESP32 firmware workflow on the Pi.

``FirmwareReadiness`` is the status-only inventory check. ``FirmwareUpdater``
downloads the manufacturer's GitHub release, verifies its SHA-256 and flashes
it with esptool, and only while the drone is not armed.
"""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path
from typing import Callable


class FirmwareReadiness:
    def __init__(
        self,
        *,
        environ: dict[str, str] | None = None,
        executable_lookup: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self._environ = os.environ if environ is None else environ
        self._which = executable_lookup

    @staticmethod
    def _configured_file(value: str | None) -> bool:
        if not value:
            return False
        try:
            return Path(value).is_file()
        except (OSError, ValueError):
            return False

    def read(self) -> dict[str, object]:
        device = self._environ.get("SCOPE07_ESP_DEVICE", "")
        device_configured = bool(device)
        device_present = False
        if device_configured:
            try:
                device_path = Path(device)
                device_present = stat.S_ISCHR(device_path.stat().st_mode)
            except (OSError, ValueError):
                device_present = False

        checks = {
            "cp210x_device_configured": device_configured,
            "cp210x_device_present": device_present,
            "vendor_public_key_file_present": self._configured_file(
                self._environ.get("SCOPE07_VENDOR_PUBLIC_KEY")
            ),
            "firmware_bundle_file_present_unverified": self._configured_file(
                self._environ.get("SCOPE07_SIGNED_BUNDLE")
            ),
            "expected_chip_configured": self._environ.get("SCOPE07_EXPECTED_CHIP", "").lower()
            == "esp32",
            "rollback_bundle_file_present_unverified": self._configured_file(
                self._environ.get("SCOPE07_ROLLBACK_BUNDLE")
            ),
            "esptool_available": self._which("esptool") is not None
            or self._which("esptool.exe") is not None,
            "safety_approval_record_file_present_unverified": self._configured_file(
                self._environ.get("SCOPE07_SAFETY_APPROVAL_RECORD")
            ),
        }
        blockers = [name for name, available in checks.items() if not available]
        # Passing inventory checks is not sufficient authorization to program
        # an aircraft controller; physical bench controls and a reviewed flash
        # procedure are not machine-verifiable by this web service.
        blockers.extend(
            (
                "vendor_signature_and_manifest_verification_not_implemented",
                "esp32_chip_identity_probe_not_implemented",
                "rollback_drill_not_verified",
                "physical_propeller_removal_and_bench_safety_not_verified",
            )
        )
        blockers.append("reviewed_flash_execution_not_implemented")
        return {
            "state": "BLOCKED",
            "can_flash": False,
            "checks": checks,
            "blockers": blockers,
            "device_label": "CP210x USB serial" if device_present else "Chưa xác định",
            "expected_chip": "ESP32" if checks["expected_chip_configured"] else "Chưa cấu hình",
            "message": "Chưa đủ điều kiện an toàn để nạp. Pi chưa ghi dữ liệu vào ESP32.",
        }


FIRMWARE_ASSET = "FC_can_bang.bin"
MAX_FIRMWARE_BYTES = 4 * 1024 * 1024
APP_OFFSET = "0x10000"


class FirmwareUpdateError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _github_json(url: str) -> dict:
    import json
    from urllib.request import Request, urlopen

    request = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "IOT-Pi-Firmware/1"})
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read(1_000_000).decode("utf-8"))


def _github_bytes(url: str, limit: int) -> bytes:
    from urllib.request import Request, urlopen

    request = Request(url, headers={"Accept": "application/octet-stream", "User-Agent": "IOT-Pi-Firmware/1"})
    with urlopen(request, timeout=60) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("download is too large")
    return data


class FirmwareUpdater:
    """Fetches the manufacturer's GitHub release and flashes it with esptool.

    The image is flashed only when its SHA-256 matches the published checksum
    and the drone is not armed. The ESP link is paused around esptool so the
    two never share the serial port.
    """

    def __init__(self, repo: str, *, link, arm_state: Callable[[], str | None], device: str | None, workdir, fetch_json: Callable[[str], dict] = _github_json, fetch_bytes: Callable[[str, int], bytes] = _github_bytes, run: Callable[..., object] | None = None) -> None:
        import subprocess

        self.repo = repo.strip()
        self._link = link
        self._arm_state = arm_state
        self._device = device
        self._workdir = Path(workdir)
        self._fetch_json = fetch_json
        self._fetch_bytes = fetch_bytes
        self._run = run or subprocess.run
        self._jobs: dict[str, dict[str, object]] = {}

    @classmethod
    def from_env(cls, *, link, arm_state, environ: dict[str, str] | None = None) -> "FirmwareUpdater":
        env = os.environ if environ is None else environ
        return cls(env.get("PI_FW_GITHUB_REPO", ""), link=link, arm_state=arm_state, device=env.get("PI_ESP_USB_DEVICE") or None, workdir=env.get("PI_FW_WORKDIR", "/tmp/iot-firmware"))

    def _release(self) -> dict:
        import re

        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}", self.repo):
            raise FirmwareUpdateError("FIRMWARE_REPO_NOT_CONFIGURED")
        try:
            release = self._fetch_json(f"https://api.github.com/repos/{self.repo}/releases/latest")
            assets = {asset["name"]: asset for asset in release["assets"]}
            image = assets[FIRMWARE_ASSET]
            checksum_text = self._fetch_bytes(assets[FIRMWARE_ASSET + ".sha256"]["browser_download_url"], 4096).decode("ascii").split()
            sha256 = checksum_text[0].lower()
            if not re.fullmatch(r"[0-9a-f]{64}", sha256):
                raise ValueError("invalid checksum file")
            return {"version": str(release["tag_name"]), "asset": FIRMWARE_ASSET, "size": int(image["size"]), "sha256": sha256, "published_at": release.get("published_at"), "url": image["browser_download_url"]}
        except FirmwareUpdateError:
            raise
        except Exception as exc:
            raise FirmwareUpdateError("FIRMWARE_RELEASE_UNAVAILABLE") from exc

    def _current_version(self) -> str | None:
        try:
            return (self._workdir / "current_version.txt").read_text(encoding="utf-8").strip() or None
        except OSError:
            return None

    def latest(self) -> dict[str, object]:
        release = self._release()
        release.pop("url")
        return {**release, "current_version": self._current_version()}

    def job(self, job_id: str) -> dict[str, object] | None:
        return self._jobs.get(job_id)

    def flash(self, version: str) -> dict[str, object]:
        import hashlib
        import secrets
        import sys

        release = self._release()
        if release["version"] != version:
            raise FirmwareUpdateError("VERSION_MISMATCH")
        if not self._device:
            raise FirmwareUpdateError("ESP_NOT_CONNECTED")
        if self._arm_state() == "ARMED":
            raise FirmwareUpdateError("DRONE_ARMED")
        job: dict[str, object] = {"job_id": secrets.token_hex(8), "version": version, "state": "DOWNLOADING", "detail": None}
        self._jobs[job["job_id"]] = job

        def fail(detail: str) -> dict[str, object]:
            job["state"], job["detail"] = "FAILED", detail
            return job

        try:
            image = self._fetch_bytes(release["url"], MAX_FIRMWARE_BYTES)
        except Exception:
            return fail("DOWNLOAD_FAILED")
        job["state"] = "VERIFYING"
        if hashlib.sha256(image).hexdigest() != release["sha256"]:
            return fail("SHA256_MISMATCH")
        self._workdir.mkdir(parents=True, exist_ok=True)
        path = self._workdir / FIRMWARE_ASSET
        path.write_bytes(image)
        job["state"] = "FLASHING"
        self._link.pause()
        try:
            result = self._run([sys.executable, "-m", "esptool", "--chip", "esp32", "-p", self._device, "-b", "460800", "write_flash", APP_OFFSET, str(path)], capture_output=True, text=True, timeout=180, check=False)
            ok = result.returncode == 0
        except Exception:
            ok = False
        finally:
            self._link.resume()
        if not ok:
            return fail("ESPTOOL_FAILED")
        (self._workdir / "current_version.txt").write_text(version, encoding="utf-8")
        job["state"] = "DONE"
        return job
