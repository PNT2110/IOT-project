"""SYNTHETIC, non-hardware GNSS fixtures for SCOPE-05 parser tests."""


def nmea_sentence(body: str) -> str:
    checksum = 0
    for byte in body.encode("ascii"):
        checksum ^= byte
    return f"${body}*{checksum:02X}"


VALID_GGA = nmea_sentence("GPGGA,000000.00,1000.0000,N,10600.0000,E,1,08,0.9,12.3,M,0.0,M,,")
NO_FIX_GGA = nmea_sentence("GPGGA,000000.00,,,,,0,00,,,M,,M,,")
MALFORMED_GGA = nmea_sentence("GPGGA,000000.00,1000.0000,N")


def ubx_frame(message_class: int = 0x01, message_id: int = 0x07, payload: bytes = b"\x00") -> bytes:
    body = bytes((message_class, message_id)) + len(payload).to_bytes(2, "little") + payload
    ck_a = 0
    ck_b = 0
    for byte in body:
        ck_a = (ck_a + byte) & 0xFF
        ck_b = (ck_b + ck_a) & 0xFF
    return b"\xb5\x62" + body + bytes((ck_a, ck_b))
