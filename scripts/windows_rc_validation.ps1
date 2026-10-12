$ErrorActionPreference='Stop'
function Assert($condition,$message){ if(-not $condition){ throw $message } }
Write-Host "Enterprise OTP RC target-host validation" -ForegroundColor Cyan

$appPort=3000; $apiPort=8000; $n8nPort=5678
$runtimePorts=Join-Path (Split-Path $PSScriptRoot -Parent) 'logs\runtime_ports.env'
if(Test-Path $runtimePorts){
  foreach($line in Get-Content $runtimePorts){
    if($line -match '^APP_HOST_PORT=(\d+)$'){ $appPort=[int]$Matches[1] }
    if($line -match '^API_HOST_PORT=(\d+)$'){ $apiPort=[int]$Matches[1] }
    if($line -match '^N8N_HOST_PORT=(\d+)$'){ $n8nPort=[int]$Matches[1] }
  }
}

$ready=Invoke-RestMethod ("http://localhost:{0}/api/v1/health/ready" -f $apiPort) -TimeoutSec 10
Assert ($ready.status -eq 'ready') 'API readiness failed'
$version=Invoke-RestMethod ("http://localhost:{0}/api/v1/health/version" -f $apiPort) -TimeoutSec 10
Assert ($version.version -eq '2.4.0-rc.3-hotfix7') "Unexpected API version: $($version.version)"

$front=Invoke-WebRequest -UseBasicParsing ("http://localhost:{0}" -f $appPort) -TimeoutSec 10
Assert ($front.StatusCode -eq 200) 'Frontend health failed'
$n8n=Invoke-WebRequest -UseBasicParsing ("http://localhost:{0}/healthz" -f $n8nPort) -TimeoutSec 10
Assert ($n8n.StatusCode -eq 200) "n8n health failed on host port $n8nPort"

$body='username=analyst%40otp.local&password=Demo-Analyst-2026%21'
$login=Invoke-RestMethod -Method Post -Uri ("http://localhost:{0}/api/v1/auth/login" -f $apiPort) -ContentType 'application/x-www-form-urlencoded' -Body $body -TimeoutSec 10
Assert ($login.access_token) 'Analyst login failed'
$h=@{Authorization="Bearer $($login.access_token)"}

$dash=Invoke-RestMethod ("http://localhost:{0}/api/v1/dashboard" -f $apiPort) -Headers $h -TimeoutSec 10
Assert ($dash.kpis.entities_monitored -ge 5) 'Unexpected entity count'
$de=$dash.entities | Where-Object {$_.entity_code -eq 'DE01'}
Assert ($de) 'DE01 missing from dashboard'
Assert ([Math]::Abs([double]$de.actual - 0.0231) -lt 0.000001) "DE01 actual ROS mismatch: $($de.actual)"
Assert ([Math]::Abs([double]$de.target - 0.04) -lt 0.000001) "DE01 target mismatch: $($de.target)"
Assert ([Math]::Abs([double]$de.suggested_adjustment - 1891110) -lt 0.01) "DE01 true-up mismatch: $($de.suggested_adjustment)"

$base=("http://localhost:{0}/api/v1" -f $apiPort)
$null=Invoke-RestMethod "$base/policies" -Headers $h -TimeoutSec 10
$null=Invoke-RestMethod "$base/mappings" -Headers $h -TimeoutSec 10
$null=Invoke-RestMethod "$base/allocations/rules" -Headers $h -TimeoutSec 10
$null=Invoke-RestMethod "$base/forecasts/DE01?fiscal_year=2026" -Headers $h -TimeoutSec 10
$null=Invoke-RestMethod "$base/data-quality" -Headers $h -TimeoutSec 10
$null=Invoke-RestMethod "$base/system-health" -Headers $h -TimeoutSec 10

Write-Host ("[PASS] API:{0}, frontend:{1}, n8n:{2}, authentication and DE01 golden controls validated." -f $apiPort,$appPort,$n8nPort) -ForegroundColor Green
