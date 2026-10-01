#include "flight_gate.h"
// --- Khai báo biến cho Target =
float roll_target, pitch_target, yaw_target, yaw_vel_target;

// --- Khai báo biến từ Cảm biến (Góc và Tốc độ góc) ---
float angleroll, anglepitch;
float rateroll, ratepitch, rateyaw;

//- biến dữ liệu thô từ icm---
float RateRoll, RatePitch, RateYaw;
float AngleRoll, AnglePitch, AngleYaw;

// --- Khai báo biến trung gian giữa 3 vòng PID ---
float Desired_RateRoll = 0, Desired_RatePitch = 0 , Desired_RateYaw = 0;

// --- Khai báo biến đầu ra motor ---
float esc_1, esc_2, esc_3, esc_4;

// --- Biến ga và các đầu ra PID ---
float throttle_smoot;

float INPUTROLL = 0;
float INPUTPITCH = 0;
float INPUTYAW = 0;

float Acc_x, Acc_y, Acc_z;
float Acc_x_bu, Acc_y_bu, Acc_z_bu;

int sbus_status;

unsigned long LoopTimer;

//Biến lấy độ cao từ gia tốc**************************************************************//
float AccZInertial;
float volocity_vertical;  

float rateroll_target;
float ratepitch_target;
//**************************************************************//
//khai báo biến cho BMP388------------------

float altitude;
uint32_t raw_press;
uint32_t raw_temp;
float Altitude_barometer;
float VelocityVerticalKalman;
float AltitudeKalman;
float Altitude_kalman; // biến lấy độ cao cuối cùng
float Velocity_kalman;
static unsigned int sbus_ch[17], channel_sbus[17];

#define arm_disarm 5
#define flight_mode 6

#define value_arm 1800
#define value_disarm 1090

#define value_angle_mode 990

int switch_arm_disarm;
int status_arm;


// ---- Bo sung: an toan ARM ----
// Co the bat yeu cau GPS co fix moi cho ARM (mac dinh tat de con test trong nha).
#define REQUIRE_GPS_FIX_TO_ARM 0
static bool arm_switch_seen_low = false;   // phai thay cong tac o vi tri DISARM truoc khi ARM
const char* arm_reason = "BOOT";            // ly do chua ARM / ly do vua DISARM, gui ve Pi
const char* flight_mode_name = "ANGLE";
float arm_ground_alt = 0;

void setup() {
 setup_icm20602();   // trong nay co Serial.begin(115200) cho USB -> Pi

 setup_sbus();
 setup_motor();
 setup_gps();
 setup_baro();
 settings_load();    // PID + do cao toi da da luu trong NVS
}

static bool arm_permitted() { return flight_authorized() && link_alive(); }

static void update_arm_state() {
  bool sw_low  = sbus_ch[arm_disarm] < value_disarm;
  bool mode_angle = sbus_ch[flight_mode] > value_angle_mode - 100 && sbus_ch[flight_mode] < value_angle_mode + 100;

  flight_mode_name = flight_mode_label(sbus_status, mode_angle, status_arm, arm_permitted());

  if (status_arm == 0) {
    if (sbus_status && sw_low) arm_switch_seen_low = true;

    ArmInputs in;
    in.rc_ok = sbus_status;
    in.auth_allowed = flight_authorized();
    in.link_alive = link_alive();
    in.gps_ok = !REQUIRE_GPS_FIX_TO_ARM || gps_has_valid_fix();
    in.mode_angle = mode_angle;
    in.arm_switch_seen_low = arm_switch_seen_low;
    in.arm_switch_high = sbus_ch[arm_disarm] > value_arm;
    in.throttle_us = sbus_ch[3];
    arm_reason = arm_block_reason(in);

    if (strcmp(arm_reason, "READY") == 0) {
      status_arm = 1;
      arm_switch_seen_low = false;
      reset_status_flight();
      altitude_limit_reset();
      arm_ground_alt = Altitude_barometer;
      arm_reason = "ARMED";
    }
  } else if (must_disarm(sw_low, sbus_status, mode_angle)) {
    // Dang bay: chi gat DISARM, mat RC hoac mode KILL moi tat motor.
    // Het han cap phep / mat Pi KHONG cat motor giua khong trung; no chan lan ARM sau.
    status_arm = 0;
    reset_status_flight();
    arm_reason = sw_low ? "DISARMED_BY_SWITCH" : (!sbus_status ? "FAILSAFE_RC_LOST" : "KILL_MODE");
  }
}

void loop() {

  icm20602();
  rateroll = get_RateRoll();
  ratepitch = get_RatePitch();
  rateyaw =  get_RateYaw();
  angleroll = get_AngleRoll();
  anglepitch = get_AnglePitch();
  yaw_integrate(rateyaw, 0.005f);

  sbus_status = read_data_control();   // doc SBUS + loc lenh (goi 1 lan moi vong)

  gps_update();
  baro_update();
  battery_update();
  imu_temperature_update();
  link_receive();

  update_arm_state();

  if (status_arm == 1) {
    angle_mode();
  } else {
    no_fly();
  }

  if (ch(3) < 1050) {
    reset_pid();
  }

  control_motor( esc_1, esc_2, esc_3, esc_4, status_arm);

  const char* arm_txt = status_arm ? "ARMED" : (arm_permitted() ? "DISARMED" : "BLOCKED");
  link_send_telemetry(arm_txt, flight_mode_name);

  while (micros() - LoopTimer < 5000);
  LoopTimer = micros();

  display();
}
