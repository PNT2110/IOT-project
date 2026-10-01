from __future__ import annotations

from dataclasses import replace
import json

import pytest
from sqlalchemy import select

from server.app.main import create_app
from server.app.models import Zone, ZoneSource
from server.app.security import utcnow
from server.app.config import validate_allowed_origins
from server.app.geo import GeometryError, validate_polygon_geojson


def test_health_is_local_and_enveloped(app):
    _, client = app
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "v1"
    assert body["data"]["status"] == "ok"
    assert body["data"]["environment"] == "test"
    assert body["data"]["local_only"] is True
    assert response.headers["x-request-id"] == body["request_id"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-security-policy"].startswith("default-src 'none'")
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert response.headers["cross-origin-opener-policy"] == "same-origin"


def test_health_recognizes_owner_managed_airspace_source(app):
    application, client = app
    with application.state.session_factory() as db:
        db.add(ZoneSource(publisher="PC operator", source_type="OPERATOR_DRAWN", license_name="Operator-controlled dataset", checksum="sha256:test-owner-source", retrieved_at=utcnow()))
        db.commit()
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"]["airspace_source_configured"] is True
    assert response.json()["data"]["official_airspace_data_available"] is False
    assert response.json()["data"]["official_airspace_sync_state"] == "NOT_IMPLEMENTED"


def test_airspace_source_url_does_not_claim_live_sync(app):
    application, client = app
    application.state.settings = replace(
        application.state.settings,
        airspace_source_url="https://cambay.mod.gov.vn/",
    )
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["airspace_source_configured"] is False
    assert payload["official_airspace_data_available"] is False
    assert payload["official_airspace_sync_state"] == "NOT_IMPLEMENTED"


def test_health_marks_official_geojson_only_when_public_geometry_is_stored(app):
    application, client = app
    now = utcnow()
    geometry = {"type": "Polygon", "coordinates": [[[106.0, 16.0], [106.1, 16.0], [106.1, 16.1], [106.0, 16.1], [106.0, 16.0]]]}
    with application.state.session_factory() as db:
        source = ZoneSource(
            publisher="Authorized public data source",
            source_type="OFFICIAL_GEOJSON",
            license_name="Source metadata supplied by owner",
            checksum="sha256:verified-fixture",
            retrieved_at=now,
        )
        db.add(source)
        db.flush()
        db.add(Zone(
            source_id=source.id,
            name="Public source zone",
            geometry_json=json.dumps(geometry),
            visibility="PUBLIC",
            classification="NO_FLY",
            version=1,
            retrieved_at=now,
            created_at=now,
            updated_at=now,
        ))
        db.commit()
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["official_airspace_data_available"] is True
    assert payload["official_airspace_sync_state"] == "NOT_IMPLEMENTED"


def test_invalid_request_id_is_replaced_with_uuid(app):
    _, client = app
    response = client.get("/api/v1/health", headers={"X-Request-ID": "not-a-uuid"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == response.json()["request_id"]
    assert response.headers["x-request-id"] != "not-a-uuid"


def test_schema_validation_uses_v1_error_envelope(app):
    _, client = app
    response = client.post("/api/v1/auth/login", json={"email": "not-an-email", "password": "", "terms_version": ""})
    assert response.status_code == 422
    body = response.json()
    assert body["data"] is None
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["request_id"] == response.headers["x-request-id"]


def test_cors_allows_authenticated_workflow_headers_only_for_configured_origin(app):
    _, client = app
    allowed = client.options(
        "/api/v1/simulated/flight-requests",
        headers={
            "Origin": "http://testserver",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type,idempotency-key,x-csrf-token",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://testserver"
    assert "idempotency-key" in allowed.headers["access-control-allow-headers"].lower()

    denied = client.options(
        "/api/v1/simulated/flight-requests",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,idempotency-key",
        },
    )
    assert "access-control-allow-origin" not in denied.headers


def test_public_api_does_not_expose_internal_fixture(app):
    _, client = app
    response = client.get("/api/v1/public/zones")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["label"].startswith("SIMULATED")
    assert len(body["data"]["items"]) == 1
    assert all(item["visibility"] == "PUBLIC" for item in body["data"]["items"])
    assert all("source_id" not in item for item in body["data"]["items"])


def test_public_mode_hides_legacy_fixture_marked_public(app):
    application, client = app
    with application.state.session_factory() as db:
        source = db.scalar(select(ZoneSource).where(ZoneSource.publisher == "TEST_FIXTURE"))
        assert source is not None
        zone = Zone(
            source_id=source.id,
            name="Legacy fixture that must stay private",
            geometry_json='{"type":"Polygon","coordinates":[[[30,30],[30.1,30],[30.1,30.1],[30,30.1],[30,30]]]}',
            visibility="PUBLIC",
            classification="NO_FLY",
            version=1,
            retrieved_at=utcnow(),
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(zone)
        db.commit()
        legacy_id = zone.id
    application.state.settings = replace(application.state.settings, public_mode=True)
    response = client.get("/api/v1/public/zones")
    assert response.status_code == 200
    assert all(item["id"] != legacy_id for item in response.json()["data"]["items"])


def test_pi_contract_is_read_only_and_has_no_control_routes_in_openapi(app):
    application, _ = app
    paths = set(application.openapi()["paths"])
    assert "/api/v1/pi/v1/map" in paths
    assert "/api/v1/pi/v1/status" in paths
    assert not any(token in path.lower() for path in paths for token in ("arm", "disarm", "flight-permit"))


def test_credentialed_cors_rejects_wildcard_origin():
    import pytest

    with pytest.raises(RuntimeError, match="must not contain"):
        validate_allowed_origins(("*",))


def test_oversized_request_is_rejected_before_json_parsing(app):
    _, client = app
    response = client.post("/api/v1/auth/login", content=b"{}", headers={"Content-Length": "1000001", "Content-Type": "application/json"})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_public_mode_rejects_non_production_and_missing_smtp(app):
    application, _ = app
    base = application.state.settings
    with pytest.raises(RuntimeError, match="non-development"):
        create_app(replace(base, public_mode=True, cookie_secure=True, seed_demo_data=False))
    with pytest.raises(RuntimeError, match="SMTP_HOST"):
        create_app(replace(base, app_env="staging", public_mode=True, cookie_secure=True, seed_demo_data=False))


def test_deeply_nested_geometry_returns_validation_error_instead_of_recursion_error():
    coordinates: object = [0.0, 0.0]
    for _ in range(1500):
        coordinates = [coordinates]
    with pytest.raises(GeometryError, match="nesting"):
        validate_polygon_geojson({"type": "Polygon", "coordinates": coordinates})
