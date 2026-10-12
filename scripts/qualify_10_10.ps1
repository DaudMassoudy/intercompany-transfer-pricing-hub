$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$results = Join-Path $root 'qualification\results'
New-Item -ItemType Directory -Force -Path $results | Out-Null
Get-ChildItem $results -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

function Write-Status([string]$name,[string]$value) {
  Set-Content -Path (Join-Path $results $name) -Value $value -Encoding ascii
}
function Step([string]$text) { Write-Host "`n=== $text ===" -ForegroundColor Cyan }
function Test-HttpOk([string]$url,[int]$timeoutSeconds=3) {
  try {
    $r=Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec $timeoutSeconds
    return ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400)
  } catch { return $false }
}
function Get-ApiVersion([string]$url,[int]$timeoutSeconds=3) {
  try {
    $r=Invoke-RestMethod -Uri $url -TimeoutSec $timeoutSeconds
    return [string]$r.version
  } catch { return $null }
}
function Read-RuntimePorts {
  $p=@{}
  if (Test-Path 'logs\runtime_ports.env') {
    Get-Content 'logs\runtime_ports.env' | ForEach-Object {
      if ($_ -match '^([^=]+)=(.+)$') { $p[$matches[1]]=$matches[2] }
    }
  }
  return $p
}
function Get-ComposePort([string]$service,[int]$containerPort) {
  try {
    $line = (& docker compose port $service $containerPort 2>$null | Select-Object -First 1)
    if ($line -match ':(\d+)\s*$') { return $matches[1] }
  } catch {}
  return $null
}
function Resolve-RuntimePorts {
  $p=Read-RuntimePorts
  if (-not $p['APP_HOST_PORT']) { $p['APP_HOST_PORT']=Get-ComposePort 'otp-frontend' 3000 }
  if (-not $p['API_HOST_PORT']) { $p['API_HOST_PORT']=Get-ComposePort 'otp-api' 8000 }
  if (-not $p['N8N_HOST_PORT']) { $p['N8N_HOST_PORT']=Get-ComposePort 'otp-n8n' 5678 }
  if (-not $p['MINIO_CONSOLE_HOST_PORT']) { $p['MINIO_CONSOLE_HOST_PORT']=Get-ComposePort 'otp-minio' 9001 }
  return $p
}
function Set-ComposeFallbacks {
  # Qualification-only containers do not consume these application secrets,
  # but Compose parses the base file before --no-deps is applied. Supplying
  # non-secret placeholders prevents noisy blank-variable warnings when a
  # healthy runtime is reused after .env has intentionally been removed.
  $defaults=@{
    'OTP_DB_PASSWORD'='qualification-not-used'
    'MINIO_ROOT_USER'='qualification-not-used'
    'MINIO_ROOT_PASSWORD'='qualification-not-used'
    'N8N_INTEGRATION_KEY'='qualification-not-used'
    'N8N_ENCRYPTION_KEY'='qualification-not-used'
  }
  foreach($k in $defaults.Keys) {
    if (-not (Test-Path "Env:$k")) { Set-Item -Path "Env:$k" -Value $defaults[$k] }
  }
}
function Write-ReleaseEvidence([string]$status) {
  $raw = Join-Path $results 'release-validation.txt'
  $tail = @()
  if (Test-Path $raw) { $tail = Get-Content $raw | Select-Object -Last 30 }
  $doc = @(
    '# Release Validation Report — v2.4.0-rc.3-hotfix7',
    '',
    "QUALIFICATION_STATUS: $status",
    '',
    "- Local release/package validation: **$status**",
    '- Raw execution evidence: `qualification/results/release-validation.txt`',
    '',
    '### Validation execution tail',
    '```text'
  ) + $tail + @('```','')
  Set-Content -Path (Join-Path $root 'docs\VALIDATION_REPORT.md') -Value $doc -Encoding utf8
}
function Sync-ReleaseEvidence {
  try {
    $loginBody = @{username='demo.admin@otp.local';password='Demo-OTP-2026!'}
    $login = Invoke-RestMethod -Method Post -Uri "http://localhost:$($env:API_HOST_PORT)/api/v1/auth/login" -ContentType 'application/x-www-form-urlencoded' -Body $loginBody
    $headers=@{Authorization="Bearer $($login.access_token)"}
    Invoke-RestMethod -Method Post -Uri "http://localhost:$($env:API_HOST_PORT)/api/v1/qualification/sync-release-evidence" -Headers $headers | Out-Null
    return $true
  } catch {
    Write-Host "[WARN] Could not synchronize Qualification Center: $($_.Exception.Message)" -ForegroundColor Yellow
    return $false
  }
}

