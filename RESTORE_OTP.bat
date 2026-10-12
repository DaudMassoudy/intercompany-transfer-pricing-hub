@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "COMPOSE_PROJECT_NAME=enterprise-otp-demo-240rc3"
echo Available backups:
dir /b backups 2>nul
set /p B=Enter backup folder name: 
if not exist "backups\%B%\postgres.sql" (echo [ERROR] Invalid backup.& pause& exit /b 1)
if exist "backups\%B%\SHA256SUMS.txt" (
  powershell -NoProfile -Command "$root=Resolve-Path 'backups\%B%'; $bad=$false; Get-Content (Join-Path $root 'SHA256SUMS.txt') | ForEach-Object {if($_ -match '^([0-9a-fA-F]{64})  (.+)$'){ $expected=$matches[1].ToLower(); $p=Join-Path $root $matches[2]; if(!(Test-Path $p) -or (Get-FileHash $p -Algorithm SHA256).Hash.ToLower() -ne $expected){Write-Host ('[ERROR] Backup checksum mismatch: '+$matches[2]); $bad=$true}}}; if($bad){exit 2}"
  if errorlevel 1 (echo [ERROR] Backup integrity verification failed.& pause& exit /b 1)
  echo [OK] Backup integrity verified.
)
set /p CONFIRM=Type RESTORE to continue: 
if /I not "%CONFIRM%"=="RESTORE" exit /b 0

echo [INFO] Restoring PostgreSQL...
docker compose exec -T otp-postgres psql -U otp -d otp < "backups\%B%\postgres.sql"
if errorlevel 1 (echo [ERROR] PostgreSQL restore failed.& pause& exit /b 1)

if exist "backups\%B%\minio-data.tgz" (
  for /f %%i in ('docker compose ps -q otp-minio') do set MINIO_CID=%%i
  docker cp "backups\%B%\minio-data.tgz" "%MINIO_CID%:/tmp/minio-data.tgz"
  docker compose exec -T otp-minio sh -c "rm -rf /data/* && tar xzf /tmp/minio-data.tgz -C /data && rm -f /tmp/minio-data.tgz"
)
if exist "backups\%B%\n8n-data.tgz" (
  for /f %%i in ('docker compose ps -q otp-n8n') do set N8N_CID=%%i
  docker cp "backups\%B%\n8n-data.tgz" "%N8N_CID%:/tmp/n8n-data.tgz"
  docker compose exec -T otp-n8n sh -c "rm -rf /home/node/.n8n/* && tar xzf /tmp/n8n-data.tgz -C /home/node/.n8n && rm -f /tmp/n8n-data.tgz"
)

echo [OK] Restore completed. Restart services with STOP_OTP.bat then START_OTP.bat.
pause
