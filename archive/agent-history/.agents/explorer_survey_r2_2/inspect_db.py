import sqlite3

conn = sqlite3.connect('backend/data/drone.sqlite3')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute(SELECT name FROM sqlite_master WHERE type='table';)
tables = [row['name'] for row in cur.fetchall()]
print('Tables:', tables)
for name in tables:
    cur.execute(fSELECT count(*) as c FROM {name})
    count = cur.fetchone()['c']
    print(fTable {name}: {count} rows)
    cur.execute(fSELECT * FROM {name} LIMIT 3)
    for r in cur.fetchall():
        print(' ', dict(r))
