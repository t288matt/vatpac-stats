@echo off
REM Controller Stats Materialized View Refresh Script (Windows Batch)
REM This script refreshes the controller_weekly_stats materialized view

echo.
echo ============================================================
echo Controller Stats Materialized View Refresh Tool
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python and ensure it's in your PATH
    pause
    exit /b 1
)

REM Check if Docker is available
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not installed or not in PATH
    echo Please install Docker Desktop and ensure it's in your PATH
    pause
    exit /b 1
)

echo ✅ Python and Docker are available
echo.

REM Run the refresh script
echo 🚀 Starting refresh process...
python scripts/refresh_controller_stats_docker.py

echo.
echo ============================================================
echo Refresh process completed
echo ============================================================
echo.
pause
