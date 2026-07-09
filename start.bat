@echo off
REM ========================================================
REM   YuShu Robot Inventory - One-Click Startup
REM   Compatible with: double-click / cmd / PowerShell
REM ========================================================

cd /d "%~dp0"
chcp 65001 >nul

echo.
echo ============================================================
echo    Starting YuShu Robot Inventory System
echo ============================================================
echo.

REM --- check python ---
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.9+ first.
    echo          https://www.python.org/downloads/
    pause
    exit /b 1
)

REM --- check node ---
where node >nul 2>&1
if errorlevel 1 (
    echo [WARN] Node.js not found. Skipping frontend build.
    goto :start_backend
)

REM --- install / build frontend ---
echo [1/3] Installing frontend deps ...
cd frontend
if not exist "node_modules" (
    call npm install
) else (
    echo       node_modules exists, skip install
)
echo [2/3] Building frontend ...
call npm run build
cd ..

:start_backend
echo [3/3] Starting backend ...
cd backend
if not exist "venv" (
    python -m venv venv
)
call venv\Scripts\activate.bat 2>nul
pip install -r requirements.txt -q
echo.
python run_external.py
pause