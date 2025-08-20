@echo off
REM Production Script: Run flights_archive synchronization
REM This script runs the database sync to ensure flights_archive has all required fields

echo Starting flights_archive synchronization in production...
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running. Please start Docker first.
    pause
    exit /b 1
)

REM Check if postgres container is running
docker-compose ps postgres | findstr "Up" >nul
if %errorlevel% neq 0 (
    echo ERROR: PostgreSQL container is not running. Starting it now...
    docker-compose up -d postgres
    timeout /t 10 /nobreak >nul
)

echo PostgreSQL container is running. Proceeding with sync...
echo.

REM Execute the SQL script in the postgres container
echo Executing database synchronization...
echo This may take several minutes depending on data size...
echo.

docker-compose exec -T postgres psql -U postgres -d vatsim_data -f /scripts/sync_flights_archive_production.sql

if %errorlevel% equ 0 (
    echo.
    echo Database synchronization completed successfully!
    echo.
    echo Next steps:
    echo 1. Verify the sync results above
    echo 2. Test the new API endpoints if needed
    echo 3. Monitor the application for any issues
) else (
    echo.
    echo ERROR: Database synchronization failed!
    echo Please check the error messages above.
)

pause
