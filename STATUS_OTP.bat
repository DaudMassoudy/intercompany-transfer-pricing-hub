@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "COMPOSE_PROJECT_NAME=enterprise-otp-demo-240rc3"
set APP_HOST_PORT=3000
set API_HOST_PORT=8000
set N8N_HOST_PORT=5678
set MINIO_CONSOLE_HOST_PORT=9001
if exist logs\runtime_ports.env (
  for /f "tokens=1,* delims==" %%A in (logs\runtime_ports.env) do set "%%A=%%B"
)
echo ========================================
echo  OTP PLATFORM STATUS v2.4.0-rc.3
echo ========================================
where docker >nul 2>&1 || (echo [ERROR] Docker CLI not found.& pause& exit /b 1)
docker info >nul 2>&1 || (echo [WARN] Docker Desktop is not running. Start the platform first.& pause& exit /b 1)
docker compose ps
echo.
echo Application: http://localhost:!APP_HOST_PORT!
echo API:         http://localhost:!API_HOST_PORT!/api/v1
echo n8n:         http://localhost:!N8N_HOST_PORT!
echo MinIO:       http://localhost:!MINIO_CONSOLE_HOST_PORT!
echo.
powershell -NoProfile -Command "try {$r=Invoke-RestMethod http://localhost:!API_HOST_PORT!/api/v1/health; Write-Host ('API Version: '+$r.version+'  Mode: '+$r.mode)} catch {Write-Host '[ERROR] API health unavailable'}"
echo.
echo Database migration:
docker compose exec -T otp-api alembic current 2>nul
pause
