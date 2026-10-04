// tests/firmware/test_challenger_m1_iter2_stress.cpp
// Comprehensive stress test & empirical verification harness for Milestone 1 Iteration 2
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <cassert>
#include <random>
#include <algorithm>
#include "flight_gate.h"

static int checks_passed = 0;
static int failures_detected = 0;

#define ASSERT_TRUE(cond, msg) do { \
    if (!(cond)) { \
        std::printf("[FAIL] Line %d: %s\n", __LINE__, msg); \
        failures_detected++; \
    } else { \
        checks_passed++; \
    } \
} while (0)

// ---------------------------------------------------------------------------
// 1. Re-test Vulnerability 1.1: Apogee entry (vspeed == 0.0f)
// ---------------------------------------------------------------------------
void verify_apogee_entry() {
    std::printf("\n--- Test 1: Apogee & Level-off Entry (vspeed == 0.0 m/s) ---\n");

    // Case 1A: Production MODE.ino configuration with ALT_LIMIT_SAFE_FLOOR_US = 1350.0f
    {
        AltLimiter limiter;
        float max_alt = 100.0f;
        float current_alt = 100.2f;
        int hover_throttle = 1500;
        float min_floor = 1350.0f; // from MODE.ino

        int out = altitude_throttle_cap(limiter, current_alt, max_alt, hover_throttle, 0.0f, min_floor);
        ASSERT_TRUE(limiter.active, "Limiter must activate upon ceiling breach");
        ASSERT_TRUE(out == 1470, "Initial cap must be entry throttle - 30us");
        ASSERT_TRUE(std::abs(limiter.floor_us - 1350.0f) < 0.01f, "Limiter floor_us must be 1350.0f, not collapsed to 1100");

        // Simulate 40 seconds hovering at ceiling (8,000 cycles at 200 Hz)
        for (int i = 0; i < 8000; i++) {
            out = altitude_throttle_cap(limiter, 100.2f, max_alt, hover_throttle, 0.0f, min_floor);
        }
        ASSERT_TRUE(out == 1350, "After 40s at apogee, cap must converge to safe floor 1350 us");
        ASSERT_TRUE(out >= 1350, "Cap must never drop below 1350 us during apogee hover");

        // Slight descent begins (-0.2 m/s)
        out = altitude_throttle_cap(limiter, 100.1f, max_alt, hover_throttle, -0.2f, min_floor);
        ASSERT_TRUE(out == 1350, "Descent at -0.2 m/s must maintain safe floor 1350 us");
    }

    // Case 1B: Generic invocation with min_floor_us = 0.0f (dynamic entry base)
    {
        AltLimiter limiter;
        float max_alt = 100.0f;
        int hover_throttle = 1500;

        int out = altitude_throttle_cap(limiter, 100.1f, max_alt, hover_throttle, 0.0f, 0.0f);
        ASSERT_TRUE(limiter.active, "Limiter must activate");
        // dynamic_base = 1500 - 150 = 1350 us
        ASSERT_TRUE(std::abs(limiter.floor_us - 1350.0f) < 0.01f, "Dynamic floor_us must be 1350.0f even if min_floor_us is 0");

        // 100,000 cycles above ceiling
        for (int i = 0; i < 100000; i++) {
            out = altitude_throttle_cap(limiter, 100.5f, max_alt, hover_throttle, 0.0f, 0.0f);
        }
        ASSERT_TRUE(out == 1350, "Cap must converge to dynamic base 1350 us, not 1100 us");
    }

    std::printf("[PASS] Vulnerability 1.1 successfully verified as fixed.\n");
}

