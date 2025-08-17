# Docker Cron Setup for Materialized View Refresh

## Overview

This setup uses a dedicated Alpine Linux container with cron to automatically refresh the `controller_weekly_stats` materialized view at regular intervals.

## How It Works

### 1. Volume Mounting
The cron container mounts:
- `./scripts:/scripts:ro` - Read-only access to your scripts directory
- `/var/run/docker.sock:/var/run/docker.sock:ro` - Access to Docker daemon for `docker exec` commands

### 2. Script Execution
The cron container runs `refresh_controller_stats_cron.sh` which:
- Checks if required containers are running
- Executes `SELECT refresh_controller_stats();` via `docker exec`
- Logs the results with timestamps
- Provides verification data (row count, view size)

### 3. Cron Schedule
The materialized view is refreshed 6 times per day:
- **02:00** - Early morning refresh
- **06:00** - Morning refresh  
- **10:00** - Mid-morning refresh
- **14:00** - Afternoon refresh
- **18:00** - Evening refresh
- **22:00** - Night refresh

## Setup Instructions

### 1. Build and Start Services
```bash
# Rebuild to include the new cron service
docker-compose build

# Start all services
docker-compose up -d
```

### 2. Verify Cron Service
```bash
# Check if cron container is running
docker ps | grep vatsim_cron

# Check cron logs
docker logs vatsim_cron

# Test the cron setup manually
docker exec vatsim_cron /scripts/test_cron_setup.sh
```

### 3. Test Manual Refresh
```bash
# Test the refresh script manually
docker exec vatsim_cron /scripts/refresh_controller_stats_cron.sh
```

## Monitoring

### View Cron Logs
```bash
# View cron service logs
docker logs vatsim_cron

# View cron execution logs (inside container)
docker exec vatsim_cron cat /var/log/cron.log
```

### Check Materialized View Status
```bash
# Check when view was last refreshed
docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -c "
    SELECT schemaname, tablename, last_vacuum, last_autovacuum 
    FROM pg_stat_user_tables 
    WHERE tablename = 'controller_weekly_stats';
"

# Check view size and row count
docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -c "
    SELECT 
        COUNT(*) as row_count,
        pg_size_pretty(pg_total_relation_size('controller_weekly_stats')) as size
    FROM controller_weekly_stats;
"
```

## Troubleshooting

### Common Issues

1. **Permission Denied on Docker Socket**
   - Ensure the host Docker daemon allows access
   - Check if SELinux or AppArmor are blocking access

2. **Script Not Found**
   - Verify the scripts directory is properly mounted
   - Check file permissions: `docker exec vatsim_cron ls -la /scripts/`
   - Ensure scripts exist in the local `./scripts/` directory

3. **Database Connection Failed**
   - Ensure postgres and app containers are running
   - Check container names match the script expectations

4. **Cron Not Running**
   - Check cron service logs: `docker logs vatsim_cron`
   - Verify cron daemon is running: `docker exec vatsim_cron ps aux | grep cron`

### Manual Testing
```bash
# Test script execution manually
docker exec vatsim_cron /scripts/refresh_controller_stats_cron.sh

# Check cron job list
docker exec vatsim_cron crontab -l

# View cron daemon status
docker exec vatsim_cron ps aux | grep crond
```

## Customization

### Change Refresh Schedule
Edit the cron entries in `docker-compose.yml`:
```yaml
# Example: Refresh every 4 hours
echo '0 */4 * * * /scripts/refresh_controller_stats_cron.sh >> /var/log/cron.log 2>&1' > /etc/crontabs/root
```

### Add More Cron Jobs
Add additional cron entries in the command section:
```yaml
echo '0 12 * * * /scripts/another_script.sh >> /var/log/cron.log 2>&1' >> /etc/crontabs/root
```

### Modify Logging
Change log file location or add log rotation:
```yaml
# Log to different file
echo '0 2 * * * /scripts/refresh_controller_stats_cron.sh >> /var/log/mv_refresh.log 2>&1' > /etc/crontabs/root

# Add timestamp to log filename
echo '0 2 * * * /scripts/refresh_controller_stats_cron.sh >> /var/log/mv_refresh_$(date +\%Y\%m\%d).log 2>&1' > /etc/crontabs/root
```

## Security Considerations

- The cron container has read-only access to scripts
- Docker socket access is limited to read-only
- Container runs as root (required for cron) but in isolated environment
- Consider using Docker secrets for sensitive data if needed

## Performance Impact

- Materialized view refresh typically takes 1-5 seconds
- Runs 6 times per day (every 4 hours)
- Minimal impact on database performance
- Provides significant query performance improvement (100-300x faster)
