@echo off
REM CodeCortex Plugin Hook Runner
REM Usage: run-hook.cmd session-start

setlocal enabledelayedexpansion

set "PLUGIN_ROOT=%~dp0.."
set "HOOK_NAME=%1"

if "%HOOK_NAME%"=="session-start" (
  rem Use bash if available (Git Bash, WSL), otherwise skip
  where bash >nul 2>nul
  if !errorlevel! equ 0 (
    bash "%PLUGIN_ROOT%\hooks\session-start"
    exit /b !errorlevel!
  )
  rem No bash available - output directly
  echo {"additionalContext": "CodeCortex available. Use `/codecortex` to load skills."}
  exit /b 0
)

exit /b 1
