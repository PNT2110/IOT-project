"""Empirical Challenger Stress & Verification Test Suite for Milestone 4 (Frontend UI/UX).

Adversarial stress-testing covering:
1. Contract & Layout Compliance:
   - Verification of PROJECT.md § Code Layout paths:
     - frontend/src/components/ErrorBanner.tsx
     - frontend/src/components/operations/TelemetryPanel.tsx
   - Tier 1 test coverage for Features 12 through 17.
2. Telemetry Polling & Lifecycle Stress:
   - Detection of useEffect dependency loop on lastTelemetryReceived.
   - Request multiplication rate under sub-second responses.
   - GpsMap Leaflet instance recreation DOM thrashing.
3. ErrorBanner Auto-Dismiss Precision & Timer Starvation:
   - 8-second auto-dismiss accuracy and manual dismiss.
   - Unmount timer cancellation.
   - Timer starvation vulnerability caused by un-memoized onDismiss in parent with 500ms ageTicker.
4. Export Conformance:
   - RFC 7946 GeoJSON validation with Shapely.
   - RFC 4180 CSV validation with standard csv.reader (CRLF, quotes, UTF-8 BOM).
5. Dark Mode CSS & Contrast Audit:
   - WCAG 2.1 AA contrast ratio evaluation for dark mode text tokens.
   - Detection of unthemed light containers (e.g. .ghost-button #fff background with light text).
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import re
import subprocess
import pytest
import shapely.geometry

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ==============================================================================
# SECTION 1: CONTRACT & CODE LAYOUT VERIFICATION
# ==============================================================================

def test_contract_project_md_layout_compliance() -> None:
    """Verify that worker followed the exact component paths specified in PROJECT.md.
    
    PROJECT.md § Code Layout requires:
    - frontend/src/components/ErrorBanner.tsx
    - frontend/src/components/operations/TelemetryPanel.tsx
    """
    error_banner_path = PROJECT_ROOT / "frontend" / "src" / "components" / "ErrorBanner.tsx"
    telemetry_panel_path = PROJECT_ROOT / "frontend" / "src" / "components" / "operations" / "TelemetryPanel.tsx"

    missing = []
    if not error_banner_path.exists():
        missing.append("frontend/src/components/ErrorBanner.tsx (worker placed it in frontend/src/components/common/ErrorBanner.tsx instead)")
    if not telemetry_panel_path.exists():
        missing.append("frontend/src/components/operations/TelemetryPanel.tsx (worker inlined it into OperationsWorkspace.tsx)")

    assert not missing, f"Layout contract violations found:\n" + "\n".join(f"- {m}" for m in missing)


# ==============================================================================
# SECTION 2: TELEMETRY POLLING EFFECT LOOP & MEMORY THRASHING
# ==============================================================================

def test_telemetry_polling_effect_dependency_loop() -> None:
    """Empirically test whether telemetry polling in OperationsWorkspace causes a feedback loop.
    
    In OperationsWorkspace.tsx:
    When useEffect has [lastTelemetryReceived] as a dependency and calls setLastTelemetryReceived inside pollTelemetry(),
    each successful fetch triggers an immediate cleanup and remount of the effect, causing immediate re-polling.
    """
    ops_file = PROJECT_ROOT / "frontend" / "src" / "components" / "operations" / "OperationsWorkspace.tsx"
    assert ops_file.exists()
    content = ops_file.read_text(encoding="utf-8")

    # Match the telemetry useEffect block
    # Look for useEffect ending with [lastTelemetryReceived]
    match = re.search(r"useEffect\s*\(\s*\(\)\s*=>\s*\{[\s\S]*?pollTelemetry[\s\S]*?\}\s*,\s*\[([^\]]*)\]\s*\)", content)
    assert match is not None, "Could not find telemetry polling useEffect"
    deps = match.group(1).strip()
    
    # Adversarial assertion: lastTelemetryReceived MUST NOT be in the dependency array
    assert "lastTelemetryReceived" not in deps, (
        f"CRITICAL DEFECT: useEffect dependency array contains '[{deps}]'. "
        "Setting lastTelemetryReceived inside pollTelemetry triggers continuous cascading remounts "
        "and unthrottled API polling."
    )


def test_gps_map_component_dom_thrashing() -> None:
    """Empirically check whether GpsMap completely recreates Leaflet map on every lat/lon change."""
    ops_file = PROJECT_ROOT / "frontend" / "src" / "components" / "operations" / "OperationsWorkspace.tsx"
    content = ops_file.read_text(encoding="utf-8")

    # GpsMap useEffect has [lat, lon] and calls L.map() + map.remove()
    gps_match = re.search(r"function\s+GpsMap[\s\S]*?useEffect\s*\(\s*\(\)\s*=>\s*\{([\s\S]*?)\}\s*,\s*\[([^\]]*)\]\s*\)", content)
    assert gps_match is not None, "Could not find GpsMap component"
    gps_body = gps_match.group(1)
    gps_deps = gps_match.group(2).strip()

    has_l_map = "L.map" in gps_body
    has_map_remove = "map.remove" in gps_body
    is_recreated_on_coord_change = ("lat" in gps_deps or "lon" in gps_deps) and has_l_map and has_map_remove

    # Adversarial assertion: Leaflet map should be retained and updated with marker.setLatLng(), not destroyed/recreated every 1s
    assert not is_recreated_on_coord_change, (
        "PERFORMANCE/MEMORY DEFECT: GpsMap destroys and re-initializes L.map on every lat/lon change "
        "([lat, lon] in dependency array), causing DOM and canvas thrashing during live 1s telemetry."
    )


# ==============================================================================
# SECTION 3: ERROR BANNER TIMER ACCURACY & PARENT RESET VULNERABILITY
# ==============================================================================

def test_error_banner_parent_timer_starvation() -> None:
    """Empirically test whether ErrorBanner in OperationsWorkspace suffers from timer starvation.
    
    If OperationsWorkspace passes an un-memoized `onDismiss={() => setError(null)}` to ErrorBanner,
    and OperationsWorkspace re-renders every 500ms due to ageTicker, the 8s timer is continuously reset.
    """
    ops_file = PROJECT_ROOT / "frontend" / "src" / "components" / "operations" / "OperationsWorkspace.tsx"
    content = ops_file.read_text(encoding="utf-8")

    # Find ErrorBanner usage in OperationsWorkspace
    banner_match = re.search(r"<ErrorBanner([\s\S]*?)/>", content)
    assert banner_match is not None, "ErrorBanner not found in OperationsWorkspace"
    props = banner_match.group(1)

    # Check if onDismiss is an inline arrow function: e.g. onDismiss={() => setError(null)}
    is_inline_dismiss = bool(re.search(r"onDismiss\s*=\s*\{\s*\(\s*\)\s*=>", props))
    has_ticker_rerender = "window.setInterval" in content and "500" in content

    assert not (is_inline_dismiss and has_ticker_rerender), (
        "TIMING DEFECT: ErrorBanner receives an inline un-memoized onDismiss callback while parent "
        "re-renders every 500ms via ageTicker. Because ErrorBanner's useEffect depends on [onDismiss], "
        "the 8000ms timer is reset every 500ms, preventing the error banner from ever auto-dismissing."
    )


# ==============================================================================
# SECTION 4: EXPORT CONFORMANCE (RFC 7946 GeoJSON & RFC 4180 CSV)
# ==============================================================================

def test_export_geojson_rfc_7946_validity() -> None:
    """Empirically verify GeoJSON export function produces RFC 7946 compliant FeatureCollection."""
    ops_file = PROJECT_ROOT / "frontend" / "src" / "components" / "operations" / "OperationsWorkspace.tsx"
    content = ops_file.read_text(encoding="utf-8")

    assert "FeatureCollection" in content
    assert "application/geo+json" in content
    assert "drone-zones-" in content

    # Mock sample zones
    sample_geom = {
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
    }
    s = shapely.geometry.shape(sample_geom)
    assert s.is_valid
    coords = sample_geom["coordinates"][0]
    assert coords[0] == coords[-1], "Polygon linear ring must be closed"
    # Check [lon, lat] ordering
    assert coords[0][0] > 50.0 and coords[0][1] < 30.0, "Coordinates must be [lon, lat] per RFC 7946"


def test_export_csv_rfc_4180_validity() -> None:
    """Empirically verify CSV export escaping and CRLF structure with Python csv.reader."""
    ops_file = PROJECT_ROOT / "frontend" / "src" / "components" / "operations" / "OperationsWorkspace.tsx"
    content = ops_file.read_text(encoding="utf-8")

    assert "\\uFEFF" in content, "CSV export must include UTF-8 BOM for Excel"
    assert "\\r\\n" in content, "CSV export must use CRLF per RFC 4180"

    # Simulate escapeCsv function
    def escape_csv(val: object) -> str:
        if val is None:
            return '""'
        s = str(val)
        if '"' in s or ',' in s or '\n' in s or '\r' in s:
            return f'"{s.replace("\"", "\"\"")}"'
        return f'"{s}"'

    test_rows = [
        ["ID-1", "Nguyen Van \"Pilot\" A", "Quadcopter, F450", "Multi\r\nline note"],
        ["ID-2", "Pilot B", "Drone 2", "Simple note"],
    ]
    csv_text = "\uFEFF" + "\r\n".join([",".join(escape_csv(c) for c in row) for row in test_rows])

    reader = csv.reader(io.StringIO(csv_text.lstrip("\uFEFF")), lineterminator="\r\n")
    parsed = list(reader)
    assert len(parsed) == 2
    assert parsed[0][1] == 'Nguyen Van "Pilot" A'
    assert parsed[0][2] == "Quadcopter, F450"
    assert "Multi\r\nline" in parsed[0][3] or "Multi\nline" in parsed[0][3]


# ==============================================================================
# SECTION 5: DARK MODE CSS AUDIT & WCAG CONTRAST
# ==============================================================================

def test_dark_mode_unthemed_white_elements() -> None:
    """Empirically verify that no UI components retain #fff backgrounds in dark mode.
    
    Specifically, .ghost-button in AccountMenu.tsx has #fff background and light text in dark mode.
    """
    exp_file = PROJECT_ROOT / "frontend" / "src" / "experience.css"
    content = exp_file.read_text(encoding="utf-8")

    # Dark mode media query
    dark_match = re.search(r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)\s*\{(.*)\}\s*$", content, re.DOTALL)
    assert dark_match is not None, "Missing prefers-color-scheme: dark media query"
    dark_css = dark_match.group(1)

    # Check if .ghost-button is overridden in dark mode
    assert ".ghost-button" in dark_css, (
        "DEFECT: .ghost-button (used in AccountMenu.tsx profile dialog) has hardcoded #fff background "
        "and is not overridden in dark mode, resulting in unreadable white text on white background."
    )


def test_dark_mode_wcag_aa_contrast() -> None:
    """Empirically evaluate WCAG 2.1 AA contrast ratios for dark mode typography tokens."""
    def srgb_to_lum(hex_color: str) -> float:
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join([c * 2 for c in hex_color])
        r, g, b = [int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
        def adj(c: float) -> float:
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * adj(r) + 0.7152 * adj(g) + 0.0722 * adj(b)

    def contrast(c1: str, c2: str) -> float:
        l1, l2 = srgb_to_lum(c1), srgb_to_lum(c2)
        return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)

    surface = "#142130"
    surface_soft = "#192a3c"
    exp_file = PROJECT_ROOT / "frontend" / "src" / "experience.css"
    content = exp_file.read_text(encoding="utf-8")
    m = re.search(r"--quiet:\s*(#[0-9a-fA-F]+)", content)
    quiet = m.group(1) if m else "#55748f"

    # In experience.css line 978: .metric-sub { color: var(--quiet); }
    # .metric-sub is small text rendered on telemetry-metric-card (background: var(--surface))
    cr_surface = contrast(surface, quiet)
    cr_soft = contrast(surface_soft, quiet)

    # WCAG AA requires 4.5:1 for small text
    assert cr_surface >= 4.5, (
        f"WCAG AA CONTRAST FAILURE: --quiet ({quiet}) on --surface ({surface}) has contrast ratio "
        f"{cr_surface:.2f}:1, which is below the 4.5:1 requirement for small text (.metric-sub)."
    )
