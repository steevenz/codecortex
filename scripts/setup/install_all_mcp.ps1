# scripts/setup/install_all_mcp.ps1
# Universal MCP Installer for CodeCortex MCP Server
# Supports: Windsurf, Trae, AntiGravity, Gemini CLI, Cursor, Claude Desktop, OpenCode, Zed, Kiro, iFlow, Qwen

$ProjectRoot = "~\MCP\mcp-codecortex"

# Common configuration for all tools
$CodecortexConfig = @{
    command = "npx"
    args = @("--yes", "--package", $ProjectRoot, "codecortex")
}

$Targets = @(
    # Windsurf
    @{ Name = "Windsurf"; Path = "$env:USERPROFILE\.codeium\windsurf\mcp_config.json"; Key = "mcpServers" },
    # Trae
    @{ Name = "Trae"; Path = "$env:APPDATA\Trae\User\mcp.json"; Key = "mcpServers" },
    # AntiGravity
    @{ Name = "AntiGravity"; Path = "$env:USERPROFILE\.gemini\antigravity\mcp_config.json"; Key = "mcpServers" },
    # Gemini CLI
    @{ Name = "Gemini CLI"; Path = "$env:USERPROFILE\.gemini\mcp_config.json"; Key = "mcpServers" },
    # Cursor
    @{ Name = "Cursor"; Path = "$env:APPDATA\Cursor\User\globalStorage\heavy-duty-build-it.cursor-chat\mcpServers.json"; Key = "mcpServers" },
    @{ Name = "Cursor (Home)"; Path = "$env:USERPROFILE\.cursor\mcp.json"; Key = "mcpServers" },
    # Claude Desktop
    @{ Name = "Claude Desktop"; Path = "$env:APPDATA\Claude\claude_desktop_config.json"; Key = "mcpServers" },
    @{ Name = "Claude Desktop (Store)"; Path = "~\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json"; Key = "mcpServers" },
    # Claude CLI
    @{ Name = "Claude CLI"; Path = "$env:USERPROFILE\.claude\mcp.json"; Key = "mcpServers" },
    # OpenCode AI Desktop
    @{ Name = "OpenCode AI"; Path = "$env:APPDATA\ai.opencode.desktop\mcp.json"; Key = "mcpServers" },
    # Kimi CLI
    @{ Name = "Kimi CLI"; Path = "$env:USERPROFILE\.kimi\config.toml"; Key = "mcp.servers"; Format = "TOML" },
    # Continue.dev
    @{ Name = "Continue.dev"; Path = "$env:USERPROFILE\.continue\config.yaml"; Key = "mcpServers"; Format = "YAML" },
    # Goose
    @{ Name = "Goose"; Path = "$env:APPDATA\Goose\config.yaml"; Key = "mcpServers"; Format = "YAML" },
    # Zed IDE
    @{ Name = "Zed IDE"; Path = "$env:APPDATA\Zed\settings.json"; Key = "context_servers" },
    # Kiro IDE
    @{ Name = "Kiro IDE"; Path = "$env:USERPROFILE\.kiro\settings\mcp.json"; Key = "mcpServers" },
    # iFlow
    @{ Name = "iFlow"; Path = "$env:USERPROFILE\.iflow\mcp.json"; Key = "mcpServers" },
    # Qwen
    @{ Name = "Qwen"; Path = "$env:USERPROFILE\.qwen\mcp.json"; Key = "mcpServers" }
)

Write-Host "`n  UNIVERSAL CODECORTEX INSTALLER " -BackgroundColor Yellow -ForegroundColor Black
Write-Host "  Project: $ProjectRoot`n" -ForegroundColor Gray

foreach ($Target in $Targets) {
    $Path = $Target.Path
    $Name = $Target.Name
    $Key = $Target.Key
    $Format = $Target.Format

    Write-Host "  Checking $Name... " -NoNewline -ForegroundColor Gray
    
    if (Test-Path $Path) {
        try {
            $configJson = $CodecortexConfig | ConvertTo-Json -Depth 10
            $tempConfigFile = New-TemporaryFile
            $configJson | Set-Content $tempConfigFile.FullName
            
            $fmt = if ($Format) { $Format } else { "JSON" }
            
            # Use Python helper for robust parsing/updating
            python scripts/setup/mcp_config_helper.py "$Path" "$Key" "$($tempConfigFile.FullName)" "$fmt"
            
            Remove-Item $tempConfigFile.FullName -ErrorAction SilentlyContinue
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "[UPDATED]" -ForegroundColor Green
            } else {
                Write-Host "[ERROR]" -ForegroundColor Red
            }
        } catch {
            Write-Host "[ERROR]" -ForegroundColor Red
            Write-Host "    $($_.Exception.Message)" -ForegroundColor DarkRed
        }
    } else {
        # Check if parent directory exists to decide whether to create
        $ParentDir = Split-Path $Path -Parent
        if (Test-Path $ParentDir) {
             Write-Host "[NOT FOUND - CREATING]" -ForegroundColor Yellow
             $json = @{ $Key = @{ "codecortex" = $CodecortexConfig } }
             $json | ConvertTo-Json -Depth 10 | Set-Content $Path
        } else {
             Write-Host "[SKIPPED - APP NOT FOUND]" -ForegroundColor DarkGray
        }
    }
}

Write-Host "`n  INSTALLATION COMPLETE`n" -ForegroundColor Green
Write-Host "  NOTE: You may need to restart your IDEs/CLIs for changes to take effect.`n" -ForegroundColor Gray
