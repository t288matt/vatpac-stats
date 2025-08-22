# Production Script: Run flights_archive synchronization
# This script runs the database sync to ensure flights_archive has all required fields

param(
    [string]$DatabaseHost = "localhost",
    [int]$DatabasePort = 5432,
    [string]$DatabaseName = "vatsim_data",
    [string]$DatabaseUser = "postgres",
    [string]$DatabasePassword = "postgres"
)

Write-Host "Starting flights_archive synchronization in production..." -ForegroundColor Green
Write-Host "Database: $DatabaseHost`:$DatabasePort/$DatabaseName" -ForegroundColor Yellow
Write-Host "User: $DatabaseUser" -ForegroundColor Yellow
Write-Host ""

# Check if Docker is running
try {
    $dockerStatus = docker info 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Docker is not running. Please start Docker first." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "ERROR: Docker is not available. Please install Docker first." -ForegroundColor Red
    exit 1
}

# Check if postgres container is running
$postgresRunning = docker-compose ps postgres | Select-String "Up"
if (-not $postgresRunning) {
    Write-Host "ERROR: PostgreSQL container is not running. Starting it now..." -ForegroundColor Red
    docker-compose up -d postgres
    Start-Sleep -Seconds 10
}

Write-Host "PostgreSQL container is running. Proceeding with sync..." -ForegroundColor Green

# Read the SQL script
$sqlScriptPath = Join-Path $PSScriptRoot "sync_flights_archive_production.sql"
if (-not (Test-Path $sqlScriptPath)) {
    Write-Host "ERROR: SQL script not found at $sqlScriptPath" -ForegroundColor Red
    exit 1
}

$sqlContent = Get-Content $sqlScriptPath -Raw

Write-Host "Executing database synchronization..." -ForegroundColor Green
Write-Host "This may take several minutes depending on data size..." -ForegroundColor Yellow

# Execute the SQL script in the postgres container
try {
    $result = docker-compose exec -T postgres psql -U $DatabaseUser -d $DatabaseName -c $sqlContent
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Database synchronization completed successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Results:" -ForegroundColor Cyan
        Write-Host $result -ForegroundColor White
    } else {
        Write-Host "❌ Database synchronization failed with exit code: $LASTEXITCODE" -ForegroundColor Red
        Write-Host "Error output:" -ForegroundColor Red
        Write-Host $result -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Error executing database synchronization: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🎉 Production sync completed successfully!" -ForegroundColor Green
Write-Host "The flights_archive table now has all required fields populated from flight_summaries." -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Verify the sync results above" -ForegroundColor White
Write-Host "2. Test the new API endpoints if needed" -ForegroundColor White
Write-Host "3. Monitor the application for any issues" -ForegroundColor White
