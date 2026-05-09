"""
mcp.py – Entry point for the CodeCortex code analysis MCP server.
"""

import sys
import os
from pathlib import Path

# Navigate to the mcp-codecortex repo root
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent  # scripts/server -> mcp-codecortex
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.main import mcp


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
