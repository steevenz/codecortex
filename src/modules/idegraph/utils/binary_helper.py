"""
@project   CodeCortex
@package   modules.idegraph.utils
@author    Steeven Andrian
@copyright (c) 2026 CODDY Codework
:package:  modules.idegraph.utils
:standard: CODDY-IdeGraph-v1.0

Binary helper — Find readable strings in binary files.
"""

import sys
from typing import Optional
from src.modules.idegraph.core.logging_service import get_logger

logger = get_logger(__name__)

def find_strings(file_path: str, min_len: int = 10) -> None:
    """
    Find readable strings in a binary file (similar to the 'strings' utility).
    Useful for diagnostic analysis of locked or proprietary database files.
    """
    try:
        with open(file_path, 'rb') as f:
            data = f.read(1024 * 1024) # Read first MB for analysis
            s = ""
            for b in data:
                if 32 <= b <= 126:
                    s += chr(b)
                else:
                    if len(s) >= min_len:
                        print(s)
                    s = ""
    except Exception as e:
        logger.error(f"Error reading binary file {file_path}: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        find_strings(sys.argv[1])
    else:
        print("Usage: python -m src.utils.binary_helper <file_path>")
