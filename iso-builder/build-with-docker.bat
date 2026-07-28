@echo off
setlocal enabledelayedexpansion

title Web OS v1.0 - ISO Builder (Docker)

:: ═══════════════════════════════════════════════════════
::  Web OS v1.0 Ultimate — Docker se ISO Builder
::  Docker Desktop chahiye (free, easy install)
::  WSL ki zaroorat nahi — restart loop nahi!
:: ═══════════════════════════════════════════════════════

echo ================================================
echo   Web OS v1.0 - Docker ISO Builder
echo   Best tarika! Docker Desktop install karo
echo   aur ek command mein ISO ready!
echo ================================================
echo.

:: ─── Check Docker ─────────────────────────────────
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker Desktop installed nahi hai.
    echo.
    echo   Download: https://www.docker.com/products/docker-desktop/
    echo.
    echo   1. Browser mein link khulega
    echo   2. "Download for Windows" dabayein
    echo   3. Install karein (restart required)
    echo   4. Docker Desktop open karein
    echo   5. Yeh script dobara chalaayein
    echo.
    start https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)
echo [OK] Docker mil gaya: 
docker --version
echo.

:: ─── Build ISO ────────────────────────────────────
echo [INFO] ISO build start ho raha hai...
echo   Time: 10-20 minutes
echo   Internet chahiye (Debian + Python packages)
echo.
echo ================================================
echo   BUILDING... Ctrl+C to cancel
echo ================================================
echo.

set SCRIPT_DIR=%~dp0
set WEBOS_DIR=%SCRIPT_DIR%..
set OUTPUT_DIR=%WEBOS_DIR%\dist
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

cd /d "%WEBOS_DIR%"

:: Build the Docker image
docker build -f iso-builder\Dockerfile -t webos-iso-builder .
if %errorlevel% neq 0 (
    echo [ERROR] Docker build fail. Error upar check karein
    pause
    exit /b 1
)

:: Extract ISO from the image
docker create --name webos-temp webos-iso-builder
docker cp webos-temp:/web-os-1.0-x86_64.iso "%OUTPUT_DIR%\web-os-1.0-x86_64.iso" 2>nul || docker cp webos-temp:/web-os-6.0-x86_64.iso "%OUTPUT_DIR%\web-os-1.0-x86_64.iso"
docker rm webos-temp

if not exist "%OUTPUT_DIR%\web-os-1.0-x86_64.iso" (
    echo [ERROR] ISO generate nahi hui. Check Dockerfile
    pause
    exit /b 1
)

:: Copy to Desktop
copy "%OUTPUT_DIR%\web-os-1.0-x86_64.iso" "%USERPROFILE%\Desktop\web-os-1.0-x86_64.iso"

echo.
echo ================================================
echo   [SUCCESS] ISO Ready!
echo   Desktop: %USERPROFILE%\Desktop\web-os-1.0-x86_64.iso
echo ================================================
echo.
echo   Size: 
for %%f in ("%USERPROFILE%\Desktop\web-os-1.0-x86_64.iso") do echo   %%~zf bytes
echo.

:: ─── Rufus Guide ──────────────────────────────────
echo ================================================
echo   USB BOOTABLE BANANA (Rufus)
echo ================================================
echo.
echo   1. Rufus: https://rufus.ie
echo   2. Open Rufus -^> USB select (8GB+)
echo   3. SELECT -^> ISO choose karein
echo   4. START -^> DD Image mode
echo   5. Boot from USB on PC -^> F12/F2/Del
echo   6. GRUB -^> "Boot Live" ya "Install to Hard Drive"
echo.
echo   Login: admin / admin
echo.

set /p OPEN=Rufus download page kholein? (Y/N): 
if /i "!OPEN!"=="Y" start https://rufus.ie

echo.
pause
