@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
if not exist logs mkdir logs
set "LOG=logs\launcher.log"
set "RELEASE_ID=2.4.0-rc.3-hotfix7"
set "EXPECTED_COMPOSE_PROJECT=enterprise-otp-demo-240rc3"
set "OTP_SHOW_BUILD_PROGRESS=1"
call :log "========================================"
call :log " INTERCOMPANY TRANSFER PRICING HUB 2.4.0-rc.3-hotfix7"
call :log " Docker recovery + low-concurrency build"
call :log "========================================"

call :ensure_engine
if errorlevel 1 (
  call :log "[ERROR] Docker Desktop Linux engine is unavailable."
  call :log "[ACTION] See logs\docker_engine_guard.log."
  if /I not "!OTP_NO_PAUSE!"=="1" pause
  exit /b 1
)

call scripts\ensure_release_env.bat
if errorlevel 1 (call :log "[ERROR] Could not create/validate release-isolated demo configuration." & if /I not "!OTP_NO_PAUSE!"=="1" pause & exit /b 1)
call scripts\load_compose_secrets.bat
if errorlevel 1 (call :log "[ERROR] Could not load release secrets from .env." & if /I not "!OTP_NO_PAUSE!"=="1" pause & exit /b 1)
set "COMPOSE_PROJECT_NAME=!EXPECTED_COMPOSE_PROJECT!"
call :log "[OK] Docker project isolation: !COMPOSE_PROJECT_NAME!"

call :log "[INFO] Stopping stale containers from this OTP project; data volumes are preserved..."
docker compose down --remove-orphans >> "%LOG%" 2>&1
if errorlevel 1 (
  call :log "[WARN] Compose cleanup failed. Checking Docker engine..."
  call :ensure_engine
  if errorlevel 1 (if /I not "!OTP_NO_PAUSE!"=="1" pause & exit /b 1)
  docker compose down --remove-orphans >> "%LOG%" 2>&1
)

call :log "[INFO] Verifying PostgreSQL credentials against the persistent database volume..."
call scripts\sync_postgres_credentials.bat >> "%LOG%" 2>&1
if errorlevel 1 (
  docker info >nul 2>&1
  if errorlevel 1 call :ensure_engine
  call scripts\sync_postgres_credentials.bat >> "%LOG%" 2>&1
  if errorlevel 1 (
    call :log "[ERROR] PostgreSQL credential preflight failed."
    call :log "[ACTION] See logs\postgres_preflight.log."
    if /I not "!OTP_NO_PAUSE!"=="1" pause
    exit /b 1
  )
)
call :log "[OK] PostgreSQL credentials verified"

call :log "[INFO] Selecting free host ports..."
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\select_runtime_ports.ps1 > logs\runtime_ports.tmp 2>> "%LOG%"
if errorlevel 1 (type logs\runtime_ports.tmp & call :log "[ERROR] Could not find free host ports." & if /I not "!OTP_NO_PAUSE!"=="1" pause & exit /b 1)
for /f "tokens=1,* delims==" %%A in (logs\runtime_ports.tmp) do set "%%A=%%B"
del /q logs\runtime_ports.tmp >nul 2>&1
if not defined APP_HOST_PORT set APP_HOST_PORT=3000
if not defined API_HOST_PORT set API_HOST_PORT=8000
if not defined N8N_HOST_PORT set N8N_HOST_PORT=5678
if not defined MINIO_CONSOLE_HOST_PORT set MINIO_CONSOLE_HOST_PORT=9001
set "NEXT_PUBLIC_API_URL=http://localhost:!API_HOST_PORT!/api/v1"
set "CORS_ORIGINS=http://localhost:!APP_HOST_PORT!"
(
  echo APP_HOST_PORT=!APP_HOST_PORT!
  echo API_HOST_PORT=!API_HOST_PORT!
  echo N8N_HOST_PORT=!N8N_HOST_PORT!
  echo MINIO_CONSOLE_HOST_PORT=!MINIO_CONSOLE_HOST_PORT!
)>logs\runtime_ports.env
call :log "[OK] Application: !APP_HOST_PORT!  API: !API_HOST_PORT!  n8n: !N8N_HOST_PORT!  MinIO: !MINIO_CONSOLE_HOST_PORT!"

set "COMPOSE_PARALLEL_LIMIT=1"
call :log "[INFO] Pre-building frontend with live progress and automatic retry..."
call :build_frontend
if errorlevel 1 (
  call :log "[ERROR] Frontend image build failed after 3 attempts."
  call :build_diagnostics
  if /I not "!OTP_NO_PAUSE!"=="1" pause
  exit /b 1
)

