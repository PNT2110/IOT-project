// Host test for firmware/FC_can_bang/gps_nmea.h (pure C++, no Arduino).
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>

#include "gps_nmea.h"

static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #cond); failures++; } } while (0)

static std::string with_checksum(const std::string& body) {
  unsigned char cs = 0;
  for (char c : body) cs ^= static_cast<unsigned char>(c);
  char tail[8];
  std::snprintf(tail, sizeof(tail), "*%02X\r\n", cs);
  return "$" + body + tail;
}

static int feed(NmeaParser& parser, const std::string& text) {
  int accepted = 0;
  for (char c : text) if (parser.feed(c)) accepted++;
  return accepted;
}

int main() {
  NmeaParser parser;

  // GGA with a fix, GN talker (multi-constellation u-blox output).
  CHECK(feed(parser, with_checksum("GNGGA,092750.000,1046.6140,N,10642.0540,E,1,09,0.9,5.4,M,-2.0,M,,")) == 1);
  CHECK(parser.data.has_fix);
  CHECK(parser.data.satellites == 9);
  CHECK(std::fabs(parser.data.latitude - 10.776900) < 1e-5);
  CHECK(std::fabs(parser.data.longitude - 106.700900) < 1e-5);
  CHECK(std::fabs(parser.data.altitude_m - 5.4f) < 0.01f);

  // Southern / western hemispheres are negative.
  NmeaParser south;
  CHECK(feed(south, with_checksum("GPGGA,092750.000,3351.0000,S,15112.0000,W,1,07,1.1,30.0,M,0.0,M,,")) == 1);
  CHECK(south.data.latitude < -33.84 && south.data.latitude > -33.86);
  CHECK(south.data.longitude < -151.19 && south.data.longitude > -151.21);

  // A corrupted checksum is dropped and counted, and does not change the fix.
  NmeaParser bad;
  CHECK(feed(bad, "$GNGGA,092750.000,1046.6140,N,10642.0540,E,1,09,0.9,5.4,M,-2.0,M,,*00\r\n") == 0);
  CHECK(!bad.data.has_fix);
  CHECK(bad.data.sentences_bad == 1);

  // GGA quality 0 means no fix.
  NmeaParser nofix;
  CHECK(feed(nofix, with_checksum("GNGGA,092750.000,,,,,0,00,99.9,,M,,M,,")) == 1);
  CHECK(!nofix.data.has_fix);

  // RMC status V clears the fix; status A carries speed in knots.
  CHECK(feed(parser, with_checksum("GNRMC,092751.000,V,1046.6140,N,10642.0540,E,0.00,0.00,011026,,,N")) == 1);
  CHECK(!parser.data.has_fix);
  CHECK(feed(parser, with_checksum("GNRMC,092752.000,A,1046.6140,N,10642.0540,E,10.00,90.00,011026,,,A")) == 1);
  CHECK(std::fabs(parser.data.speed_mps - 5.1444f) < 0.01f);
  CHECK(std::fabs(parser.data.course_deg - 90.0f) < 0.01f);

  // Other valid sentences are counted but not treated as position updates.
  uint32_t before = parser.data.sentences_ok;
  CHECK(feed(parser, with_checksum("GNGSA,A,3,01,02,03,,,,,,,,,,1.5,0.9,1.2")) == 0);
  CHECK(parser.data.sentences_ok == before + 1);

  // Binary noise (for example UBX frames) and over-long lines do not crash or produce a fix.
  NmeaParser noise;
  std::string junk = "\xB5\x62\x01\x07";
  junk += std::string(300, 'x');
  CHECK(feed(noise, junk) == 0);
  CHECK(!noise.data.has_fix);
  CHECK(feed(noise, with_checksum("GNGGA,092750.000,1046.6140,N,10642.0540,E,1,09,0.9,5.4,M,-2.0,M,,")) == 1);

  // Command lines from the Pi use the same checksum.
  char ok_line[] = "$AUTH,ALLOW,60,ref-1*00";
  unsigned char cs = 0;
  for (const char* p = ok_line + 1; *p != '*'; ++p) cs ^= static_cast<unsigned char>(*p);
  std::snprintf(ok_line + std::strlen(ok_line) - 2, 3, "%02X", cs);
  char* fields[8];
  CHECK(parse_checked_line(ok_line, fields, 8) == 4);
  CHECK(std::strcmp(fields[0], "AUTH") == 0 && std::strcmp(fields[1], "ALLOW") == 0 && std::strcmp(fields[2], "60") == 0 && std::strcmp(fields[3], "ref-1") == 0);
  char bad_line[] = "$AUTH,ALLOW,60,ref-1*00";
  CHECK(parse_checked_line(bad_line, fields, 8) == 0);
  char no_star[] = "$PING";
  CHECK(parse_checked_line(no_star, fields, 8) == 0);

  if (failures == 0) std::printf("gps_nmea: all checks passed\n");
  return failures == 0 ? 0 : 1;
}
