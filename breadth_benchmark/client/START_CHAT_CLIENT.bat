@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"

echo [1/3] Preparing uv virtual environment...
if not exist ".venv" (
  uv venv
  if errorlevel 1 goto :error
)

echo [2/3] Installing requirements...
uv pip install -r requirements.txt
if errorlevel 1 goto :error

echo [3/3] Starting MCP API chat client...
uv run python scripts\chat_mcp_api.py
set EXITCODE=%ERRORLEVEL%
echo.
echo Chat client exited with code %EXITCODE%.
echo Logs remain in the runs folder. Press any key to close this window.
pause >nul
exit /b %EXITCODE%

:error
echo.
echo Setup failed. Press any key to close this window.
pause >nul
exit /b 1
