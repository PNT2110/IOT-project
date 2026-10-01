import sqlite3
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

db_path = r"C:\Users\pnt21\.gemini\antigravity\conversations\f3494b39-4376-4d6c-b848-91bef7f31ff1.db"
conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
cur = conn.cursor()

cur.execute("SELECT step_payload FROM steps")
for row in cur.fetchall():
    data = row[0]
    if isinstance(data, bytes):
        # find printable strings
        text = data.decode('utf-8', errors='ignore')
        for match in re.findall(r'[A-Za-z0-9_/\.\-]{4,}', text):
            if any(k in match.lower() for k in ['zone', 'cambay', 'geojson', 'geofence']):
                print("Match:", match)
        for line in text.splitlines():
            if any(k in line.lower() for k in ['cambay', 'zones.geojson', 'flight-zones']):
                print("Line:", line[:120])
conn.close()
