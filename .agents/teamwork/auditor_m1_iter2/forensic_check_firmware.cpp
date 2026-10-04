// Independent forensic verification of firmware/FC_can_bang/flight_gate.h
#include <cstdio>
#include <cstdlib>
#include <cassert>
#include <cmath>
#include "flight_gate.h"

#define AUDIT_ASSERT(cond, msg) do { \
    if (!(cond)) { \
        std::printf("[AUDIT FAIL] %s:%d: %s\n", __FILE__, __LINE__, msg); \
        std::exit(1); \
    } \
} while(0)

void verify_apogee_level_off_entry() {
    std::printf("[AUDIT] Verifying Apogee / Level-off entry (vspeed = 0.0 m/s)...\n");

    // Case 1A: Production call pattern in MODE.ino (min_floor_us = 1350.0f)
    AltLimiter lim_prod;
    int out = altitude_throttle_cap(lim_prod, 100.1f, 100.0f, 1500, 0.0f, 1350.0f);
    AUDIT_ASSERT(lim_prod.active, "Limiter must be active above ceiling");
    AUDIT_ASSERT(lim_prod.floor_us == 1350.0f, "floor_us must be set to min_floor_us (1350)");
    AUDIT_ASSERT(out == 1470, "Initial cap must be entry throttle - 30us (1470)");

    // Run 50,000 cycles (250s at 200Hz) above ceiling
    for (int i = 0; i < 50000; i++) {
        out = altitude_throttle_cap(lim_prod, 100.1f, 100.0f, 1500, 0.0f, 1350.0f);
    }
    AUDIT_ASSERT(out == 1350, "Capped throttle must converge to exactly 1350 us");
    AUDIT_ASSERT(lim_prod.floor_us == 1350.0f, "floor_us must remain 1350 us");

    // Case 1B: Fallback call pattern without min_floor (min_floor_us = 0.0f)
    AltLimiter lim_fallback;
    out = altitude_throttle_cap(lim_fallback, 100.1f, 100.0f, 1500, 0.0f, 0.0f);
    AUDIT_ASSERT(lim_fallback.active, "Limiter must be active above ceiling");
    AUDIT_ASSERT(lim_fallback.floor_us == 1350.0f, "Dynamic base from 1500us must be 1350us (1500 - 150)");

    for (int i = 0; i < 50000; i++) {
        out = altitude_throttle_cap(lim_fallback, 100.1f, 100.0f, 1500, 0.0f, 0.0f);
    }
    AUDIT_ASSERT(out == 1350, "Fallback cap must converge to dynamic floor 1350 us, NOT 1100 us!");

    std::printf("[AUDIT] Apogee / Level-off entry: PASS\n");
}

void verify_high_climb_entry() {
    std::printf("[AUDIT] Verifying High Climb punch-out entry (throttle = 1850 us, vspeed = +4.0 m/s)...\n");
    AltLimiter lim_climb;
    int out = altitude_throttle_cap(lim_climb, 100.5f, 100.0f, 1850, 4.0f, 0.0f);
    AUDIT_ASSERT(lim_climb.active, "Limiter must be active");
    // Entry throttle 1850 - 150 = 1700, but must be clamped to ALT_LIMIT_MAX_ENTRY_FLOOR_US (1450)
    AUDIT_ASSERT(lim_climb.floor_us == 1450.0f, "Climb entry floor must be capped at 1450 us, NOT 1700 us!");

    for (int i = 0; i < 50000; i++) {
        out = altitude_throttle_cap(lim_climb, 105.0f, 100.0f, 1850, 1.0f, 0.0f);
    }
    AUDIT_ASSERT(out == 1450, "Capped throttle must decay down to 1450 us hover ceiling, NOT 1700 us!");

    std::printf("[AUDIT] High Climb entry: PASS\n");
}

void verify_descent_protection() {
    std::printf("[AUDIT] Verifying rapid descent floor protection...\n");
    AltLimiter lim_desc;
    // Pilot at 1460 us, min_floor at 1450 us, descending at -1.0 m/s
    int out = altitude_throttle_cap(lim_desc, 105.0f, 100.0f, 1460, -1.0f, 1450.0f);
    AUDIT_ASSERT(out >= 1450, "Throttle cap must not be depressed below min_floor (1450 us) during descent!");

    // Fast descent (-2.0 m/s) should boost effective floor
    AltLimiter lim_boost;
    altitude_throttle_cap(lim_boost, 105.0f, 100.0f, 1600, 0.0f, 1350.0f);
    for (int i = 0; i < 50000; i++) {
        altitude_throttle_cap(lim_boost, 105.0f, 100.0f, 1600, 0.0f, 1350.0f);
    }
    // Now plunge at -1.5 m/s: vspeed dampening adds (-(-1.5) - 0.4) * 100 = 110 us -> floor becomes 1460 us
    int boosted_out = altitude_throttle_cap(lim_boost, 105.0f, 100.0f, 1600, -1.5f, 1350.0f);
    AUDIT_ASSERT(boosted_out >= 1450, "Effective floor must boost throttle during fast descent to arrest fall!");

    std::printf("[AUDIT] Rapid descent floor protection: PASS\n");
}

void verify_pilot_override_and_hysteresis() {
    std::printf("[AUDIT] Verifying pilot override authority and hysteresis release band...\n");
    AltLimiter lim;
    altitude_throttle_cap(lim, 105.0f, 100.0f, 1600, 0.0f, 1350.0f);
    AUDIT_ASSERT(lim.active, "Limiter active");

    // Pilot pulls throttle to 1000 us (disarm/idle cut)
    int out = altitude_throttle_cap(lim, 105.0f, 100.0f, 1000, 0.0f, 1350.0f);
    AUDIT_ASSERT(out == 1000, "Pilot must always retain full lower throttle authority!");

    // Pilot pulls throttle to 1250 us
    out = altitude_throttle_cap(lim, 105.0f, 100.0f, 1250, 0.0f, 1350.0f);
    AUDIT_ASSERT(out == 1250, "Pilot command below cap must pass through directly!");

    // Drone drops to 99.5m (within 1m hysteresis band under 100m ceiling) -> still active
    out = altitude_throttle_cap(lim, 99.5f, 100.0f, 1500, 0.0f, 1350.0f);
    AUDIT_ASSERT(lim.active, "Hysteresis band must keep limiter active between 99m and 100m");

    // Drone drops to 98.9m (below 99m) -> releases!
    out = altitude_throttle_cap(lim, 98.9f, 100.0f, 1500, 0.0f, 1350.0f);
    AUDIT_ASSERT(!lim.active, "Limiter must release below (max_alt - 1.0m)");
    AUDIT_ASSERT(out == 1500, "Throttle must be unrestrained when released");
    AUDIT_ASSERT(lim.floor_us == ALT_LIMIT_DEFAULT_FLOOR_US, "floor_us must reset to default on release");

    std::printf("[AUDIT] Pilot override authority and hysteresis release band: PASS\n");
}

int main() {
    std::printf("=== INDEPENDENT FORENSIC AUDIT: FIRMWARE ALTITUDE LIMITER ===\n");
    verify_apogee_level_off_entry();
    verify_high_climb_entry();
    verify_descent_protection();
    verify_pilot_override_and_hysteresis();
    std::printf("=== ALL FIRMWARE FORENSIC CHECKS PASSED ===\n");
    return 0;
}
