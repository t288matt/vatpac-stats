@echo off
REM Batch file to run the delete invalid controllers script inside the Docker container
REM This script deletes rows from the controllers table where the controller
REM isn't in the controller callsigns list

echo.
echo ========================================
echo Delete Invalid Controllers Script
echo ========================================
echo.

REM Check if Docker container is running
echo Checking if Docker container is running...
docker ps --filter "name=vatsim_app" --format "table {{.Names}}\t{{.Status}}" | findstr "vatsim_app" >nul
if %errorlevel% neq 0 (
    echo ERROR: vatsim_app container is not running!
    echo Please start the container first with: docker-compose up -d
    pause
    exit /b 1
)

echo Container is running. Starting script...
echo.

REM Run the script inside the container
echo Running delete_invalid_controllers.py inside the container...
echo.

REM First, do a dry run to see what would be deleted
echo ========================================
echo DRY RUN - Showing what would be deleted
echo ========================================
docker exec vatsim_app python scripts/delete_invalid_controllers.py --dry-run

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Dry run failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Dry run completed successfully!
echo ========================================
echo.

REM Ask user if they want to proceed with actual deletion
set /p confirm="Do you want to proceed with the actual deletion? (y/N): "
if /i "%confirm%"=="y" (
    echo.
    echo ========================================
    echo PERFORMING ACTUAL DELETION
    echo ========================================
    echo.
    
    docker exec vatsim_app python scripts/delete_invalid_controllers.py
    
    if %errorlevel% neq 0 (
        echo.
        echo ERROR: Deletion failed!
        pause
        exit /b 1
    )
    
    echo.
    echo ========================================
    echo Deletion completed successfully!
    echo ========================================
) else (
    echo.
    echo Deletion cancelled by user.
)

echo.
echo Script completed.
pause



