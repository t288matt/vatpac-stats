# Database Status Check Script
# This script runs SQL queries to check if data is flowing into the database

param(
    [string]$DatabaseHost = "localhost",
    [string]$DatabasePort = "5432",
    [string]$DatabaseName = "vatsim_data",
    [string]$DatabaseUser = "vatsim_user",
    [string]$DatabasePassword = "vatsim_password",
    [int]$Interval = 30
)

# Function to run SQL query and display results
function Invoke-SqlQuery {
    param(
        [string]$Query,
        [string]$Description
    )
    
    Write-Host "`n🔍 $Description" -ForegroundColor Cyan
    Write-Host "-" * 50
    
    try {
        # Use psql command if available
        $env:PGPASSWORD = $DatabasePassword
        $psqlCommand = "psql -h $DatabaseHost -p $DatabasePort -U $DatabaseUser -d $DatabaseName -c `"$Query`""
        
        # Run the query
        $result = Invoke-Expression $psqlCommand 2>$null
        
        if ($result) {
            Write-Host $result -ForegroundColor White
        } else {
            Write-Host "No results or error occurred" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "Error running query: $_" -ForegroundColor Red
    }
}

# Function to check if psql is available
function Test-PsqlAvailable {
    try {
        $null = Get-Command psql -ErrorAction Stop
        return $true
    }
    catch {
        return $false
    }
}

# Main monitoring loop
function Start-DatabaseMonitoring {
    Write-Host "🗄️  VATSIM Database Monitor" -ForegroundColor Green
    Write-Host "=" * 60
    Write-Host "Host: $DatabaseHost`:$DatabasePort" -ForegroundColor Yellow
    Write-Host "Database: $DatabaseName" -ForegroundColor Yellow
    Write-Host "User: $DatabaseUser" -ForegroundColor Yellow
    Write-Host "Update Interval: $Interval seconds" -ForegroundColor Yellow
    Write-Host "=" * 60
    Write-Host "Press Ctrl+C to stop monitoring`n" -ForegroundColor Red
    
    # Check if psql is available
    if (-not (Test-PsqlAvailable)) {
        Write-Host "❌ Error: psql command not found!" -ForegroundColor Red
        Write-Host "Please install PostgreSQL client tools or add psql to your PATH" -ForegroundColor Red
        Write-Host "Alternatively, use the Python monitoring script: python scripts/monitor_database_live.py" -ForegroundColor Yellow
        return
    }
    
    try {
        while ($true) {
            $currentTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            Write-Host "`n🕐 $currentTime - Checking database status..." -ForegroundColor Green
            
            # Run key status queries
            $tableCountsQuery = @"
SELECT 
    tablename,
    n_live_tup as live_rows,
    n_tup_ins as inserts,
    n_tup_upd as updates
FROM pg_stat_user_tables 
ORDER BY n_live_tup DESC;
"@
            
            Invoke-SqlQuery -Query $tableCountsQuery -Description "Table Counts and Activity"
            
            # Check recent flight activity
            $flightActivityQuery = @"
SELECT 
    COUNT(*) as total_flights,
    COUNT(CASE WHEN last_updated_api >= NOW() - INTERVAL '10 minutes' THEN 1 END) as flights_last_10min,
    COUNT(CASE WHEN last_updated_api >= NOW() - INTERVAL '1 minute' THEN 1 END) as flights_last_minute,
    MAX(last_updated_api) as most_recent_update
FROM flights;
"@
            
            Invoke-SqlQuery -Query $flightActivityQuery -Description "Flight Activity (Last 10 min / 1 min)"
            
            # Check sector tracking
            $sectorQuery = @"
SELECT 
    COUNT(*) as total_sectors,
    COUNT(CASE WHEN exit_timestamp IS NULL THEN 1 END) as open_sectors,
    COUNT(CASE WHEN entry_timestamp >= NOW() - INTERVAL '10 minutes' THEN 1 END) as sectors_last_10min
FROM flight_sector_occupancy;
"@
            
            Invoke-SqlQuery -Query $sectorQuery -Description "Sector Tracking Status"
            
            # Show recent flights sample
            $recentFlightsQuery = @"
SELECT 
    callsign,
    ROUND(latitude::numeric, 4) as lat,
    ROUND(longitude::numeric, 4) as lon,
    altitude,
    EXTRACT(EPOCH FROM (NOW() - last_updated_api))/60 as minutes_ago
FROM flights 
WHERE last_updated_api >= NOW() - INTERVAL '5 minutes'
ORDER BY last_updated_api DESC 
LIMIT 3;
"@
            
            Invoke-SqlQuery -Query $recentFlightsQuery -Description "Recent Flights (Last 5 minutes)"
            
            Write-Host "`n⏳ Next update in $Interval seconds... (Press Ctrl+C to stop)" -ForegroundColor Yellow
            Start-Sleep -Seconds $Interval
        }
    }
    catch {
        Write-Host "`n❌ Monitoring stopped: $_" -ForegroundColor Red
    }
}

# Function to run a single quick check
function Invoke-QuickCheck {
    Write-Host "🔍 Quick Database Check" -ForegroundColor Green
    Write-Host "=" * 40
    
    # Test connection
    try {
        $env:PGPASSWORD = $DatabasePassword
        $testQuery = "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public';"
        $result = psql -h $DatabaseHost -p $DatabasePort -U $DatabaseUser -d $DatabaseName -c $testQuery 2>$null
        
        if ($result -match "table_count") {
            Write-Host "✅ Database connection successful" -ForegroundColor Green
            
            # Run quick status check
            $quickQuery = @"
SELECT 
    'flights' as table_name,
    COUNT(*) as record_count,
    MAX(last_updated_api) as last_update
FROM flights
UNION ALL
SELECT 
    'controllers' as table_name,
    COUNT(*) as record_count,
    MAX(last_updated) as last_update
FROM controllers
UNION ALL
SELECT 
    'flight_sector_occupancy' as table_name,
    COUNT(*) as record_count,
    MAX(entry_timestamp) as last_update
FROM flight_sector_occupancy;
"@
            
            Invoke-SqlQuery -Query $quickQuery -Description "Quick Status Check"
            
        } else {
            Write-Host "❌ Database connection failed" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "❌ Error: $_" -ForegroundColor Red
    }
}

# Main script logic
if ($args[0] -eq "--quick") {
    Invoke-QuickCheck
} else {
    Start-DatabaseMonitoring
}
