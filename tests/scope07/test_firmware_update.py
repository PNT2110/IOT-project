from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest

from pi5.web.firmware import FirmwareUpdateError, FirmwareUpdater

BIN = b"\xe9" + b"firmware-image" * 100
SHA = hashlib.sha256(BIN).hexdigest()
RELEASE = {
    "tag_name": "v1.2.0",
    "published_at": "2026-10-01T00:00:00Z",
    "assets": [
        {"name": "FC_can_bang.bin", "browser_download_url": "https://github.com/o/r/releases/download/v1.2.0/FC_can_bang.bin", "size": len(BIN)},
        {"name": "FC_can_bang.bin.sha256", "browser_download_url": "https://github.com/o/r/releases/download/v1.2.0/FC_can_bang.bin.sha256", "size": 80},
    ],
}


class FakeLink:
    def __init__(self):
        self.events: list[str] = []

    def pause(self):
        self.events.append("pause")

    def resume(self):
        self.events.append("resume")


def make(tmp_path, *, sha=SHA, arm_state="DISARMED", returncode=0, repo="o/r"):
    link = FakeLink()
    runs: list[list[str]] = []

    def fetch_json(url):
        assert url == "https://api.github.com/repos/o/r/releases/latest"
        return RELEASE

    def fetch_bytes(url, limit):
        return f"{sha}  FC_can_bang.bin\n".encode() if url.endswith(".sha256") else BIN

    def run(args, **kwargs):
        runs.append(list(args))
        return SimpleNamespace(returncode=returncode, stdout="Hash of data verified.", stderr="boom" if returncode else "")

    updater = FirmwareUpdater(repo, fetch_json=fetch_json, fetch_bytes=fetch_bytes, run=run, link=link, arm_state=lambda: arm_state, device="/dev/ttyUSB0", workdir=tmp_path)
    return updater, link, runs


def test_latest_parses_release(tmp_path):
    updater, _, _ = make(tmp_path)
    assert updater.latest() == {"version": "v1.2.0", "asset": "FC_can_bang.bin", "size": len(BIN), "sha256": SHA, "published_at": "2026-10-01T00:00:00Z", "current_version": None}


def test_repo_not_configured(tmp_path):
    updater, _, _ = make(tmp_path, repo="")
    with pytest.raises(FirmwareUpdateError) as error:
        updater.latest()
    assert error.value.code == "FIRMWARE_REPO_NOT_CONFIGURED"


def test_flash_success_records_version_and_brackets_link(tmp_path):
    updater, link, runs = make(tmp_path)
    job = updater.flash("v1.2.0")
    assert job["state"] == "DONE"
    assert link.events == ["pause", "resume"]
    assert runs[0][-4:] == ["write_flash", "0x10000", str(tmp_path / "FC_can_bang.bin"), ] or runs[0][-3:-1] == ["write_flash", "0x10000"]
    assert "--chip" in runs[0] and "esp32" in runs[0] and "/dev/ttyUSB0" in runs[0]
    assert updater.latest()["current_version"] == "v1.2.0"
    assert updater.job(job["job_id"])["state"] == "DONE"


def test_sha_mismatch_fails_without_flashing(tmp_path):
    updater, link, runs = make(tmp_path, sha="0" * 64)
    job = updater.flash("v1.2.0")
    assert job["state"] == "FAILED" and job["detail"] == "SHA256_MISMATCH"
    assert runs == [] and link.events == []


def test_flash_refused_when_armed(tmp_path):
    updater, link, runs = make(tmp_path, arm_state="ARMED")
    with pytest.raises(FirmwareUpdateError) as error:
        updater.flash("v1.2.0")
    assert error.value.code == "DRONE_ARMED"
    assert runs == [] and link.events == []


def test_flash_refuses_stale_version(tmp_path):
    updater, _, runs = make(tmp_path)
    with pytest.raises(FirmwareUpdateError) as error:
        updater.flash("v0.0.1")
    assert error.value.code == "VERSION_MISMATCH"
    assert runs == []


def test_flash_pauses_and_resumes_link_even_on_failure(tmp_path):
    updater, link, _ = make(tmp_path, returncode=2)
    job = updater.flash("v1.2.0")
    assert job["state"] == "FAILED" and job["detail"] == "ESPTOOL_FAILED"
    assert link.events == ["pause", "resume"]
    assert updater.latest()["current_version"] is None
