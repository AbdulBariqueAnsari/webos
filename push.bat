@echo off
title Web OS — Push to GitHub
echo ==================================================
echo      Web OS — Git Auto Commit ^& Push Tool
echo ==================================================
echo.

REM Check if git is available
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed or not available in PATH!
    pause
    exit /b 1
)

echo [1/3] Adding modified files to Git...
git add .

set /p msg="Enter commit message (Press ENTER for default): "
if "%msg%"=="" set msg=Update Web OS: Fix screen freeze and add continuous live network IP monitor

echo.
echo [2/3] Creating Git commit: "%msg%"
git commit -m "%msg%"

echo.
echo [3/3] Pushing to GitHub repository...
git push origin main

if %errorlevel% equ 0 (
    echo.
    echo ==================================================
    echo    [SUCCESS] Successfully pushed to GitHub!
    echo ==================================================
) else (
    echo.
    echo [ERROR] Git push failed. Please check your network or GitHub permissions.
)

echo.
pause
