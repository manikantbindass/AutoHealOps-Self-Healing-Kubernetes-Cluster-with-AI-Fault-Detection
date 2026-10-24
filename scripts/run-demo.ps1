param([ValidateSet('cpu','memory','restarts','latency','reset')][string]$Scenario='cpu',[int]$BackendPort=8000,[int]$DashboardPort=3000)
$ErrorActionPreference = 'Stop'
$body = @{scenario=$Scenario} | ConvertTo-Json
$result = Invoke-RestMethod -Method Post -Uri "http://localhost:$BackendPort/api/v1/demo/scenarios" -ContentType 'application/json' -Body $body
Write-Host "Scenario submitted. Mode: $($result.mode). Open http://localhost:$DashboardPort/healing to review, approve, resume and simulate recovery."
