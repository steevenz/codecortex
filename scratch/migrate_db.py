import sqlite3
import os
from pathlib import Path

def backup_db(source_path, dest_path):
    print(f"Backing up {source_path} to {dest_path}...")
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    src_conn = sqlite3.connect(source_path)
    dest_conn = sqlite3.connect(dest_path)
    
    with dest_conn:
        src_conn.backup(dest_conn)
    
    dest_conn.close()
    src_conn.close()
    print("Backup complete.")

if __name__ == "__main__":
    src = r"c:\Users\steevenz\.aicoders\scripts\pythons\codecortex\database\codecortex.db"
    dst = r"c:\Users\steevenz\.aicoders\scripts\pythons\codecortex\data\storage\codecortex.db"
    try:
        backup_db(src, dst)
    except Exception as e:
        print(f"Error during backup: {e}")
