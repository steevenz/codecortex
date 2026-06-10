"""Check DB schema"""
import sqlite3
conn = sqlite3.connect('database/codecortex.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print('Tables:')
for t in tables:
    cols = conn.execute(f"PRAGMA table_info({t[0]})").fetchall()
    print(f'  {t[0]}: {len(cols)} cols -> {[c[1] for c in cols]}')
conn.close()
