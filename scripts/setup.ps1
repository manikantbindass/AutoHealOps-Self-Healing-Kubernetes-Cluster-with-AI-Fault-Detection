param([switch]$Monitoring)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Install Docker Desktop first.' }
docker info --format '{{.ServerVersion}}' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop, select Linux containers, and wait until the engine is ready.' }
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Replace only blank credential fields, preserving all existing user configuration.
$text = Get-Content .env -Raw
foreach ($key in @('JWT_SECRET','ADMIN_PASSWORD','GRAFANA_ADMIN_PASSWORD')) {
    if ($text -match "(?m)^${key}=\s*$") {
        $bytes = New-Object byte[] 48
        $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
        $rng.GetBytes($bytes); $rng.Dispose()
        $value = [Convert]::ToBase64String($bytes)
        $text = [regex]::Replace($text, "(?m)^${key}=\s*$", "${key}=$value")
    }
}
Set-Content -LiteralPath .env -Value $text
# Never render resolved Compose configuration: it contains credentials.
docker compose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Compose validation failed. Review .env without sharing secrets.' }
& "$PSScriptRoot/start-local.ps1" -Monitoring:$Monitoring
