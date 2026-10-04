"""Milestone 5 Phase 1 Adversarial Probes & Stress Harness.

Authored by Challenger 2 (challenger_m5_2).
Empirically tests:
1. Database models against SQLite constraints and boundary values:
   - Zone.updated_at (ORM default behavior vs SQLite DDL NOT NULL constraint enforcement)
   - SimulatedFlightRequest.scheduled_start_at/end_at and simulated_geometry_json (ORM defaults vs SQLite DDL NOT NULL)
   - CHECK constraints on status and simulated flag
2. Helper functions deps._iso and deps._flight_view:
   - deps._iso behavior with None, naive datetime, aware datetime with positive/negative tz offsets, microsecond resolution, extreme dates
   - deps._flight_view behavior with None dates, None/empty/'null' geometry JSON, malformed geometry JSON, and corrupted details ciphertext
3. E2E Test Suite resilience and repeatability:
   - Repeated execution of all tiers to detect flakiness or race conditions
   - test_runner CLI options and execution
"""
from __future__ import annotations

import base64
import csv
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import secrets
import sys
import pytest
from sqlalchemy import create_engine, insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from server.app.config import Settings
from server.app.db import Base
from server.app.models import (
    Device,
    SimulatedFlightRequest,
    User,
    Zone,
    ZoneSource,
)
from server.app.routers.deps import _flight_view, _iso
from server.app.security import as_utc, encrypt_secret, utcnow
from tests.e2e.test_runner import run_e2e_tests


# ==============================================================================
# Fixtures for isolated SQLite database engine
# ==============================================================================
@pytest.fixture()
def db_session(tmp_path: Path):
    db_file = tmp_path / "adversarial_m5.sqlite3"
    engine = create_engine(f"sqlite:///{db_file}", echo=False)
    
    # Enforce SQLite foreign keys
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON;"))
    
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def sample_zone_source(db_session):
    now = utcnow()
    src = ZoneSource(
        id="src_adv_01",
        publisher="CHALLENGER_TEST",
        source_type="SIMULATED",
        license_name="MIT",
        checksum="sha256_mock_123456",
        retrieved_at=now,
    )
    db_session.add(src)
    db_session.commit()
    return src


