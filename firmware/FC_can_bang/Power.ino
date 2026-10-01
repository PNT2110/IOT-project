// Power.ino - do dien ap pin qua ADC (cau phan ap).
// MAC DINH TAT (BATTERY_ADC_PIN = -1) vi chua co so do chan do pin tren mach.
// Khi bat: dat chan ADC1 (32..39) va ti le cau phan ap thuc te, so cell LiPo.
#define BATTERY_ADC_PIN   -1
#define BATTERY_DIVIDER   11.0f   // (R1+R2)/R2, vd 10k/1k
#define BATTERY_CELLS     4
#define CELL_EMPTY_V      3.50f
#define CELL_FULL_V       4.20f

static float battery_v_filtered = NAN;

void battery_update() {
#if BATTERY_ADC_PIN >= 0
  static unsigned long last = 0;
  if (millis() - last < 50) return;
  last = millis();
  float v = analogReadMilliVolts(BATTERY_ADC_PIN) / 1000.0f * BATTERY_DIVIDER;
  battery_v_filtered = isnan(battery_v_filtered) ? v : battery_v_filtered * 0.9f + v * 0.1f;
#endif
}

float battery_voltage() { return battery_v_filtered; }

float battery_percent() {
  if (isnan(battery_v_filtered)) return NAN;
  float cell = battery_v_filtered / BATTERY_CELLS;
  float pct = (cell - CELL_EMPTY_V) / (CELL_FULL_V - CELL_EMPTY_V) * 100.0f;
  return pct < 0 ? 0 : (pct > 100 ? 100 : pct);
}
