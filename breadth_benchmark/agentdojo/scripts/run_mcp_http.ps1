param(
  [string]$HostName = "127.0.0.1",
  [int]$Port = 58473,
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
if ($HostName -eq "127.0.0.1" -and $Port -eq 58473) {
  & $Python mcp_server.py
} else {
  & $Python mcp_server.py --transport http --host $HostName --port $Port
}
