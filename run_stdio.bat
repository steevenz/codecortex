@echo off
cd /d "C:\Users\steevenz\MCP\mcp-codecortex"
set CODECORTEX_TRANSPORT=stdio
call uv run python -m src.main