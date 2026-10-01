import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

search_roots = [
    Path(r"c:\Users\pnt21\OneDrive\Máy tính\IOT"),
    Path(r"c:\Users\pnt21\OneDrive\Máy tính"),
    Path(r"c:\Users\pnt21\Downloads"),
    Path(r"c:\Users\pnt21\Documents"),
]

keywords = ["zone", "cambay", "cam_bay", "geofence", "nofly", "no_fly", "cam bay", "vung cam"]

found_files = []

for root in search_roots:
    if not root.exists():
        continue
    print(f"Scanning {root}...")
    for dirpath, dirnames, filenames in os.walk(root):
        # skip heavy dirs
        if any(ignored in dirpath.lower() for ignored in ["node_modules", ".venv", ".venv310", ".venv_new", ".git"]):
            continue
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            lower_name = f.lower()
            p = Path(dirpath) / f
            matched = False
            if ext in [".geojson", ".kml", ".gpx"]:
                matched = True
            elif any(k in lower_name for k in keywords):
                matched = True
            
            if matched:
                try:
                    sz = p.stat().st_size
                    found_files.append((p, sz))
                    print(f"MATCH: {p} ({sz} bytes)")
                except Exception as e:
                    pass

print(f"\nTotal matches: {len(found_files)}")
