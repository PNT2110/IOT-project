// Adversarial test probe for firmware/FC_can_bang/flight_gate.h
#include <cstdio>
#include <cmath>
#include <cassert>
#include "flight_gate.h"

int main() {
    printf("=== ADVERSARIAL FLIGHT GATE PROBE ===\n");
    int failures = 0;

    // SCENARIO 1: Drone reaches ceiling at apogee where vertical speed is 0 m/s
    // Pilot is at hover throttle (1500 us). Relative altitude reaches 100.1m (ceiling 100m).
    // In production (MODE.ino), min_floor_us is not passed (defaults to 0.0f).
    // vspeed_mps is passed from baro_vspeed_mps, which is 0.0f.
    {
        AltLimiter limiter;
        int initial_throttle = 1500;
        float max_alt = 100.0f;
        float current_alt = 100.1f;
        float vspeed = 0.0f; // apogee / level hover

        int out = altitude_throttle_cap(limiter, current_alt, max_alt, initial_throttle, vspeed);
        printf("[PROBE 1.1] Apogee entry (vspeed=0.0m/s): cap=%d, floor_us=%.1f\n", out, limiter.floor_us);

        // Check floor_us: Because vspeed == 0.0f, the worker's logic fell back to ALT_LIMIT_DEFAULT_FLOOR_US (1100)!
        if (std::abs(limiter.floor_us - (float)ALT_LIMIT_DEFAULT_FLOOR_US) < 0.1f) {
            printf("  -> OBSERVED BEHAVIOR: floor_us collapsed to 1100 us despite 1500 us hover throttle!\n");
        }

        // Now simulate the drone hovering / floating above ceiling for 40 seconds (8000 cycles at 200Hz)
        // e.g. in a gentle ridge updraft or sensor drift
        for (int i = 0; i < 8000; i++) {
            out = altitude_throttle_cap(limiter, 100.2f, max_alt, 1500, -0.2f);
        }
        printf("[PROBE 1.2] After 40s above ceiling: cap=%d (vspeed=-0.2 m/s)\n", out);
        if (out == 1100) {
            printf("  -> OBSERVED VULNERABILITY: Capped at 1100 us (severe thrust drop / below hover on F450)!\n");
        }

        // Now simulate the drone beginning to descend at -0.35 m/s (downward descent, but > -0.4 m/s threshold)
        out = altitude_throttle_cap(limiter, 100.1f, max_alt, 1500, -0.35f);
        printf("[PROBE 1.3] During descent at -0.35 m/s: cap=%d\n", out);
        if (out == 1100) {
            printf("  -> CONFIRMED: Descent at -0.35 m/s receives only 1100 us throttle (uncontrolled fall)!\n");
        }
    }

    // SCENARIO 2: Punch-out coasting entry with low entry throttle
    // Pilot punched out, then cut throttle stick to 1150 us to stop climbing.
    // Drone passes 100m on inertia at 1150 us throttle.
    // Pilot immediately pushes stick to 1500 us (hover) to stabilize.
    {
        AltLimiter limiter;
        float max_alt = 100.0f;

        // Entry at 1150 us, climbing at +1.5 m/s on inertia
        int out = altitude_throttle_cap(limiter, 100.2f, max_alt, 1150, 1.5f);
        printf("[PROBE 2.1] Punch-out entry (throttle=1150 us): cap=%d, floor_us=%.1f\n", out, limiter.floor_us);

        // Pilot now requests 1500 us hover throttle
        out = altitude_throttle_cap(limiter, 100.2f, max_alt, 1500, 0.5f);
        printf("[PROBE 2.2] Pilot demands 1500 us hover: returned throttle=%d\n", out);
        if (out <= 1150) {
            printf("  -> OBSERVED VULNERABILITY: Output clamped to %d us even though pilot commanded 1500 us!\n", out);
        }

        // Pilot demands full 1800 us throttle to prevent crash
        out = altitude_throttle_cap(limiter, 100.1f, max_alt, 1800, -0.3f);
        printf("[PROBE 2.3] Pilot demands 1800 us recovery throttle: returned throttle=%d\n", out);
    }

    // SCENARIO 3: Vertical speed dampening threshold and gain measurement
    {
        AltLimiter limiter;
        // Entry with vspeed = 1.0 m/s at 1500 us -> dynamic floor = 1350 us
        altitude_throttle_cap(limiter, 100.5f, 100.0f, 1500, 1.0f);
        printf("[PROBE 3.1] Dynamic entry floor: %.1f us\n", limiter.floor_us);

        // Let cap ramp down to floor
        for (int i = 0; i < 4000; i++) {
            altitude_throttle_cap(limiter, 100.5f, 100.0f, 1500, 0.0f);
        }

        // Test response across various descent rates
        float test_vspeeds[] = {-0.2f, -0.4f, -0.6f, -1.0f, -2.0f, -3.0f};
        for (float vs : test_vspeeds) {
            int capped = altitude_throttle_cap(limiter, 100.5f, 100.0f, 1500, vs);
            printf("  vspeed = %5.1f m/s -> throttle = %d us\n", vs, capped);
        }
    }

    // SCENARIO 4: Hysteresis exit behavior
    {
        AltLimiter limiter;
        altitude_throttle_cap(limiter, 100.5f, 100.0f, 1500, 1.0f);
        assert(limiter.active);

        // In the release band (between 99.0m and 100.0m)
        int in_band = altitude_throttle_cap(limiter, 99.5f, 100.0f, 1500, -0.5f);
        printf("[PROBE 4.1] In release band (99.5m / ceiling 100m): active=%d, throttle=%d\n", limiter.active, in_band);

        // Below release band (< 99.0m)
        int released = altitude_throttle_cap(limiter, 98.9f, 100.0f, 1500, -0.5f);
        printf("[PROBE 4.2] Released below 99.0m: active=%d, throttle=%d\n", limiter.active, released);
    }

    printf("=== ADVERSARIAL PROBE COMPLETE ===\n");
    return 0;
}
