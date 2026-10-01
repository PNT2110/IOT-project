import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

brain_dir = Path(r"C:\Users\pnt21\.gemini\antigravity\brain")

matches = []
for dirpath, dirnames, filenames in os.walk(brain_dir):
    for f in filenames:
        if f.endswith(('.json', '.md', '.txt', '.ts', '.py')):
            p = Path(dirpath) / f
            try:
                content = p.read_text(encoding='utf-8', errors='replace')
                if any(kw in content.lower() for kw in ['cambay', 'vùng cấm bay', 'cam_bay', 'zones.geojson', 'nofly']):
                    matches.append((str(p), len(content)))
                    print(f"FOUND: {p} ({len(content)} chars)")
            except:
                pass

print(f"\nTotal matches in brain: {len(matches)}")
