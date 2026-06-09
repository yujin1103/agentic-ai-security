param(
  [int]$Port = 58473
)

$ErrorActionPreference = "Stop"
$cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cloudflared) {
  Write-Error "cloudflared not found. Install Cloudflare Tunnel cloudflared first, then rerun this script."
}

Write-Host "Starting Cloudflare Quick Tunnel to http://localhost:$Port"
Write-Host "Use the printed https://*.trycloudflare.com/mcp URL as the remote MCP endpoint."
cloudflared tunnel --url "http://localhost:$Port"
