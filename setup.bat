@echo off
title Web OS v5.0 Ultimate - Setup
setlocal enabledelayedexpansion

set "WEBOS_DIR=%~dp0"
cd /d "%WEBOS_DIR%"

:MENU
cls
echo ================================================
echo     Web OS v5.0 Ultimate - Windows Setup
echo ================================================
echo.
echo  [1] Install/Update Dependencies
echo  [2] Start Web OS (with auto-start on boot)
echo  [3] Start Web OS (manual - one time)
echo  [4] Install as Windows Service (boot auto-start)
echo  [5] Remove Windows Service
echo  [6] Open Web OS in Browser
echo  [7] Open Web OS Dashboard (desktop)
echo  [8] About Web OS
echo  [9] Exit
echo.
set /p choice="Select option [1-9]: "

if "%choice%"=="1" goto INSTALL_DEPS
if "%choice%"=="2" goto START_AUTO
if "%choice%"=="3" goto START_MANUAL
if "%choice%"=="4" goto INSTALL_SERVICE
if "%choice%"=="5" goto REMOVE_SERVICE
if "%choice%"=="6" goto OPEN_BROWSER
if "%choice%"=="7" goto OPEN_DESKTOP
if "%choice%"=="8" goto ABOUT
if "%choice%"=="9" exit /b 0
goto MENU

:INSTALL_DEPS
cls
echo ================================================
echo  Installing Dependencies
echo ================================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed!
    echo Download: https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during installation
    start https://www.python.org/downloads/
    pause
    goto MENU
)
echo [OK] Python found
python --version

REM Check pip
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    python -m pip --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] pip not found
        pause
        goto MENU
    )
)
echo [OK] pip found

REM Install packages
echo.
echo Installing Python packages (this may take a minute)...
echo.
pip install -r "%WEBOS_DIR%requirements.txt" 2>nul
if %errorlevel% neq 0 (
    python -m pip install -r "%WEBOS_DIR%requirements.txt" 2>nul
)
if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Some packages failed to install.
    echo Web OS may still work with basic features.
) else (
    echo [OK] All dependencies installed successfully
)
echo.
pause
goto MENU

:START_AUTO
cls
echo ================================================
echo  Starting Web OS with Auto-Start
echo ================================================
echo.

REM Install Windows Task Scheduler entry for auto-start
schtasks /query /tn "WebOS" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Creating auto-start task...
    schtasks /create /tn "WebOS" /tr "\"%WEBOS_DIR%start.bat\"" /sc onstart /delay 0000:30 /rl highest /f >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Web OS will auto-start on boot
    ) else (
        echo [WARNING] Could not create auto-start task
        echo Run this as Administrator to enable auto-start
    )
) else (
    echo [OK] Auto-start task already exists
)

REM Start Web OS now
echo [INFO] Starting Web OS now...
echo.
start "Web OS Server" /MIN cmd /c "cd /d \"%WEBOS_DIR%\" && python main.py"
echo.

REM Wait for server to start
echo [INFO] Waiting for server...
timeout /t 5 /nobreak >nul

REM Open browser
echo [INFO] Opening browser...
start http://localhost:8080

echo.
echo ================================================
echo  Web OS is starting!
echo ================================================
echo  URL:  http://localhost:8080
echo  Login: admin / admin
echo  PID:  Check task manager for python.exe
echo ================================================
echo.
echo  [Tip] Web OS will auto-start on next boot too
echo  [Tip] To remove auto-start, run setup.bat option 5
echo.
pause
goto MENU

:START_MANUAL
cls
echo ================================================
echo  Starting Web OS (Manual)
echo ================================================
echo.

start "Web OS Server" /MIN cmd /c "cd /d \"%WEBOS_DIR%\" && python main.py"
timeout /t 5 /nobreak >nul
start http://localhost:8080

echo.
echo Web OS started!
echo URL: http://localhost:8080
echo Login: admin / admin
echo.
pause
goto MENU

:INSTALL_SERVICE
cls
echo ================================================
echo  Installing as Windows Service
echo ================================================
echo.

REM Check for admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Administrator rights required.
    echo Right-click setup.bat and select "Run as administrator"
    pause
    goto MENU
)

REM Install using nssm or sc
where nssm >nul 2>&1
if %errorlevel% equ 0 (
    nssm install WebOS "python" "main.py"
    nssm set WebOS AppDirectory "%WEBOS_DIR%"
    nssm set WebOS Start SERVICE_AUTO_START
    nssm set WebOS AppStdout "%WEBOS_DIR%logs\webos.log"
    nssm set WebOS AppStderr "%WEBOS_DIR%logs\webos-error.log"
    nssm start WebOS
    echo [OK] Web OS installed as Windows service via NSSM
) else (
    echo [INFO] NSSM not found. Creating scheduled task instead...
    schtasks /create /tn "WebOS" /tr "\"%WEBOS_DIR%start.bat\"" /sc onstart /delay 0000:30 /rl highest /f
    if %errorlevel% equ 0 (
        echo [OK] Web OS scheduled task created
        echo It will start automatically on next boot
    ) else (
        echo [ERROR] Could not create service
    )
)
echo.
pause
goto MENU

:REMOVE_SERVICE
cls
echo ================================================
echo  Removing Web OS Auto-Start
echo ================================================
echo.

schtasks /delete /tn "WebOS" /f >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Auto-start task removed
) else (
    echo [INFO] No auto-start task found
)

where nssm >nul 2>&1
if %errorlevel% equ 0 (
    nssm stop WebOS >nul 2>&1
    nssm remove WebOS confirm >nul 2>&1
)

echo [OK] Web OS auto-start has been removed
echo.
pause
goto MENU

:OPEN_BROWSER
start http://localhost:8080
goto MENU

:OPEN_DESKTOP
start http://localhost:8080/desktop
goto MENU

:ABOUT
cls
echo ================================================
echo     Web OS v5.0 Ultimate
echo ================================================
echo.
echo  A complete web-based operating system
echo  that runs on any device with a browser.
echo.
echo  Features:
echo   - 40+ Built-in Apps
echo   - 6 AI Agents
echo   - 3 Games (Snake, Tetris, Minesweeper)
echo   - File Manager with Recycle Bin
echo   - Code Editor with Syntax Highlighting
echo   - Terminal with Command History
echo   - Docker Manager
echo   - Database Manager (SQLite, MySQL, PostgreSQL)
echo   - API Playground
echo   - File Sharing with Links
echo   - Backup Manager
echo   - Whiteboard, Paint, Drawing Pad
echo   - Music Player, Image Gallery
echo   - Download Manager, Port Scanner
echo   - Lock Screen, Power Menu
echo   - And much more!
echo.
echo  Default Login: admin / admin
echo  Ports: HTTP=8080, WebDAV=8081, File=8082, WS=8084
echo.
echo  Made with Python, Flask, JavaScript
echo.
pause
goto MENU
