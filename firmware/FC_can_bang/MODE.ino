// Gioi han do cao toi da (so voi diem ARM): xem altitude_throttle_cap() trong flight_gate.h.
// Khi vuot tran: chot tran ga, ha dan 10 us/giay cho may bay tu xuong, nha khi thap hon tran 1 m.
static AltLimiter alt_limiter;

bool altitude_limit_active() { return alt_limiter.active; }
void altitude_limit_reset() { alt_limiter = AltLimiter(); }

static void apply_altitude_limit() {
  if (!baro_available()) { alt_limiter.active = false; return; }
  throttle_smoot = altitude_throttle_cap(alt_limiter, Altitude_barometer - arm_ground_alt, max_altitude_m, (int)throttle_smoot);
}

void angle_mode() {
  apply_altitude_limit();
  PID_Angle(roll_target, pitch_target, yaw_target, angleroll, anglepitch, 0);
  PID_Rate(Desired_RateRoll, Desired_RatePitch, yaw_vel_target, rateroll, ratepitch, rateyaw);

  // PID_Rate(rateroll_target, ratepitch_target, yaw_vel_target, rateroll, ratepitch, rateyaw);

  esc_1=throttle_smoot - INPUTROLL - INPUTPITCH - INPUTYAW;  // CÁI angle_pid này k cần & vì nó chỉ lấy ra để nó tính toán thoi
  esc_2=throttle_smoot + INPUTROLL + INPUTPITCH - INPUTYAW;
  esc_3=throttle_smoot + INPUTROLL - INPUTPITCH + INPUTYAW;
  esc_4=throttle_smoot - INPUTROLL + INPUTPITCH + INPUTYAW;
  limit_value(900, 1600);
 
}

void limit_value(int min, int max){
  if(esc_1<min) esc_1=min;
  if(esc_2<min) esc_2=min;
  if(esc_3<min) esc_3=min;
  if(esc_4<min) esc_4=min;

  if(esc_1>max) esc_1=max;
  if(esc_2>max) esc_2=max;
  if(esc_3>max) esc_3=max;
  if(esc_4>max) esc_4=max;
}

void no_fly() {
  esc_1 = 800;
  esc_2 = 800;
  esc_3 = 800;
  esc_4 = 800;
  // Khong doi status_arm o day: trang thai ARM do update_arm_state() quyet dinh.
}