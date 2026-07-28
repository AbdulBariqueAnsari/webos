@echo off
title Web OS v5.0
echo ============================================
echo    Starting Web OS v5.0 Ultimate
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Please install Python first.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Starting servers...
echo Open browser: http://localhost:8080
echo Login: admin / admin
echo Press Ctrl+C to stop
echo.

python main.py

pause
