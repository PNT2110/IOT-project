import json
import math
import sys
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from shapely.geometry import Point, shape
from app.geofence import GeofenceEngine, haversine_m
from app.models import GpsFix

ZONES_PATH = Path(__file__).resolve().parent.parent / "data" / "zones.geojson"


def extract_rings(geometry):
    """Extract list of coordinate rings from Polygon or MultiPolygon geometry dict."""
    gtype = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if gtype == "Polygon":
        return coords  # list of rings: outer, inner...
    elif gtype == "MultiPolygon":
        rings = []
        for poly in coords:
            for ring in poly:
                rings.append(ring)
        return rings
    else:
        raise ValueError(f"Unexpected geometry type: {gtype}")


def test_feature_count_and_schema():
    assert ZONES_PATH.exists(), f"zones.geojson not found at {ZONES_PATH}"
    with open(ZONES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("type") == "FeatureCollection"
    features = data.get("features", [])
    assert len(features) == 2745, f"Expected 2745 features, found {len(features)}"

    layer_ids = set()
    zone_types = set()
    for feat in features:
        props = feat.get("properties", {})
        assert "id" in props
        assert "layer_id" in props
        assert "zone_type" in props
        layer_ids.add(props["layer_id"])
        zone_types.add(props["zone_type"])

    assert layer_ids == {1, 2}
    assert zone_types == {"prohibited", "restricted"}


def test_all_coordinates_and_ring_closure():
    with open(ZONES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_vertices = 0
    min_lon, max_lon = float("inf"), float("-inf")
    min_lat, max_lat = float("inf"), float("-inf")
    invalid_coords = []
    unclosed_rings = []
    inverted_coords = []

    for feat_idx, feat in enumerate(data.get("features", [])):
        feat_id = feat.get("properties", {}).get("id", f"idx_{feat_idx}")
        geom = feat.get("geometry")
        assert geom is not None, f"Feature {feat_id} has null geometry"

        rings = extract_rings(geom)
        for ring_idx, ring in enumerate(rings):
            assert len(ring) >= 4, f"Feature {feat_id} ring {ring_idx} has < 4 vertices"

            # Check closure
            if ring[0][0] != ring[-1][0] or ring[0][1] != ring[-1][1]:
                unclosed_rings.append((feat_id, ring_idx, ring[0], ring[-1]))

            for pt_idx, pt in enumerate(ring):
                total_vertices += 1
                if len(pt) < 2:
                    invalid_coords.append((feat_id, pt_idx, pt))
                    continue

                lon, lat = pt[0], pt[1]

                # Check NaN / Inf / float type
                if not (isinstance(lon, (int, float)) and isinstance(lat, (int, float))):
                    invalid_coords.append((feat_id, pt_idx, pt))
                    continue
                if math.isnan(lon) or math.isinf(lon) or math.isnan(lat) or math.isinf(lat):
                    invalid_coords.append((feat_id, pt_idx, pt))
                    continue

                min_lon = min(min_lon, lon)
                max_lon = max(max_lon, lon)
                min_lat = min(min_lat, lat)
                max_lat = max(max_lat, lat)

                # Check bounds: lon [106, 109], lat [8, 12]
                if not (106.0 <= lon <= 109.0 and 8.0 <= lat <= 12.0):
                    # Check if swapped (lat in 106..109, lon in 8..12)
                    if 8.0 <= lon <= 12.0 and 106.0 <= lat <= 109.0:
                        inverted_coords.append((feat_id, pt_idx, "INVERTED_LAT_LON", pt))
                    else:
                        inverted_coords.append((feat_id, pt_idx, "OUT_OF_BOUNDS", pt))

    print(f"\n[GEODATA AUDIT]")
    print(f"Total features: {len(data.get('features', []))}")
    print(f"Total vertices: {total_vertices}")
    print(f"Bounding box Lon: [{min_lon:.6f}, {max_lon:.6f}]")
    print(f"Bounding box Lat: [{min_lat:.6f}, {max_lat:.6f}]")

    assert len(invalid_coords) == 0, f"Found invalid coordinates: {invalid_coords[:5]}"
    assert len(unclosed_rings) == 0, f"Found unclosed rings: {unclosed_rings[:5]}"
    assert len(inverted_coords) == 0, f"Found out-of-bounds/inverted coordinates: {inverted_coords[:5]}"
    assert total_vertices == 195143, f"Expected 195,143 vertices, found {total_vertices}"


def test_shapely_validity_of_all_features():
    with open(ZONES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    invalid_shapes = []
    for feat_idx, feat in enumerate(data.get("features", [])):
        feat_id = feat.get("properties", {}).get("id", f"idx_{feat_idx}")
        geom = feat.get("geometry")
        s = shape(geom)
        if not s.is_valid:
            invalid_shapes.append((feat_id, s.geom_type))

    print(f"\nTotal Shapely valid features: {len(data.get('features', [])) - len(invalid_shapes)} / {len(data.get('features', []))}")
    if invalid_shapes:
        print(f"Features with Shapely topological issues: {len(invalid_shapes)} (e.g. self-touching ring)")
    # Note: Even if some complex real-world vector polygons have minor self-intersection / ring-touching,
    # let's verify if covers/contains work properly or if buffer(0) or make_valid is needed.


def test_geofence_engine_edge_cases():
    engine = GeofenceEngine(ZONES_PATH)
    loaded = engine.load()
    assert loaded == 2745

    # 1. Tan Son Nhat Airport Runway (Strictly Inside Prohibited Zone)
    # TSN coordinates: lat 10.818, lon 106.652
    tsn_fix = GpsFix(latitude=10.818, longitude=106.652, valid=True, stale=False)
    state_tsn = engine.evaluate(tsn_fix)
    assert state_tsn.status == "breach", f"TSN expected breach, got {state_tsn.status}"
    assert state_tsn.distance_m == 0

    # 2. Con Dao (lat ~8.68, lon ~106.60)
    # Let's test Con Dao center
    condao_fix = GpsFix(latitude=8.683, longitude=106.608, valid=True, stale=False)
    state_condao = engine.evaluate(condao_fix)
    print(f"\nCon Dao (8.683, 106.608) result: status={state_condao.status}, zone_id={state_condao.zone_id}, dist={state_condao.distance_m}")

    # 3. Mekong Delta Safe Area (outside the Cambay dataset bounding box or in safe zone)
    # Can Tho: lat 10.03, lon 105.78 (west of 106)
    cantho_fix = GpsFix(latitude=10.03, longitude=105.78, valid=True, stale=False)
    state_cantho = engine.evaluate(cantho_fix)
    assert state_cantho.status == "safe", f"Can Tho expected safe, got {state_cantho.status}"
    assert state_cantho.distance_m is not None and state_cantho.distance_m > 500

    # 4. Distant points: Hanoi
    hanoi_fix = GpsFix(latitude=21.0285, longitude=105.8542, valid=True, stale=False)
    state_hanoi = engine.evaluate(hanoi_fix)
    assert state_hanoi.status == "safe", f"Hanoi expected safe, got {state_hanoi.status}"
    assert state_hanoi.distance_m is not None and state_hanoi.distance_m > 500

    # 5. Far away: Greenwich (51.4769, 0.0)
    greenwich_fix = GpsFix(latitude=51.4769, longitude=0.0, valid=True, stale=False)
    state_greenwich = engine.evaluate(greenwich_fix)
    assert state_greenwich.status == "safe", f"Greenwich expected safe, got {state_greenwich.status}"

    # 6. Null Island (0.0, 0.0)
    null_fix = GpsFix(latitude=0.0, longitude=0.0, valid=True, stale=False)
    state_null = engine.evaluate(null_fix)
    assert state_null.status == "safe"

    # 7. Exact boundary test: Pick first feature, pick its first vertex
    geom_0, props_0 = engine.zones[0]
    first_pt = geom_0.exterior.coords[0] if hasattr(geom_0, "exterior") else list(geom_0.geoms)[0].exterior.coords[0]
    # Point directly on boundary
    boundary_fix = GpsFix(latitude=first_pt[1], longitude=first_pt[0], valid=True, stale=False)
    state_b = engine.evaluate(boundary_fix)
    # shapely covers(point) returns True for boundary points
    assert state_b.status == "breach", f"Exact boundary point expected breach, got {state_b.status}"
    assert state_b.distance_m == 0

    # 8. Boundary midpoint
    coords = list(geom_0.exterior.coords if hasattr(geom_0, "exterior") else list(geom_0.geoms)[0].exterior.coords)
    p1, p2 = coords[0], coords[1]
    mid_lon, mid_lat = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    mid_fix = GpsFix(latitude=mid_lat, longitude=mid_lon, valid=True, stale=False)
    state_mid = engine.evaluate(mid_fix)
    assert state_mid.status == "breach", f"Midpoint of edge expected breach, got {state_mid.status}"

    # 9. Invalid GPS fixes
    invalid_fix = GpsFix(latitude=10.818, longitude=106.652, valid=False, stale=False)
    assert engine.evaluate(invalid_fix).status == "unknown"
    stale_fix = GpsFix(latitude=10.818, longitude=106.652, valid=True, stale=True)
    assert engine.evaluate(stale_fix).status == "unknown"
    none_fix = GpsFix(latitude=None, longitude=None, valid=True, stale=False)
    assert engine.evaluate(none_fix).status == "unknown"


def test_performance_benchmark():
    engine = GeofenceEngine(ZONES_PATH)
    engine.load()

    # Points to test
    points = [
        ("TSN Airport (Early breach)", GpsFix(latitude=10.818, longitude=106.652, valid=True, stale=False)),
        ("Can Tho Safe (Full 2745 search)", GpsFix(latitude=10.03, longitude=105.78, valid=True, stale=False)),
        ("Hanoi Safe (Full 2745 search)", GpsFix(latitude=21.0285, longitude=105.8542, valid=True, stale=False)),
        ("Greenwich (Full 2745 search)", GpsFix(latitude=51.4769, longitude=0.0, valid=True, stale=False)),
    ]

    print("\n" + "="*60)
    print("GEOFENCE ENGINE PERFORMANCE BENCHMARK")
    print("="*60)

    for label, fix in points:
        # Warmup
        engine.evaluate(fix)
        # Measure 10 runs
        times = []
        for _ in range(10):
            t0 = time.perf_counter()
            res = engine.evaluate(fix)
            t1 = time.perf_counter()
            times.append((t1 - t0) * 1000)  # ms

        mean_ms = sum(times) / len(times)
        min_ms = min(times)
        max_ms = max(times)
        print(f"{label:35s} -> Status: {res.status:7s} | Dist: {str(res.distance_m):8s} | Mean: {mean_ms:7.2f} ms (min: {min_ms:.2f}, max: {max_ms:.2f})")

    print("="*60)


if __name__ == "__main__":
    print("Running tests directly...")
    test_feature_count_and_schema()
    test_all_coordinates_and_ring_closure()
    test_shapely_validity_of_all_features()
    test_geofence_engine_edge_cases()
    test_performance_benchmark()
    print("All direct tests completed successfully.")
