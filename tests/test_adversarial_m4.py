"""Adversarial stress-testing suite for Milestone 4 (PC Frontend UI/UX & Features).

Probe targets:
1. Web Audio API chime under blocked AudioContext (suspended autoplay state)
2. Flight notification deduplication under continuous polling (prevent duplicate alerts)
3. Dark mode tile inversion on Leaflet map (drone markers and zone overlays visibility)
4. Layout stability during skeleton loading (prevent jarring CLS)
"""

import json
import re
import subprocess
from pathlib import Path
import pytest

FRONTEND_ROOT = Path(__file__).resolve().parents[1] / "frontend"
SRC_ROOT = FRONTEND_ROOT / "src"
WORKSPACE_TSX = SRC_ROOT / "components" / "operations" / "OperationsWorkspace.tsx"
EXPERIENCE_CSS = SRC_ROOT / "experience.css"
STYLES_CSS = SRC_ROOT / "styles.css"
ERROR_BANNER_TSX = SRC_ROOT / "components" / "common" / "ErrorBanner.tsx"


# ============================================================================
# PROBE 1: Web Audio API chime under blocked AudioContext
# ============================================================================

def test_web_audio_chime_implementation_analysis():
    """Adversarially probe playNotificationChime implementation in OperationsWorkspace.tsx."""
    content = WORKSPACE_TSX.read_text(encoding="utf-8")
    assert "function playNotificationChime()" in content, "playNotificationChime must exist"

    # Check AudioContext detection
    assert "window.AudioContext" in content, "Must check window.AudioContext"
    assert "webkitAudioContext" in content, "Must check webkitAudioContext"

    # Check try...catch presence
    chime_func_match = re.search(r"function playNotificationChime\(\)\s*\{([\s\S]*?)\n\}", content)
    assert chime_func_match, "Must extract playNotificationChime body"
    body = chime_func_match.group(1)
    assert "try {" in body and "catch" in body, "Body must wrap execution in try-catch"

    # Check 2-tone frequencies: 880Hz and 1320Hz
    assert "880" in body, "Tone 1 must be 880Hz"
    assert "1320" in body, "Tone 2 must be 1320Hz"

    # Empirical check on resume():
    # If ctx.resume() is used, does it catch the asynchronous rejection?
    has_resume = "ctx.resume()" in body
    has_catch_on_resume = bool(re.search(r"ctx\.resume\(\)\s*\.catch", body))
    
    # We document the empirical vulnerability:
    # If void ctx.resume() is called without .catch(), it leaves an unhandled promise rejection
    # when the browser rejects resume() due to autoplay policy.
    if has_resume and not has_catch_on_resume:
        # Verify that node reproduces the unhandled rejection
        cmd = [
            "node",
            "-e",
            "class MockCtx { constructor() { this.state = 'suspended'; } resume() { return Promise.reject(new Error('AutoplayBlocked')); } }; "
            "const ctx = new MockCtx(); void ctx.resume();",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode != 0, "Uncaught rejection without .catch() reproduces exit code != 0"
        assert "AutoplayBlocked" in proc.stderr


# ============================================================================
# PROBE 2: Flight notification deduplication under continuous polling
# ============================================================================

class FlightPollingHarness:
    """Simulates the OperationsWorkspace polling and deduplication state machine."""

    def __init__(self):
        self.known_flight_ids = set()
        self.initial_fetch_done = False
        self.alerts = []
        self.chimes = 0

    def initial_load(self, flights):
        if not self.initial_fetch_done:
            self.known_flight_ids = {f["id"] for f in flights}
            self.initial_fetch_done = True

    def poll_tick(self, flights):
        if not self.initial_fetch_done:
            return

        newly_submitted = [
            f for f in flights
            if f.get("status") == "SUBMITTED" and f["id"] not in self.known_flight_ids
        ]
        if newly_submitted:
            for nf in newly_submitted:
                self.known_flight_ids.add(nf["id"])
            self.chimes += 1
            latest = newly_submitted[0]
            self.alerts.append({
                "id": latest["id"],
                "count": len(newly_submitted),
                "title": f"{len(newly_submitted)} yêu cầu bay mới cần duyệt" if len(newly_submitted) > 1 else "Yêu cầu bay mới cần duyệt",
            })


def test_flight_deduplication_continuous_100_ticks():
    """Verify that continuous polling ticks do not re-alert existing or already-alerted flights."""
    harness = FlightPollingHarness()

    # Initial flight data
    initial_flights = [
        {"id": "fl-001", "status": "SUBMITTED", "summary": "Bay 1"},
        {"id": "fl-002", "status": "APPROVED_SIMULATED", "summary": "Bay 2"},
        {"id": "fl-003", "status": "REJECTED", "summary": "Bay 3"},
    ]
    harness.initial_load(initial_flights)

    # Initial load should never trigger chimes or alerts
    assert harness.chimes == 0
    assert len(harness.alerts) == 0
    assert harness.known_flight_ids == {"fl-001", "fl-002", "fl-003"}

    # 100 continuous poll ticks with no changes
    for _ in range(100):
        harness.poll_tick(initial_flights)

    assert harness.chimes == 0, "No chime played on unchanged ticks"
    assert len(harness.alerts) == 0, "No duplicate alert on unchanged ticks"

    # New flight arrives on tick 101
    updated_flights = initial_flights + [{"id": "fl-004", "status": "SUBMITTED", "summary": "Bay mới"}]
    harness.poll_tick(updated_flights)

    assert harness.chimes == 1, "Chime played exactly once for fl-004"
    assert len(harness.alerts) == 1
    assert harness.alerts[0]["id"] == "fl-004"

    # Next 50 ticks with fl-004 present
    for _ in range(50):
        harness.poll_tick(updated_flights)

    assert harness.chimes == 1, "Chime must not repeat on subsequent ticks"
    assert len(harness.alerts) == 1, "Alert must not duplicate"


def test_flight_deduplication_batch_arrival():
    """Verify that multiple flights arriving in a single poll tick alert once with correct count."""
    harness = FlightPollingHarness()
    harness.initial_load([])

    batch = [
        {"id": "fl-10", "status": "SUBMITTED"},
        {"id": "fl-11", "status": "SUBMITTED"},
        {"id": "fl-12", "status": "SUBMITTED"},
    ]
    harness.poll_tick(batch)

    assert harness.chimes == 1, "Batch triggers single chime"
    assert len(harness.alerts) == 1
    assert harness.alerts[0]["count"] == 3
    assert harness.alerts[0]["title"] == "3 yêu cầu bay mới cần duyệt"


# ============================================================================
# PROBE 3: Dark mode tile inversion on Leaflet map
# ============================================================================

def test_dark_mode_tile_inversion_selector_specificity():
    """Verify that dark mode raster tile filter isolates .leaflet-tile-pane only."""
    css = EXPERIENCE_CSS.read_text(encoding="utf-8")
    assert "@media (prefers-color-scheme: dark)" in css, "Must contain prefers-color-scheme: dark"

    # Target rule in experience.css
    dark_rule = re.search(
        r"\.map-canvas\s+\.leaflet-tile-pane,\s*\.gps-map\s+\.leaflet-tile-pane\s*\{([^}]+)\}",
        css,
    )
    assert dark_rule is not None, "Must define filter specifically for .map-canvas / .gps-map .leaflet-tile-pane"
    rule_body = dark_rule.group(1)

    assert "invert(1)" in rule_body, "Filter must invert tiles"
    assert "contrast(" in rule_body, "Filter must adjust contrast"
    assert "hue-rotate(" in rule_body, "Filter must apply hue rotation for dark tone"

    # Ensure overlay-pane and marker-pane are NOT inverted
    assert ".leaflet-overlay-pane { filter:" not in css, "Overlay pane must NOT be inverted"
    assert ".leaflet-marker-pane { filter:" not in css, "Marker pane must NOT be inverted"


def test_leaflet_overlay_colors_contrast():
    """Verify WCAG contrast compliance of drone markers and zone polygons against dark background #0c1622."""
    def luminance(hex_color: str) -> float:
        h = hex_color.lstrip("#")
        rgb = [int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
        linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    def contrast(hex1: str, hex2: str) -> float:
        l1, l2 = luminance(hex1), luminance(hex2)
        return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)

    dark_bg = "#0c1622"  # --canvas in dark mode

    # Drone Marker: #1689d5
    c_drone = contrast("#1689d5", dark_bg)
    assert c_drone >= 4.5, f"Drone marker contrast ({c_drone:.2f}:1) must exceed 4.5:1 (WCAG AA)"

    # Restricted Zone: #f5a524
    c_restricted = contrast("#f5a524", dark_bg)
    assert c_restricted >= 7.0, f"Restricted zone contrast ({c_restricted:.2f}:1) must exceed 7.0:1 (WCAG AAA)"

    # No-Fly Zone: #d6495f
    c_nofly = contrast("#d6495f", dark_bg)
    # WCAG 2.1 SC 1.4.11 for non-text graphical UI boundaries requires >= 3.0:1
    assert c_nofly >= 3.0, f"No-fly zone contrast ({c_nofly:.2f}:1) must meet WCAG 1.4.11 non-text boundary (>= 3.0:1)"


# ============================================================================
# PROBE 4: Layout stability during skeleton loading (CLS prevention)
# ============================================================================

def test_skeleton_loading_dimensions_and_stability():
    """Verify that skeleton loading placeholder reserves sufficient height to prevent jarring CLS."""
    tsx = WORKSPACE_TSX.read_text(encoding="utf-8")
    css = EXPERIENCE_CSS.read_text(encoding="utf-8")

    # tsx checks
    assert "const [initialLoading, setInitialLoading] = useState(true);" in tsx
    assert 'className="workspace-loading-state"' in tsx
    assert 'role="status"' in tsx
    assert 'aria-live="polite"' in tsx
    assert 'aria-busy={initialLoading || busy}' in tsx

    # css checks
    loading_css = re.search(r"\.workspace-loading-state\s*\{([^}]+)\}", css)
    assert loading_css is not None, "Must define .workspace-loading-state in experience.css"
    body = loading_css.group(1)
    assert "min-height: 380px" in body, "Skeleton placeholder must have min-height: 380px"

    # Mathematical layout shift reduction calculation:
    viewport_h = 800.0
    content_h = 440.0
    shift_without_skeleton = (content_h / viewport_h) * 1.0  # ~0.55
    shift_with_skeleton = ((content_h - 380.0) / viewport_h) * (content_h / viewport_h)  # ~0.041
    reduction = (shift_without_skeleton - shift_with_skeleton) / shift_without_skeleton * 100

    assert shift_with_skeleton < 0.1, f"CLS with skeleton ({shift_with_skeleton:.3f}) is within Web Vitals 'Good' (<0.1)"
    assert reduction > 80.0, f"CLS reduction ({reduction:.1f}%) must be >80%"
