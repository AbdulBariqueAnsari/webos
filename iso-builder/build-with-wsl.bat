@echo off
setlocal enabledelayedexpansion

title Web OS v1.0 - ISO Builder (WSL)

:: ──────────────────────────────────────────────────────
::  Web OS v1.0 Ultimate — Windows se ISO Builder
::  WSL + Ubuntu ke through bootable ISO banega
:: ──────────────────────────────────────────────────────
::
::  YE ESTA'ML KARNE KA TARIKA:
::  1. Run AS ADMINISTRATOR (right-click → Run as admin)
::  2. Ye script khud sab karega:
::     - WSL feature enable (ek baar, restart ke baad dobara chalao)
::     - Ubuntu WSL install
::     - ISO build
::     - Rufus guide
::
::  PROBLEM HO TO:
::  - Windows feature: "Virtual Machine Platform" + "WSL" ON karo
::  - ya Docker Desktop use karo (recommended + easy)
:: ──────────────────────────────────────────────────────

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Is script ko "Run as Administrator" se chalayein
    echo   Right-click -^> "Run as administrator"
    pause
    exit /b 1
)

:: ─── PHASE 1: WSL Feature Enable (one-time) ──────────
echo.
echo ================================================
echo   Phase 1: WSL Feature Check
echo ================================================

:: Check if WSL is already working
wsl --status >nul 2>&1
if %errorlevel% equ 0 goto PHASE2

:: Check if WSL feature is already enabled (but not fully set up)
dism /online /get-featureinfo /featurename:Microsoft-Windows-Subsystem-Linux 2>nul | find "State : Enabled" >nul
set "WSL_FEATURE_ENABLED=%errorlevel%"

dism /online /get-featureinfo /featurename:VirtualMachinePlatform 2>nul | find "State : Enabled" >nul
set "VM_FEATURE_ENABLED=%errorlevel%"

if %WSL_FEATURE_ENABLED% neq 0 (
    echo [ACTION] WSL feature enabled nahi hai. Enable kar rahe hain...
    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart >nul 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] WSL enable fail. Manual karein:
        echo   Control Panel -^> Programs -^> Turn Windows features on/off
        echo   Tick: "Windows Subsystem for Linux"
        echo   OK -^> Restart -^> Script dobara chalaayein
        pause
        exit /b 1
    )
)

if %VM_FEATURE_ENABLED% neq 0 (
    echo [ACTION] Virtual Machine Platform enable kar rahe hain...
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart >nul 2>&1
    if !errorlevel! neq 0 (
        echo [WARN] VM Platform enable fail - WSL2 nahi chalega
    )
)

:: If we enabled anything, restart needed
if %WSL_FEATURE_ENABLED% neq 0 (
    echo.
    echo [RESTART REQUIRED] Windows features enable ho gaye.
    echo   Ab system restart hoga. Restart ke baad yehi script dubara chalaayein.
    echo   (bash build-with-wsl.bat)
    echo.
    echo   Restart ho raha hai 15 seconds mein...
    shutdown /r /t 15
    echo   Cancel karne ke liye: shutdown /a
    pause
    exit /b 0
)

echo [OK] WSL features already enabled
echo.

:: ─── PHASE 2: Ubuntu WSL Install ──────────────────
:PHASE2
echo.
echo ================================================
echo   Phase 2: Ubuntu WSL Check
echo ================================================

:: Check for Ubuntu distro
set "UBUNTU_INSTALLED=0"
for /f "tokens=*" %%i in ('wsl -l -q 2^>nul') do (
    echo %%i | find /i "Ubuntu" >nul && set "UBUNTU_INSTALLED=1"
)

if "%UBUNTU_INSTALLED%"=="0" (
    echo [ACTION] Ubuntu WSL install ho raha hai...
    echo   Yeh 5-10 min le sakta hai. Wait karein...
    echo.
    
    :: Try wsl --install method first
    wsl --install -d Ubuntu
    if !errorlevel! neq 0 (
        echo.
        echo [ERROR] wsl --install -d Ubuntu fail hua. 2 tarike hain:
        echo.
        echo   TARIQA 1: Microsoft Store se
        echo     Start -^> "Microsoft Store" search -^> "Ubuntu" search -^> Install
        echo.
        echo   TARIQA 2: Manual download
        echo     1. Browser mein kholein:
        echo        https://apps.microsoft.com/detail/9pdxgn4nx7sr
        echo     2. "Get" / "Install" dabayein
        echo     3. Start -^> "Ubuntu" open -^> username/password set karein
        echo     4. "exit" type karke close karein
        echo.
        echo   FIR YAHI SCRIPT DOBARA CHALAYEIN
        echo.
        pause
        exit /b 1
    )
    
    echo.
    echo [IMPORTANT] Ubuntu install ho gaya. Pehle manually launch karein:
    echo   Start menu -^> "Ubuntu" -^> Enter
    echo   Username aur password set karein
    echo   "exit" type karein
    echo.
    echo   Phir yehi script dobara chalaayein
    echo.
    pause
    exit /b 0
)

