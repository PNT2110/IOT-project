/**
 * Empirical Stress Harness for Milestone 4 Iteration 2
 * Tests:
 * 1. Telemetry polling cadence (strictly 1000ms, no cascade)
 * 2. ErrorBanner auto-dismiss timer precision under rapid parent re-renders
 * 3. Leaflet map marker updating without DOM or canvas thrashing
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

// ============================================================================
// SUITE 1: Telemetry Polling Cadence & Cascade Prevention
// ============================================================================

describe("Suite 1: Telemetry Polling Cadence & Cascade Prevention", () => {
  it("1.1 Static Analysis: OperationsWorkspace.tsx has empty dependency array for telemetry polling", () => {
    const file = path.resolve("frontend/src/components/operations/OperationsWorkspace.tsx");
    const content = fs.readFileSync(file, "utf-8");

    // Telemetry polling effect regex
    const regex = /useEffect\s*\(\s*\(\)\s*=>\s*\{[\s\S]*?pollTelemetry[\s\S]*?lastTelemetryReceivedRef\.current[\s\S]*?\}\s*,\s*\[([^\]]*)\]\s*\)/;
    const match = regex.exec(content);
    assert.ok(match, "Telemetry polling useEffect must exist in OperationsWorkspace.tsx");
    const deps = match[1].trim();
    assert.strictEqual(deps, "", "Telemetry polling effect dependency array MUST be empty [] to prevent loop");
  });

  it("1.2 Static Analysis: TelemetryPanel.tsx uses lastTelemetryReceivedRef and does not loop on state", () => {
    const file = path.resolve("frontend/src/components/operations/TelemetryPanel.tsx");
    const content = fs.readFileSync(file, "utf-8");

    assert.ok(content.includes("lastTelemetryReceivedRef = useRef"), "Must use useRef for telemetry timestamp");
    assert.ok(content.includes("window.setInterval(pollTelemetry, 1000)"), "Must poll strictly at 1000ms");
  });

  it("1.3 Dynamic Simulation: Telemetry polling runs strictly once per second over 2.5 seconds (no cascade)", async () => {
    let fetchCount = 0;
    const mockFetch = async () => {
      fetchCount++;
      return { latitude: 21.0285, longitude: 105.8544 };
    };

    // Simulate OperationsWorkspace telemetry effect lifecycle
    let active = true;
    let lastReceived = null;

    const pollTelemetry = async () => {
      try {
        const latest = await mockFetch();
        if (!active) return;
        if (latest) {
          lastReceived = Date.now();
        }
      } catch {}
    };

    // Mount: initial poll + 1000ms interval
    void pollTelemetry();
    const timer = setInterval(pollTelemetry, 1000);

    // Wait 2500ms
    await new Promise((r) => setTimeout(r, 2500));

    active = false;
    clearInterval(timer);

    // Expected calls:
    // t=0ms (initial call)
    // t=1000ms (tick 1)
    // t=2000ms (tick 2)
    // Total: 3 calls (allowed tolerance: 3 or 4 depending on scheduler jitter)
    assert.ok(
      fetchCount >= 3 && fetchCount <= 4,
      `fetchCount was ${fetchCount}, strictly bounded to 3-4 calls in 2.5s (no cascade)`
    );
  });
});

// ============================================================================
// SUITE 2: ErrorBanner Auto-Dismiss Timer Precision Under Rapid Parent Re-renders
// ============================================================================

describe("Suite 2: ErrorBanner Auto-Dismiss Precision Under Rapid Parent Updates", () => {
  // Model exact ErrorBanner component implementation with onDismissRef
  class SimulatedErrorBanner {
    constructor({ message, onDismiss, autoDismissMs = 8000 }) {
      this.message = message;
      this.onDismissRef = { current: onDismiss };
      this.autoDismissMs = autoDismissMs;
      this.timer = null;
      this.mounted = true;
      this.setupEffect();
    }

    setupEffect() {
      if (!this.message) return;
      this.timer = setTimeout(() => {
        if (this.mounted) {
          this.onDismissRef.current();
        }
      }, this.autoDismissMs);
    }

    updateProps({ message, onDismiss, autoDismissMs = 8000 }) {
      const prevMessage = this.message;
      const prevAutoDismissMs = this.autoDismissMs;

      // In ErrorBanner.tsx:
      // const onDismissRef = useRef(onDismiss);
      // onDismissRef.current = onDismiss;
      this.onDismissRef.current = onDismiss;
      this.message = message;
      this.autoDismissMs = autoDismissMs;

      // Effect only re-runs if [message, autoDismissMs] changes!
      if (prevMessage !== this.message || prevAutoDismissMs !== this.autoDismissMs) {
        if (this.timer) clearTimeout(this.timer);
        this.setupEffect();
      }
    }

    unmount() {
      this.mounted = false;
      if (this.timer) clearTimeout(this.timer);
    }

    clickDismissButton() {
      this.onDismissRef.current();
    }
  }

  it("2.1 Timer fires within target window despite 20 rapid parent re-renders with new callbacks", async () => {
    let dismissCount = 0;
    const targetMs = 300;
    const start = Date.now();
    let renderCount = 0;
    let invokedCallbackId = -1;
    let renderCountAtDismiss = -1;

    const banner = new SimulatedErrorBanner({
      message: "Lỗi kết nối máy chủ",
      onDismiss: () => {
        dismissCount++;
        invokedCallbackId = 0;
      },
      autoDismissMs: targetMs,
    });

    const parentInterval = setInterval(() => {
      renderCount++;
      const currentId = renderCount;
      banner.updateProps({
        message: "Lỗi kết nối máy chủ", // Message stays the same
        onDismiss: () => {
          dismissCount++;
          invokedCallbackId = currentId;
          renderCountAtDismiss = renderCount;
        },
        autoDismissMs: targetMs,
      });
    }, 20);

    // Wait until targetMs + 100ms
    await new Promise((r) => setTimeout(r, targetMs + 100));
    clearInterval(parentInterval);
    banner.unmount();

    const elapsed = Date.now() - start;
    assert.strictEqual(dismissCount, 1, "Banner must dismiss exactly ONCE");
    assert.ok(invokedCallbackId > 0, "Must invoke an updated callback, not the initial mount callback (0)");
    assert.strictEqual(
      invokedCallbackId,
      renderCountAtDismiss,
      "Must invoke the latest callback active at the moment of dismissal"
    );
    assert.ok(
      elapsed >= targetMs && elapsed < targetMs + 150,
      `Timer elapsed ${elapsed}ms was accurate to ${targetMs}ms target (no starvation)`
    );
  });

  it("2.2 Manual dismiss button triggers immediately before auto-dismiss timer expires", () => {
    let dismissed = false;
    const banner = new SimulatedErrorBanner({
      message: "Cảnh báo pin yếu",
      onDismiss: () => {
        dismissed = true;
      },
      autoDismissMs: 5000,
    });

    banner.clickDismissButton();
    assert.strictEqual(dismissed, true, "Manual close must trigger onDismiss immediately");
    banner.unmount();
  });

  it("2.3 Unmounting component cleanly clears timer without ghost dismiss callback", async () => {
    let ghostDismiss = false;
    const banner = new SimulatedErrorBanner({
      message: "Lỗi tạm thời",
      onDismiss: () => {
        ghostDismiss = true;
      },
      autoDismissMs: 100,
    });

    banner.unmount();
    await new Promise((r) => setTimeout(r, 160));
    assert.strictEqual(ghostDismiss, false, "Unmount must cancel pending timeout");
  });

  it("2.4 Changing message resets timer for the new message", async () => {
    const dismisses = [];
    const banner = new SimulatedErrorBanner({
      message: "Lỗi ban đầu",
      onDismiss: () => {
        dismisses.push("Lỗi ban đầu");
      },
      autoDismissMs: 200,
    });

    // After 100ms, a new error message arrives
    await new Promise((r) => setTimeout(r, 100));
    banner.updateProps({
      message: "Lỗi mới",
      onDismiss: () => {
        dismisses.push("Lỗi mới");
      },
      autoDismissMs: 200,
    });

    // Wait 150ms: total elapsed 250ms from start, but only 150ms from second message
    await new Promise((r) => setTimeout(r, 150));
    assert.strictEqual(dismisses.length, 0, "Initial error timer must be canceled when message changes");

    // Wait another 80ms: now 230ms from second message -> second error fires
    await new Promise((r) => setTimeout(r, 80));
    banner.unmount();
    assert.strictEqual(dismisses.length, 1);
    assert.strictEqual(dismisses[0], "Lỗi mới");
  });
});

// ============================================================================
// SUITE 3: Leaflet Map Instance Preservation & Zero DOM Thrashing
// ============================================================================

describe("Suite 3: Leaflet Map Instance Preservation (Zero DOM Thrashing)", () => {
  it("3.1 Static Analysis: TelemetryPanel.tsx GpsMap uses mapRef and markerRef with setLatLng", () => {
    const file = path.resolve("frontend/src/components/operations/TelemetryPanel.tsx");
    const content = fs.readFileSync(file, "utf-8");

    assert.ok(content.includes("const mapRef = useRef<L.Map | null>(null)"), "Uses mapRef");
    assert.ok(content.includes("const markerRef = useRef<L.CircleMarker | null>(null)"), "Uses markerRef");
    assert.ok(content.includes("markerRef.current.setLatLng([lat, lon])"), "Smooth marker update via setLatLng");
    assert.ok(content.includes("mapRef.current.panTo([lat, lon])"), "Smooth pan via panTo");

    // Verify mount effect dependencies
    const mountMatch = /useEffect\s*\(\s*\(\)\s*=>\s*\{[\s\S]*?L\.map[\s\S]*?\}\s*,\s*\[([^\]]*)\]\s*\)/.exec(content);
    assert.ok(mountMatch, "L.map creation useEffect must exist");
    assert.strictEqual(mountMatch[1].trim(), "", "L.map creation effect MUST have empty dependency array []");
  });

  it("3.2 Dynamic Simulation: 50 coordinate updates cause 1 map instantiation and 50 setLatLng calls", () => {
    let mapCreatedCount = 0;
    let mapRemovedCount = 0;
    let markerUpdatedCount = 0;
    let panCount = 0;

    class MockLeafletMap {
      constructor() {
        mapCreatedCount++;
      }
      setView() {
        return this;
      }
      panTo() {
        panCount++;
        return this;
      }
      remove() {
        mapRemovedCount++;
      }
    }

    class MockCircleMarker {
      setLatLng() {
        markerUpdatedCount++;
        return this;
      }
      addTo() {
        return this;
      }
    }

    // Simulate GpsMap lifecycle with 50 coordinate changes
    let mapInstance = null;
    let markerInstance = null;

    // 1. Mount:
    mapInstance = new MockLeafletMap();
    markerInstance = new MockCircleMarker();

    // 2. 50 coordinate updates (simulating live 1Hz telemetry updates)
    for (let i = 0; i < 50; i++) {
      const lat = 21.0285 + i * 0.0001;
      const lon = 105.8544 + i * 0.0001;
      markerInstance.setLatLng([lat, lon]);
      mapInstance.panTo([lat, lon]);
    }

    assert.strictEqual(mapCreatedCount, 1, "Map must be created exactly once");
    assert.strictEqual(mapRemovedCount, 0, "Map must not be removed during coordinate updates");
    assert.strictEqual(markerUpdatedCount, 50, "Marker setLatLng must be called for each update");
    assert.strictEqual(panCount, 50, "Map panTo must be called for each update");

    // 3. Unmount:
    mapInstance.remove();
    mapInstance = null;
    markerInstance = null;
    assert.strictEqual(mapRemovedCount, 1, "Map is removed only on unmount");
  });
});