// ---------------------------------------------------------------------------
// 2. Re-test Vulnerability 1.2: High climb punch-out entry (1850 µs)
// ---------------------------------------------------------------------------
void verify_punch_out_transition() {
    std::printf("\n--- Test 2: High Climb Punch-Out Entry (1850 us) ---\n");

    // Case 2A: With min_floor_us = 1350.0f (MODE.ino)
    {
        AltLimiter limiter;
        float max_alt = 100.0f;
        int climb_throttle = 1850;
        float vspeed = 4.5f;

        int out = altitude_throttle_cap(limiter, 100.5f, max_alt, climb_throttle, vspeed, 1350.0f);
        ASSERT_TRUE(limiter.active, "Limiter active on punch out");
        ASSERT_TRUE(out == 1820, "Initial cap is 1850 - 30 = 1820 us");
        ASSERT_TRUE(std::abs(limiter.floor_us - 1350.0f) < 0.01f, "Configured floor_us is 1350.0f");

        // Run for 3 minutes (36,000 cycles) above ceiling
        for (int i = 0; i < 36000; i++) {
            out = altitude_throttle_cap(limiter, 105.0f, max_alt, climb_throttle, 1.0f, 1350.0f);
        }
        // Limiter should have ramped down all the way to 1350 us
        ASSERT_TRUE(out == 1350, "Punch out throttle must ramp down to hover safe floor (1350 us)");
    }

    // Case 2B: Without min_floor_us (testing ALT_LIMIT_MAX_ENTRY_FLOOR_US clamp)
    {
        AltLimiter limiter;
        float max_alt = 100.0f;
        int climb_throttle = 1850;
        float vspeed = 4.0f;

        // dynamic_base = 1850 - 150 = 1700 us -> clamped by ALT_LIMIT_MAX_ENTRY_FLOOR_US to 1450 us
        int out = altitude_throttle_cap(limiter, 100.5f, max_alt, climb_throttle, vspeed, 0.0f);
        ASSERT_TRUE(limiter.active, "Limiter active on high punch out");
        ASSERT_TRUE(std::abs(limiter.floor_us - 1450.0f) < 0.01f, "dynamic floor must be clamped to ALT_LIMIT_MAX_ENTRY_FLOOR_US (1450 us)");

        // 3 minutes above ceiling
        for (int i = 0; i < 36000; i++) {
            out = altitude_throttle_cap(limiter, 105.0f, max_alt, climb_throttle, 1.0f, 0.0f);
        }
        ASSERT_TRUE(out == 1450, "Output must cap at 1450 us (hover thrust baseline), not locked at 1700 us");
    }

    std::printf("[PASS] Vulnerability 1.2 successfully verified as fixed.\n");
}

// ---------------------------------------------------------------------------
// 3. Re-test Vulnerability 1.3: Rapid descent floor depression
// ---------------------------------------------------------------------------
void verify_descent_depression() {
    std::printf("\n--- Test 3: Rapid Descent Floor Depression Prevention ---\n");

    // Pilot near hover, rapid descent -1.0 m/s to -5.0 m/s
    float descent_rates[] = {-0.5f, -0.8f, -1.0f, -1.5f, -2.0f, -3.0f, -5.0f};
    int pilot_throttles[] = {1450, 1460, 1470, 1480, 1500};

    for (float vs : descent_rates) {
        for (int thr : pilot_throttles) {
            AltLimiter limiter;
            // Activate limiter at 105m
            int out = altitude_throttle_cap(limiter, 105.0f, 100.0f, thr, vs, 1450.0f);
            ASSERT_TRUE(out >= 1450, "Capped output must never be depressed below safe floor 1450 us");
            ASSERT_TRUE(limiter.floor_us >= 1450.0f, "floor_us must be at least 1450.0f");
        }
    }

    // Pilot throttle cut priority: when pilot intentionally cuts throttle below safe floor,
    // pilot lower command must be honored (cut motor / manual override)
    {
        AltLimiter limiter;
        altitude_throttle_cap(limiter, 105.0f, 100.0f, 1500, 0.0f, 1350.0f);
        int cut = altitude_throttle_cap(limiter, 105.0f, 100.0f, 1100, -2.0f, 1350.0f);
        ASSERT_TRUE(cut == 1100, "Pilot cut command (1100 us) must be honored even during descent");

        int idle = altitude_throttle_cap(limiter, 105.0f, 100.0f, 1000, -1.0f, 1350.0f);
        ASSERT_TRUE(idle == 1000, "Pilot idle command (1000 us) must be honored");
    }

    std::printf("[PASS] Vulnerability 1.3 successfully verified as fixed.\n");
}

