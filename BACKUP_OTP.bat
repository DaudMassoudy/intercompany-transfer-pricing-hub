@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "COMPOSE_PROJECT_NAME=enterprise-otp-demo-240rc3"
for /f "usebackq delims=" %%v in ("VERSION.txt") do set APP_VERSION=%%v
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmmss"') do set TS=%%i
set DEST=backups\%TS%
mkdir "%DEST%" 2>nul

echo [INFO] Backing up Intercompany Transfer Pricing Hub v%APP_VERSION%...
call scripts\ensure_docker_desktop.bat
if errorlevel 1 (pause& exit /b 1)

echo [INFO] Backing up PostgreSQL...
docker compose exec -T otp-postgres pg_dump -U otp -d otp > "%DEST%\postgres.sql"
if errorlevel 1 (echo [ERROR] PostgreSQL backup failed.& pause& exit /b 1)

echo [INFO] Backing up MinIO volume...
docker compose exec -T otp-minio sh -c "tar czf - -C /data ." > "%DEST%\minio-data.tgz"
if errorlevel 1 (echo [ERROR] MinIO backup failed.& pause& exit /b 1)

echo [INFO] Backing up n8n state...
docker compose exec -T otp-n8n sh -c "tar czf - -C /home/node/.n8n ." > "%DEST%\n8n-data.tgz"
if errorlevel 1 (echo [ERROR] n8n backup failed.& pause& exit /b 1)

copy /Y .env "%DEST%\.env.backup" >nul 2>&1
xcopy /E /I /Y n8n\workflows "%DEST%\workflows" >nul 2>&1
(
 echo version=%APP_VERSION%
 echo created=%TS%
 echo includes=postgres,minio,n8n,env,workflow-source
)>"%DEST%\backup-manifest.txt"

powershell -NoProfile -Command "$files=Get-ChildItem '%DEST%' -File | Where-Object {$_.Name -ne 'SHA256SUMS.txt'}; $lines=foreach($f in $files){$h=(Get-FileHash $f.FullName -Algorithm SHA256).Hash.ToLower(); $h+'  '+$f.Name}; $lines | Set-Content -Encoding ASCII '%DEST%\SHA256SUMS.txt'"
if errorlevel 1 (echo [ERROR] Backup checksum generation failed.& pause& exit /b 1)

echo [OK] Backup created at %DEST%
echo [OK] SHA-256 manifest: %DEST%\SHA256SUMS.txt
pause
