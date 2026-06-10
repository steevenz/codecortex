"""
@project   CodeCortex
@package   modules.idegraph.utils
@author    Steeven Andrian
@copyright (c) 2026 Aegis Codework
:package:  modules.idegraph.utils
:standard: Aegis-IdeGraph-v1.0

DB Explorer — Explore VSCode-style SQLite storage.
"""

import sqlite3
import json
import sys
import os
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

def dump_vscdb(db_path: str) -> None:
    """
    Explore the content of a vscdb (SQLite) file and print interesting keys.
    """
    logger.info(f"Exploring database: {db_path}")
    
    if not os.path.exists(db_path):
        logger.error(f"Database file does not exist: {db_path}")
        return

    try:
        # Use URI for read-only access to avoid locking issues
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
            cursor = conn.cursor()

            # Check for ItemTable (standard VSCode storage table)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ItemTable'")
            if not cursor.fetchone():
                logger.warning("ItemTable not found in database. Listing available tables:")
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                for row in cursor.fetchall():
                    print(f"  - {row[0]}")
                return

            cursor.execute("SELECT key, value FROM ItemTable")
            rows = cursor.fetchall()
            logger.info(f"Found {len(rows)} entries in ItemTable")

            for key, value in rows:
                # Filter for interesting keys related to AI interactions
                if any(term in key.lower() for term in ['chat', 'conversation', 'agent', 'composer', 'history', 'ai', 'session', 'trae']):
                    print(f"\nKEY: {key}")
                    try:
                        data = json.loads(value)
                        if isinstance(data, list) and len(data) > 5:
                            print(f"VALUE: List of {len(data)} items. Preview: {json.dumps(data[0], indent=2)[:500]}...")
                        elif isinstance(data, dict):
                            print(f"VALUE: Dict with keys: {list(data.keys())}")
                            print(f"PREVIEW: {json.dumps(data, indent=2)[:1000]}")
                        else:
                            print(f"VALUE: {json.dumps(data, indent=2)[:1000]}")
                    except (json.JSONDecodeError, TypeError):
                        # Not JSON, show raw preview
                        preview = str(value)[:1000]
                        print(f"VALUE (raw): {preview}...")
    except Exception as e:
        logger.error(f"Failed to explore database {db_path}: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        dump_vscdb(sys.argv[1])
    else:
        print("Usage: python -m src.utils.db_explorer <path_to_vscdb>")
