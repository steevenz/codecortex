import sqlite3
conn = sqlite3.connect('database/codecortex.db')
for table in ['symbols', 'files']:
    schema = conn.execute(f"PRAGMA table_info({table})").fetchall()
    print(f"{table}: {[s[1] for s in schema]}")