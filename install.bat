@echo off
title Web OS v5.0 - Windows Installer
echo ============================================
echo    Web OS v5.0 Ultimate - Windows Installation
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed!
    echo.
    echo Download Python from: https://www.python.org/downloads/
    echo.
    echo IMPORTANT: During installation, check "Add Python to PATH"
    echo.
    pause
    start https://www.python.org/downloads/
    exit /b 1
)

echo [OK] Python found
python --version

REM Check if pip is available
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    python -m pip --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] pip not found. Please install Python with pip.
        pause
        exit /b 1
    )
)

echo [OK] pip found
echo.
echo Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    python -m pip install -r requirements.txt
)

echo.
echo ============================================
echo  Installation Complete!
echo ============================================
echo.
echo To start Web OS:
echo   Double-click start.bat
echo   OR
echo   python main.py
echo.
echo Open browser: http://localhost:8080
echo Login: admin / admin
echo.
pause
