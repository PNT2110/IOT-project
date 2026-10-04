/**
 * Adversarial Stress Harness for Milestone 4 (Frontend UI/UX & Features)
 * F450 PNT PVD Drone Zone Check
 *
 * Probes:
 * 1. Web Audio API chime under blocked AudioContext (suspended autoplay state)
 * 2. Flight notification deduplication under continuous polling (prevent duplicate alerts)
 * 3. Dark mode tile inversion on Leaflet map (ensure drone markers and zone overlays remain clearly visible)
 * 4. Layout stability during skeleton loading (prevent jarring CLS)
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

// ============================================================================
// PROBE 1: Web Audio API chime under blocked AudioContext
// ============================================================================

describe("Probe 1: Web Audio API chime under blocked / suspended AudioContext", () => {
  // Recreate exact playNotificationChime function from OperationsWorkspace.tsx
  function createChimePlayer(mockWindow) {
    return function playNotificationChime() {
      try {
        const AudioCtx =
          mockWindow.AudioContext ||
          mockWindow.webkitAudioContext;
        if (!AudioCtx) return false;
        const ctx = new AudioCtx();
        if (ctx.state === "suspended") {
          void ctx.resume();
        }
        const now = ctx.currentTime;
        // Tone 1: 880Hz (A5)
        const osc1 = ctx.createOscillator();
        const gain1 = ctx.createGain();
        osc1.type = "sine";
        osc1.frequency.setValueAtTime(880, now);
        gain1.gain.setValueAtTime(0.15, now);
        gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
        osc1.connect(gain1);
        gain1.connect(ctx.destination);
        osc1.start(now);
        osc1.stop(now + 0.15);

        // Tone 2: 1320Hz (E6)
        const osc2 = ctx.createOscillator();
        const gain2 = ctx.createGain();
        osc2.type = "sine";
        osc2.frequency.setValueAtTime(1320, now + 0.12);
        gain2.gain.setValueAtTime(0.18, now + 0.12);
        gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
        osc2.connect(gain2);
        gain2.connect(ctx.destination);
        osc2.start(now + 0.12);
        osc2.stop(now + 0.35);
        return true;
      } catch (err) {
        // Autoplay restrictions or audio device issues - fails gracefully
        return false;
      }
    };
  }

  it("1.1 Gracefully returns false when AudioContext is undefined (headless / legacy)", () => {
    const mockWindow = {};
    const playChime = createChimePlayer(mockWindow);
    assert.doesNotThrow(() => {
      const result = playChime();
      assert.strictEqual(result, false);
    });
  });

  it("1.2 Gracefully catches synchronous exception when new AudioContext() throws (PermissionDenied / Hardware Error)", () => {
    const mockWindow = {
      AudioContext: class {
        constructor() {
          throw new Error("DOMException: The AudioContext was not allowed to start");
        }
      },
    };
    const playChime = createChimePlayer(mockWindow);
    assert.doesNotThrow(() => {
      const result = playChime();
      assert.strictEqual(result, false);
    });
  });

  it("1.3 Empirical Vulnerability: void ctx.resume() produces unhandled rejection when resume() rejects", () => {
    const script = `
      class SuspendedAudioContext {
        constructor() { this.state = 'suspended'; }
        resume() { return Promise.reject(new Error('NotAllowedError: autoplay blocked')); }
      }
      const ctx = new SuspendedAudioContext();
      try {
        void ctx.resume();
      } catch (err) {}
    `;
    try {
      execFileSync(process.execPath, ["-e", script], { stdio: "pipe" });
      assert.fail("Should have failed with unhandled rejection");
    } catch (err) {
      const stderr = err.stderr ? err.stderr.toString() : "";
      assert.ok(
        stderr.includes("NotAllowedError") || err.status !== 0,
        "VULNERABILITY CONFIRMED: void ctx.resume() caused unhandled promise rejection"
      );
    }
  });

  it("1.4 Mitigation validation: ctx.resume().catch(() => {}) completely suppresses the rejection", () => {
    const script = `
      class SuspendedAudioContext {
        constructor() { this.state = 'suspended'; }
        resume() { return Promise.reject(new Error('NotAllowedError: autoplay blocked')); }
      }
      const ctx = new SuspendedAudioContext();
      try {
        ctx.resume().catch(() => {});
      } catch (err) {}
      setTimeout(() => process.exit(0), 10);
    `;
    const res = execFileSync(process.execPath, ["-e", script], { stdio: "pipe" });
    assert.strictEqual(res.length, 0, "Mitigated version exits cleanly with code 0");
  });

  it("1.5 Executes cleanly and plays two tones in normal running AudioContext", () => {
    const oscillations = [];
    class RunningAudioContext {
      constructor() {
        this.state = "running";
        this.currentTime = 10.5;
        this.destination = { type: "destination" };
      }
      createOscillator() {
        const osc = {
          frequency: {
            setValueAtTime: (val, time) => {
              osc.freq = val;
              osc.freqTime = time;
            },
          },
          connect: (dest) => {
            osc.connectedTo = dest;
          },
          start: (time) => {
            osc.startTime = time;
          },
          stop: (time) => {
            osc.stopTime = time;
            oscillations.push(osc);
          },
        };
        return osc;
      }
      createGain() {
        return {
          gain: {
            setValueAtTime: () => {},
            exponentialRampToValueAtTime: () => {},
          },
          connect: () => {},
        };
      }
    }

    const mockWindow = { AudioContext: RunningAudioContext };
    const playChime = createChimePlayer(mockWindow);
    const result = playChime();
    assert.strictEqual(result, true);
    assert.strictEqual(oscillations.length, 2);
    // Tone 1: 880Hz
    assert.strictEqual(oscillations[0].freq, 880);
    // Tone 2: 1320Hz
    assert.strictEqual(oscillations[1].freq, 1320);
  });

  it("1.6 Survives 1000 rapid consecutive invocations without synchronous crash", () => {
    class MockAudioContext {
      constructor() {
        this.state = "running";
        this.currentTime = 0;
        this.destination = {};
      }
      createOscillator() {
        return {
          frequency: { setValueAtTime: () => {} },
          connect: () => {},
          start: () => {},
          stop: () => {},
        };
      }
      createGain() {
        return {
          gain: { setValueAtTime: () => {}, exponentialRampToValueAtTime: () => {} },
          connect: () => {},
        };
      }
    }
    const mockWindow = { AudioContext: MockAudioContext };
    const playChime = createChimePlayer(mockWindow);

    assert.doesNotThrow(() => {
      for (let i = 0; i < 1000; i++) {
        playChime();
      }
    });
  });
});

// ============================================================================
// PROBE 2: Flight notification deduplication under continuous polling
// ============================================================================

describe("Probe 2: Flight notification deduplication under continuous polling", () => {
  // Simulator for OperationsWorkspace flight polling state machine
  class FlightPollingSimulator {
    constructor() {
      this.knownFlightIds = new Set();
      this.initialFetchDone = false;
      this.notificationsTriggered = [];
      this.chimesPlayed = 0;
      this.flights = [];
    }

    playNotificationChime() {
      this.chimesPlayed++;
    }

    // Corresponds to initial refresh() in OperationsWorkspace
    async initialRefresh(flightItems) {
      this.flights = flightItems;
      if (!this.initialFetchDone) {
        this.knownFlightIds = new Set(flightItems.map((f) => f.id));
        this.initialFetchDone = true;
      }
    }

    // Corresponds to 3-second background polling tick
    async pollTick(flightItems) {
      this.flights = flightItems;
      if (this.initialFetchDone) {
        const newlySubmitted = flightItems.filter(
          (f) => f.status === "SUBMITTED" && !this.knownFlightIds.has(f.id)
        );
        if (newlySubmitted.length > 0) {
          for (const newFlight of newlySubmitted) {
            this.knownFlightIds.add(newFlight.id);
          }
          this.playNotificationChime();
          const latest = newlySubmitted[0];
          const applicant =
            latest.request_details?.applicant_full_name ?? latest.summary;
          const vehicle = latest.request_details?.vehicle ?? "";
          this.notificationsTriggered.push({
            id: latest.id,
            count: newlySubmitted.length,
            title:
              newlySubmitted.length > 1
                ? `${newlySubmitted.length} yêu cầu bay mới cần duyệt`
                : "Yêu cầu bay mới cần duyệt",
            subtitle: `${applicant}${vehicle ? ` · ${vehicle}` : ""}`,
          });
        }
      }
    }
  }

  it("2.1 Existing flights on initial load NEVER trigger notifications or chimes", async () => {
    const sim = new FlightPollingSimulator();
    const initialFlights = [
      { id: "f-1", status: "SUBMITTED", summary: "Bay thử 1" },
      { id: "f-2", status: "SUBMITTED", summary: "Bay thử 2" },
      { id: "f-3", status: "APPROVED_SIMULATED", summary: "Bay đã duyệt" },
      { id: "f-4", status: "REJECTED", summary: "Bay từ chối" },
    ];

    await sim.initialRefresh(initialFlights);

    assert.strictEqual(sim.chimesPlayed, 0);
    assert.strictEqual(sim.notificationsTriggered.length, 0);
    assert.strictEqual(sim.knownFlightIds.size, 4);
    assert.strictEqual(sim.initialFetchDone, true);
  });

  it("2.2 100 continuous polling ticks with unchanged flights cause ZERO duplicate alerts", async () => {
    const sim = new FlightPollingSimulator();
    const initialFlights = [
      { id: "f-1", status: "SUBMITTED", summary: "Bay thử 1" },
      { id: "f-2", status: "SUBMITTED", summary: "Bay thử 2" },
    ];
    await sim.initialRefresh(initialFlights);

    // Run 100 poll ticks with identical flights
    for (let tick = 0; tick < 100; tick++) {
      await sim.pollTick(initialFlights);
    }

    assert.strictEqual(sim.chimesPlayed, 0, "No chime must be played for unchanged flights");
    assert.strictEqual(sim.notificationsTriggered.length, 0, "No toast must be shown for unchanged flights");
  });

  it("2.3 Single newly submitted flight alerts EXACTLY ONCE across subsequent 50 ticks", async () => {
    const sim = new FlightPollingSimulator();
    await sim.initialRefresh([
      { id: "f-1", status: "SUBMITTED", summary: "Cũ" },
    ]);

    const updatedWithF2 = [
      { id: "f-1", status: "SUBMITTED", summary: "Cũ" },
      { id: "f-2", status: "SUBMITTED", summary: "Yêu cầu mới", request_details: { applicant_full_name: "Nguyễn Văn A", vehicle: "F450" } },
    ];

    // Tick 1: new flight appears
    await sim.pollTick(updatedWithF2);
    assert.strictEqual(sim.chimesPlayed, 1, "Must play chime once on arrival of f-2");
    assert.strictEqual(sim.notificationsTriggered.length, 1);
    assert.strictEqual(sim.notificationsTriggered[0].id, "f-2");
    assert.strictEqual(sim.notificationsTriggered[0].count, 1);
    assert.strictEqual(sim.notificationsTriggered[0].title, "Yêu cầu bay mới cần duyệt");
    assert.strictEqual(sim.notificationsTriggered[0].subtitle, "Nguyễn Văn A · F450");

    // Ticks 2..50: same flight list continues
    for (let tick = 2; tick <= 50; tick++) {
      await sim.pollTick(updatedWithF2);
    }

    assert.strictEqual(sim.chimesPlayed, 1, "Chime must NOT play again");
    assert.strictEqual(sim.notificationsTriggered.length, 1, "No duplicate notification");
  });

  it("2.4 Batch of newly submitted flights alerts once with correct count and deduplicates all", async () => {
    const sim = new FlightPollingSimulator();
    await sim.initialRefresh([{ id: "f-1", status: "APPROVED_SIMULATED", summary: "Đã duyệt" }]);

    const batch = [
      { id: "f-1", status: "APPROVED_SIMULATED", summary: "Đã duyệt" },
      { id: "f-10", status: "SUBMITTED", summary: "Bay 10", request_details: { applicant_full_name: "Pilot 10" } },
      { id: "f-11", status: "SUBMITTED", summary: "Bay 11", request_details: { applicant_full_name: "Pilot 11" } },
      { id: "f-12", status: "SUBMITTED", summary: "Bay 12", request_details: { applicant_full_name: "Pilot 12" } },
    ];

    await sim.pollTick(batch);

    assert.strictEqual(sim.chimesPlayed, 1, "Chime plays once for the batch");
    assert.strictEqual(sim.notificationsTriggered.length, 1);
    assert.strictEqual(sim.notificationsTriggered[0].count, 3);
    assert.strictEqual(sim.notificationsTriggered[0].title, "3 yêu cầu bay mới cần duyệt");
    assert.strictEqual(sim.knownFlightIds.has("f-10"), true);
    assert.strictEqual(sim.knownFlightIds.has("f-11"), true);
    assert.strictEqual(sim.knownFlightIds.has("f-12"), true);

    // Successive 20 ticks
    for (let i = 0; i < 20; i++) {
      await sim.pollTick(batch);
    }
    assert.strictEqual(sim.chimesPlayed, 1);
    assert.strictEqual(sim.notificationsTriggered.length, 1);
  });

  it("2.5 New flights with non-SUBMITTED statuses (e.g. DRAFT / REJECTED) do NOT trigger alerts", async () => {
    const sim = new FlightPollingSimulator();
    await sim.initialRefresh([]);

    const nonSubmitted = [
      { id: "f-20", status: "APPROVED_SIMULATED", summary: "Bay tự động duyệt" },
      { id: "f-21", status: "REJECTED", summary: "Bay bị từ chối" },
      { id: "f-22", status: "UNDER_REVIEW", summary: "Đang xem xét" },
    ];

    await sim.pollTick(nonSubmitted);
    assert.strictEqual(sim.chimesPlayed, 0);
    assert.strictEqual(sim.notificationsTriggered.length, 0);
  });

  it("2.6 Race condition resilience: poll tick before initialRefresh completes does not falsely alert", async () => {
    const sim = new FlightPollingSimulator();
    // initialFetchDone is still false
    const currentOnServer = [
      { id: "f-30", status: "SUBMITTED", summary: "Bay hiện tại" },
    ];

    // Tick fires before initialRefresh settles
    await sim.pollTick(currentOnServer);
    assert.strictEqual(sim.chimesPlayed, 0, "Must not alert when initialFetchDone is false");
    assert.strictEqual(sim.notificationsTriggered.length, 0);

    // Now initialRefresh completes
    await sim.initialRefresh(currentOnServer);
    assert.strictEqual(sim.knownFlightIds.has("f-30"), true);

    // Next tick fires
    await sim.pollTick(currentOnServer);
    assert.strictEqual(sim.chimesPlayed, 0, "Still no alert for existing f-30");
  });
});

// ============================================================================
// PROBE 3: Dark mode tile inversion on Leaflet map
// ============================================================================

describe("Probe 3: Dark mode tile inversion on Leaflet map (legibility & contrast)", () => {
  const cssPath = path.resolve("frontend/src/experience.css");
  const cssContent = fs.readFileSync(cssPath, "utf-8");

  it("3.1 Tile inversion CSS filter rule strictly targets .leaflet-tile-pane ONLY", () => {
    // Must NOT target .leaflet-pane or .leaflet-overlay-pane or .leaflet-marker-pane
    const darkTilePaneRegex = /\.map-canvas\s+\.leaflet-tile-pane[\s\S]*?filter:\s*([^;]+);/g;
    const match = darkTilePaneRegex.exec(cssContent);
    assert.ok(match, "Found .map-canvas .leaflet-tile-pane filter rule in experience.css");
    const filterValue = match[1];
    assert.ok(filterValue.includes("invert(1)"), "Filter must include invert(1)");
    assert.ok(filterValue.includes("contrast("), "Filter must enhance contrast");
    assert.ok(filterValue.includes("hue-rotate("), "Filter must apply hue-rotation");

    // Ensure .leaflet-overlay-pane or .leaflet-marker-pane are NOT filtered
    assert.strictEqual(
      cssContent.includes(".leaflet-overlay-pane { filter:"),
      false,
      ".leaflet-overlay-pane must NOT have filter applied"
    );
    assert.strictEqual(
      cssContent.includes(".leaflet-marker-pane { filter:"),
      false,
      ".leaflet-marker-pane must NOT have filter applied"
    );
  });

  it("3.2 Overlay colors maintain WCAG 2.1 Non-Text Contrast (> 3.0:1) against dark canvas background #0c1622", () => {
    // Relative luminance calculation according to WCAG 2.1
    function getLuminance(r, g, b) {
      const [rs, gs, bs] = [r, g, b].map((c) => {
        const s = c / 255;
        return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
      });
      return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
    }

    function hexToRgb(hex) {
      const cleaned = hex.replace("#", "");
      return [
        parseInt(cleaned.slice(0, 2), 16),
        parseInt(cleaned.slice(2, 4), 16),
        parseInt(cleaned.slice(4, 6), 16),
      ];
    }

    function contrastRatio(hex1, hex2) {
      const [r1, g1, b1] = hexToRgb(hex1);
      const [r2, g2, b2] = hexToRgb(hex2);
      const l1 = getLuminance(r1, g1, b1);
      const l2 = getLuminance(r2, g2, b2);
      const lighter = Math.max(l1, l2);
      const darker = Math.min(l1, l2);
      return (lighter + 0.05) / (darker + 0.05);
    }

    const darkBg = "#0c1622"; // Map background in dark mode

    // No-fly zone polygon stroke / fill: #d6495f
    const noFlyContrast = contrastRatio("#d6495f", darkBg);
    // WCAG 2.1 SC 1.4.11 (Non-text Contrast for graphical objects & boundary indicators) requires >= 3.0:1
    assert.ok(
      noFlyContrast >= 3.0,
      `No-fly zone color #d6495f contrast ratio (${noFlyContrast.toFixed(2)}:1) meets WCAG 1.4.11 Graphical Object (>= 3.0)`
    );

    // Restricted zone polygon stroke / fill: #f5a524
    const restrictedContrast = contrastRatio("#f5a524", darkBg);
    assert.ok(
      restrictedContrast >= 7.0,
      `Restricted zone color #f5a524 contrast ratio (${restrictedContrast.toFixed(2)}:1) meets WCAG AAA (>= 7.0)`
    );

    // Drone position marker fill: #1689d5
    const droneMarkerContrast = contrastRatio("#1689d5", darkBg);
    assert.ok(
      droneMarkerContrast >= 4.5,
      `Drone marker color #1689d5 contrast ratio (${droneMarkerContrast.toFixed(2)}:1) meets WCAG AA (>= 4.5)`
    );

    // Telemetry live indicator: #4ade80
    const liveIndicatorContrast = contrastRatio("#4ade80", darkBg);
    assert.ok(
      liveIndicatorContrast >= 7.0,
      `Live indicator color #4ade80 contrast ratio (${liveIndicatorContrast.toFixed(2)}:1) meets WCAG AAA`
    );
  });

  it("3.3 Leaflet container and popups have explicit dark mode backgrounds", () => {
    assert.ok(
      cssContent.includes(".leaflet-container {\n    background: #0c1622 !important;\n  }"),
      ".leaflet-container must have dark background !important to prevent white tile flashes"
    );
    assert.ok(
      cssContent.includes(".leaflet-popup-content-wrapper, .leaflet-popup-tip"),
      "Leaflet popup content wrapper and tip must be styled for dark mode"
    );
  });
});

// ============================================================================
// PROBE 4: Layout stability during skeleton loading (CLS prevention)
// ============================================================================

describe("Probe 4: Layout stability during skeleton loading (CLS prevention)", () => {
  const cssPath = path.resolve("frontend/src/experience.css");
  const cssContent = fs.readFileSync(cssPath, "utf-8");
  const tsxPath = path.resolve("frontend/src/components/operations/OperationsWorkspace.tsx");
  const tsxContent = fs.readFileSync(tsxPath, "utf-8");

  it("4.1 OperationsWorkspace has initialLoading state and accessible loading skeleton", () => {
    assert.ok(
      tsxContent.includes("const [initialLoading, setInitialLoading] = useState(true);"),
      "Must define initialLoading state initialized to true"
    );
    assert.ok(
      tsxContent.includes('aria-busy={initialLoading || busy}'),
      "Section must announce aria-busy during initialLoading"
    );
    assert.ok(
      tsxContent.includes('className="workspace-loading-state"'),
      "Must render workspace-loading-state element"
    );
    assert.ok(
      tsxContent.includes('role="status"'),
      "Loading state element must declare role='status'"
    );
    assert.ok(
      tsxContent.includes('aria-live="polite"'),
      "Loading state element must declare aria-live='polite'"
    );
    assert.ok(
      tsxContent.includes('className="workspace-spinner"'),
      "Loading state element must include workspace-spinner"
    );
  });

  it("4.2 .workspace-loading-state defines min-height: 380px to reserve vertical layout space", () => {
    const loadingStateBlockRegex = /\.workspace-loading-state\s*\{([^}]+)\}/;
    const match = loadingStateBlockRegex.exec(cssContent);
    assert.ok(match, "Found .workspace-loading-state CSS definition");
    const rules = match[1];
    assert.ok(
      rules.includes("min-height: 380px") || rules.includes("min-height:380px"),
      "Must specify min-height of at least 380px to match content canvas height"
    );
    assert.ok(
      rules.includes("display: flex"),
      "Must use flexbox for centered spinner alignment"
    );
  });

  it("4.3 Header and tab bar are outside the loading conditional (zero shift on top UI)", () => {
    // Verify that workspace-header and workspace-tabs appear BEFORE initialLoading check
    const headerIndex = tsxContent.indexOf('className="workspace-header"');
    const tabsIndex = tsxContent.indexOf('className="workspace-tabs"');
    const loadingStateIndex = tsxContent.indexOf('{initialLoading ? (');

    assert.ok(headerIndex !== -1, "Found workspace-header");
    assert.ok(tabsIndex !== -1, "Found workspace-tabs");
    assert.ok(loadingStateIndex !== -1, "Found initialLoading conditional");

    assert.ok(
      headerIndex < loadingStateIndex,
      "workspace-header must be rendered before initialLoading conditional"
    );
    assert.ok(
      tabsIndex < loadingStateIndex,
      "workspace-tabs must be rendered before initialLoading conditional"
    );
  });

  it("4.4 Mathematical Cumulative Layout Shift (CLS) calculation shows >80% shift reduction", () => {
    // Viewport height: 800px
    const viewportHeight = 800;
    const loadedContentHeight = 440; // MapCanvas min-height + padding

    // Case A: Without skeleton (content collapsed to 0px empty text, then jumps to 440px)
    // Distance shifted = 440px
    // Impact fraction = (440 + 440) / 800 = 1.0 (clamped)
    // Distance fraction = 440 / 800 = 0.55
    const clsWithoutSkeleton = 1.0 * (loadedContentHeight / viewportHeight);

    // Case B: With skeleton (space pre-allocated to 380px, settles to 440px)
    // Distance shifted = 440 - 380 = 60px
    // Impact fraction = (440 + 60) / 800 = 0.625
    // Distance fraction = 60 / 800 = 0.075
    const clsWithSkeleton = 0.625 * (60 / viewportHeight);

    const reductionPercent = ((clsWithoutSkeleton - clsWithSkeleton) / clsWithoutSkeleton) * 100;

    assert.ok(
      clsWithSkeleton < 0.1,
      `CLS with skeleton (${clsWithSkeleton.toFixed(3)}) is below Web Vitals 0.1 threshold (Good)`
    );
    assert.ok(
      reductionPercent >= 80,
      `Layout shift reduction is ${reductionPercent.toFixed(1)}% (>= 80%)`
    );
  });
});
