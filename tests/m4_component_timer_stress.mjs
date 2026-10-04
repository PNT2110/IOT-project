/**
 * Empirical stress test for ErrorBanner timers, unmounts, and Telemetry effect loop.
 */

// ============================================================================
// Test 1: ErrorBanner Timer Precision & Manual Dismiss & Unmount Cleanup
// ============================================================================

class MockErrorBanner {
  constructor({ message, onDismiss, autoDismissMs = 8000 }) {
    this.message = message;
    this.onDismiss = onDismiss;
    this.autoDismissMs = autoDismissMs;
    this.timer = null;
    this.mounted = true;
    this.setupEffect();
  }

  setupEffect() {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    if (!this.message) return;
    this.timer = setTimeout(() => {
      if (this.mounted) {
        this.onDismiss();
      }
    }, this.autoDismissMs);
  }

  update({ message, onDismiss, autoDismissMs = 8000 }) {
    const prevMessage = this.message;
    const prevOnDismiss = this.onDismiss;
    const prevAutoDismissMs = this.autoDismissMs;
    this.message = message;
    this.onDismiss = onDismiss;
    this.autoDismissMs = autoDismissMs;
    // React effect runs if any dependency in [message, onDismiss, autoDismissMs] changes
    if (
      prevMessage !== this.message ||
      prevOnDismiss !== this.onDismiss ||
      prevAutoDismissMs !== this.autoDismissMs
    ) {
      this.setupEffect();
    }
  }

  unmount() {
    this.mounted = false;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }

  clickManualClose() {
    this.onDismiss();
  }
}

async function testTimerPrecision() {
  console.log("--- Test 1.1: ErrorBanner 8-second auto-dismiss timer precision ---");
  let dismissed = false;
  const start = Date.now();
  
  // Test with 200ms scaled down timer for fast empirical test
  const testMs = 200;
  const banner = new MockErrorBanner({
    message: "Network Error: 500",
    onDismiss: () => {
      dismissed = true;
      const elapsed = Date.now() - start;
      console.log(`  Auto-dismissed after ${elapsed}ms (target: ${testMs}ms)`);
    },
    autoDismissMs: testMs,
  });

  await new Promise((r) => setTimeout(r, testMs + 50));
  if (!dismissed) throw new Error("Banner failed to auto-dismiss!");
  console.log("  PASS: Auto-dismiss timer fired accurately.");
}

async function testManualDismiss() {
  console.log("--- Test 1.2: ErrorBanner manual close button (×) ---");
  let dismissed = false;
  const banner = new MockErrorBanner({
    message: "Sample Error",
    onDismiss: () => {
      dismissed = true;
    },
    autoDismissMs: 5000,
  });

  banner.clickManualClose();
  if (!dismissed) throw new Error("Manual dismiss failed!");
  banner.unmount();
  console.log("  PASS: Manual dismiss button triggers onDismiss immediately.");
}

async function testUnmountCleanup() {
  console.log("--- Test 1.3: ErrorBanner unmount timer cleanup ---");
  let dismissedAfterUnmount = false;
  const banner = new MockErrorBanner({
    message: "Sample Error",
    onDismiss: () => {
      dismissedAfterUnmount = true;
    },
    autoDismissMs: 100,
  });

  banner.unmount();
  await new Promise((r) => setTimeout(r, 150));
  if (dismissedAfterUnmount) throw new Error("Timer fired after component unmounted!");
  console.log("  PASS: Timer properly cleared on unmount.");
}

