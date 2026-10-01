// Link.ino - giao tiep USB (Serial, 115200) voi Raspberry Pi 5.
//
// ESP -> Pi: moi 200 ms gui 1 dong JSON theo hop dong "scope05.esp32.usb.v1".
// Pi -> ESP: dong lenh co checksum kieu NMEA: $LENH,tham_so...*HH
//   $AUTH,ALLOW,<giay>,<ma_don>*HH  cho phep ARM trong <giay> (1..86400)
//   $AUTH,DENY,<ma_don>*HH          tu choi / thu hoi quyen ARM
//   $PID,<truc>,<kp>,<ki>,<kd>*HH   truc: roll|pitch|yaw (vong rate), angle (P vong goc)
//   $MAXALT,<met>*HH                do cao toi da so voi diem cat canh (2..500 m)
//   $PING*HH                        nhip tim cua Pi
// Quyen ARM chi luu trong RAM -> khoi dong lai ESP thi luon bi CHAN cho toi khi Pi cap lai.
// Quyen ARM con can Pi "con song": khong co $PING trong 10 s thi khong ARM duoc (PI_LINK_LOST).
// PID va do cao toi da duoc luu vao NVS (Preferences "fc") moi khi Pi gui gia tri moi.
// Pi KHONG the tu ARM / quay motor: ARM van phai gat cong tac tren tay dieu khien.
#include "gps_nmea.h"
#include <Preferences.h>

// Bien PID khai bao trong PID.ino (file nay duoc ghep truoc PID.ino)
extern float PAngleRoll, IAngleRoll, DAngleRoll, PAnglePitch, IAnglePitch, DAnglePitch;
extern float PRateRoll, IRateRoll, DRateRoll, PRatePitch, IRatePitch, DRatePitch;
extern float PRateYaw, IRateYaw, DRateYaw;

#define LINK_TELEMETRY_MS 200
#define LINK_RX_MAX 128

// ---- Trang thai cap phep bay ----
enum AuthState { AUTH_NONE = 0, AUTH_ALLOWED = 1, AUTH_DENIED = 2 };
static AuthState auth_state = AUTH_NONE;
static unsigned long auth_until_ms = 0;
static char auth_ref[33] = "";
float max_altitude_m = 120.0f;

static char link_rx[LINK_RX_MAX + 1];
static int link_rx_len = 0;
static char link_last_cmd[12] = "";
static const char* link_last_result = "NONE";
static uint32_t link_cmd_count = 0;
static unsigned long link_last_ping_ms = 0;
static unsigned long link_last_tx_ms = 0;
static uint32_t link_seq = 0;

static bool link_ping_seen = false;
static Preferences fc_settings;

bool link_alive() { return pi_link_alive(millis(), link_last_ping_ms, link_ping_seen); }

// Chi goi khi DISARM (ghi flash mat vai ms).
static void settings_save() {
  fc_settings.begin("fc", false);
  fc_settings.putFloat("rr_p", PRateRoll);  fc_settings.putFloat("rr_i", IRateRoll);  fc_settings.putFloat("rr_d", DRateRoll);
  fc_settings.putFloat("rp_p", PRatePitch); fc_settings.putFloat("rp_i", IRatePitch); fc_settings.putFloat("rp_d", DRatePitch);
  fc_settings.putFloat("ry_p", PRateYaw);   fc_settings.putFloat("ry_i", IRateYaw);   fc_settings.putFloat("ry_d", DRateYaw);
  fc_settings.putFloat("an_p", PAngleRoll); fc_settings.putFloat("an_i", IAngleRoll); fc_settings.putFloat("an_d", DAngleRoll);
  fc_settings.putFloat("maxalt", max_altitude_m);
  fc_settings.end();
}

static float setting_in(const char* key, float fallback, float lo, float hi) {
  float value = fc_settings.getFloat(key, fallback);
  return (isnan(value) || value < lo || value > hi) ? fallback : value;
}

