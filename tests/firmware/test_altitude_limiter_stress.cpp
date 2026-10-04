// tests/firmware/test_altitude_limiter_stress.cpp
// Empirical stress test and simulation generator for altitude limiter in flight_gate.h
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <cassert>
#include <vector>
#include <random>
#include <algorithm>

#include "flight_gate.h"

static int checks_passed = 0;
static int vulnerabilities_detected = 0;

// Simulation test 1: Prolonged Ceiling Hover with Step-Down Clamping
void test_prolonged_ceiling_clamping() {
    AltLimiter limiter;
    float max_alt = 100.0f;
    float alt = 105.0f; // 5m above max altitude
    int pilot_throttle = 1600; // Pilot trying to punch out
    float min_floor = 1350.0f; // Configured hover floor for loaded F450

    // 100,000 cycles at 200 Hz = 500 seconds (~8.3 minutes) above ceiling
    int last_capped = 0;
    for (int cycle = 0; cycle < 100000; cycle++) {
        last_capped = altitude_throttle_cap(limiter, alt, max_alt, pilot_throttle, 0.0f, min_floor);
        if (last_capped < 1350) {
            std::printf("FAIL: Throttle cap dropped to %d < 1350 at cycle %d\n", last_capped, cycle);
            return;
        }
    }
    assert(last_capped == 1350);
    assert(limiter.active);
    checks_passed++;
    std::printf("[PASS] Prolonged ceiling clamping converges to min_floor.\n");
}

// Simulation test 2: Pilot Throttle Cut Priority (Manual Land / Cut)
void test_pilot_lower_throttle_override() {
    AltLimiter limiter;
    altitude_throttle_cap(limiter, 125.0f, 120.0f, 1600, 0.0f, 1350.0f);
    assert(limiter.active);

    int cut_output = altitude_throttle_cap(limiter, 125.0f, 120.0f, 1000, 0.0f, 1350.0f);
    assert(cut_output == 1000);

    int mid_output = altitude_throttle_cap(limiter, 125.0f, 120.0f, 1200, 0.0f, 1350.0f);
    assert(mid_output == 1200);
    checks_passed++;
    std::printf("[PASS] Pilot lower throttle override honored.\n");
}

// Simulation test 3: Hysteresis and Release Dynamics
void test_release_hysteresis() {
    AltLimiter limiter;
    float max_alt = 100.0f;

    int out = altitude_throttle_cap(limiter, 99.0f, max_alt, 1500, 0.0f, 1350.0f);
    assert(!limiter.active && out == 1500);

    out = altitude_throttle_cap(limiter, 100.5f, max_alt, 1500, 0.0f, 1350.0f);
    assert(limiter.active && out == 1470);

    // Drops to max_alt - 0.5m (inside 1.0m band) -> still active
    out = altitude_throttle_cap(limiter, 99.5f, max_alt, 1500, 0.0f, 1350.0f);
    assert(limiter.active);

    // Drops below 99.0m -> released
    out = altitude_throttle_cap(limiter, 98.9f, max_alt, 1500, 0.0f, 1350.0f);
    assert(!limiter.active && out == 1500);
    assert(limiter.floor_us == ALT_LIMIT_DEFAULT_FLOOR_US);
    checks_passed++;
    std::printf("[PASS] Hysteresis and release band correctly implemented.\n");
}

// VULNERABILITY PROBE 1: Zero vspeed entry collapses floor to 1100 us
void probe_zero_vspeed_entry_collapse() {
    AltLimiter limiter;
    // Enter ceiling with hover throttle 1500 us and vspeed = 0.0 m/s (level off)
    // In production MODE.ino, min_floor_us defaults to 0.0f
    altitude_throttle_cap(limiter, 100.1f, 100.0f, 1500, 0.0f, 0.0f);
    if (std::abs(limiter.floor_us - 1100.0f) < 0.1f) {
        std::printf("[VULNERABILITY 1 CONFIRMED] Level-off ceiling entry (vspeed=0) resets floor_us to 1100 us!\n");
        vulnerabilities_detected++;
    }
}

// VULNERABILITY PROBE 2: High climb rate punches out and locks floor above hover
void probe_high_climb_lockout() {
    AltLimiter limiter;
    // Enter ceiling at high throttle 1850 us, vspeed = +4.0 m/s
    altitude_throttle_cap(limiter, 100.5f, 100.0f, 1850, 4.0f, 0.0f);
    // Limiter latches floor_us = 1850 - 150 = 1700 us
    // Drone stays above ceiling for 2 minutes
    int capped = 0;
    for (int i = 0; i < 24000; i++) {
        capped = altitude_throttle_cap(limiter, 120.0f, 100.0f, 1850, 1.0f, 0.0f);
    }
    if (capped >= 1700) {
        std::printf("[VULNERABILITY 2 CONFIRMED] High climb entry locks throttle floor at %d us (> 1450 hover)!\n", capped);
        std::printf("                             Drone will climb indefinitely above ceiling!\n");
        vulnerabilities_detected++;
    }
}

// VULNERABILITY PROBE 3: Descent floor depression below min_floor
void probe_descent_depression_below_min_floor() {
    AltLimiter limiter;
    // Pilot at 1460 us, min_floor at 1450 us, descending at -1.0 m/s
    int capped = altitude_throttle_cap(limiter, 105.0f, 100.0f, 1460, -1.0f, 1450.0f);
    if (capped < 1450) {
        std::printf("[VULNERABILITY 3 CONFIRMED] Rapid descent (-1.0 m/s) depresses throttle cap to %d us (< min_floor 1450 us)!\n", capped);
        vulnerabilities_detected++;
    }
}

int main() {
    std::printf("============================================================\n");
    std::printf("CHALLENGER 1: Empirical Altitude Limiter Stress & Simulation\n");
    std::printf("============================================================\n");

    test_prolonged_ceiling_clamping();
    test_pilot_lower_throttle_override();
    test_release_hysteresis();

    std::printf("\n--- Adversarial Vulnerability Probes ---\n");
    probe_zero_vspeed_entry_collapse();
    probe_high_climb_lockout();
    probe_descent_depression_below_min_floor();

    std::printf("\nResults: %d checks passed, %d critical vulnerabilities confirmed empirically.\n",
                checks_passed, vulnerabilities_detected);
    std::printf("============================================================\n");
    return 0;
}
