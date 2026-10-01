// Host test for firmware/FC_can_bang/flight_gate.h (pure C++, no Arduino).
#include <cstdio>
#include <cstring>

#include "flight_gate.h"

static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #cond); failures++; } } while (0)
#define CHECK_STR(actual, expected) do { const char* a = (actual); if (std::strcmp(a, (expected)) != 0) { std::printf("FAIL %s:%d got %s want %s\n", __FILE__, __LINE__, a, (expected)); failures++; } } while (0)

static ArmInputs ready() {
  ArmInputs in;
  in.rc_ok = true; in.auth_allowed = true; in.link_alive = true; in.gps_ok = true;
  in.mode_angle = true; in.arm_switch_seen_low = true; in.arm_switch_high = true; in.throttle_us = 1000;
  return in;
}

int main() {
  // Every reason, in priority order.
  ArmInputs in = ready();
  CHECK_STR(arm_block_reason(in), "READY");
  in = ready(); in.arm_switch_high = false;       CHECK_STR(arm_block_reason(in), "ARM_SWITCH_LOW");
  in = ready(); in.throttle_us = 1050;            CHECK_STR(arm_block_reason(in), "THROTTLE_HIGH");
  in = ready(); in.throttle_us = 1049;            CHECK_STR(arm_block_reason(in), "READY");
  in = ready(); in.arm_switch_seen_low = false;   CHECK_STR(arm_block_reason(in), "ARM_SWITCH_NOT_RESET");
  in = ready(); in.mode_angle = false;            CHECK_STR(arm_block_reason(in), "MODE_NOT_ANGLE");
  in = ready(); in.gps_ok = false;                CHECK_STR(arm_block_reason(in), "NO_GPS_FIX");
  in = ready(); in.link_alive = false;            CHECK_STR(arm_block_reason(in), "PI_LINK_LOST");
  in = ready(); in.auth_allowed = false;          CHECK_STR(arm_block_reason(in), "NO_FLIGHT_AUTHORIZATION");
  in = ready(); in.rc_ok = false;                 CHECK_STR(arm_block_reason(in), "RC_LOST");
  // Priority: a denied flight outranks everything except a lost RC link.
  in = ready(); in.auth_allowed = false; in.link_alive = false; in.mode_angle = false; in.throttle_us = 1800;
  CHECK_STR(arm_block_reason(in), "NO_FLIGHT_AUTHORIZATION");
  in.rc_ok = false;
  CHECK_STR(arm_block_reason(in), "RC_LOST");

  // Pi heartbeat: alive only after a ping, and for 10 s after the last one.
  CHECK(!pi_link_alive(5000, 0, false));
  CHECK(pi_link_alive(5000, 1000, true));
  CHECK(pi_link_alive(11000, 1000, true));
  CHECK(!pi_link_alive(11001, 1000, true));
  CHECK(pi_link_alive(100, 0xFFFFFF00UL, true));  // millis() wrap-around

  // In flight, only the pilot's switch, RC loss or the kill mode disarm.
  // Losing the authorization or the Pi mid-flight is not an input here.
  CHECK(!must_disarm(false, true, true));
  CHECK(must_disarm(true, true, true));
  CHECK(must_disarm(false, false, true));
  CHECK(must_disarm(false, true, false));

  // Mode label.
  CHECK_STR(flight_mode_label(false, true, false, true), "FAILSAFE");
  CHECK_STR(flight_mode_label(true, false, true, true), "KILL");
  CHECK_STR(flight_mode_label(true, true, false, false), "BLOCKED");
  CHECK_STR(flight_mode_label(true, true, false, true), "ANGLE");
  CHECK_STR(flight_mode_label(true, true, true, false), "ANGLE");  // armed, permission expired mid-flight

  // Altitude ceiling: latch 30 us under the throttle, ease down, release 1 m below.
  AltLimiter limiter;
  CHECK(altitude_throttle_cap(limiter, 50.0f, 120.0f, 1500) == 1500);
  CHECK(!limiter.active);
  CHECK(altitude_throttle_cap(limiter, 120.5f, 120.0f, 1500) == 1470);
  CHECK(limiter.active);
  CHECK(altitude_throttle_cap(limiter, 120.5f, 120.0f, 1400) == 1400);  // pilot may always go lower
  int capped = 1470;
  for (int i = 0; i < 2000; i++) capped = altitude_throttle_cap(limiter, 121.0f, 120.0f, 1600);
  CHECK(capped < 1470 && capped >= 1360 && capped <= 1375);              // 10 us per second at 200 Hz
  for (int i = 0; i < 200000; i++) capped = altitude_throttle_cap(limiter, 121.0f, 120.0f, 1600);
  CHECK(capped == ALT_LIMIT_FLOOR_US);
  CHECK(altitude_throttle_cap(limiter, 119.5f, 120.0f, 1600) == ALT_LIMIT_FLOOR_US);  // still inside the 1 m band
  CHECK(limiter.active);
  CHECK(altitude_throttle_cap(limiter, 118.9f, 120.0f, 1600) == 1600);
  CHECK(!limiter.active);

  // SBUS flag byte: bit 3 is failsafe.
  CHECK(sbus_flags_ok(0x00));
  CHECK(sbus_flags_ok(0x04));   // one lost frame is not a failsafe
  CHECK(!sbus_flags_ok(0x08));
  CHECK(!sbus_flags_ok(0x0C));

  if (failures == 0) std::printf("flight_gate: all checks passed\n");
  return failures == 0 ? 0 : 1;
}
