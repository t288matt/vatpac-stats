#!/bin/sh
# Controller Stats Materialized View Refresh Script for Cron
# This script runs inside the cron container and refreshes the materialized view

# Set timestamp for logging
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
echo "[$TIMESTAMP] Starting materialized view refresh..."

# Check if required containers are running
if ! docker ps | grep -q "vatsim_postgres"; then
    echo "[$TIMESTAMP] ERROR: vatsim_postgres container not running"
    exit 1
fi

if ! docker ps | grep -q "vatsim_app"; then
    echo "[$TIMESTAMP] ERROR: vatsim_app container not running"
    exit 1
fi

# Refresh the materialized view
echo "[$TIMESTAMP] Refreshing controller_weekly_stats materialized view..."
if docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -c "SELECT refresh_controller_stats();" > /dev/null 2>&1; then
    echo "[$TIMESTAMP] SUCCESS: Materialized view refreshed successfully"
    
    # Get row count for verification
    ROW_COUNT=$(docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -t -c "SELECT COUNT(*) FROM controller_weekly_stats;" 2>/dev/null | tr -d ' ')
    echo "[$TIMESTAMP] INFO: View now contains $ROW_COUNT controller records"
    
    # Get view size
    VIEW_SIZE=$(docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -t -c "
        SELECT pg_size_pretty(pg_total_relation_size('controller_weekly_stats'));
    " 2>/dev/null | tr -d ' ')
    echo "[$TIMESTAMP] INFO: View size: $VIEW_SIZE"
    
    exit 0
else
    echo "[$TIMESTAMP] ERROR: Failed to refresh materialized view"
    exit 1
fi
