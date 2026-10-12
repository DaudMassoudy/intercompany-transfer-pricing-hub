@echo off
setlocal
cd /d "%~dp0"
set "COMPOSE_PROJECT_NAME=enterprise-otp-demo-240rc3"
echo ========================================
echo  INTERCOMPANY TRANSFER PRICING HUB v2.4.0-rc.3 VALIDATION
echo ========================================
call scripts\ensure_docker_desktop.bat
if errorlevel 1 (pause& exit /b 1)
docker compose ps
echo.
echo [INFO] Database migration state:
docker compose exec -T otp-api alembic current
if errorlevel 1 (echo [ERROR] Could not read migration state.& pause& exit /b 1)
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows_rc_validation.ps1
if errorlevel 1 (echo [ERROR] RC validation failed.& pause& exit /b 1)
echo [PASS] Target-host release candidate validation completed.
pause
