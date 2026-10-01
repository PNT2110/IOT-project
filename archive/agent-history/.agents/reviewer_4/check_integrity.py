import pynmea2
import re

content = open("tests/conftest.py").read()
sentences = re.findall(r'(\$[A-Z]{5},[^*]+\*[0-9A-Fa-f]{2})', content)
print(f"Found {len(sentences)} NMEA sentences in conftest.py:")
for s in sentences:
    try:
        parsed = pynmea2.parse(s, check=True)
        print(f"  VALID: {s} -> {parsed.sentence_type}")
    except Exception as e:
        print(f"  INVALID: {s} -> {e}")

autodetect_content = open("tests/test_serial_autodetect.py").read()
auto_sentences = re.findall(r'(\$[A-Z]{5},[^*]+\*[0-9A-Fa-f]{2})', autodetect_content)
print(f"Found {len(auto_sentences)} NMEA sentences in test_serial_autodetect.py:")
for s in auto_sentences:
    try:
        parsed = pynmea2.parse(s, check=True)
        print(f"  VALID: {s} -> {parsed.sentence_type}")
    except Exception as e:
        print(f"  INVALID: {s} -> {e}")