// Nap lai gia tri da luu; khong co hoac ngoai khoang -> giu gia tri mac dinh trong code.
void settings_load() {
  fc_settings.begin("fc", true);
  PRateRoll  = setting_in("rr_p", PRateRoll, 0, 50);  IRateRoll  = setting_in("rr_i", IRateRoll, 0, 50);  DRateRoll  = setting_in("rr_d", DRateRoll, 0, 5);
  PRatePitch = setting_in("rp_p", PRatePitch, 0, 50); IRatePitch = setting_in("rp_i", IRatePitch, 0, 50); DRatePitch = setting_in("rp_d", DRatePitch, 0, 5);
  PRateYaw   = setting_in("ry_p", PRateYaw, 0, 50);   IRateYaw   = setting_in("ry_i", IRateYaw, 0, 50);   DRateYaw   = setting_in("ry_d", DRateYaw, 0, 5);
  PAngleRoll = PAnglePitch = setting_in("an_p", PAngleRoll, 0, 50);
  IAngleRoll = IAnglePitch = setting_in("an_i", IAngleRoll, 0, 50);
  DAngleRoll = DAnglePitch = setting_in("an_d", DAngleRoll, 0, 5);
  max_altitude_m = setting_in("maxalt", max_altitude_m, 2, 500);
  fc_settings.end();
}

bool flight_authorized() {
  if (auth_state != AUTH_ALLOWED) return false;
  if ((long)(auth_until_ms - millis()) <= 0) { auth_state = AUTH_NONE; return false; }
  return true;
}

static const char* auth_state_name() {
  flight_authorized();  // cap nhat het han
  switch (auth_state) {
    case AUTH_ALLOWED: return "ALLOWED";
    case AUTH_DENIED:  return "DENIED";
    default:           return "NONE";
  }
}

static bool parse_float_in(const char* s, float lo, float hi, float& out) {
  if (!s || !*s) return false;
  char* end;
  out = strtof(s, &end);
  return *end == 0 && !isnan(out) && out >= lo && out <= hi;
}

static void copy_ref(const char* s) {
  size_t i = 0;
  for (; s && s[i] && i < sizeof(auth_ref) - 1; i++) {
    char c = s[i];
    auth_ref[i] = (isalnum((unsigned char)c) || c == '-' || c == '_') ? c : '_';
  }
  auth_ref[i] = 0;
}

static void handle_command(char* line) {
  char* f[8];
  int n = parse_checked_line(line, f, 8);
  link_cmd_count++;
  if (n == 0) { strcpy(link_last_cmd, "?"); link_last_result = "BAD_CHECKSUM"; return; }
  strncpy(link_last_cmd, f[0], sizeof(link_last_cmd) - 1);
  link_last_cmd[sizeof(link_last_cmd) - 1] = 0;

  if (strcmp(f[0], "PING") == 0) {
    link_last_ping_ms = millis();
    link_ping_seen = true;
    link_last_result = "OK";
  } else if (strcmp(f[0], "AUTH") == 0 && n >= 2) {
    if (strcmp(f[1], "ALLOW") == 0 && n == 4) {
      float sec;
      if (!parse_float_in(f[2], 1, 86400, sec)) { link_last_result = "BAD_ARG"; return; }
      auth_state = AUTH_ALLOWED;
      auth_until_ms = millis() + (unsigned long)(sec * 1000.0f);
      copy_ref(f[3]);
      link_last_result = "OK";
    } else if (strcmp(f[1], "DENY") == 0 && n == 3) {
      auth_state = AUTH_DENIED;
      auth_until_ms = 0;
      copy_ref(f[2]);
      link_last_result = "OK";
    } else {
      link_last_result = "BAD_ARG";
    }
  } else if (strcmp(f[0], "PID") == 0 && n == 5) {
    if (status_arm) { link_last_result = "REJECTED_ARMED"; return; }
    float kp, ki, kd;
    if (!parse_float_in(f[2], 0, 50, kp) || !parse_float_in(f[3], 0, 50, ki) || !parse_float_in(f[4], 0, 5, kd)) {
      link_last_result = "BAD_ARG"; return;
    }
    if      (strcmp(f[1], "roll") == 0)  { PRateRoll = kp;  IRateRoll = ki;  DRateRoll = kd; }
    else if (strcmp(f[1], "pitch") == 0) { PRatePitch = kp; IRatePitch = ki; DRatePitch = kd; }
    else if (strcmp(f[1], "yaw") == 0)   { PRateYaw = kp;   IRateYaw = ki;   DRateYaw = kd; }
    else if (strcmp(f[1], "angle") == 0) { PAngleRoll = PAnglePitch = kp; IAngleRoll = IAnglePitch = ki; DAngleRoll = DAnglePitch = kd; }
    else { link_last_result = "BAD_ARG"; return; }
    reset_status_flight();
    settings_save();
    link_last_result = "OK";
  } else if (strcmp(f[0], "MAXALT") == 0 && n == 2) {
    if (status_arm) { link_last_result = "REJECTED_ARMED"; return; }
    float m;
    if (!parse_float_in(f[1], 2, 500, m)) { link_last_result = "BAD_ARG"; return; }
    max_altitude_m = m;
    settings_save();
    link_last_result = "OK";
  } else {
    link_last_result = "UNKNOWN";
  }
}

