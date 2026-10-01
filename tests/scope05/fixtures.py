from __future__ import annotations


def nmea_sentence(body: str) -> str:
    checksum = 0
    for byte in body.encode("ascii"):
        checksum ^= byte
    return f"${body}*{checksum:02X}"


VALID_GGA = nmea_sentence("GNGGA,000010,1000.0000,N,10600.0000,E,1,08,0.9,12.3,M,0.0,M,,")
VALID_GGA_NO_FRACTION = nmea_sentence("GPGGA,000010,1000.0000,N,10600.0000,E,1,08,0.9,12.3,M,0.0,M,,")
NO_FIX_GGA = nmea_sentence("GPGGA,000010,,,,,0,00,99.9,,M,,M,,")

