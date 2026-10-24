param([switch]$Monitoring)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path .env)) { throw 'Run ./scripts/setup.ps1 first.' }
if ($Monitoring) {
    $line = Get-Content .env | Where-Object { $_ -match '^GRAFANA_ADMIN_PASSWORD=.+$' }
    if (-not $line) { throw 'Set a random GRAFANA_ADMIN_PASSWORD or run setup.ps1.' }
    docker compose --profile monitoring up --build -d --wait --wait-timeout 240
} else {
    docker compose up --build -d --wait --wait-timeout 240
}
if ($LASTEXITCODE -ne 0) { throw 'Startup failed. Run docker compose ps and docker compose logs --tail 100.' }
& "$PSScriptRoot/health-check.ps1"
Write-Host 'Dashboard: http://localhost:3000 | API docs: http://localhost:8000/docs | AI docs: http://localhost:8001/docs'
if ($Monitoring) { Write-Host 'Prometheus: http://localhost:9090 | Grafana: http://localhost:3001 (password stored privately in .env)' }
