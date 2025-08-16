@echo off
REM Database Status Check Script for Windows
REM This batch file runs the PowerShell monitoring script

echo 🗄️  VATSIM Database Monitor
echo ================================
echo.

REM Check if PowerShell is available
powershell -Command "Get-Host" >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: PowerShell is not available
    echo Please install PowerShell or use the Python script instead
    echo.
    echo Alternative: python scripts/monitor_database_live.py
    pause
    exit /b 1
)

REM Check if psql is available
psql --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Warning: psql command not found
    echo PostgreSQL client tools may not be installed
    echo.
    echo Using Python monitoring script instead...
    echo.
    python scripts/monitor_database_live.py
    pause
    exit /b 0
)

echo ✅ PowerShell and psql are available
echo.
echo Starting database monitoring...
echo Press Ctrl+C to stop
echo.

REM Run the PowerShell script
powershell -ExecutionPolicy Bypass -File "%~dp0check_database.ps1"

echo.
echo Monitoring stopped.
pause
