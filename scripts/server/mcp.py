"""
mcp.py – Entry point for the CodeCortex code analysis MCP server.
"""

import sys
from pathlib import Path

src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.main import mcp


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