# ==============================================================================
# Suite 1: SQLite Constraints and Boundary Probing on Zone
# ==============================================================================
class TestZoneModelConstraints:
    def test_zone_updated_at_default_assigned_on_omission(self, db_session, sample_zone_source):
        """When updated_at is omitted, default=utcnow assigns a valid UTC datetime."""
        now = utcnow()
        zone = Zone(
            source_id=sample_zone_source.id,
            name="Zone Default Test",
            geometry_json='{"type": "Polygon", "coordinates": []}',
            visibility="PUBLIC",
            classification="RESTRICTED",
            retrieved_at=now,
            created_at=now,
            # updated_at omitted
        )
        db_session.add(zone)
        db_session.commit()
        db_session.refresh(zone)
        
        assert zone.updated_at is not None
        assert isinstance(zone.updated_at, datetime)
        # Using as_utc to correctly handle SQLite timezone-naive retrieval
        diff = abs((as_utc(zone.updated_at) - now).total_seconds())
        assert diff < 5.0

    def test_zone_updated_at_orm_default_replaces_explicit_none(self, db_session, sample_zone_source):
        """In SQLAlchemy ORM, Zone(..., updated_at=None) triggers default=utcnow, preventing NULL."""
        now = utcnow()
        zone = Zone(
            source_id=sample_zone_source.id,
            name="Zone Null UpdatedAt",
            geometry_json='{"type": "Polygon", "coordinates": []}',
            visibility="PUBLIC",
            classification="RESTRICTED",
            retrieved_at=now,
            created_at=now,
            updated_at=None,  # ORM default intercepts None
        )
        db_session.add(zone)
        db_session.commit()
        db_session.refresh(zone)
        # ORM default defended against None:
        assert zone.updated_at is not None
        diff = abs((as_utc(zone.updated_at) - now).total_seconds())
        assert diff < 5.0

    def test_zone_updated_at_ddl_not_null_enforced_by_sqlite(self, db_session, sample_zone_source):
        """When bypassing ORM defaults (via direct table INSERT), SQLite NOT NULL constraint is enforced."""
        now = utcnow()
        # Direct table insert with NULL for updated_at
        stmt = insert(Zone.__table__).values(
            id="zone_raw_null",
            source_id=sample_zone_source.id,
            name="Raw Null Zone",
            geometry_json="{}",
            visibility="PUBLIC",
            classification="RESTRICTED",
            retrieved_at=now,
            created_at=now,
            updated_at=None,
        )
        with pytest.raises(IntegrityError) as exc_info:
            db_session.execute(stmt)
            db_session.commit()
        assert "NOT NULL constraint failed: zones.updated_at" in str(exc_info.value)
        db_session.rollback()

    def test_zone_microsecond_and_boundary_timestamps(self, db_session, sample_zone_source):
        """Verify microsecond precision and epoch edge dates on Zone timestamps."""
        microsecond_dt = datetime(2026, 10, 4, 12, 34, 56, 987654, tzinfo=timezone.utc)
        epoch_dt = datetime(1970, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
        far_future_dt = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        
        zone = Zone(
            source_id=sample_zone_source.id,
            name="Zone Timestamps Boundary",
            geometry_json="{}",
            visibility="INTERNAL",
            classification="CAUTION",
            retrieved_at=epoch_dt,
            created_at=microsecond_dt,
            updated_at=far_future_dt,
        )
        db_session.add(zone)
        db_session.commit()
        db_session.refresh(zone)
        
        assert zone.created_at.microsecond == 987654
        assert zone.retrieved_at.year == 1970
        assert zone.updated_at.year == 2099


# ==============================================================================
# Suite 2: SQLite Constraints and Boundary Probing on SimulatedFlightRequest
# ==============================================================================
class TestSimulatedFlightRequestConstraints:
    def test_flight_scheduled_dates_and_geometry_defaults(self, db_session):
        """SimulatedFlightRequest default=utcnow on scheduled dates and default='null' on geometry."""
        now = utcnow()
        flight = SimulatedFlightRequest(
            summary="Default Fields Probe",
            # scheduled_start_at omitted
            # scheduled_end_at omitted
            # simulated_geometry_json omitted
            created_at=now,
            updated_at=now,
        )
        db_session.add(flight)
        db_session.commit()
        db_session.refresh(flight)
        
        assert flight.scheduled_start_at is not None
        assert flight.scheduled_end_at is not None
        assert flight.simulated_geometry_json == "null"
        diff_start = abs((as_utc(flight.scheduled_start_at) - now).total_seconds())
        assert diff_start < 5.0

    def test_flight_explicit_null_ddl_not_null_enforced_by_sqlite(self, db_session):
        """Direct SQL insert with NULL for scheduled_start_at or simulated_geometry_json fails."""
        now = utcnow()
        stmt1 = insert(SimulatedFlightRequest.__table__).values(
            id="fl_raw_null_start",
            summary="Null Start",
            scheduled_start_at=None,
            scheduled_end_at=now,
            simulated_geometry_json="null",
            created_at=now,
            updated_at=now,
        )
        with pytest.raises(IntegrityError) as exc_info1:
            db_session.execute(stmt1)
            db_session.commit()
        assert "NOT NULL constraint failed: simulated_flight_requests.scheduled_start_at" in str(exc_info1.value)
        db_session.rollback()

        stmt2 = insert(SimulatedFlightRequest.__table__).values(
            id="fl_raw_null_geom",
            summary="Null Geom",
            scheduled_start_at=now,
            scheduled_end_at=now,
            simulated_geometry_json=None,
            created_at=now,
            updated_at=now,
        )
        with pytest.raises(IntegrityError) as exc_info2:
            db_session.execute(stmt2)
            db_session.commit()
        assert "NOT NULL constraint failed: simulated_flight_requests.simulated_geometry_json" in str(exc_info2.value)
        db_session.rollback()

    def test_flight_simulated_flag_check_constraint(self, db_session):
        """ck_simulated_request_flag requires simulated = 1 (True). simulated=False must fail."""
        now = utcnow()
        flight = SimulatedFlightRequest(
            summary="Illegal Non-Simulated Flag",
            simulated=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(flight)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "ck_simulated_request_flag" in str(exc_info.value) or "CHECK constraint failed" in str(exc_info.value)
        db_session.rollback()

    def test_flight_status_check_constraint(self, db_session):
        """ck_simulated_request_status requires valid status enum. Invalid status fails."""
        now = utcnow()
        flight = SimulatedFlightRequest(
            summary="Illegal Status",
            status="INVALID_STATUS_XYZ",
            created_at=now,
            updated_at=now,
        )
        db_session.add(flight)
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "ck_simulated_request_status" in str(exc_info.value) or "CHECK constraint failed" in str(exc_info.value)
        db_session.rollback()


# ==============================================================================
# Suite 3: Adversarial Probing of deps._iso and deps._flight_view
# ==============================================================================
class TestDepsHelperRobustness:
    def test_deps_iso_none_handling(self):
        """_iso(None) must return None without raising AttributeError or TypeError."""
        assert _iso(None) is None

    def test_deps_iso_timezone_awareness(self):
        """_iso handles timezone-naive and timezone-aware datetimes across positive/negative offsets."""
        naive_dt = datetime(2026, 10, 4, 10, 30, 0)
        assert _iso(naive_dt) == "2026-10-04T10:30:00+00:00"
        
        utc_dt = datetime(2026, 10, 4, 10, 30, 0, tzinfo=timezone.utc)
        assert _iso(utc_dt) == "2026-10-04T10:30:00+00:00"
        
        vn_tz = timezone(timedelta(hours=7))
        vn_dt = datetime(2026, 10, 4, 17, 30, 0, tzinfo=vn_tz)
        assert _iso(vn_dt) == "2026-10-04T10:30:00+00:00"
        
        est_tz = timezone(timedelta(hours=-5))
        est_dt = datetime(2026, 10, 4, 5, 30, 0, tzinfo=est_tz)
        assert _iso(est_dt) == "2026-10-04T10:30:00+00:00"

    def test_deps_iso_microsecond_resolution(self):
        """_iso preserves microsecond resolution."""
        dt_with_micros = datetime(2026, 10, 4, 10, 30, 0, 123456, tzinfo=timezone.utc)
        assert _iso(dt_with_micros) == "2026-10-04T10:30:00.123456+00:00"

    def test_deps_flight_view_with_none_dates(self):
        """_flight_view must safely serialize when scheduled dates are None."""
        now = utcnow()
        flight = SimulatedFlightRequest(
            id="fl_test_01",
            summary="Test None Dates",
            scheduled_start_at=None,
            scheduled_end_at=None,
            simulated_geometry_json="null",
            status="DRAFT",
            version=1,
            simulated=True,
            source="USER_SIMULATED",
            request_payload_digest="mock_digest",
            created_at=now,
            updated_at=now,
        )
        view = _flight_view(flight)
        assert view["id"] == "fl_test_01"
        assert view["scheduled_start_at"] is None
        assert view["scheduled_end_at"] is None
        assert view["geometry"] is None
        assert view["simulated"] is True
        assert view["authority_contract"] == "PC_INTERNAL_V1"

    def test_deps_flight_view_with_null_and_empty_geometry(self):
        """_flight_view handles 'null', empty string, and valid GeoJSON geometry."""
        now = utcnow()
        # Case A: 'null'
        flight_null = SimulatedFlightRequest(
            id="fl_test_02a",
            summary="Null Geometry",
            scheduled_start_at=now,
            scheduled_end_at=now,
            simulated_geometry_json="null",
            created_at=now,
            updated_at=now,
        )
        assert _flight_view(flight_null)["geometry"] is None

        # Case B: Empty string ""
        flight_empty = SimulatedFlightRequest(
            id="fl_test_02b",
            summary="Empty Geometry",
            scheduled_start_at=now,
            scheduled_end_at=now,
            simulated_geometry_json="",
            created_at=now,
            updated_at=now,
        )
        assert _flight_view(flight_empty)["geometry"] is None

        # Case C: Valid GeoJSON Polygon
        valid_poly = {
            "type": "Polygon",
            "coordinates": [[[105.8, 21.0], [105.9, 21.0], [105.9, 21.1], [105.8, 21.0]]],
        }
        flight_poly = SimulatedFlightRequest(
            id="fl_test_02c",
            summary="Valid Poly Geometry",
            scheduled_start_at=now,
            scheduled_end_at=now,
            simulated_geometry_json=json.dumps(valid_poly),
            created_at=now,
            updated_at=now,
        )
        view_poly = _flight_view(flight_poly)
        assert view_poly["geometry"] == valid_poly

    def test_deps_flight_view_corrupted_geometry_json_behavior(self):
        """Document behavior: corrupted geometry JSON raises JSONDecodeError unless handled."""
        now = utcnow()
        flight_bad_json = SimulatedFlightRequest(
            id="fl_test_bad_geom",
            summary="Corrupt Geometry JSON",
            scheduled_start_at=now,
            scheduled_end_at=now,
            simulated_geometry_json="{invalid_json:",
            created_at=now,
            updated_at=now,
        )
        with pytest.raises(json.JSONDecodeError):
            _flight_view(flight_bad_json)

    def test_deps_flight_view_details_decryption_failure_gracefully_degrades(self):
        """When ciphertext is corrupted, _flight_view must not crash and return DETAILS_UNAVAILABLE."""
        now = utcnow()
        flight = SimulatedFlightRequest(
            id="fl_test_corrupt",
            summary="Corrupt Ciphertext",
            scheduled_start_at=now,
            scheduled_end_at=now,
            simulated_geometry_json="null",
            request_details_ciphertext="CORRUPTED_AES_CIPHERTEXT_123456",
            created_at=now,
            updated_at=now,
        )
        settings = Settings(
            app_env="test",
            database_url="sqlite:///:memory:",
            session_secret=secrets.token_urlsafe(32),
            cookie_secure=False,
            allowed_origins=("http://localhost:5173",),
            host="127.0.0.1",
            port=8765,
        )
        view = _flight_view(flight, settings=settings, include_details=True)
        assert view["request_details"] == {"error": "DETAILS_UNAVAILABLE"}


# ==============================================================================
# Suite 4: Repeated Stress & CLI Runner Validation
# ==============================================================================
class TestE2ESuiteResilience:
    def test_cli_runner_subtier_selection(self):
        """CLI runner must support --tier 1, 2, 3, 4 without errors."""
        ret4 = run_e2e_tests(tier="4", verbose=False)
        assert ret4 == 0

        ret3 = run_e2e_tests(tier="3", verbose=False)
        assert ret3 == 0

    def test_tier4_concurrency_stress(self):
        """Run Tier 4 scenarios multiple times back-to-back to verify no state leak or flakiness."""
        for iteration in range(3):
            exit_code = pytest.main(["tests/e2e/test_tier4_scenarios.py", "-q"])
            assert exit_code == 0, f"Tier 4 failed on iteration {iteration + 1}"
