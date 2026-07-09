@echo off
REM ========================================================
REM   YuShu Robot Inventory - Dev Mode
REM   Starts backend (8000) + frontend dev server (5173)
REM ========================================================

cd /d "%~dp0"
chcp 65001 >nul

echo.
echo ============================================================
echo    Dev Mode - Backend + Frontend dev server
echo ============================================================
echo.

start "" cmd /k "cd /d %~dp0backend && python run_external.py"
timeout /t 3 /nobreak >nul
start "" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Services started in new windows:
echo   Backend: http://localhost:8000
echo   API Doc: http://localhost:8000/docs
echo   Frontend: http://localhost:5173
echo.
pause