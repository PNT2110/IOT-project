import pynmea2
import sys

line1 = "$GNGGA,123519.00,1046.1234,N,10640.5678,E,1,08,0.9,15.4,M,0.0,M,,*4A"
line2 = "$GNRMC,123519.00,A,1046.1234,N,10640.5678,E,0.22,120.5,090926,,,A*7B"
valid_line = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"

print("Parsing valid_line...")
msg_valid = pynmea2.parse(valid_line)
print("valid_line ok:", msg_valid)

print("Parsing line1...")
try:
    msg1 = pynmea2.parse(line1, check=True)
    print("line1 check=True ok:", msg1)
except Exception as e:
    print("line1 check=True failed:", type(e), e)

print("Parsing line2...")
try:
    msg2 = pynmea2.parse(line2, check=True)
    print("line2 check=True ok:", msg2)
except Exception as e:
    print("line2 check=True failed:", type(e), e)
