param([int]$TimeoutSeconds = 90,[int]$BackendPort=8000,[int]$AiPort=8001,[int]$DashboardPort=3000)
$ErrorActionPreference = 'Stop'
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
foreach ($url in @("http://localhost:$BackendPort/health/ready","http://localhost:$AiPort/health/live","http://localhost:$DashboardPort")) {
    $ready = $false
    while ((Get-Date) -lt $deadline) {
        try { $response = Invoke-WebRequest -Uri $url -TimeoutSec 5 -UseBasicParsing; if ($response.StatusCode -eq 200) { $ready = $true; break } } catch {}
        Start-Sleep -Seconds 2
    }
    if (-not $ready) { throw "Health check timed out: $url. Inspect docker compose logs --tail 100." }
    Write-Host "Healthy: $url"
}
