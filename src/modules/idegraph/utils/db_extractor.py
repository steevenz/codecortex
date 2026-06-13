"""
@project   CodeCortex
@package   modules.idegraph.utils
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.utils
:standard: CODDY-IdeGraph-v1.0

DB Extractor — Extract specific keys from SQLite storage.
"""

import sqlite3
import json
import sys
import os
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

def extract_key(db_path: str, key_name: str, out_path: str) -> None:
    """
    Extract a specific value from the ItemTable and save it to a file.
    """
    if not os.path.exists(db_path):
        logger.error(f"Database file does not exist: {db_path}")
        return

    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM ItemTable WHERE key = ?", (key_name,))
            row = cursor.fetchone()

            if row:
                val = row[0]
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(val)
                logger.info(f"Successfully extracted key '{key_name}' to {out_path}")
            else:
                logger.warning(f"Key '{key_name}' not found in ItemTable")
    except Exception as e:
        logger.error(f"Failed to extract key '{key_name}' from {db_path}: {e}")

if __name__ == "__main__":
    if len(sys.argv) == 4:
        extract_key(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Usage: python -m src.utils.db_extractor <db_path> <key_name> <output_path>")