call :log "[INFO] Starting the complete stack (one service build at a time)..."
set "START_FAILED=0"
call :compose_up
if errorlevel 1 set "START_FAILED=1"
if "!START_FAILED!"=="1" (
  docker info >nul 2>&1
  if errorlevel 1 (
    call :log "[WARN] Docker engine dropped during startup. Recovering and retrying once..."
    call :ensure_engine
    if not errorlevel 1 (
      set "START_FAILED=0"
      call :compose_up
      if errorlevel 1 set "START_FAILED=1"
    )
  )
)
if "!START_FAILED!"=="1" (
  call :log "[ERROR] Docker Compose startup failed."
  call :diagnostics
  if /I not "!OTP_NO_PAUSE!"=="1" pause
  exit /b 1
)

call :log "[INFO] Waiting for API readiness..."
powershell -NoProfile -Command "$ok=$false; 1..90 | %% { try {$r=Invoke-WebRequest -UseBasicParsing http://localhost:!API_HOST_PORT!/api/v1/health/ready -TimeoutSec 2; if($r.StatusCode -eq 200){$ok=$true;break}} catch {}; Start-Sleep -Seconds 2 }; if(-not $ok){exit 1}"
if errorlevel 1 (call :log "[ERROR] API did not become ready." & call :diagnostics & if /I not "!OTP_NO_PAUSE!"=="1" pause & exit /b 1)
call :log "[OK] FastAPI + PostgreSQL ready"

call :log "[INFO] Waiting for frontend..."
powershell -NoProfile -Command "$ok=$false; 1..60 | %% { try {$r=Invoke-WebRequest -UseBasicParsing http://localhost:!APP_HOST_PORT! -TimeoutSec 2; if($r.StatusCode -eq 200){$ok=$true;break}} catch {}; Start-Sleep -Seconds 2 }; if(-not $ok){exit 1}"
if errorlevel 1 (call :log "[ERROR] Frontend did not become ready." & call :diagnostics & if /I not "!OTP_NO_PAUSE!"=="1" pause & exit /b 1)

call :log "[INFO] Running startup smoke test..."
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows_smoke_test.ps1 -ApiPort !API_HOST_PORT! -AppPort !APP_HOST_PORT! >> "%LOG%" 2>&1
if errorlevel 1 (call :log "[ERROR] Startup smoke test failed. See logs\launcher.log" & if /I not "!OTP_NO_PAUSE!"=="1" pause & exit /b 1)

call :log "[OK] All core services healthy"
call :log "Application: http://localhost:!APP_HOST_PORT!"
call :log "API: http://localhost:!API_HOST_PORT!/api/v1"
if /I not "!OTP_NO_BROWSER!"=="1" start "" http://localhost:!APP_HOST_PORT!
exit /b 0

:build_frontend
set "FRONTEND_BUILD_OK=0"
for /L %%R in (1,1,3) do (
  call :log "[INFO] Frontend build attempt %%R of 3..."
  docker compose --progress plain build otp-frontend
  if not errorlevel 1 (
    set "FRONTEND_BUILD_OK=1"
    goto :build_frontend_done
  )
  call :log "[WARN] Frontend build failed. Checking Docker engine..."
  docker info >nul 2>&1
  if errorlevel 1 call :ensure_engine
  if %%R LSS 3 powershell -NoProfile -Command "Start-Sleep -Seconds 8"
)
:build_frontend_done
if "!FRONTEND_BUILD_OK!"=="1" exit /b 0
exit /b 1

:compose_up
if /I "!OTP_QUIET_BUILD!"=="1" (
  docker compose up -d --build >> "%LOG%" 2>&1
) else (
  docker compose --progress plain up -d --build
)
exit /b %ERRORLEVEL%

:ensure_engine
call scripts\ensure_docker_desktop.bat >> "%LOG%" 2>&1
if errorlevel 1 (
  powershell -NoProfile -Command "if (Test-Path 'logs\docker_engine_guard.log') { Get-Content 'logs\docker_engine_guard.log' -Tail 30 }"
  exit /b 1
)
exit /b 0

:build_diagnostics
echo.
echo ===== FRONTEND BUILD DIAGNOSTICS =====
docker version 2>&1
echo.
docker system df 2>&1
echo [INFO] Persistent volumes were not deleted.
exit /b 0

:diagnostics
echo.
echo ===== DOCKER ENGINE =====
docker version 2>&1
echo.
echo ===== SERVICE STATUS =====
docker compose ps 2>&1
echo.
echo ===== FASTAPI DIAGNOSTICS =====
docker compose logs --tail=160 otp-api 2>&1
exit /b 0

:log
echo %~1
echo [%date% %time%] %~1>>"%LOG%"
exit /b 0
