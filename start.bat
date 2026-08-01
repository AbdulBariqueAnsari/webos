@echo off
title Web OS v1.0 Ultimate — Graphical Desktop Center
set PYTHONUNBUFFERED=1
set PYTHONIOENCODING=utf-8

echo ==================================================
echo    Starting Web OS v1.0 Ultimate GUI Center
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

echo [OK] Launching Web OS Native GUI Window & Web Desktop...
echo.

python gui.py

pause


