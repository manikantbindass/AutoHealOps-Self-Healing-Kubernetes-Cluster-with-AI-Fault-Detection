$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (Test-Path .local/processes.json) {
    $processes = Get-Content .local/processes.json -Raw | ConvertFrom-Json
    foreach ($entry in $processes.PSObject.Properties) {
        # Only PIDs recorded by start-native, inspect PID reuse before stopping long-lived sessions.
        $proc = Get-Process -Id $entry.Value -ErrorAction SilentlyContinue
        if ($proc -and $proc.ProcessName -in @('python','node')) { taskkill /PID $entry.Value /T /F | Out-Null }
    }
    Remove-Item -LiteralPath .local/processes.json
}
