#!/bin/bash

# Database Health Maintenance Script
# This script prevents index corruption by running regular maintenance
# Run this script weekly via cron to maintain database health

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/logs/database_maintenance.log"
MAINTENANCE_SCRIPT="$SCRIPT_DIR/prevent_index_corruption.sql"
DOCKER_COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S UTC')
    
    case "$level" in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        "DEBUG")
            echo -e "${BLUE}[DEBUG]${NC} $message"
            ;;
    esac
    
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        log "ERROR" "Docker is not running or not accessible"
        exit 1
    fi
}

# Check if timeout command is available
check_timeout() {
    if ! command -v timeout >/dev/null 2>&1; then
        log "WARN" "timeout command not available - REINDEX operations may hang indefinitely"
        log "WARN" "Consider installing coreutils or using a timeout wrapper"
        return 1
    fi
    return 0
}

# Check if PostgreSQL container is running and responding
check_postgres_container() {
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker ps --format "table {{.Names}}" | grep -q "vatsim_postgres"; then
            # Additional check: container is actually responding
            if docker exec vatsim_postgres pg_isready -U vatsim_user >/dev/null 2>&1; then
                log "INFO" "PostgreSQL container is running and responding"
                return 0
            else
                log "WARN" "Container exists but PostgreSQL not responding (attempt $attempt/$max_attempts)"
            fi
        else
            log "WARN" "PostgreSQL container not found (attempt $attempt/$max_attempts)"
        fi
        
        if [ $attempt -lt $max_attempts ]; then
            sleep 2
        fi
        ((attempt++))
    done
    
    log "ERROR" "PostgreSQL container is not running or not responding after $max_attempts attempts"
    exit 1
}

# Run maintenance script
run_maintenance() {
    log "INFO" "Starting database maintenance..."
    
    # Copy maintenance script to container first
    if ! docker cp "$MAINTENANCE_SCRIPT" vatsim_postgres:/tmp/prevent_index_corruption.sql; then
        log "ERROR" "Failed to copy maintenance script to container"
        exit 1
    fi
    
    # Verify the file was copied successfully
    if ! docker exec vatsim_postgres test -f /tmp/prevent_index_corruption.sql; then
        log "ERROR" "Maintenance script not found in container after copy"
        exit 1
    fi
    
    # Run the maintenance script
    docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f /tmp/prevent_index_corruption.sql >> "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        log "INFO" "Database maintenance completed successfully"
    else
        log "ERROR" "Database maintenance failed - check logs for details"
        exit 1
    fi
}

