@echo off
cd /d "%~dp0"
set "COMPOSE_PROJECT_NAME=enterprise-otp-demo-240rc3"
where docker >nul 2>&1 || (echo [ERROR] Docker CLI not found.& pause& exit /b 1)
docker info >nul 2>&1 || (echo [WARN] Docker Desktop is not running. Nothing to stop.& pause& exit /b 0)
docker compose stop
echo OTP services stopped. Persistent data was preserved.
pause
