$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose --profile monitoring down
if ($LASTEXITCODE -ne 0) { throw 'Docker shutdown failed.' }
Write-Host 'Stopped. Persistent volumes retained.'
