Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
uv venv
uv pip install -r requirements.txt
Write-Host "[OK] uv environment ready"
Write-Host "Run: uv run python mcp_server.py"
