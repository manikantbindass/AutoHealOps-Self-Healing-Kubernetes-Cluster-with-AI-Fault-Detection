param([switch]$Install,[int]$BackendPort=8000,[int]$AiPort=8001,[int]$DashboardPort=3000)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
if ($Install) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 virtual environment creation failed.' }
    & ./.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    Push-Location frontend
    try { npm.cmd ci --no-audit --no-fund; if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' }; npm.cmd run build; if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' } } finally { Pop-Location }
}
$python = Join-Path $root '.venv/Scripts/python.exe'
if (-not (Test-Path $python)) { throw 'Run ./scripts/start-native.ps1 -Install first (Python 3.12 required).' }
New-Item -ItemType Directory -Force .local | Out-Null
foreach ($port in @($BackendPort,$AiPort,$DashboardPort)) {
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$port)
    try { $listener.Start() } catch { throw "Port $port is unavailable. Choose alternate -BackendPort, -AiPort and -DashboardPort values." } finally { $listener.Stop() }
}
$env:MODE='demo'; $env:ENVIRONMENT='development'; $env:MONGO_URI=''; $env:DRY_RUN='true'; $env:ALLOW_AUTOMATIC='false'; $env:HEALING_MODE='manual'
$env:BACKEND_PORT="$BackendPort"; $env:DASHBOARD_PORT="$DashboardPort"; $env:ORIGINS="http://localhost:$DashboardPort,http://127.0.0.1:$DashboardPort"; $env:AI_URL="http://127.0.0.1:$AiPort"; $env:SQLITE_PATH=(Join-Path $root 'data/autohealops.sqlite')
Remove-Item Env:REACT_APP_API_URL -ErrorAction SilentlyContinue; $env:BROWSER='none'; $env:HOST='127.0.0.1'
$backend = Start-Process -FilePath $python -ArgumentList '-m','uvicorn','main:app','--host','127.0.0.1','--port',"$BackendPort" -WorkingDirectory (Join-Path $root 'backend') -RedirectStandardOutput (Join-Path $root '.local/backend.log') -RedirectStandardError (Join-Path $root '.local/backend-error.log') -WindowStyle Hidden -PassThru
$ai = Start-Process -FilePath $python -ArgumentList '-m','uvicorn','main:app','--host','127.0.0.1','--port',"$AiPort" -WorkingDirectory (Join-Path $root 'ai-engine') -RedirectStandardOutput (Join-Path $root '.local/ai.log') -RedirectStandardError (Join-Path $root '.local/ai-error.log') -WindowStyle Hidden -PassThru
$web = Start-Process -FilePath 'node.exe' -ArgumentList 'scripts/serve-preview.cjs' -WorkingDirectory $root -RedirectStandardOutput (Join-Path $root '.local/frontend.log') -RedirectStandardError (Join-Path $root '.local/frontend-error.log') -WindowStyle Hidden -PassThru
@{backend=$backend.Id;ai=$ai.Id;frontend=$web.Id} | ConvertTo-Json | Set-Content .local/processes.json
& "$PSScriptRoot/health-check.ps1" -TimeoutSeconds 180 -BackendPort $BackendPort -AiPort $AiPort -DashboardPort $DashboardPort
Write-Host "Native demo: http://localhost:$DashboardPort | API: http://localhost:$BackendPort/docs | AI: http://localhost:$AiPort/docs. Logs: .local/."