void link_receive() {
  int budget = 64;
  while (budget-- > 0 && Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (link_rx_len > 0) { link_rx[link_rx_len] = 0; handle_command(link_rx); }
      link_rx_len = 0;
    } else if (link_rx_len < LINK_RX_MAX) {
      link_rx[link_rx_len++] = c;
    } else {
      link_rx_len = 0;  // dong qua dai -> bo
      link_last_result = "TOO_LONG";
    }
  }
}

// ---- JSON helper: so khong hop le -> null ----
static int jnum(char* out, size_t cap, float v, int dec) {
  if (isnan(v) || isinf(v)) return snprintf(out, cap, "null");
  return snprintf(out, cap, "%.*f", dec, v);
}

#define JAPPEND(...) do { if (pos < (int)sizeof(buf)) pos += snprintf(buf + pos, sizeof(buf) - pos, __VA_ARGS__); } while (0)
#define JNUM(v, d)   do { if (pos < (int)sizeof(buf)) pos += jnum(buf + pos, sizeof(buf) - pos, (v), (d)); } while (0)

static int clamp_ch(int v) { return v < 0 ? 0 : (v > 2047 ? 2047 : v); }

void link_send_telemetry(const char* arm_state, const char* mode) {
  if (millis() - link_last_tx_ms < LINK_TELEMETRY_MS) return;
  link_last_tx_ms = millis();
  static char buf[1200];
  int pos = 0;
  const GpsData& g = gps_parser.data;
  bool fix = gps_has_valid_fix();

  JAPPEND("{\"schema_version\":\"scope05.esp32.usb.v1\",\"seq\":%lu,", (unsigned long)link_seq);
  JAPPEND("\"imu\":{\"roll_deg\":"); JNUM(angleroll, 2);
  JAPPEND(",\"pitch_deg\":"); JNUM(anglepitch, 2);
  JAPPEND(",\"yaw_deg\":"); JNUM(get_YawRelative(), 1);
  JAPPEND(",\"yaw_reference\":\"GYRO_RELATIVE\"},");
  JAPPEND("\"baro\":{\"altitude_m\":"); JNUM(baro_available() ? Altitude_barometer : NAN, 2);
  JAPPEND(",\"vertical_speed_mps\":"); JNUM(baro_available() ? baro_vspeed_mps : NAN, 2);
  JAPPEND(",\"temperature_c\":"); JNUM(baro_temperature_c, 1);
  JAPPEND(",\"available\":%s},", baro_available() ? "true" : "false");
  JAPPEND("\"temperature_c\":"); JNUM(get_imu_temperature(), 1);
  JAPPEND(",\"power\":{\"battery_pct\":"); JNUM(battery_percent(), 0);
  JAPPEND(",\"voltage_v\":"); JNUM(battery_voltage(), 2);
  JAPPEND("},\"sbus\":{\"signal_ok\":%s,\"channels\":[", sbus_status ? "true" : "false");
  for (int i = 1; i <= 8; i++) JAPPEND("%s%d", i > 1 ? "," : "", clamp_ch((int)sbus_ch[i]));
  JAPPEND("]},\"gnss\":{\"fix_state\":\"%s\"", gps_fix_state());
  if (fix) {
    JAPPEND(",\"latitude\":%.7f,\"longitude\":%.7f,\"altitude_m\":", g.latitude, g.longitude);
    JNUM(g.altitude_m, 1);
  }
  JAPPEND(",\"satellites\":%u,\"hdop\":", g.satellites); JNUM(g.hdop, 1);
  JAPPEND(",\"speed_mps\":"); JNUM(fix ? g.speed_mps : NAN, 2);
  JAPPEND(",\"course_deg\":"); JNUM(fix ? g.course_deg : NAN, 1);
  JAPPEND(",\"uart_rx_pin\":%d,\"baud\":38400,\"detected\":%s},", gps_rx_pin_in_use(), gps_pins_detected() ? "true" : "false");
  JAPPEND("\"flight\":{\"arm_state\":\"%s\",\"mode\":\"%s\",\"authorization\":\"%s\",\"auth_ref\":\"%s\",\"auth_remaining_s\":%ld,",
          arm_state, mode, auth_state_name(), auth_ref,
          flight_authorized() ? (long)((auth_until_ms - millis()) / 1000) : 0L);
  JAPPEND("\"arm_block_reason\":\"%s\",\"max_altitude_m\":", arm_reason); JNUM(max_altitude_m, 1);
  JAPPEND(",\"altitude_limited\":%s,\"throttle_us\":", altitude_limit_active() ? "true" : "false");
  JNUM(throttle_smoot, 0);
  JAPPEND(",\"motors_us\":[%d,%d,%d,%d]},", (int)esc_1, (int)esc_2, (int)esc_3, (int)esc_4);
  JAPPEND("\"pid\":{\"roll\":{\"kp\":%.3f,\"ki\":%.3f,\"kd\":%.4f},", PRateRoll, IRateRoll, DRateRoll);
  JAPPEND("\"pitch\":{\"kp\":%.3f,\"ki\":%.3f,\"kd\":%.4f},", PRatePitch, IRatePitch, DRatePitch);
  JAPPEND("\"yaw\":{\"kp\":%.3f,\"ki\":%.3f,\"kd\":%.4f},", PRateYaw, IRateYaw, DRateYaw);
  JAPPEND("\"angle\":{\"kp\":%.3f,\"ki\":%.3f,\"kd\":%.4f}},", PAngleRoll, IAngleRoll, DAngleRoll);
  JAPPEND("\"link\":{\"last_cmd\":\"%s\",\"last_result\":\"%s\",\"cmd_count\":%lu,\"pi_alive\":%s,\"pi_heartbeat_age_ms\":%ld},",
          link_last_cmd, link_last_result, (unsigned long)link_cmd_count, link_alive() ? "true" : "false",
          link_ping_seen ? (long)(millis() - link_last_ping_ms) : -1L);
  JAPPEND("\"uptime_ms\":%lu}\n", (unsigned long)millis());

  if (pos >= (int)sizeof(buf)) return;  // khong gui frame bi cat
  // Khong bao gio chan vong dieu khien 5 ms: neu buffer TX khong du cho thi bo frame nay
  if (Serial.availableForWrite() < pos) return;
  Serial.write((const uint8_t*)buf, pos);
  link_seq++;
}
