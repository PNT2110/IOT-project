"""Empirical verification of RFC 7946 GeoJSON and RFC 4180 CSV export generation."""
import csv
import io
import json
import shapely.geometry

def js_escape_csv(val):
    if val is None:
        return '""'
    s = str(val)
    if '"' in s or ',' in s or '\n' in s or '\r' in s:
        return f'"{s.replace("\"", "\"\"")}"'
    return f'"{s}"'

def simulate_export_flights_csv(flights):
    headers = [
        "Mã yêu cầu",
        "Người xin cấp",
        "Bằng lái",
        "Phương tiện",
        "Thời gian bắt đầu",
        "Thời gian kết thúc",
        "Thiết bị",
        "Trạng thái",
        "Vĩ độ",
        "Kinh độ",
        "Lý do",
    ]
    rows = []
    for flight in flights:
        details = flight.get("request_details") or {}
        gps = details.get("gps") or {}
        lat = f"{gps.get('lat'):.6f}" if gps.get("lat") is not None else ""
        lon = f"{gps.get('lon'):.6f}" if gps.get("lon") is not None else ""
        applicant = details.get("applicant_full_name") or flight.get("summary", "")
        status_label = flight.get("status", "")
        if status_label == "APPROVED_SIMULATED":
            status_label = "Đã duyệt"
        elif status_label == "REJECTED":
            status_label = "Đã từ chối"
        elif status_label == "SUBMITTED":
            status_label = "Chờ duyệt"
        
        row = [
            js_escape_csv(flight.get("id")),
            js_escape_csv(applicant),
            js_escape_csv(details.get("license_code", "")),
            js_escape_csv(details.get("vehicle", "")),
            js_escape_csv(flight.get("scheduled_start_at")),
            js_escape_csv(flight.get("scheduled_end_at")),
            js_escape_csv(flight.get("device_name", "Web PC")),
            js_escape_csv(status_label),
            js_escape_csv(lat),
            js_escape_csv(lon),
            js_escape_csv(flight.get("summary")),
        ]
        rows.append(",".join(row))
    
    header_line = ",".join(js_escape_csv(h) for h in headers)
    content = "\uFEFF" + "\r\n".join([header_line] + rows)
    return content

def simulate_export_zones_geojson(zones):
    collection = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": z.get("id"),
                "properties": {
                    "id": z.get("id"),
                    "name": z.get("name"),
                    "classification": z.get("classification"),
                    "visibility": z.get("visibility"),
                    "version": z.get("version"),
                    "retrieved_at": z.get("retrieved_at"),
                    "source_id": z.get("source_id"),
                },
                "geometry": z.get("geometry"),
            }
            for z in zones
        ],
    }
    return json.dumps(collection, indent=2)

