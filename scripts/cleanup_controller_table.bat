@echo off
REM Controller Table Cleanup Script - Windows Batch File
REM This script runs the Python cleanup script with common options

echo.
echo ========================================
echo Controller Table Cleanup Script
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "scripts\cleanup_controller_table.py" (
    echo ERROR: Please run this script from the project root directory
    echo Current directory: %CD%
    echo Expected: VATSIM data project root
    pause
    exit /b 1
)

echo Available options:
echo 1. Dry run (show what would be deleted)
echo 2. Perform actual cleanup
echo 3. Custom callsign file path
echo.

set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" (
    echo.
    echo Running DRY RUN mode...
    echo This will show what would be deleted without making changes
    echo.
    python scripts\cleanup_controller_table.py --dry-run
) else if "%choice%"=="2" (
    echo.
    echo WARNING: This will permanently delete controllers with invalid callsigns!
    echo.
    set /p confirm="Are you sure? Type 'YES' to continue: "
    if /i "%confirm%"=="YES" (
        echo.
        echo Performing cleanup...
        python scripts\cleanup_controller_table.py
    ) else (
        echo Cleanup cancelled.
    )
) else if "%choice%"=="3" (
    echo.
    set /p custom_path="Enter custom callsign file path: "
    if exist "%custom_path%" (
        echo.
        echo Running cleanup with custom file: %custom_path%
        python scripts\cleanup_controller_table.py --callsign-file "%custom_path%"
    ) else (
        echo ERROR: File not found: %custom_path%
    )
) else (
    echo Invalid choice. Please run the script again.
)

echo.
echo Script completed. Press any key to exit...
pause >nul
