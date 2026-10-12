@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ============================================================
echo  INTERCOMPANY TRANSFER PRICING HUB v2.4.0-rc.3-hotfix7
ECHO  LOCAL 10/10 PRACTICALITY QUALIFICATION
ECHO ============================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\qualify_10_10.ps1
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo [PASS] All 15 target layers qualified at 10/10 practicality on this computer.
) else (
  echo [NOT QUALIFIED] One or more mandatory local runtime checks did not pass.
  echo Review qualification\results\LOCAL_10_10_QUALIFICATION.md and failure artifacts.
)
echo.
pause
exit /b %RC%
