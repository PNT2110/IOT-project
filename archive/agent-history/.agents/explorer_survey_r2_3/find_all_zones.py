import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

roots = [
    Path(r"c:\Users\pnt21"),
    Path(r"D:"),
]

exclude_parts = ["node_modules", ".venv", ".venv310", ".venv_new", ".git", "appdata", "AppData"]

matches = []

for root in roots:
    print(f"Walking {root}...")
    for dirpath, dirnames, filenames in os.walk(root):
        if any(ex in dirpath for ex in exclude_parts):
            continue
        for f in filenames:
            lower = f.lower()
            if any(term in lower for term in ["zone", "cambay", "geofence", "geojson", "no_fly", "nofly", "fly"]):
                full_path = Path(dirpath) / f
                try:
                    sz = full_path.stat().st_size
                    matches.append((str(full_path), sz))
                    print(f"FOUND: {full_path} ({sz} bytes)")
                except:
                    pass

print(f"\nFound {len(matches)} matches.")
