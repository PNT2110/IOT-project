import pynmea2

c1 = "GNGGA,123519.00,1046.1234,N,10640.5678,E,1,08,0.9,15.4,M,0.0,M,,"
c2 = "GNRMC,123519.00,A,1046.1234,N,10640.5678,E,0.22,120.5,090926,,,A"
x1 = 0
for c in c1:
    x1 ^= ord(c)
x2 = 0
for c in c2:
    x2 ^= ord(c)

s1 = f"${c1}*{x1:02X}"
s2 = f"${c2}*{x2:02X}"
print("s1:", s1)
print("s2:", s2)

m1 = pynmea2.parse(s1, check=True)
m2 = pynmea2.parse(s2, check=True)
print("Parsed m1:", m1)
print("Parsed m2:", m2)
