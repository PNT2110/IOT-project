from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
import pyotp
from fastapi.testclient import TestClient

from app.config import settings
from app.db import db
from app.main import app, geofence_sync_is_fresh


@pytest.fixture
def auth_admin(tmp_path):
    orig_db = db.path
    db.path = tmp_path / "test_stress.sqlite3"
    db.initialize()
    from app.auth import login_limiter
    login_limiter.attempts.clear()
    secret = pyotp.random_base32()
    db.create_user("admin-stress", "secure-password", "admin", secret)

    client = TestClient(app, raise_server_exceptions=False)
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin-stress", "password": "secure-password", "totp": pyotp.TOTP(secret).now()},
    )
    assert login_resp.status_code == 200

    yield client, db.path

    client.close()
    db.path = orig_db


# =========================================================================
# TASK 1: /api/v1/geofence/zones STRESS TESTS
# =========================================================================

def test_geofence_zones_live_metrics_and_compression(auth_admin):
    client, _ = auth_admin
    # Request with gzip accept encoding
    t0 = time.perf_counter()
    resp = client.get("/api/v1/geofence/zones", headers={"Accept-Encoding": "gzip"})
    t_roundtrip = time.perf_counter() - t0

    assert resp.status_code == 200
    content_bytes = resp.content
    content_len = len(content_bytes)

    # Check headers
    content_encoding = resp.headers.get("content-encoding")
    content_type = resp.headers.get("content-type")

    # Parsing time test
    t_parse_start = time.perf_counter()
    data = resp.json()
    t_parse = time.perf_counter() - t_parse_start

    print(f"\n[METRICS] Raw payload size: {content_len / (1024*1024):.2f} MB ({content_len} bytes)")
    print(f"[METRICS] Roundtrip time: {t_roundtrip * 1000:.2f} ms")
    print(f"[METRICS] JSON parsing time: {t_parse * 1000:.2f} ms")
    print(f"[METRICS] Content-Encoding: {content_encoding}")
    print(f"[METRICS] Content-Type: {content_type}")

    # Verify RFC 7946 Schema Compliance
    assert data["type"] == "FeatureCollection"
    features = data["features"]
    assert len(features) == 2745

    for idx, f in enumerate(features):
        assert f.get("type") == "Feature", f"Feature {idx} missing type: Feature"
        geom = f.get("geometry")
        assert geom is not None, f"Feature {idx} missing geometry"
        assert geom["type"] in ("Polygon", "MultiPolygon"), f"Feature {idx} invalid geom type {geom['type']}"
        coords = geom.get("coordinates")
        assert isinstance(coords, list) and len(coords) > 0, f"Feature {idx} empty coordinates"

        props = f.get("properties")
        assert isinstance(props, dict), f"Feature {idx} properties not a dict"
        assert "id" in props, f"Feature {idx} missing id"
        assert "layer_id" in props, f"Feature {idx} missing layer_id"
        assert props["layer_id"] in (1, 2), f"Feature {idx} invalid layer_id: {props['layer_id']}"
        assert "zone_type" in props, f"Feature {idx} missing zone_type"
        assert props["zone_type"] in ("prohibited", "restricted"), f"Feature {idx} invalid zone_type: {props['zone_type']}"


def test_geofence_zones_missing_file_fallback(auth_admin, tmp_path, monkeypatch):
    client, _ = auth_admin
    non_existent = tmp_path / "non_existent_zones.geojson"
    monkeypatch.setattr(settings.__class__, "zones_path", property(lambda self: non_existent))
    resp = client.get("/api/v1/geofence/zones")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload == {"type": "FeatureCollection", "features": []}


def test_geofence_zones_empty_file_behavior(auth_admin, tmp_path, monkeypatch):
    client, _ = auth_admin
    empty_file = tmp_path / "empty_zones.geojson"
    empty_file.write_text("", encoding="utf-8")
    monkeypatch.setattr(settings.__class__, "zones_path", property(lambda self: empty_file))
    
    resp = client.get("/api/v1/geofence/zones")
    print(f"\n[EMPTY FILE TEST] Status code: {resp.status_code}")
    # With raise_server_exceptions=False, empty file triggers 500
    assert resp.status_code == 500