Step '1/7 Verify or reuse the real Docker application'
$env:OTP_NO_BROWSER='1'
$env:OTP_NO_PAUSE='1'
$ports=Resolve-RuntimePorts
$reuse=$false
if ($ports['APP_HOST_PORT'] -and $ports['API_HOST_PORT']) {
  $appUrl="http://localhost:$($ports['APP_HOST_PORT'])"
  $apiReady="http://localhost:$($ports['API_HOST_PORT'])/api/v1/health/ready"
  Write-Host "[INFO] Checking existing application: $appUrl"
  Write-Host "[INFO] Checking existing API:         $apiReady"
  if ((Test-HttpOk $appUrl) -and (Test-HttpOk $apiReady)) {
    $expectedVersion=(Get-Content (Join-Path $root 'VERSION.txt') -Raw).Trim()
    $runtimeVersion=Get-ApiVersion "http://localhost:$($ports['API_HOST_PORT'])/api/v1/health/version"
    if ($runtimeVersion -eq $expectedVersion) {
      $reuse=$true
      Write-Host "[PASS] Existing OTP runtime is healthy and version-matched ($runtimeVersion). Reusing it; no rebuild/restart is required." -ForegroundColor Green
    } else {
      Write-Host "[INFO] Healthy runtime is version '$runtimeVersion' but Hotfix 7 requires '$expectedVersion'. Rebuilding the current release." -ForegroundColor Yellow
    }
  }
}

if (-not $reuse) {
  Write-Host '[INFO] No reusable healthy runtime was detected.' -ForegroundColor Yellow
  Write-Host '[INFO] Starting the application. Docker build progress will remain visible in this window.' -ForegroundColor Yellow
  $env:OTP_SHOW_BUILD_PROGRESS='1'
  cmd /c START_DEMO.bat
  $startRc=$LASTEXITCODE
  Remove-Item Env:OTP_SHOW_BUILD_PROGRESS -ErrorAction SilentlyContinue
  if ($startRc -ne 0) {
    Write-Status 'runtime-startup.status' 'FAIL'
    Write-Status 'frontend-runtime.status' 'FAIL'
    Write-Host '[FAIL] Application startup failed. See logs\launcher.log.' -ForegroundColor Red
    exit 1
  }
  $ports=Resolve-RuntimePorts
  if (-not $ports['APP_HOST_PORT'] -or -not $ports['API_HOST_PORT']) {
    Write-Status 'runtime-startup.status' 'FAIL'
    Write-Status 'frontend-runtime.status' 'FAIL'
    Write-Host '[FAIL] Startup completed but runtime ports could not be resolved.' -ForegroundColor Red
    exit 1
  }
  $appUrl="http://localhost:$($ports['APP_HOST_PORT'])"
  $apiReady="http://localhost:$($ports['API_HOST_PORT'])/api/v1/health/ready"
  if (-not ((Test-HttpOk $appUrl) -and (Test-HttpOk $apiReady))) {
    Write-Status 'runtime-startup.status' 'FAIL'
    Write-Status 'frontend-runtime.status' 'FAIL'
    Write-Host '[FAIL] Runtime did not pass the post-start HTTP/API health verification.' -ForegroundColor Red
    exit 1
  }
}

Write-Status 'runtime-startup.status' 'PASS'
Write-Status 'frontend-runtime.status' 'PASS'
$env:APP_HOST_PORT = $ports['APP_HOST_PORT']
$env:API_HOST_PORT = $ports['API_HOST_PORT']
$env:N8N_HOST_PORT = $ports['N8N_HOST_PORT']
$env:MINIO_CONSOLE_HOST_PORT = $ports['MINIO_CONSOLE_HOST_PORT']
Set-ComposeFallbacks
Write-Host "Application: http://localhost:$($env:APP_HOST_PORT)"
Write-Host "API:         http://localhost:$($env:API_HOST_PORT)/api/v1"

$compose=@('-f','docker-compose.yml','-f','docker-compose.qualification.yml','--profile','qualification')

Step '2/7 Build the isolated qualification runners'
Write-Host '[INFO] This does NOT rebuild the OTP application.' -ForegroundColor DarkGray
Write-Host '[INFO] On the first run Docker may download the pinned Playwright browser image and Python test image.' -ForegroundColor Yellow
Write-Host '[INFO] Progress is intentionally visible below. Later runs should mostly use Docker cache.' -ForegroundColor Yellow
$buildArgs=@('-f','docker-compose.yml','-f','docker-compose.qualification.yml','--profile','qualification','--progress','plain','build','otp-backend-tests','otp-qualification')
& docker compose @buildArgs
if ($LASTEXITCODE -ne 0) {
  Write-Host '[FAIL] Could not build qualification containers.' -ForegroundColor Red
  Write-Status 'backend-tests.status' 'NOT RUN'
  Write-Status 'release-validation.status' 'NOT RUN'
  Write-Host '[ACTION] Check Docker Desktop network/proxy access and the visible build error above.' -ForegroundColor Yellow
  exit 1
}

