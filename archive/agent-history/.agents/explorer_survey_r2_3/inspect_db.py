import sqlite3
import json

conn = sqlite3.connect('backend/data/drone.sqlite3')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print('Tables:', tables)
for t in tables:
    name = t[0]
    cur.execute(f"SELECT count(*) FROM {name}")
    print(f'{name}: {cur.fetchone()[0]} rows')

cur.execute("SELECT * FROM map_sync")
print('map_sync:', cur.fetchall())
conn.close()