def test_csv_rfc_4180():
    print("Testing CSV Export RFC 4180 Compliance...")
    test_flights = [
        {
            "id": "flight-001",
            "summary": "Bay khảo sát đê điều, khu vực Tân Bình",
            "status": "APPROVED_SIMULATED",
            "scheduled_start_at": "2026-10-04T08:00:00Z",
            "scheduled_end_at": "2026-10-04T10:00:00Z",
            "device_name": "Pi-Gateway-01",
            "request_details": {
                "applicant_full_name": "Nguyễn Văn \"Phi Công\" A",
                "license_code": "VN-UAV-2026-09",
                "vehicle": "Quadcopter F450, Serial #441",
                "gps": {"lat": 10.7769, "lon": 106.7009},
            },
        },
        {
            "id": "flight-002",
            "summary": "Khảo sát khẩn cấp:\r\nĐường dây 500kV",
            "status": "SUBMITTED",
            "scheduled_start_at": "2026-10-04T12:00:00Z",
            "scheduled_end_at": "2026-10-04T14:00:00Z",
            "device_name": None,
            "request_details": None,
        },
    ]

    csv_data = simulate_export_flights_csv(test_flights)
    # Check UTF-8 BOM
    assert csv_data.startswith("\uFEFF"), "CSV must start with UTF-8 BOM"
    
    # Check line endings (\r\n)
    raw_without_bom = csv_data[1:]
    lines = raw_without_bom.split("\r\n")
    print(f"  CSV Lines count: {len(lines)}")
    
    # Parse with Python's standard csv.reader (RFC 4180 compliant)
    reader = csv.reader(io.StringIO(raw_without_bom), lineterminator="\r\n")
    rows = list(reader)
    print(f"  Parsed rows count: {len(rows)}")
    assert len(rows) == 3, f"Expected 3 rows (header + 2 data), got {len(rows)}"
    
    # Check Header
    assert rows[0][0] == "Mã yêu cầu"
    assert rows[0][1] == "Người xin cấp"
    
    # Check Row 1 values
    r1 = rows[1]
    assert r1[0] == "flight-001"
    assert r1[1] == 'Nguyễn Văn "Phi Công" A', f"Failed quote unescape: {r1[1]}"
    assert r1[3] == "Quadcopter F450, Serial #441", f"Failed comma in vehicle: {r1[3]}"
    assert r1[7] == "Đã duyệt"
    assert r1[8] == "10.776900"
    assert r1[9] == "106.700900"
    
    # Check Row 2 values (multiline reason and missing details)
    r2 = rows[2]
    assert r2[0] == "flight-002"
    assert "Đường dây 500kV" in r2[10]
    assert r2[7] == "Chờ duyệt"
    assert r2[8] == ""
    assert r2[9] == ""
    print("  CSV RFC 4180: PASS")

def test_geojson_rfc_7946():
    print("\nTesting GeoJSON Export RFC 7946 Compliance...")
    test_zones = [
        {
            "id": "zone-poly-01",
            "name": "Khu vực sân bay Tân Sơn Nhất",
            "classification": "NO_FLY",
            "visibility": "PUBLIC",
            "version": 1,
            "retrieved_at": "2026-10-04T00:00:00Z",
            "source_id": "source-01",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [106.65, 10.81],
                        [106.67, 10.81],
                        [106.67, 10.83],
                        [106.65, 10.83],
                        [106.65, 10.81],
                    ]
                ],
            },
        },
        {
            "id": "zone-poly-02",
            "name": "Trạm biến áp 500kV",
            "classification": "RESTRICTED",
            "visibility": "INTERNAL",
            "version": 2,
            "retrieved_at": "2026-10-04T00:00:00Z",
            "source_id": None,
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [105.80, 21.00],
                        [105.82, 21.00],
                        [105.82, 21.02],
                        [105.80, 21.02],
                        [105.80, 21.00],
                    ]
                ],
            },
        },
    ]

    gj_text = simulate_export_zones_geojson(test_zones)
    parsed = json.loads(gj_text)
    
    assert parsed.get("type") == "FeatureCollection"
    assert "features" in parsed
    assert len(parsed["features"]) == 2
    
    for f in parsed["features"]:
        assert f.get("type") == "Feature"
        assert "properties" in f
        assert "geometry" in f
        geom = f["geometry"]
        assert "type" in geom
        assert "coordinates" in geom
        # Validate geometry with Shapely
        s = shapely.geometry.shape(geom)
        assert s.is_valid, f"Invalid geometry in feature {f['id']}"
        # RFC 7946 check: longitude between -180 and 180, lat between -90 and 90
        coords = geom["coordinates"][0]
        for pt in coords:
            lon, lat = pt[0], pt[1]
            assert -180.0 <= lon <= 180.0, f"Invalid longitude: {lon}"
            assert -90.0 <= lat <= 90.0, f"Invalid latitude: {lat}"
            # Coordinates must be [lon, lat], so Vietnam coordinates lon is ~105-107, lat is ~10-21
            assert lon > 50.0 and lat < 30.0, f"Longitude and Latitude might be swapped: [{lon}, {lat}]"

    print("  GeoJSON RFC 7946: PASS")

if __name__ == "__main__":
    test_csv_rfc_4180()
    test_geojson_rfc_7946()
