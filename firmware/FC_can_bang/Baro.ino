// Baro.ino - BMP388 qua I2C (SDA 21, SCL 22). Tu do dia chi 0x76/0x77.
// Neu khong tim thay cam bien, telemetry gui null (Pi hien "khong co du lieu"),
// khong bia so lieu.
#include <Wire.h>

#define BARO_SDA 21
#define BARO_SCL 22
#define BARO_PERIOD_MS 40

static uint8_t baro_addr = 0;
static bool baro_ok = false;
static double bT1, bT2, bT3, bP1, bP2, bP3, bP4, bP5, bP6, bP7, bP8, bP9, bP10, bP11;
static double baro_ground_pa = 0;
static unsigned long baro_last_ms = 0;
static float baro_prev_alt = 0;
float baro_temperature_c = NAN;
float baro_pressure_pa = NAN;
float baro_vspeed_mps = 0;

static bool baro_read(uint8_t reg, uint8_t* out, uint8_t n) {
  Wire.beginTransmission(baro_addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)baro_addr, (int)n) != n) return false;
  for (uint8_t i = 0; i < n; i++) out[i] = Wire.read();
  return true;
}

static void baro_write(uint8_t reg, uint8_t v) {
  Wire.beginTransmission(baro_addr);
  Wire.write(reg); Wire.write(v);
  Wire.endTransmission();
}

static bool baro_sample(double& t, double& p) {
  uint8_t d[6];
  if (!baro_read(0x04, d, 6)) return false;
  double up = (uint32_t)d[0] | ((uint32_t)d[1] << 8) | ((uint32_t)d[2] << 16);
  double ut = (uint32_t)d[3] | ((uint32_t)d[4] << 8) | ((uint32_t)d[5] << 16);
  double pd1 = ut - bT1, pd2 = pd1 * bT2;
  t = pd2 + pd1 * pd1 * bT3;
  double o1 = bP5 + bP6 * t + bP7 * t * t + bP8 * t * t * t;
  double o2 = up * (bP1 + bP2 * t + bP3 * t * t + bP4 * t * t * t);
  double q = up * up * (bP9 + bP10 * t) + up * up * up * bP11;
  p = o1 + o2 + q;
  return p > 30000 && p < 120000;
}

void setup_baro() {
  Wire.begin(BARO_SDA, BARO_SCL, 400000);
  Wire.setTimeOut(5);
  const uint8_t addrs[2] = {0x77, 0x76};
  for (int i = 0; i < 2 && !baro_ok; i++) {
    baro_addr = addrs[i];
    uint8_t id = 0;
    if (baro_read(0x00, &id, 1) && id == 0x50) baro_ok = true;
  }
  if (!baro_ok) return;
  uint8_t c[21];
  if (!baro_read(0x31, c, 21)) { baro_ok = false; return; }
  auto u16 = [&](int i) { return (uint16_t)(c[i] | (c[i + 1] << 8)); };
  auto s16 = [&](int i) { return (int16_t)(c[i] | (c[i + 1] << 8)); };
  bT1 = u16(0) * 256.0;
  bT2 = u16(2) / 1073741824.0;
  bT3 = (int8_t)c[4] / 281474976710656.0;
  bP1 = (s16(5) - 16384) / 1048576.0;
  bP2 = (s16(7) - 16384) / 536870912.0;
  bP3 = (int8_t)c[9] / 4294967296.0;
  bP4 = (int8_t)c[10] / 137438953472.0;
  bP5 = u16(11) * 8.0;
  bP6 = u16(13) / 64.0;
  bP7 = (int8_t)c[15] / 256.0;
  bP8 = (int8_t)c[16] / 32768.0;
  bP9 = s16(17) / 281474976710656.0;
  bP10 = (int8_t)c[19] / 281474976710656.0;
  bP11 = (int8_t)c[20] / 36893488147419103232.0;
  baro_write(0x1C, 0x03);  // OSR press x8, temp x1
  baro_write(0x1D, 0x02);  // ODR 50 Hz
  baro_write(0x1F, 0x04);  // IIR coef 3
  baro_write(0x1B, 0x33);  // press + temp, normal mode
  delay(100);
  // Ap suat mat dat = trung binh 20 mau, dung lam moc do cao 0 m
  double sum = 0; int n = 0;
  for (int i = 0; i < 20; i++) {
    double t, p;
    if (baro_sample(t, p)) { sum += p; n++; }
    delay(25);
  }
  if (n == 0) { baro_ok = false; return; }
  baro_ground_pa = sum / n;
}

void baro_update() {
  if (!baro_ok || millis() - baro_last_ms < BARO_PERIOD_MS) return;
  float dt = (millis() - baro_last_ms) / 1000.0f;
  baro_last_ms = millis();
  double t, p;
  if (!baro_sample(t, p)) return;
  baro_temperature_c = t;
  baro_pressure_pa = p;
  float alt = 44330.0 * (1.0 - pow(p / baro_ground_pa, 0.1903));
  if (dt > 0 && dt < 1) {
    float v = (alt - baro_prev_alt) / dt;
    baro_vspeed_mps = baro_vspeed_mps * 0.8f + v * 0.2f;
  }
  baro_prev_alt = alt;
  Altitude_barometer = Altitude_barometer * 0.7f + alt * 0.3f;  // bien da co san trong FW goc
}

bool baro_available() { return baro_ok && !isnan(baro_pressure_pa); }