:: Wake up Ubuntu
echo [OK] Ubuntu WSL mil gaya. Wake up kar rahe hain...
wsl -d Ubuntu bash -c "echo WSL_ALIVE" 2>nul | find "WSL_ALIVE" >nul
if %errorlevel% neq 0 (
    echo [ERROR] Ubuntu start nahi ho raha. Pehle manually:
    echo   Start -^> "Ubuntu" -^> username/password set -^> exit
    echo   Phir script dobara chalaayein
    pause
    exit /b 1
)
echo [OK] Ubuntu ready
echo.

:: ─── PHASE 3: Install Build Deps ──────────────────
echo.
echo ================================================
echo   Phase 3: Build Dependencies Install
echo ================================================

set SCRIPT_DIR=%~dp0
set WEBOS_DIR=%SCRIPT_DIR%..
set WSL_WEBOS_DIR=/opt/webos-build

echo [INFO] Web OS files WSL mein copy ho rahi hain...
wsl -d Ubuntu bash -c "sudo rm -rf %WSL_WEBOS_DIR% && sudo mkdir -p %WSL_WEBOS_DIR%"
cd /d "%WEBOS_DIR%"
tar cf - --exclude=dist --exclude=__pycache__ --exclude=*.pyc --exclude=.git --exclude=node_modules . 2>nul | wsl -d Ubuntu bash -c "cd %WSL_WEBOS_DIR% && sudo tar xf -"
if %errorlevel% neq 0 (
    echo [ERROR] File copy fail
    pause
    exit /b 1
)
echo [OK] Files transerred
echo.

echo [INFO] Build dependencies install ho rahi hain...
echo   Sudo password maang sakta hai (Ubuntu ka password daalein)
echo.
wsl -d Ubuntu bash -c "sudo apt update -qq && sudo apt install -y -qq debootstrap grub-pc-bin grub-efi-amd64-bin xorriso squashfs-tools cpio wget ca-certificates python3 python3-pip rsync dosfstools 2>&1 | tail -3"
if %errorlevel% neq 0 (
    echo [WARN] Kuch packages fail hue. Continuing...
)
echo.

:: ─── PHASE 4: Build ISO ──────────────────────────
echo.
echo ================================================
echo   Phase 4: ISO Build Start
echo ================================================
echo   Time: 10-30 minutes
echo   Internet required (Debian base system download)
echo.
echo   Building... Ctrl+C to cancel
echo.

wsl -d Ubuntu bash -c "cd %WSL_WEBOS_DIR%/iso-builder && sudo bash build-iso.sh"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] ISO build fail. Check karein:
    echo   1. Internet connected hai?
    echo   2. WSL mein space hai? (wsl --shutdown, wsl --resize)
    echo   3. Ubuntu update: wsl -d Ubuntu sudo apt update
    pause
    exit /b 1
)

:: ─── PHASE 5: Copy ISO Back ──────────────────────
echo [INFO] ISO Desktop par copy ho raha hai...
wsl -d Ubuntu bash -c "cp -f %WSL_WEBOS_DIR%/dist/*.iso /mnt/c/Users/%USERNAME%/Desktop/ 2>/dev/null"
if %errorlevel% equ 0 (
    echo.
    echo ================================================
    echo   [SUCCESS] ISO Ready!
    echo   C:\Users\%USERNAME%\Desktop\web-os-6.0-x86_64.iso
    echo ================================================
) else (
    echo [WARN] Copy fail. WSL mein check karein:
    echo   ls -la /opt/webos-build/dist/
)

:: Cleanup
wsl -d Ubuntu bash -c "sudo rm -rf %WSL_WEBOS_DIR%" 2>nul

:: ─── PHASE 6: Rufus Guide ─────────────────────────
echo.
echo ================================================
echo   USB BOOTABLE BANANE KA TARIKA
echo ================================================
echo.
echo   1. Rufus download karein (FREE): https://rufus.ie
echo.
echo   2. Rufus open karein (Admin mode)
echo   3. USB drive select karein (8GB+)
echo   4. SELECT -^> ISO choose karein
echo      C:\Users\%USERNAME%\Desktop\web-os-6.0-x86_64.iso
echo   5. Partition scheme: GPT (UEFI) / MBR (Legacy)
echo   6. START -^> DD Image mode me HA
echo   7. Wait (5-10 min)
echo.
echo   BOOT: USB lagao -^> F12/F2/Del -^> USB select -^>
echo         GRUB -^> "Boot Live" -^> Web OS desktop!
echo.
echo   Login: admin / admin
echo   URL:   http://localhost:8080
echo.

set /p OPEN=Kya Rufus download page kholein? (Y/N): 
if /i "!OPEN!"=="Y" start https://rufus.ie

echo.
pause
