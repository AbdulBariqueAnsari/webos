@echo off
title Web OS v1.0 Ultimate
set PYTHONUNBUFFERED=1
set PYTHONIOENCODING=utf-8

echo ==================================================
echo    Starting Web OS v1.0 Ultimate Operating System
echo ==================================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Please install Python first.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Starting servers and detecting active network IPs...
echo.

python main.py

pause

