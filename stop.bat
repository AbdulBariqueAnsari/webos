@echo off
title Web OS v5.0 - Stop Server
echo ================================================
echo    Stopping Web OS v5.0
echo ================================================
echo.

REM Kill all Python processes that might be Web OS
echo [INFO] Stopping Web OS servers...

taskkill /f /im python.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Web OS stopped
) else (
    echo [INFO] No running Web OS server found
)

REM Also try to kill any process on port 8080
for /f "tokens=5" %%a in ('netstat -ano ^| find ":8080" ^| find "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| find ":8081" ^| find "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)

echo.
echo [OK] All Web OS servers stopped
echo.
pause
