@echo off
rem Intentionally no SETLOCAL: values must remain in the caller's environment.
if not exist .env (
  echo [ERROR] .env not found. Run scripts\ensure_release_env.bat first.
  exit /b 1
)

set "OTP_DB_PASSWORD="
set "MINIO_IMAGE="
set "MINIO_ROOT_USER="
set "MINIO_ROOT_PASSWORD="
set "N8N_ENCRYPTION_KEY="
set "N8N_INTEGRATION_KEY="
set "N8N_SECURE_COOKIE="

for /f "tokens=1,* delims==" %%A in ('findstr /B /C:"OTP_DB_PASSWORD=" .env') do set "OTP_DB_PASSWORD=%%B"
for /f "tokens=1,* delims==" %%A in ('findstr /B /C:"MINIO_IMAGE=" .env') do set "MINIO_IMAGE=%%B"
for /f "tokens=1,* delims==" %%A in ('findstr /B /C:"MINIO_ROOT_USER=" .env') do set "MINIO_ROOT_USER=%%B"
for /f "tokens=1,* delims==" %%A in ('findstr /B /C:"MINIO_ROOT_PASSWORD=" .env') do set "MINIO_ROOT_PASSWORD=%%B"
for /f "tokens=1,* delims==" %%A in ('findstr /B /C:"N8N_ENCRYPTION_KEY=" .env') do set "N8N_ENCRYPTION_KEY=%%B"
for /f "tokens=1,* delims==" %%A in ('findstr /B /C:"N8N_INTEGRATION_KEY=" .env') do set "N8N_INTEGRATION_KEY=%%B"
for /f "tokens=1,* delims==" %%A in ('findstr /B /C:"N8N_SECURE_COOKIE=" .env') do set "N8N_SECURE_COOKIE=%%B"

if not defined OTP_DB_PASSWORD (
  echo [ERROR] OTP_DB_PASSWORD is missing from .env.
  exit /b 2
)
if not defined MINIO_ROOT_PASSWORD (
  echo [ERROR] MINIO_ROOT_PASSWORD is missing from .env.
  exit /b 3
)
if not defined N8N_ENCRYPTION_KEY (
  echo [ERROR] N8N_ENCRYPTION_KEY is missing from .env.
  exit /b 4
)
exit /b 0
