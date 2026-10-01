// GPS.ino - doc GPS NMEA 0183 v4.0/4.1 qua UART1, 38400 bps 8N1, chan GPIO16/GPIO17.
// Day noi: TX cua GPS -> RX cua ESP (GPIO16). Vi co the day TX cua GPS dang cam vao 17,
// firmware tu do: nghe tren 16 truoc, 3 giay khong co cau NMEA hop le thi nghe tren 17.
// CHI NGHE: khong gan chan TX (-1) nen ESP khong bao gio keo dien ap vao ngo ra cua GPS,
// va khong gui lenh cau hinh (UBX) xuong GPS. Module phai dang xuat NMEA.
#include "gps_nmea.h"

HardwareSerial Serial_gps(1);

#define GPS_BAUD         38400
#define GPS_PIN_A        16
#define GPS_PIN_B        17
#define GPS_STALE_MS     2000
#define GPS_SWAP_MS      3000
#define GPS_LOCK_SENTENCES 3         // so cau dung checksum can thay truoc khi chot chan RX
#define GPS_MAX_BYTES_PER_LOOP 128   // gioi han thoi gian xu ly trong vong 5 ms

NmeaParser gps_parser;
static int gps_rx_pin = GPS_PIN_A;
static unsigned long gps_last_sentence_ms = 0;
static unsigned long gps_pin_since_ms = 0;
static uint32_t gps_ok_at_pin_start = 0;
static bool gps_pins_locked = false;

static void gps_listen_on(int rx) {
  Serial_gps.end();
  Serial_gps.setRxBufferSize(1024);
  Serial_gps.begin(GPS_BAUD, SERIAL_8N1, rx, -1);
  gps_rx_pin = rx;
  gps_pin_since_ms = millis();
  gps_ok_at_pin_start = gps_parser.data.sentences_ok;
}

void setup_gps() {
  gps_listen_on(GPS_PIN_A);
}

void gps_update() {
  int budget = GPS_MAX_BYTES_PER_LOOP;
  while (budget-- > 0 && Serial_gps.available()) {
    if (gps_parser.feed((char)Serial_gps.read())) gps_last_sentence_ms = millis();
  }
  if (gps_pins_locked) return;
  if (gps_parser.data.sentences_ok - gps_ok_at_pin_start >= GPS_LOCK_SENTENCES) {
    gps_pins_locked = true;
  } else if (millis() - gps_pin_since_ms > GPS_SWAP_MS) {
    gps_listen_on(gps_rx_pin == GPS_PIN_A ? GPS_PIN_B : GPS_PIN_A);
  }
}

// "VALID_FIX" | "NO_FIX" | "STALE" | "UNAVAILABLE" (dung voi hop dong scope05 cua Pi)
const char* gps_fix_state() {
  if (gps_last_sentence_ms == 0) return "UNAVAILABLE";
  if (millis() - gps_last_sentence_ms > GPS_STALE_MS) return "STALE";
  return gps_parser.data.has_fix ? "VALID_FIX" : "NO_FIX";
}

bool gps_has_valid_fix() { return strcmp(gps_fix_state(), "VALID_FIX") == 0; }
int  gps_rx_pin_in_use() { return gps_rx_pin; }
bool gps_pins_detected() { return gps_pins_locked; }
