// gps_nmea.h - bo phan tich NMEA 0183 v4.x thuan C++ (khong phu thuoc Arduino)
// de co the test tren may tinh. Ho tro cau GGA va RMC voi moi talker (GP/GN/GL/GA/BD).
// Kiem tra checksum bat buoc; cau sai checksum bi bo qua.
#pragma once
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

struct GpsData {
  bool    has_fix;        // GGA quality > 0 va RMC status A (neu co)
  uint8_t fix_quality;    // 0 = no fix, 1 = GPS, 2 = DGPS, 4/5 = RTK, 6 = dead reckoning
  uint8_t satellites;
  float   hdop;
  double  latitude;       // do, + Bac
  double  longitude;      // do, + Dong
  float   altitude_m;     // MSL
  float   speed_mps;
  float   course_deg;
  bool    rmc_valid;
  uint32_t sentences_ok;
  uint32_t sentences_bad;
};

class NmeaParser {
 public:
  NmeaParser() { reset(); }

  void reset() {
    memset(&data, 0, sizeof(data));
    len_ = 0;
    in_sentence_ = false;
  }

  // Tra ve true khi vua xu ly xong 1 cau hop le (GGA hoac RMC).
  bool feed(char c) {
    if (c == '$') { in_sentence_ = true; len_ = 0; return false; }
    if (!in_sentence_) return false;
    if (c == '\r' || c == '\n') {
      in_sentence_ = false;
      buf_[len_] = 0;
      return process();
    }
    if (len_ >= sizeof(buf_) - 1) { in_sentence_ = false; data.sentences_bad++; return false; }
    buf_[len_++] = c;
    return false;
  }

  GpsData data;

 private:
  char buf_[100];
  size_t len_;
  bool in_sentence_;

  static int hexval(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return -1;
  }

  // Chuyen ddmm.mmmm (hoac dddmm.mmmm) sang do thap phan.
  static double nmea_to_deg(const char* s, char hemi) {
    if (!s || !*s) return 0.0;
    double v = atof(s);
    int deg = (int)(v / 100.0);
    double minutes = v - deg * 100.0;
    double d = deg + minutes / 60.0;
    if (hemi == 'S' || hemi == 'W') d = -d;
    return d;
  }

  bool process() {
    char* star = strchr(buf_, '*');
    if (!star || star[1] == 0 || star[2] == 0) { data.sentences_bad++; return false; }
    uint8_t cs = 0;
    for (char* p = buf_; p < star; ++p) cs ^= (uint8_t)*p;
    int h = hexval(star[1]), l = hexval(star[2]);
    if (h < 0 || l < 0 || cs != (uint8_t)((h << 4) | l)) { data.sentences_bad++; return false; }
    *star = 0;

    // Tach truong (giu truong rong).
    const int MAXF = 24;
    char* f[MAXF];
    int n = 0;
    char* p = buf_;
    f[n++] = p;
    while (*p && n < MAXF) {
      if (*p == ',') { *p = 0; f[n++] = p + 1; }
      ++p;
    }
    if (strlen(f[0]) < 5) { data.sentences_bad++; return false; }
    const char* type = f[0] + strlen(f[0]) - 3;

    if (strcmp(type, "GGA") == 0 && n >= 10) {
      data.fix_quality = (uint8_t)atoi(f[6]);
      data.satellites  = (uint8_t)atoi(f[7]);
      data.hdop        = *f[8] ? (float)atof(f[8]) : 99.9f;
      if (data.fix_quality > 0 && *f[2] && *f[4]) {
        data.latitude   = nmea_to_deg(f[2], f[3][0]);
        data.longitude  = nmea_to_deg(f[4], f[5][0]);
        data.altitude_m = (float)atof(f[9]);
      }
      data.has_fix = data.fix_quality > 0;
      data.sentences_ok++;
      return true;
    }
    if (strcmp(type, "RMC") == 0 && n >= 9) {
      data.rmc_valid = (f[2][0] == 'A');
      if (data.rmc_valid && *f[3] && *f[5]) {
        data.latitude  = nmea_to_deg(f[3], f[4][0]);
        data.longitude = nmea_to_deg(f[5], f[6][0]);
        data.speed_mps = (float)(atof(f[7]) * 0.514444);
        data.course_deg = (float)atof(f[8]);
      }
      if (!data.rmc_valid) data.has_fix = false;
      data.sentences_ok++;
      return true;
    }
    data.sentences_ok++;  // cau hop le nhung khong dung toi (GSA, GSV, VTG...)
    return false;
  }
};

// ---- Lenh tu Pi: "$CMD,a,b,c*HH" ; kiem tra checksum giong NMEA ----
// Tra ve so truong (>=1) neu hop le, 0 neu sai. Ghi de buffer.
static inline int parse_checked_line(char* line, char** fields, int max_fields) {
  if (line[0] != '$') return 0;
  char* star = strchr(line, '*');
  if (!star || !star[1] || !star[2]) return 0;
  uint8_t cs = 0;
  for (char* p = line + 1; p < star; ++p) cs ^= (uint8_t)*p;
  auto hv = [](char c) -> int {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return -1;
  };
  int h = hv(star[1]), l = hv(star[2]);
  if (h < 0 || l < 0 || star[3] != 0 || (uint8_t)((h << 4) | l) != cs) return 0;
  *star = 0;
  int n = 0;
  char* p = line + 1;
  fields[n++] = p;
  while (*p && n < max_fields) {
    if (*p == ',') { *p = 0; fields[n++] = p + 1; }
    ++p;
  }
  return n;
}
