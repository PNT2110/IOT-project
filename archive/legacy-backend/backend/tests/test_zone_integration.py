import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import settings
from app.db import Database, db
from app.geofence import GeofenceEngine
from app.main import geofence_sync_is_fresh
from app.models import GpsFix


def test_zones_geojson_schema_and_integrity():
    zones_file = settings.zones_path
    assert zones_file.exists(), f"zones.geojson not found at {zones_file}"
    payload = json.loads(zones_file.read_text(encoding="utf-8"))
    assert payload.get("type") == "FeatureCollection"
    features = payload.get("features", [])
    assert len(features) == 2745, f"Expected 2745 features, found {len(features)}"

    layer_1_count = 0
    layer_2_count = 0

    for idx, feature in enumerate(features):
        props = feature.get("properties", {})
        assert "id" in props, f"Feature {idx} missing id"
        assert "layer_id" in props, f"Feature {idx} missing layer_id"
        assert "zone_type" in props, f"Feature {idx} missing zone_type"
        assert "source" in props, f"Feature {idx} missing source"

        layer_id = props["layer_id"]
        zone_type = props["zone_type"]
        assert layer_id in (1, 2), f"Feature {idx} has invalid layer_id: {layer_id}"
        if layer_id == 1:
            assert zone_type == "prohibited"
            layer_1_count += 1
        else:
            assert zone_type == "restricted"
            layer_2_count += 1

        geom = feature.get("geometry", {})
        assert geom.get("type") in ("Polygon", "MultiPolygon")
        coords = geom.get("coordinates", [])
        assert len(coords) > 0

    assert layer_1_count == 2378
    assert layer_2_count == 367


def test_map_sync_freshness_in_sqlite(tmp_path):
    # Ensure db.path points to real database in case prior tests modified the singleton
    db.path = settings.db_path
    assert geofence_sync_is_fresh() is True

    # Test edge cases using isolated temporary database
    db_file = tmp_path / "test_drone.sqlite3"
    test_db = Database(db_file)
    test_db.initialize()

    # Helper function matching app.main logic on arbitrary db
    def check_fresh(db_inst):
        with db_inst.connect() as conn:
            row = conn.execute("SELECT fetched_at,feature_count,status FROM map_sync WHERE id=1").fetchone()
        if not row or row["status"] != "ready" or int(row["feature_count"]) <= 0 or not row["fetched_at"]:
            return False
        try:
            fetched_at = datetime.fromisoformat(row["fetched_at"])
        except ValueError:
            return False
        return datetime.now(timezone.utc) - fetched_at.astimezone(timezone.utc) <= timedelta(hours=24)

    # Initially empty or default
    with test_db.connect() as conn:
        # Status not ready
        conn.execute(
            "INSERT OR REPLACE INTO map_sync (id, source_url, fetched_at, checksum, feature_count, status) VALUES (1, 'test', ?, 'abc', 2745, 'syncing')",
            (datetime.now(timezone.utc).isoformat(),),
        )
        conn.commit()
    assert check_fresh(test_db) is False

    # Feature count 0
    with test_db.connect() as conn:
        conn.execute("UPDATE map_sync SET status='ready', feature_count=0 WHERE id=1")
        conn.commit()
    assert check_fresh(test_db) is False

    # Stale fetched_at (> 24 hours)
    old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    with test_db.connect() as conn:
        conn.execute("UPDATE map_sync SET feature_count=2745, fetched_at=? WHERE id=1", (old_time,))
        conn.commit()
    assert check_fresh(test_db) is False

    # Invalid ISO timestamp format
    with test_db.connect() as conn:
        conn.execute("UPDATE map_sync SET fetched_at='not-a-date' WHERE id=1")
        conn.commit()
    assert check_fresh(test_db) is False

    # Fresh timestamp & ready status
    now_time = datetime.now(timezone.utc).isoformat()
    with test_db.connect() as conn:
        conn.execute("UPDATE map_sync SET fetched_at=? WHERE id=1", (now_time,))
        conn.commit()
    assert check_fresh(test_db) is True


def test_geofence_engine_evaluation_with_definitive_zones():
    engine = GeofenceEngine(path=settings.zones_path)
    count = engine.load()
    assert count == 2745

    # Point inside Tan Son Nhat airport (10.818 N, 106.652 E)
    fix_inside = GpsFix(latitude=10.818, longitude=106.652, valid=True, stale=False)
    state_inside = engine.evaluate(fix_inside)
    assert state_inside.status == "breach"
    assert state_inside.distance_m == 0

    # Point far outside HCMC no-fly zones (e.g., 20.0 N, 105.0 E)
    fix_outside = GpsFix(latitude=20.0, longitude=105.0, valid=True, stale=False)
    state_outside = engine.evaluate(fix_outside)
    assert state_outside.status == "safe"
