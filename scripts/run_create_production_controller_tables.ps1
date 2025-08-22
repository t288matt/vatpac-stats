# PowerShell script to create controller_summaries and controllers_archive tables in production
# This script executes the SQL creation script using Docker Compose

Write-Host "Creating Controller Tables in Production Database..." -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

# Check if we're in the right directory
if (-not (Test-Path "docker-compose.yml")) {
    Write-Host "Error: docker-compose.yml not found. Please run this script from the project root directory." -ForegroundColor Red
    exit 1
}

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "Error: Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

Write-Host "Executing SQL script to create controller tables..." -ForegroundColor Yellow

# Execute the SQL script using Docker Compose
try {
    docker-compose exec -T db psql -U postgres -d vatsim_data -f /scripts/create_production_controller_tables.sql
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Successfully created controller tables!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Tables created:" -ForegroundColor Cyan
        Write-Host "  - controller_summaries" -ForegroundColor White
        Write-Host "  - controllers_archive" -ForegroundColor White
        Write-Host ""
        Write-Host "Indexes and triggers have also been created for optimal performance." -ForegroundColor Cyan
    } else {
        Write-Host "Error: Failed to create controller tables. Check the database logs for details." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Error: Failed to execute SQL script: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Verification: You can now check the tables exist by running:" -ForegroundColor Yellow
Write-Host "  docker-compose exec db psql -U postgres -d vatsim_data -c \"\dt controller*\"" -ForegroundColor White
Write-Host ""
Write-Host "Script execution completed." -ForegroundColor Green


