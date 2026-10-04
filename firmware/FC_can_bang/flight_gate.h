// flight_gate.h - nguyen ly mode bay / khoa ARM, thuan C++ (khong phu thuoc Arduino)
// de test duoc tren may tinh (tests/firmware/test_flight_gate.cpp).
//
// Nguyen ly:
//  * ESP khoi dong la BLOCKED. Chi ARM duoc khi Pi da cap phep ($AUTH,ALLOW con han)
//    VA Pi con song ($PING trong 10 s gan nhat), roi phi cong moi gat cong tac ARM.
//  * Khi dang bay, chi 3 thu tat motor: gat DISARM, mat RC, gat mode KILL.
//    Het han cap phep / mat Pi giua chuyen bay KHONG cat motor (tranh roi may bay);
//    no chi chan lan ARM ke tiep.
//  * Vuot do cao toi da: chan tran ga roi ha dan tran ga cho may bay tu xuong.
#pragma once
#include <stdint.h>

struct ArmInputs {
  bool rc_ok;                 // dang nhan SBUS va khong o failsafe
  bool auth_allowed;          // $AUTH,ALLOW con han
  bool link_alive;            // Pi con gui $PING
  bool gps_ok;                // co fix, hoac khong yeu cau fix de ARM
  bool mode_angle;            // cong tac mode o ANGLE
  bool arm_switch_seen_low;   // da thay cong tac ARM o DISARM tu luc bat nguon / lan ARM truoc
  bool arm_switch_high;       // cong tac ARM dang o vi tri ARM
  int  throttle_us;
};

#define ARM_THROTTLE_MAX_US 1050

// Ly do chua ARM duoc, theo thu tu uu tien. "READY" = du dieu kien, ARM ngay.
static inline const char* arm_block_reason(const ArmInputs& in) {
  if (!in.rc_ok)                 return "RC_LOST";
  if (!in.auth_allowed)          return "NO_FLIGHT_AUTHORIZATION";
  if (!in.link_alive)            return "PI_LINK_LOST";
  if (!in.gps_ok)                return "NO_GPS_FIX";
  if (!in.mode_angle)            return "MODE_NOT_ANGLE";
  if (!in.arm_switch_seen_low)   return "ARM_SWITCH_NOT_RESET";
  if (in.throttle_us >= ARM_THROTTLE_MAX_US) return "THROTTLE_HIGH";
  if (!in.arm_switch_high)       return "ARM_SWITCH_LOW";
  return "READY";
}

#define PI_LINK_TIMEOUT_MS 10000UL

// Hieu unsigned tu xu ly duoc truong hop millis() tran so.
static inline bool pi_link_alive(unsigned long now_ms, unsigned long last_ping_ms, bool ping_seen, unsigned long timeout_ms = PI_LINK_TIMEOUT_MS) {
  return ping_seen && (unsigned long)(now_ms - last_ping_ms) <= timeout_ms;
}

static inline bool must_disarm(bool arm_switch_low, bool rc_ok, bool mode_angle) {
  return arm_switch_low || !rc_ok || !mode_angle;
}

// Ten mode gui ve Pi: FAILSAFE | KILL | BLOCKED | ANGLE
static inline const char* flight_mode_label(bool rc_ok, bool mode_angle, bool armed, bool arm_permitted) {
  if (!rc_ok)      return "FAILSAFE";
  if (!mode_angle) return "KILL";
  if (!armed && !arm_permitted) return "BLOCKED";
  return "ANGLE";
}

// ---- Gioi han do cao toi da (so voi diem ARM) ----
#define ALT_LIMIT_DEFAULT_FLOOR_US 1100
#define ALT_LIMIT_FLOOR_US ALT_LIMIT_DEFAULT_FLOOR_US
#define ALT_LIMIT_MARGIN_US 150.0f
#define ALT_LIMIT_MAX_ENTRY_FLOOR_US 1450.0f
#define ALT_LIMIT_STEP_US 0.05f     // moi vong 5 ms -> ha tran ga 10 us / giay
#define ALT_LIMIT_RELEASE_M 1.0f

struct AltLimiter {
  bool  active = false;
  float cap_us = 0;
  float floor_us = ALT_LIMIT_DEFAULT_FLOOR_US;
};

// Tra ve ga da gioi han. Phi cong luon co the giam ga thap hon tran.
// Ho tro ca che do mac dinh (tuong thich nguoc) lan che do dong dua tren trang thai bay / barometer.
static inline int altitude_throttle_cap(
    AltLimiter& s,
    float rel_alt_m,
    float max_alt_m,
    int throttle_us,
    float vspeed_mps = 0.0f,
    float min_floor_us = 0.0f
) {
  if (!s.active) {
    if (rel_alt_m <= max_alt_m) return throttle_us;
    s.active = true;
    s.cap_us = (float)throttle_us - 30.0f;
    float dynamic_base = (float)throttle_us - ALT_LIMIT_MARGIN_US;
    if (dynamic_base > ALT_LIMIT_MAX_ENTRY_FLOOR_US) {
      dynamic_base = ALT_LIMIT_MAX_ENTRY_FLOOR_US;
    }
    if (dynamic_base < (float)ALT_LIMIT_DEFAULT_FLOOR_US) {
      dynamic_base = (float)ALT_LIMIT_DEFAULT_FLOOR_US;
    }

    if (min_floor_us > 0.0f) {
      s.floor_us = min_floor_us;
    } else {
      s.floor_us = dynamic_base;
    }
  } else if (rel_alt_m < max_alt_m - ALT_LIMIT_RELEASE_M) {
    s.active = false;
    s.floor_us = ALT_LIMIT_DEFAULT_FLOOR_US;
    return throttle_us;
  } else if (rel_alt_m > max_alt_m) {
    s.cap_us -= ALT_LIMIT_STEP_US;   // van con tren tran -> tiep tuc ha tran ga
  }

  // Tinh san ga dong dua vao floor da luu, min_floor_us va giam chan toc do roi (vspeed_mps)
  float effective_floor = s.floor_us;
  if (min_floor_us > 0.0f && min_floor_us > effective_floor) {
    effective_floor = min_floor_us;
  }
  if (vspeed_mps < -0.4f) {
    // May bay dang roi nhanh hon 0.4 m/s: nang tran ga len de tranh mat kiem soat do cao tren F450
    effective_floor += (-vspeed_mps - 0.4f) * 100.0f;
    if (effective_floor > (float)throttle_us - 20.0f) {
      effective_floor = (float)throttle_us - 20.0f;
    }
  }

  // Khong cho effective_floor bi ha thap hon floor an toan (min_floor_us hoac s.floor_us)
  float safe_floor = (min_floor_us > 0.0f) ? min_floor_us : s.floor_us;
  if (effective_floor < safe_floor) {
    effective_floor = safe_floor;
  }
  if (effective_floor < (float)ALT_LIMIT_DEFAULT_FLOOR_US) {
    effective_floor = (float)ALT_LIMIT_DEFAULT_FLOOR_US;
  }

  if (s.cap_us < effective_floor) s.cap_us = effective_floor;
  return throttle_us > (int)s.cap_us ? (int)s.cap_us : throttle_us;
}

// Byte co cua frame SBUS (byte 23): bit 3 = failsafe, bit 2 = mat 1 frame.
static inline bool sbus_flags_ok(uint8_t flags) { return (flags & 0x08) == 0; }
