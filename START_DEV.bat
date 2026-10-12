@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
if not exist logs mkdir logs
call scripts\ensure_release_env.bat
if errorlevel 1 (echo [ERROR] Could not create/validate RC.5 release environment.& pause& exit /b 1)

call scripts\load_compose_secrets.bat
if errorlevel 1 (echo [ERROR] Could not load release secrets from .env.& pause& exit /b 1)
set "COMPOSE_PROJECT_NAME=enterprise-otp-demo-240rc3"
call scripts\sync_postgres_credentials.bat
if errorlevel 1 (echo [ERROR] PostgreSQL credential preflight failed.& pause& exit /b 1)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\select_runtime_ports.ps1 > logs\runtime_ports.tmp 2>nul
if errorlevel 1 (type logs\runtime_ports.tmp & echo [ERROR] Could not find free runtime ports.& pause& exit /b 1)
for /f "tokens=1,* delims==" %%A in (logs\runtime_ports.tmp) do set "%%A=%%B"
del /q logs\runtime_ports.tmp >nul 2>&1
if not defined APP_HOST_PORT set APP_HOST_PORT=3000
if not defined API_HOST_PORT set API_HOST_PORT=8000
if not defined N8N_HOST_PORT set N8N_HOST_PORT=5678
if not defined MINIO_CONSOLE_HOST_PORT set MINIO_CONSOLE_HOST_PORT=9001
(
 echo APP_HOST_PORT=!APP_HOST_PORT!
 echo API_HOST_PORT=!API_HOST_PORT!
 echo N8N_HOST_PORT=!N8N_HOST_PORT!
 echo MINIO_CONSOLE_HOST_PORT=!MINIO_CONSOLE_HOST_PORT!
)>logs\runtime_ports.env
docker compose up -d otp-postgres otp-redis otp-minio otp-n8n
if errorlevel 1 (echo [ERROR] Infrastructure startup failed.& pause& exit /b 1)
start "OTP API DEV" cmd /k "cd backend && set DATABASE_URL=sqlite:///./otp-dev.db && set DEMO_MODE=true && set CORS_ORIGINS=http://localhost:!APP_HOST_PORT! && uvicorn app.main:app --reload --port !API_HOST_PORT!"
start "OTP FRONTEND DEV" cmd /k "cd frontend && set NEXT_PUBLIC_API_URL=http://localhost:!API_HOST_PORT!/api/v1 && npm install && npm run dev -- -p !APP_HOST_PORT!"
echo [OK] Application: http://localhost:!APP_HOST_PORT!
echo [OK] API: http://localhost:!API_HOST_PORT!/api/v1
echo [OK] n8n: http://localhost:!N8N_HOST_PORT!
start "" http://localhost:!APP_HOST_PORT!
