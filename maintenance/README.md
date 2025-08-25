# Database Maintenance Scripts

This folder contains scripts for maintaining database health and preventing index corruption.

## Files

### `maintain_database_health.sh`
Main bash script for database maintenance operations.

**Usage:**
```bash
# Run all maintenance tasks
./maintain_database_health.sh

# Check database health only
./maintain_database_health.sh check

# Run maintenance only
./maintain_database_health.sh maintain

# Optimize indexes only
./maintain_database_health.sh optimize

# Clean up logs only
./maintain_database_health.sh cleanup

# Show help
./maintain_database_health.sh help
```

**Features:**
- Container health validation
- Database health monitoring
- Index optimization with REINDEX
- Log cleanup
- Comprehensive error handling

### `prevent_index_corruption.sql`
PostgreSQL maintenance script that:
- Updates table statistics (ANALYZE)
- Cleans up dead tuples (VACUUM ANALYZE)
- Detects index bloat using real PostgreSQL statistics
- Identifies unused indexes
- Monitors long-running transactions
- Checks for lock conflicts
- Provides maintenance summary

## Scheduling

### Weekly Maintenance (Recommended)
Run every Wednesday at 16:00 UTC:

**Linux/macOS (cron):**
```bash
# Add to crontab
0 16 * * 3 /path/to/your/project/maintenance/maintain_database_health.sh
```

**Windows (Task Scheduler):**
- Create a scheduled task
- Program: `bash`
- Arguments: `maintenance/maintain_database_health.sh`
- Schedule: Weekly, Wednesday, 16:00 UTC

### Post-Deployment
Run after major deployments or schema changes:
```bash
./maintenance/maintain_database_health.sh
```

## Requirements

- Docker running with `vatsim_postgres` container
- PostgreSQL 16+ compatibility
- Bash shell (for the script)
- `timeout` command (optional, for REINDEX timeout protection)

## Logs

Maintenance logs are written to:
```
logs/database_maintenance.log
```

## Safety Features

- **Container Health Checks**: Validates PostgreSQL responsiveness
- **Timeout Protection**: 5-minute timeout for REINDEX operations
- **Error Handling**: Comprehensive error logging and validation
- **Transaction Safety**: Proper handling of REINDEX operations
- **File Validation**: Verifies script copy success before execution

## Monitoring

The scripts provide actionable insights:
- High bloat indexes requiring REINDEX
- Unused indexes that can be dropped
- Long-running transactions
- Lock conflicts
- Database size growth patterns

## Troubleshooting

If scripts fail:
1. Check Docker container status: `docker ps`
2. Verify PostgreSQL connectivity: `docker exec vatsim_postgres pg_isready -U vatsim_user`
3. Check logs: `tail -f logs/database_maintenance.log`
4. Ensure proper file permissions on scripts
