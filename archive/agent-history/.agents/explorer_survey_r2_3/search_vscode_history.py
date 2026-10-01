import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

hist_dir = Path(r"C:\Users\pnt21\AppData\Roaming\Code\User\History")
if not hist_dir.exists():
    print("No history dir")
    sys.exit(0)

found = []
for sub in hist_dir.iterdir():
    if not sub.is_dir():
        continue
    entry_file = sub / "entries.json"
    if entry_file.exists():
        try:
            data = json.loads(entry_file.read_text(encoding="utf-8"))
            resource = data.get("resource", "")
            if any(k in resource.lower() for k in ["zone", "geofence", "cambay", "app.tsx", "flightmap"]):
                found.append((resource, sub, data.get("entries", [])))
                print(f"MATCH: {resource} -> {len(data.get('entries', []))} revisions in {sub}")
        except Exception as e:
            pass

print(f"\nTotal matched resources: {len(found)}")
