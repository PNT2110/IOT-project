from __future__ import annotations

import hashlib
import io
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from pi5.web.app import PiWebConfig, create_pi_app
from pi5.web.auth import PiAuthService
from pi5.web.camera import MockCameraAdapter, V4L2CameraAdapter
from pi5.web.firmware import FirmwareUpdater, FirmwareUpdateError


class FakeLink:
    def __init__(self, arm_state: str = "DISARMED"):
        self._arm = arm_state
        self.events: list[str] = []

    def arm_state(self) -> str:
        return self._arm

    def pause(self) -> None:
        self.events.append("pause")

    def resume(self) -> None:
        self.events.append("resume")


def test_ota_upload_valid_binary_and_job_query(tmp_path: Path):
    auth = PiAuthService(allow_inmemory_email=True)
    link = FakeLink("DISARMED")
    config = PiWebConfig(secure_cookies=False)
    updater = FirmwareUpdater(
        repo="",
        link=link,
        arm_state=link.arm_state,
        device=None,
        workdir=tmp_path,
    )
    app = create_pi_app(config, auth=auth, esp_link=link, firmware_updater=updater)

    client = TestClient(app)
    binary_data = b"\xe9" + b"TEST_PAYLOAD_FOR_F450_ESP32" * 100
    expected_sha = hashlib.sha256(binary_data).hexdigest()

    response = client.post(
        "/api/pi/v1/firmware/upload",
        files={"file": ("FC_can_bang.bin", io.BytesIO(binary_data), "application/octet-stream")},
    )
    assert response.status_code == 202
    body = response.json()
    job = body.get("data", body)
    assert "job_id" in job
    assert job["status"] in {"QUEUED", "FLASHING", "COMPLETED", "DONE"}
    assert job["sha256"] == expected_sha
    assert link.events == ["pause", "resume"]

    # Verify binary and sha files were saved
    saved_bin = tmp_path / "FC_can_bang.bin"
    assert saved_bin.exists()
    assert saved_bin.read_bytes() == binary_data

    # Query job status via jobs/{job_id}
    job_id = job["job_id"]
    job_res = client.get(f"/api/pi/v1/firmware/jobs/{job_id}")
    assert job_res.status_code == 200
    job_data = job_res.json().get("data", job_res.json())
    assert job_data["job_id"] == job_id
    assert job_data["status"] == "COMPLETED"


def test_ota_upload_raw_binary_octet_stream(tmp_path: Path):
    auth = PiAuthService(allow_inmemory_email=True)
    link = FakeLink("DISARMED")
    config = PiWebConfig(secure_cookies=False)
    updater = FirmwareUpdater(
        repo="",
        link=link,
        arm_state=link.arm_state,
        device=None,
        workdir=tmp_path,
    )
    app = create_pi_app(config, auth=auth, esp_link=link, firmware_updater=updater)

    client = TestClient(app)
    binary_data = b"\xe9" + b"RAW_OCTET_STREAM_DATA" * 50
    response = client.post(
        "/api/pi/v1/firmware/upload",
        content=binary_data,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 202
    job = response.json().get("data")
    assert job["size"] == len(binary_data)


def test_ota_upload_rejected_when_drone_armed(tmp_path: Path):
    auth = PiAuthService(allow_inmemory_email=True)
    link = FakeLink("ARMED")
    config = PiWebConfig(secure_cookies=False)
    updater = FirmwareUpdater(
        repo="",
        link=link,
        arm_state=link.arm_state,
        device=None,
        workdir=tmp_path,
    )
    app = create_pi_app(config, auth=auth, esp_link=link, firmware_updater=updater)

    client = TestClient(app)
    binary_data = b"\xe9" + b"ARMED_REJECT_TEST" * 50
    response = client.post(
        "/api/pi/v1/firmware/upload",
        files={"file": ("FC_can_bang.bin", io.BytesIO(binary_data), "application/octet-stream")},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DRONE_ARMED"
    assert link.events == []


def test_ota_upload_rejected_invalid_magic_byte(tmp_path: Path):
    auth = PiAuthService(allow_inmemory_email=True)
    config = PiWebConfig(secure_cookies=False)
    app = create_pi_app(config, auth=auth)

    client = TestClient(app)
    bad_bin = b"\x00" + b"BAD_MAGIC_BYTE" * 50
    response = client.post(
        "/api/pi/v1/firmware/upload",
        files={"file": ("firmware.bin", io.BytesIO(bad_bin), "application/octet-stream")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_MAGIC_BYTE"


def test_ota_upload_rejected_empty_payload(tmp_path: Path):
    auth = PiAuthService(allow_inmemory_email=True)
    config = PiWebConfig(secure_cookies=False)
    app = create_pi_app(config, auth=auth)

    client = TestClient(app)
    response = client.post(
        "/api/pi/v1/firmware/upload",
        files={"file": ("empty.bin", io.BytesIO(b""), "application/octet-stream")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EMPTY_FILE"


def test_ota_upload_rejected_oversized(tmp_path: Path):
    auth = PiAuthService(allow_inmemory_email=True)
    config = PiWebConfig(secure_cookies=False)
    app = create_pi_app(config, auth=auth)

    client = TestClient(app)
    huge_bin = b"\xe9" + b"X" * (4 * 1024 * 1024 + 1)
    response = client.post(
        "/api/pi/v1/firmware/upload",
        files={"file": ("huge.bin", io.BytesIO(huge_bin), "application/octet-stream")},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] in {"PAYLOAD_TOO_LARGE", "REQUEST_TOO_LARGE"}


def test_camera_consumer_disconnect_behavior():
    mock = MockCameraAdapter()
    assert mock.consumer_count == 0
    mock.start()
    assert mock.consumer_count == 1
    assert mock.running is True

    # Disconnecting single consumer stops adapter
    mock.disconnect_consumer()
    assert mock.consumer_count == 0
    assert mock.running is False