async function testParentRerenderResetVulnerability() {
  console.log("--- Test 1.4: Parent re-render non-memoized callback timer starvation ---");
  // In OperationsWorkspace.tsx:
  // <ErrorBanner message={error} onDismiss={() => setError(null)} />
  // ageTicker ticks every 500ms causing parent re-render.
  // Each re-render passes a NEW arrow function () => setError(null).
  
  let dismissed = false;
  const banner = new MockErrorBanner({
    message: "Critical Error",
    onDismiss: () => {
      dismissed = true;
    },
    autoDismissMs: 400, // 400ms target dismiss
  });

  // Parent ticks every 100ms passing a new arrow function
  const tickInterval = setInterval(() => {
    banner.update({
      message: "Critical Error",
      onDismiss: () => {
        dismissed = true;
      }, // NEW function reference!
      autoDismissMs: 400,
    });
  }, 100);

  // Wait 600ms (longer than 400ms autoDismissMs)
  await new Promise((r) => setTimeout(r, 600));
  clearInterval(tickInterval);
  banner.unmount();

  if (dismissed) {
    console.log("  Dismissed despite re-renders (UNEXPECTED if non-memoized)");
  } else {
    console.log("  FINDING CONFIRMED: Non-memoized onDismiss callback in parent causes continuous timer reset.");
    console.log("  Banner never auto-dismisses when parent ticks faster than autoDismissMs!");
  }
}

// ============================================================================
// Test 2: Telemetry Polling Effect Loop Bug
// ============================================================================

async function testTelemetryPollingLoop() {
  console.log("\n--- Test 2.1: Telemetry Polling Effect Dependency Feedback Loop ---");
  // In OperationsWorkspace.tsx lines 322-362:
  // useEffect(() => {
  //   let active = true;
  //   const pollTelemetry = async () => {
  //     const latest = await getLatestTelemetry();
  //     if (latest) {
  //       setTelemetry(latest);
  //       setLastTelemetryReceived(Date.now()); // <-- UPDATES DEPENDENCY!
  //     }
  //   };
  //   void pollTelemetry();
  //   const telemetryInterval = window.setInterval(pollTelemetry, 1000);
  //   return () => { active = false; window.clearInterval(telemetryInterval); };
  // }, [lastTelemetryReceived]); // <-- DEPENDENCY ON STATE SET BY THE EFFECT!

  let apiCallCount = 0;
  const mockApi = async () => {
    apiCallCount++;
    // Simulate fast 10ms server response
    await new Promise((r) => setTimeout(r, 10));
    return { latitude: 10.7769, longitude: 106.7009 };
  };

  // Simulate React effect lifecycle with dependency [lastTelemetryReceived]
  let lastTelemetryReceived = null;
  let activeEffectCleanup = null;
  let isRunning = true;

  function runEffect() {
    if (!isRunning) return;
    if (activeEffectCleanup) {
      activeEffectCleanup();
      activeEffectCleanup = null;
    }

    let active = true;
    const pollTelemetry = async () => {
      try {
        const latest = await mockApi();
        if (!active || !isRunning) return;
        if (latest) {
          // Setting state triggers effect re-run!
          lastTelemetryReceived = Date.now();
          // React schedules re-render:
          setImmediate(() => {
            if (isRunning) runEffect();
          });
        }
      } catch {}
    };

    void pollTelemetry();
    const interval = setInterval(pollTelemetry, 1000);
    activeEffectCleanup = () => {
      active = false;
      clearInterval(interval);
    };
  }

  // Run for 500ms
  runEffect();
  await new Promise((r) => setTimeout(r, 500));
  isRunning = false;
  if (activeEffectCleanup) activeEffectCleanup();

  console.log(`  In 500ms, mockApi was called: ${apiCallCount} times!`);
  if (apiCallCount > 5) {
    console.log(`  BUG CONFIRMED: Polling effect fired ${apiCallCount} calls in 500ms instead of 1 call!`);
    console.log(`  Rate: ${(apiCallCount / 0.5).toFixed(0)} calls/sec (Expected: 1 call/sec).`);
    console.log("  Root cause: [lastTelemetryReceived] in useEffect dependency array triggers infinite cascading effect re-mounts on every packet.");
  } else {
    console.log("  Effect polled at nominal rate.");
  }
}

async function main() {
  await testTimerPrecision();
  await testManualDismiss();
  await testUnmountCleanup();
  await testParentRerenderResetVulnerability();
  await testTelemetryPollingLoop();
}

main().catch((err) => {
  console.error("Test error:", err);
  process.exit(1);
});
