import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

agent_dir = Path(r"c:\Users\pnt21\OneDrive\Máy tính\IOT\.agents")

results = []

for dirpath, dirnames, filenames in os.walk(agent_dir):
    for f in filenames:
        if f.endswith(('.md', '.py', '.json', '.txt')):
            p = Path(dirpath) / f
            try:
                text = p.read_text(encoding='utf-8', errors='replace')
                for i, line in enumerate(text.splitlines()):
                    lower = line.lower()
                    if any(k in lower for k in ['cấm bay', 'zones.geojson', 'geofence', 'cambay', 'layer_id']):
                        results.append((str(p.relative_to(agent_dir)), i+1, line.strip()))
            except Exception as e:
                pass

print(f"Total occurrences found in .agents: {len(results)}")
for path, line_no, content in results[:60]:
    print(f"{path}:{line_no} -> {content[:100]}")
if len(results) > 60:
    print(f"... and {len(results)-60} more")