Step '3/7 Run release/package validation on an uncontaminated release tree'
# A local runtime .env is legitimate after first start but must never count as a
# packaged release artifact. Temporarily move it outside the release tree while
# validating. If present, still use it as Compose interpolation input so the
# qualification command remains quiet and deterministic.
$runtimeEnv = Join-Path $root '.env'
$envBackup = $null
$releaseCompose = @($compose)
try {
  if (Test-Path $runtimeEnv) {
    $envBackup = Join-Path ([System.IO.Path]::GetTempPath()) ("otp-hotfix7-" + [guid]::NewGuid().ToString('N') + '.env')
    Move-Item -Force $runtimeEnv $envBackup
    $releaseCompose = @('--env-file',$envBackup) + $compose
    Write-Host '[INFO] Local runtime .env isolated outside the release tree for package-integrity validation.' -ForegroundColor DarkGray
  }
  & docker compose @releaseCompose run --rm --no-deps otp-backend-tests bash -lc "cd /workspace && python scripts/release_validate.py > /results/release-validation.txt 2>&1"
  $releaseRc=$LASTEXITCODE
} finally {
  if ($envBackup -and (Test-Path $envBackup)) {
    Move-Item -Force $envBackup $runtimeEnv
    Write-Host '[INFO] Local runtime .env restored after release validation.' -ForegroundColor DarkGray
  }
}
if ($releaseRc -eq 0) {
  Write-Status 'release-validation.status' 'PASS'
  Write-ReleaseEvidence 'PASS'
  Write-Host '[PASS] Release validation.' -ForegroundColor Green
} else {
  Write-Status 'release-validation.status' 'FAIL'
  Write-ReleaseEvidence 'FAIL'
  Write-Host '[FAIL] Release validation. See qualification\results\release-validation.txt.' -ForegroundColor Red
}
# Publish this run's release-integrity result before browser UAT. This prevents
# the UI qualification from reading stale evidence left by an earlier run.
if (Sync-ReleaseEvidence) { Write-Host '[OK] Current release-integrity evidence synchronized before browser UAT.' -ForegroundColor Green }

Step '4/7 Run backend regression + measured coverage in isolated result storage'
Write-Host '[INFO] Running pytest without writing .coverage/.pytest_cache into the release tree...'
& docker compose @compose run --rm --no-deps -e COVERAGE_FILE=/results/.coverage-local otp-backend-tests bash -lc "cd /workspace/backend && pytest -q -o cache_dir=/results/pytest-cache --cov=app --cov-report=term-missing --cov-report=xml:/results/coverage-local.xml --junitxml=/results/backend-junit.xml > /results/backend-tests.txt 2>&1"
if ($LASTEXITCODE -eq 0) { Write-Status 'backend-tests.status' 'PASS'; Write-Host '[PASS] Backend regression suite.' -ForegroundColor Green }
else { Write-Status 'backend-tests.status' 'FAIL'; Write-Host '[FAIL] Backend tests. See qualification\results\backend-tests.txt.' -ForegroundColor Red }

Step '5/7 Run real Chromium browser + live API UAT for all 15 layers'
Write-Host '[INFO] Running the browser/API qualification against the already-running OTP containers...'
& docker compose @compose run --rm --no-deps -e APP_HOST_PORT=$env:APP_HOST_PORT -e API_HOST_PORT=$env:API_HOST_PORT otp-qualification
$e2eExit=$LASTEXITCODE
if ($e2eExit -eq 0) { Write-Host '[PASS] Browser/API UAT.' -ForegroundColor Green }
else { Write-Host '[FAIL] Browser/API UAT. Traces/screenshots are in qualification\results\test-artifacts.' -ForegroundColor Red }

Step '6/7 Generate the strict per-layer 10/10 scorecard'
& docker compose @compose run --rm --no-deps otp-backend-tests python /workspace/scripts/generate_local_qualification_report.py
$reportExit=$LASTEXITCODE

Step '7/7 Synchronize final local evidence into Qualification Center'
if (Sync-ReleaseEvidence) { Write-Host '[OK] Qualification Center synchronized with final local evidence.' -ForegroundColor Green }

$report=Join-Path $results 'LOCAL_10_10_QUALIFICATION.md'
if (Test-Path $report) {
  Write-Host "`n------------------------------------------------------------"
  Get-Content $report
  Write-Host "------------------------------------------------------------"
}

if ($reportExit -eq 0 -and $e2eExit -eq 0) {
  Start-Process "http://localhost:$($env:APP_HOST_PORT)/qualification"
  exit 0
}
exit 1
