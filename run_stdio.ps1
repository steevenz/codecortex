Set-Location "C:\Users\steevenz\MCP\mcp-codecortex"
$env:CODECORTEX_TRANSPORT = "stdio"
& uv run python -m src.main