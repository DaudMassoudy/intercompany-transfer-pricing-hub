@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
if not exist logs mkdir logs
set "LOG=logs\start_otp.log"

echo [INFO] Checking Docker Desktop Linux engine...
call scripts\ensure_docker_desktop.bat
if errorlevel 1 (echo [ERROR] Docker engine is unavailable. See logs\docker_engine_guard.log.& pause& exit /b 1)

call scripts\ensure_release_env.bat
if errorlevel 1 (echo [ERROR] Could not create/validate v2.4.0-rc.3-hotfix7 release environment.& pause& exit /b 1)
call scripts\load_compose_secrets.bat
if errorlevel 1 (echo [ERROR] Could not load release secrets from .env.& pause& exit /b 1)
set "COMPOSE_PROJECT_NAME=enterprise-otp-demo-240rc3"
echo [OK] Docker project isolation: !COMPOSE_PROJECT_NAME!

docker compose down --remove-orphans >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [WARN] Compose cleanup failed; checking Docker engine...
  call scripts\ensure_docker_desktop.bat
  if errorlevel 1 (pause& exit /b 1)
  docker compose down --remove-orphans >> "%LOG%" 2>&1
)

echo [INFO] Verifying PostgreSQL credentials...
set "PG_PREFLIGHT_FAILED=0"
call scripts\sync_postgres_credentials.bat
if errorlevel 1 set "PG_PREFLIGHT_FAILED=1"
if "!PG_PREFLIGHT_FAILED!"=="1" (
  docker info >nul 2>&1
  if errorlevel 1 (
    echo [WARN] Docker engine dropped during PostgreSQL preflight. Recovering...
    call scripts\ensure_docker_desktop.bat
    if not errorlevel 1 (
      set "PG_PREFLIGHT_FAILED=0"
      call scripts\sync_postgres_credentials.bat
      if errorlevel 1 set "PG_PREFLIGHT_FAILED=1"
    )
  )
)
if "!PG_PREFLIGHT_FAILED!"=="1" (echo [ERROR] PostgreSQL credential preflight failed.& pause& exit /b 1)

powershell -NoProfile -ExecutionPolicy Bypass -File scripts\select_runtime_ports.ps1 > logs\runtime_ports.tmp 2>> "%LOG%"
if errorlevel 1 (type logs\runtime_ports.tmp & echo [ERROR] Could not find free runtime ports.& pause& exit /b 1)
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

echo [INFO] Application port: !APP_HOST_PORT!  API: !API_HOST_PORT!  n8n: !N8N_HOST_PORT!  MinIO Console: !MINIO_CONSOLE_HOST_PORT!
echo [INFO] Building/starting services. First build may take several minutes...
set "START_FAILED=0"
docker compose --progress plain up -d --build
if errorlevel 1 set "START_FAILED=1"
if "!START_FAILED!"=="1" (
  docker info >nul 2>&1
  if errorlevel 1 (
    echo [WARN] Docker engine failed during startup. Attempting automatic recovery...
    call scripts\ensure_docker_desktop.bat
    if not errorlevel 1 (
      set "START_FAILED=0"
      docker compose --progress plain up -d --build
      if errorlevel 1 set "START_FAILED=1"
    )
  )
)
if "!START_FAILED!"=="1" (
  echo [ERROR] Startup failed.
  docker version >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] Docker Linux engine is unavailable. See logs\docker_engine_guard.log.
  ) else (
    echo.
    echo ===== SERVICE STATUS =====
    docker compose ps
    echo.
    echo ===== FASTAPI DIAGNOSTICS =====
    docker compose logs --tail=180 otp-api
  )
  pause
  exit /b 1
)
echo [OK] Application: http://localhost:!APP_HOST_PORT!
echo [OK] API: http://localhost:!API_HOST_PORT!/api/v1
echo [OK] n8n: http://localhost:!N8N_HOST_PORT!
start "" http://localhost:!APP_HOST_PORT!
