// tests/firmware/test_downward_override_stress.cpp
// Adversarial verification of pilot downward throttle override at all times.
#include <cstdio>
#include <cstdlib>
#include <cassert>
#include <random>
#include "flight_gate.h"

int main() {
    printf("=== ADVERSARIAL PILOT DOWNWARD OVERRIDE PROBE ===\n");
    int failures = 0;
    int test_cases = 0;

    std::mt19937 rng(42);
    std::uniform_real_distribution<float> alt_dist(50.0f, 150.0f);
    std::uniform_real_distribution<float> vspeed_dist(-15.0f, 15.0f);
    std::uniform_real_distribution<float> min_floor_dist(0.0f, 1500.0f);
    std::uniform_int_distribution<int> throttle_dist(800, 2000);

    // Test 1: Full combinatorial / fuzzed sweep across 100,000 states
    for (int i = 0; i < 100000; i++) {
        AltLimiter limiter;
        // Randomly pre-activate or leave inactive
        if (i % 2 == 0) {
            limiter.active = true;
            limiter.cap_us = (float)(1000 + (rng() % 900));
            limiter.floor_us = (float)(1000 + (rng() % 500));
        }

        float max_alt = 100.0f;
        float current_alt = alt_dist(rng);
        float vspeed = vspeed_dist(rng);
        float min_floor = min_floor_dist(rng);
        int pilot_throttle = throttle_dist(rng);

        int output_throttle = altitude_throttle_cap(limiter, current_alt, max_alt, pilot_throttle, vspeed, min_floor);
        test_cases++;

        // Property under test: Pilot can ALWAYS override downward.
        // output_throttle must NEVER exceed pilot_throttle.
        if (output_throttle > pilot_throttle) {
            printf("CRITICAL FAILURE: output_throttle (%d) > pilot_throttle (%d) at alt=%.1f, vspeed=%.1f\n",
                   output_throttle, pilot_throttle, current_alt, vspeed);
            failures++;
            break;
        }

        // Test immediate downward stick deflection:
        // If pilot drops throttle by delta, output must drop accordingly and not be higher than new throttle.
        for (int delta = 10; delta <= 500; delta += 50) {
            int lower_throttle = pilot_throttle - delta;
            if (lower_throttle < 800) lower_throttle = 800;
            int lower_output = altitude_throttle_cap(limiter, current_alt, max_alt, lower_throttle, vspeed, min_floor);
            test_cases++;

            if (lower_output > lower_throttle) {
                printf("CRITICAL FAILURE: downward override failed! lower_output (%d) > lower_throttle (%d)\n",
                       lower_output, lower_throttle);
                failures++;
                break;
            }
        }
    }

    // Test 2: Specific emergency descent / motor cut scenarios
    {
        AltLimiter limiter;
        // Drone breached ceiling at 105m, climbing at +2m/s
        altitude_throttle_cap(limiter, 105.0f, 100.0f, 1700, 2.0f, 1350.0f);
        assert(limiter.active);

        // Pilot cuts throttle completely to 900 us (disarm / cut)
        int cut_out = altitude_throttle_cap(limiter, 105.0f, 100.0f, 900, 2.0f, 1350.0f);
        test_cases++;
        if (cut_out != 900) {
            printf("CRITICAL FAILURE: Emergency throttle cut to 900 us returned %d us\n", cut_out);
            failures++;
        }

        // Pilot commands gentle descent stick: 1200 us (< safe floor 1350 us)
        int descend_out = altitude_throttle_cap(limiter, 105.0f, 100.0f, 1200, 0.0f, 1350.0f);
        test_cases++;
        if (descend_out != 1200) {
            printf("CRITICAL FAILURE: Pilot commanded descent 1200 us returned %d us (floor locked out pilot stick!)\n", descend_out);
            failures++;
        }

        // Drone in rapid descent -3.0 m/s, limiter boosts effective_floor to protect altitude.
        // Pilot STILL wants lower throttle (1150 us) to land.
        int land_out = altitude_throttle_cap(limiter, 101.0f, 100.0f, 1150, -3.0f, 1350.0f);
        test_cases++;
        if (land_out != 1150) {
            printf("CRITICAL FAILURE: Rapid descent land command 1150 us returned %d us\n", land_out);
            failures++;
        }
    }

    printf("Tested %d conditions: %d failures.\n", test_cases, failures);
    if (failures == 0) {
        printf("[VERIFIED] Pilot downward throttle override is strictly guaranteed at all times.\n");
    }
    return failures;
}
