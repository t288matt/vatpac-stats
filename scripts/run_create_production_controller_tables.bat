@echo off
REM Batch script to create controller_summaries and controllers_archive tables in production
REM This script executes the SQL creation script using Docker Compose

echo Creating Controller Tables in Production Database...
echo ==================================================

REM Check if we're in the right directory
if not exist "docker-compose.yml" (
    echo Error: docker-compose.yml not found. Please run this script from the project root directory.
    pause
    exit /b 1
)

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

echo Executing SQL script to create controller tables...

REM Execute the SQL script using Docker Compose
docker-compose exec -T db psql -U postgres -d vatsim_data -f /scripts/create_production_controller_tables.sql

if %errorlevel% equ 0 (
    echo.
    echo Successfully created controller tables!
    echo.
    echo Tables created:
    echo   - controller_summaries
    echo   - controllers_archive
    echo.
    echo Indexes and triggers have also been created for optimal performance.
) else (
    echo Error: Failed to create controller tables. Check the database logs for details.
    pause
    exit /b 1
)

echo.
echo Verification: You can now check the tables exist by running:
echo   docker-compose exec db psql -U postgres -d vatsim_data -c "\dt controller*"
echo.
echo Script execution completed.
pause

