@echo off
cd /d "%~dp0"
set "COMPOSE_PROJECT_NAME=enterprise-otp-demo-240rc3"
echo WARNING: This resets ONLY the Docker demo volumes for this project.
set /p CONFIRM=Type RESET to continue: 
if /I not "%CONFIRM%"=="RESET" exit /b 0
docker compose down -v --remove-orphans
if exist .env copy /Y .env logs\reset_previous.env.bak >nul 2>&1
if exist .env del /Q .env
call START_DEMO.bat
