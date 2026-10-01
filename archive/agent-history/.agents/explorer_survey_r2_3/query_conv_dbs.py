import sqlite3
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

conv_dir = r"C:\Users\pnt21\.gemini\antigravity\conversations"

for fname in os.listdir(conv_dir):
    if fname.endswith(".db"):
        db_path = os.path.join(conv_dir, fname)
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cur.fetchall()]
            for tbl in tables:
                cur.execute(f"PRAGMA table_info({tbl})")
                cols = [c[1] for c in cur.fetchall()]
                for col in cols:
                    query = f"SELECT {col} FROM {tbl} WHERE {col} LIKE '%zones.geojson%' OR {col} LIKE '%cambay%' OR {col} LIKE '%rawName%'"
                    try:
                        cur.execute(query)
                        rows = cur.fetchall()
                        for r in rows:
                            text = str(r[0])
                            # find snippets
                            for line in text.splitlines():
                                if any(k in line.lower() for k in ['zone', 'cambay', 'rawname', 'prohibited', 'restricted', 'geojson']):
                                    print(f"[{fname}:{tbl}.{col}] {line[:120]}")
                    except Exception:
                        pass
            conn.close()
        except Exception:
            pass