# Check database health
check_database_health() {
    log "INFO" "Checking database health..."
    
    # Check for corrupted indexes
    local corrupted_indexes=$(docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -t -c "
        SELECT indexname 
        FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND indexdef LIKE '%corrupt%' OR indexdef LIKE '%invalid%'
    " 2>&1 | wc -l)
    
    if [ "$corrupted_indexes" -gt 0 ]; then
        log "WARN" "Found $corrupted_indexes potentially corrupted indexes"
    else
        log "INFO" "No corrupted indexes detected"
    fi
    
    # Check for long-running transactions
    local long_transactions=$(docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -t -c "
        SELECT COUNT(*) 
        FROM pg_stat_activity 
        WHERE state != 'idle' 
        AND query_start < NOW() - INTERVAL '5 minutes'
    " 2>&1 | tr -d ' ')
    
    if [ "$long_transactions" -gt 0 ]; then
        log "WARN" "Found $long_transactions long-running transactions"
    else
        log "INFO" "No long-running transactions detected"
    fi
    
    # Check for lock conflicts
    local lock_conflicts=$(docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -t -c "
        SELECT COUNT(*) 
        FROM pg_stat_activity 
        WHERE wait_event_type IS NOT NULL 
        AND state != 'idle'
    " 2>&1 | tr -d ' ')
    
    if [ "$lock_conflicts" -gt 0 ]; then
        log "WARN" "Found $lock_conflicts lock conflicts"
    else
        log "INFO" "No lock conflicts detected"
    fi
}

# Optimize indexes if needed
optimize_indexes() {
    log "INFO" "Checking if index optimization is needed..."
    
            # Check for high bloat indexes (>30%)
        # Check for high bloat indexes using actual table statistics (>30% dead tuples)
        local high_bloat_count
        high_bloat_count=$(docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -t -c "
            SELECT COUNT(*) FROM (
                SELECT 1 FROM pg_stat_user_indexes s
                JOIN pg_index i ON s.indexrelid = i.indexrelid
                JOIN pg_stat_user_tables t ON s.relid = t.relid
                WHERE s.schemaname = 'public'
                AND t.n_live_tup > 0
                AND t.n_dead_tup > (t.n_live_tup * 0.3)  -- More than 30% dead tuples
            ) bloat_check
        " 2>&1)
        
        # Check if the query failed
        if [ $? -ne 0 ]; then
            log "ERROR" "Failed to check for high bloat indexes: $high_bloat_count"
            return 1
        fi
        
        # Clean up the result
        high_bloat_count=$(echo "$high_bloat_count" | tr -d ' ')
    
    if [ "$high_bloat_count" -gt 0 ]; then
        log "WARN" "Found $high_bloat_count high bloat indexes - running REINDEX"
        
        # Get list of high bloat indexes using actual table statistics
        local high_bloat_indexes=$(docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -t -c "
            SELECT indexrelname FROM (
                SELECT 
                    s.indexrelname,
                    ROUND((t.n_dead_tup::float / (t.n_live_tup + t.n_dead_tup)) * 100, 2) as bloat_ratio
                FROM pg_stat_user_indexes s
                JOIN pg_index i ON s.indexrelid = i.indexrelid
                JOIN pg_stat_user_tables t ON s.relid = t.relid
                WHERE s.schemaname = 'public'
                AND t.n_live_tup > 0
                AND t.n_dead_tup > (t.n_live_tup * 0.3)  -- More than 30% dead tuples
            ) bloat_check
        " 2>&1)
        
        # Reindex each high bloat index with safety checks
        # Use process substitution to avoid subshell variable issues
        local reindex_success_count=0
        local reindex_failure_count=0
        
        while IFS= read -r indexname; do
            if [ -n "$indexname" ]; then
                log "INFO" "Reindexing $indexname..."
                
                # Check index state before REINDEX
                local before_state=$(docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -t -c "
                    SELECT indexdef FROM pg_indexes WHERE indexname = '$indexname'
                " 2>&1 | tr -d ' ')
                
                if [ -z "$before_state" ]; then
                    log "ERROR" "Cannot find index $indexname before REINDEX"
                    ((reindex_failure_count++))
                    continue
                fi
                
                # Run REINDEX with timeout protection (no transaction - REINDEX can't be rolled back)
                log "INFO" "Starting REINDEX on $indexname (this may take several minutes)..."
                
                local reindex_result
                local reindex_exit_code
                
                if command -v timeout >/dev/null 2>&1; then
                    reindex_result=$(timeout 300 docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -c "REINDEX INDEX $indexname;" 2>&1)
                    reindex_exit_code=$?
                else
                    # Fallback without timeout - user will need to manually interrupt if it hangs
                    log "WARN" "No timeout protection - REINDEX may hang indefinitely"
                    reindex_result=$(docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -c "REINDEX INDEX $indexname;" 2>&1)
                    reindex_exit_code=$?
                fi
                
                if [ $reindex_exit_code -eq 0 ]; then
                    # Verify index after REINDEX
                    local after_state=$(docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -t -c "
                        SELECT indexdef FROM pg_indexes WHERE indexname = '$indexname'
                    " 2>&1 | tr -d ' ')
                    
                    if [ "$before_state" != "$after_state" ]; then
                        log "INFO" "Successfully reindexed $indexname"
                        ((reindex_success_count++))
                    else
                        log "WARN" "REINDEX completed but index definition unchanged for $indexname"
                        ((reindex_failure_count++))
                    fi
                elif [ $reindex_exit_code -eq 124 ]; then
                    log "ERROR" "REINDEX on $indexname timed out after 5 minutes"
                    ((reindex_failure_count++))
                else
                    log "ERROR" "Failed to reindex $indexname: $reindex_result"
                    ((reindex_failure_count++))
                fi
            fi
        done < <(echo "$high_bloat_indexes")
        
        # Log summary of REINDEX operations
        log "INFO" "REINDEX summary: $reindex_success_count successful, $reindex_failure_count failed"
        
        log "INFO" "Index optimization completed"
    else
        log "INFO" "No high bloat indexes detected - optimization not needed"
    fi
}

# Clean up old logs
cleanup_logs() {
    log "INFO" "Cleaning up old log files..."
    
    # Keep only last 30 days of logs
    find "$PROJECT_DIR/logs" -name "*.log" -type f -mtime +30 -delete 2>/dev/null || true
    
    log "INFO" "Log cleanup completed"
}

# Main execution
main() {
    log "INFO" "=== Database Health Maintenance Started ==="
    
    # Create logs directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Check prerequisites
    check_docker
    check_postgres_container
    check_timeout
    
    # Run maintenance tasks
    check_database_health
    run_maintenance
    optimize_indexes
    cleanup_logs
    
    log "INFO" "=== Database Health Maintenance Completed ==="
}

# Handle script arguments
case "${1:-}" in
    "check")
        check_database_health
        ;;
    "maintain")
        run_maintenance
        ;;
    "optimize")
        optimize_indexes
        ;;
    "cleanup")
        cleanup_logs
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  check     - Check database health only"
        echo "  maintain  - Run maintenance only"
        echo "  optimize  - Optimize indexes only"
        echo "  cleanup   - Clean up logs only"
        echo "  (none)    - Run all maintenance tasks"
        echo ""
        echo "Examples:"
        echo "  $0              # Run all maintenance"
        echo "  $0 check        # Check health only"
        echo "  $0 optimize     # Optimize indexes only"
        ;;
    *)
        main
        ;;
esac