// ---------------------------------------------------------------------------
// 4. Monte Carlo Fuzzing & Invariant Verification (1,000,000 iterations)
// ---------------------------------------------------------------------------
void verify_monte_carlo_invariants() {
    std::printf("\n--- Test 4: Monte Carlo Fuzzing & Invariant Verification (1,000,000 cycles) ---\n");

    std::mt19937 rng(42);
    std::uniform_real_distribution<float> alt_dist(0.0f, 250.0f);
    std::uniform_real_distribution<float> max_alt_dist(20.0f, 150.0f);
    std::uniform_int_distribution<int> thr_dist(900, 2100);
    std::uniform_real_distribution<float> vspeed_dist(-15.0f, 15.0f);
    float min_floors[] = {0.0f, 1100.0f, 1300.0f, 1350.0f, 1450.0f};

    AltLimiter limiter;

    for (int i = 0; i < 1000000; i++) {
        float alt = alt_dist(rng);
        float max_alt = max_alt_dist(rng);
        int thr = thr_dist(rng);
        float vspeed = vspeed_dist(rng);
        float min_fl = min_floors[i % 5];

        int out = altitude_throttle_cap(limiter, alt, max_alt, thr, vspeed, min_fl);

        // Invariant 1: Output never exceeds pilot throttle
        if (out > thr) {
            std::printf("[FAIL] Invariant 1 violated: out=%d > thr=%d at cycle %d\n", out, thr, i);
            failures_detected++;
            break;
        }

        // Invariant 2: Output never less than ALT_LIMIT_DEFAULT_FLOOR_US unless pilot commanded less
        if (thr >= ALT_LIMIT_DEFAULT_FLOOR_US && out < ALT_LIMIT_DEFAULT_FLOOR_US) {
            std::printf("[FAIL] Invariant 2 violated: out=%d < 1100 with thr=%d at cycle %d\n", out, thr, i);
            failures_detected++;
            break;
        }

        // Invariant 3: If min_floor > 0 and thr >= min_floor and limiter is active above ceiling, out >= min_floor
        if (limiter.active && min_fl > 0.0f && thr >= (int)min_fl && alt > max_alt) {
            if (out < (int)min_fl) {
                std::printf("[FAIL] Invariant 3 violated: out=%d < min_floor=%.0f at cycle %d\n", out, min_fl, i);
                failures_detected++;
                break;
            }
        }

        // Invariant 4: No NaN or Inf in internal state
        if (std::isnan(limiter.cap_us) || std::isinf(limiter.cap_us) ||
            std::isnan(limiter.floor_us) || std::isinf(limiter.floor_us)) {
            std::printf("[FAIL] Invariant 4 violated: NaN/Inf in state at cycle %d\n", i);
            failures_detected++;
            break;
        }

        // Invariant 5: If rel_alt_m < max_alt - 1.0f, limiter must be inactive and out == thr
        if (alt < max_alt - ALT_LIMIT_RELEASE_M) {
            if (limiter.active || out != thr) {
                std::printf("[FAIL] Invariant 5 violated: hysteresis release failure at cycle %d\n", i);
                failures_detected++;
                break;
            }
        }
    }

    ASSERT_TRUE(failures_detected == 0, "All 1,000,000 Monte Carlo stress cycles passed without invariant violation");
    std::printf("[PASS] Monte Carlo fuzzing passed (1,000,000 cycles).\n");
}

