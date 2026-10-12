@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ========================================
echo  Intercompany Transfer Pricing Hub - Docker Engine Repair
echo ========================================
echo.
call scripts\ensure_docker_desktop.bat
if errorlevel 1 (
  echo.
  echo [ERROR] Automatic recovery did not complete successfully.
  echo [ACTION] See logs\docker_engine_guard.log.
  pause
  exit /b 1
)
echo.
echo [OK] Docker Desktop Linux engine is healthy.
docker version
echo.
pause