def test_geofence_zones_corrupt_json_behavior(auth_admin, tmp_path, monkeypatch):
    client, _ = auth_admin
    corrupt_file = tmp_path / "corrupt_zones.geojson"
    corrupt_file.write_text('{"type": "FeatureCollection", "features": [', encoding="utf-8")
    monkeypatch.setattr(settings.__class__, "zones_path", property(lambda self: corrupt_file))
    
    resp = client.get("/api/v1/geofence/zones")
    print(f"\n[CORRUPT FILE TEST] Status code: {resp.status_code}")
    assert resp.status_code == 500


# =========================================================================
# TASK 2: /api/v1/preflight & geofence_sync_is_fresh STRESS TESTS
# =========================================================================

def test_sync_freshness_fresh_timestamp(auth_admin):
    client, db_path = auth_admin
    now_iso = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE map_sync SET fetched_at=?, feature_count=2745, status='ready' WHERE id=1", (now_iso,))
    
    assert geofence_sync_is_fresh() is True
    resp = client.get("/api/v1/preflight")
    assert resp.status_code == 200
    data = resp.json()
    assert data["checks"]["geofence_sync_fresh"] is True


def test_sync_freshness_stale_timestamp(auth_admin):
    client, db_path = auth_admin
    stale_iso = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE map_sync SET fetched_at=?, feature_count=2745, status='ready' WHERE id=1", (stale_iso,))
    
    assert geofence_sync_is_fresh() is False
    resp = client.get("/api/v1/preflight")
    assert resp.status_code == 200
    data = resp.json()
    assert data["checks"]["geofence_sync_fresh"] is False
    assert data["checks"]["geofence"] is False
    assert data["ready"] is False


def test_sync_freshness_corrupt_timestamp(auth_admin):
    client, db_path = auth_admin
    for bad_ts in ["not-a-timestamp", "2026-99-99T99:99:99", "", "null", "12345"]:
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE map_sync SET fetched_at=?, feature_count=2745, status='ready' WHERE id=1", (bad_ts,))
        
        assert geofence_sync_is_fresh() is False
        resp = client.get("/api/v1/preflight")
        assert resp.status_code == 200
        data = resp.json()
        assert data["checks"]["geofence_sync_fresh"] is False


def test_sync_freshness_missing_record(auth_admin):
    client, db_path = auth_admin
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM map_sync WHERE id=1")
    
    assert geofence_sync_is_fresh() is False
    resp = client.get("/api/v1/preflight")
    assert resp.status_code == 200
    assert resp.json()["checks"]["geofence_sync_fresh"] is False


def test_sync_freshness_corrupt_feature_count(auth_admin):
    client, db_path = auth_admin
    now_iso = datetime.now(timezone.utc).isoformat()
    # Test zero or negative feature count
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE map_sync SET fetched_at=?, feature_count=0, status='ready' WHERE id=1", (now_iso,))
    assert geofence_sync_is_fresh() is False

    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE map_sync SET fetched_at=?, feature_count=-5, status='ready' WHERE id=1", (now_iso,))
    assert geofence_sync_is_fresh() is False

    # Test non-integer feature count: raises ValueError
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE map_sync SET fetched_at=?, feature_count='invalid_num', status='ready' WHERE id=1", (now_iso,))
    with pytest.raises(ValueError):
        geofence_sync_is_fresh()


def test_sync_freshness_status_non_ready(auth_admin):
    client, db_path = auth_admin
    now_iso = datetime.now(timezone.utc).isoformat()
    for status_val in ["missing", "syncing", "failed", "stale", "unknown"]:
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE map_sync SET fetched_at=?, feature_count=2745, status=? WHERE id=1", (now_iso, status_val))
        assert geofence_sync_is_fresh() is False


def test_sync_freshness_naive_timestamp(auth_admin):
    client, db_path = auth_admin
    # Naive ISO string without timezone (e.g. "2026-09-09T12:00:00")
    naive_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE map_sync SET fetched_at=?, feature_count=2745, status='ready' WHERE id=1", (naive_iso,))
    # In Python 3.12, datetime.fromisoformat parses naive datetime, astimezone(utc) uses local system tz
    res = geofence_sync_is_fresh()
    assert res is True


def test_sync_freshness_future_timestamp_clock_drift(auth_admin):
    client, db_path = auth_admin
    # Future timestamp: 48 hours in the future
    future_iso = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE map_sync SET fetched_at=?, feature_count=2745, status='ready' WHERE id=1", (future_iso,))
    res = geofence_sync_is_fresh()
    print(f"\n[FUTURE TIMESTAMP TEST] Timestamp +48h evaluates to: {res}")
    # Note: because now - future < 0 <= 24h, this currently returns True!
    assert res is True