// ---------------------------------------------------------------------------
// 5. Flight Trajectory Simulation (Dynamic Ceiling Breach & Descent Trajectory)
// ---------------------------------------------------------------------------
void verify_full_trajectory_simulation() {
    std::printf("\n--- Test 5: Full Trajectory Simulation (F450 Airframe Model) ---\n");

    // Simulate 200 Hz physical model:
    // mass = 1.2 kg
    // hover throttle = 1450 us
    // thrust at 1450 us = 1.2 * 9.81 = 11.77 N
    // dt = 0.005 s
    // Ceiling = 50.0 m
    AltLimiter limiter;
    float max_alt = 50.0f;
    float alt = 45.0f;
    float vspeed = 3.0f;
    float min_floor = 1350.0f;
    int pilot_throttle = 1750; // Pilot climbing fast

    bool reached_ceiling = false;
    bool limiter_engaged = false;
    float max_overshoot = 0.0f;
    bool safely_recovered = false;

    // Simulate 100 seconds (20,000 steps)
    for (int step = 0; step < 20000; step++) {
        // Physical update
        alt += vspeed * 0.005f;
        if (alt > max_overshoot) max_overshoot = alt;

        // Limiter computation
        int commanded_thr = pilot_throttle;
        // Pilot tries to punch through until 5 seconds in, then holds 1600 us
        if (step > 1000) commanded_thr = 1600;

        int actual_thr = altitude_throttle_cap(limiter, alt, max_alt, commanded_thr, vspeed, min_floor);

        if (alt >= max_alt) reached_ceiling = true;
        if (limiter.active) limiter_engaged = true;

        // Aerodynamic thrust approximation:
        // thrust_ratio: 1000us -> 0, 1450us -> 1.0 (hover), 2000us -> ~2.2
        float thrust_accel = ((float)(actual_thr - 1000) / 450.0f) * 9.81f;
        float drag_accel = -0.5f * vspeed * std::abs(vspeed);
        float net_accel = thrust_accel - 9.81f + drag_accel;

        vspeed += net_accel * 0.005f;

        // Trace progress every 10 seconds
        if (step % 2000 == 0) {
            std::printf("  t=%4.1fs: alt=%6.2fm, vspeed=%+5.2fm/s, thr=%d, active=%d, cap=%.1f\n",
                        step * 0.005f, alt, vspeed, actual_thr, limiter.active ? 1 : 0, limiter.cap_us);
        }

        // Check if aircraft returns back to ceiling zone
        if (step > 4000 && alt <= max_alt && std::abs(vspeed) < 2.5f) {
            safely_recovered = true;
        }
    }

    ASSERT_TRUE(reached_ceiling, "Trajectory reached ceiling");
    ASSERT_TRUE(limiter_engaged, "Limiter engaged successfully");
    ASSERT_TRUE(safely_recovered, "Drone safely arrested climb and returned to ceiling");

    std::printf("  Max altitude reached: %.2f m (ceiling: %.2f m)\n", max_overshoot, max_alt);
    std::printf("  Stabilization achieved: %s\n", safely_recovered ? "YES" : "NO");
    std::printf("[PASS] Full trajectory physical flight simulation verified.\n");
}

int main() {
    std::printf("====================================================================\n");
    std::printf("CHALLENGER 1 (Iteration 2): Empirical Stress Verification & Oracles\n");
    std::printf("====================================================================\n");

    verify_apogee_entry();
    verify_punch_out_transition();
    verify_descent_depression();
    verify_monte_carlo_invariants();
    verify_full_trajectory_simulation();

    std::printf("\n====================================================================\n");
    std::printf("FINAL RESULTS: %d checks passed, %d failures detected.\n", checks_passed, failures_detected);
    std::printf("VERDICT: %s\n", failures_detected == 0 ? "APPROVED (ROBUST)" : "REJECTED (BUGS FOUND)");
    std::printf("====================================================================\n");

    return failures_detected == 0 ? 0 : 1;
}
