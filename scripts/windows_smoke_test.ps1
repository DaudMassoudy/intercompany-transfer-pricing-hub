param([int]$ApiPort = 8000, [int]$AppPort = 3000)
$health=Invoke-RestMethod ("http://localhost:{0}/api/v1/health/ready" -f $ApiPort) -TimeoutSec 5
if($health.status -ne 'ready'){exit 1}
$front=Invoke-WebRequest -UseBasicParsing ("http://localhost:{0}" -f $AppPort) -TimeoutSec 5
if($front.StatusCode -ne 200){exit 1}
$body='username=analyst%40otp.local&password=Demo-Analyst-2026%21'
$login=Invoke-RestMethod -Method Post -Uri ("http://localhost:{0}/api/v1/auth/login" -f $ApiPort) -ContentType 'application/x-www-form-urlencoded' -Body $body -TimeoutSec 5
if(-not $login.access_token){exit 1}
$headers=@{Authorization="Bearer $($login.access_token)"}
$dash=Invoke-RestMethod ("http://localhost:{0}/api/v1/dashboard" -f $ApiPort) -Headers $headers -TimeoutSec 5
if($dash.kpis.entities_monitored -lt 5){exit 1}
Write-Host "Smoke test PASS - $($dash.kpis.entities_monitored) entities; frontend $AppPort; API $ApiPort"
