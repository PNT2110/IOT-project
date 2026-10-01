from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.geofence import GeofenceEngine
from app.models import GpsFix
from app.serial_io import CommandDispatcher, TelemetryState, parse_nmea_line, state


def test_valid_gga_sentence():
    line = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
    fix = parse_nmea_line(line)
    assert fix is not None
    assert fix.valid
    assert round(fix.latitude or 0, 4) == 48.1173
    assert fix.satellites == 8


def test_bad_checksum_rejected():
    assert parse_nmea_line("$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*00") is None


def test_geofence_inside_outside_warning(tmp_path: Path):
    zones = tmp_path / "zones.geojson"
    zones.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"id": "zone-1", "name": "Vùng thử"},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[106.6, 10.7], [106.8, 10.7], [106.8, 10.9], [106.6, 10.9], [106.6, 10.7]]],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    engine = GeofenceEngine(zones)
    assert engine.load() == 1
    inside = engine.evaluate(GpsFix(latitude=10.8, longitude=106.7, valid=True, stale=False))
    outside = engine.evaluate(GpsFix(latitude=11.5, longitude=107.5, valid=True, stale=False))
    assert inside.status == "breach"
    assert outside.status == "safe"


def test_jsonl_esp_parser_updates_attitude():
    state.update_esp_line('{"type":"telemetry","attitude":{"roll":1,"pitch":2,"yaw":3},"armed":true}')
    frame = state.snapshot()
    assert frame.attitude.roll == 1
    assert frame.armed is True


def test_command_retry_reuses_id_and_accepts_ack():
    telemetry = TelemetryState()

    class FakeWorker:
        def __init__(self):
            self.lines = []

        def write_line(self, line):
            self.lines.append(line)
            if len(self.lines) == 2:
                command_id = json.loads(line)["id"]
                telemetry.update_esp_line(json.dumps({"version": 1, "type": "ack", "command_id": command_id, "accepted": True}))
            return True

    worker = FakeWorker()
    frame, ack, attempts = asyncio.run(CommandDispatcher(worker, telemetry).land("ADMIN"))
    assert attempts == 2
    assert ack is not None and ack.accepted
    assert len({json.loads(line)["id"] for line in worker.lines}) == 1
    assert str(frame.id) == json.loads(worker.lines[0])["id"]


def test_command_fails_fast_without_serial():
    class MissingWorker:
        def write_line(self, _line):
            return False

    _, ack, attempts = asyncio.run(CommandDispatcher(MissingWorker(), TelemetryState()).land("GPS_LOST"))
    assert ack is None
    assert attempts == 1


def test_command_times_out_after_three_attempts():
    class SilentWorker:
        def __init__(self):
            self.lines = []

        def write_line(self, line):
            self.lines.append(line)
            return True

    worker = SilentWorker()
    _, ack, attempts = asyncio.run(CommandDispatcher(worker, TelemetryState()).land("GEOFENCE_BREACH"))
    assert ack is None
    assert attempts == 3
    assert len(worker.lines) == 3
    assert len({json.loads(line)["id"] for line in worker.lines}) == 1
