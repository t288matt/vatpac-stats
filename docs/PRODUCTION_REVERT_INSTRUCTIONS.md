# Production Reversion Instructions
## Reverting to Commit 6aa1225d8b654480cf58d884770b96a6d6092b5f

**⚠️ CRITICAL WARNING: This process will completely wipe your production database. Ensure you have proper backups and maintenance windows scheduled.**

### Prerequisites
- Access to production Cursor instance
- Docker and Docker Compose installed
- Git access to the repository
- Maintenance window scheduled
- Team notification sent

---

## Step 1: Create Production Backup

**IMPORTANT: Always backup before any destructive operations**

```bash
# Create timestamped backup
docker-compose exec postgres pg_dump -U vatsim_user vatsim_data > production_backup_$(date +%Y%m%d_%H%M%S).sql

# Example filename: production_backup_20250824_143000.sql
```

**Verify backup was created:**
```bash
ls -la production_backup_*.sql
```

---

## Step 2: Stop All Services

```bash
# Stop all running containers
docker-compose down

# Verify all containers are stopped
docker ps
```

---

## Step 3: Revert Git Repository

```bash
# Hard reset to target commit
git reset --hard 6aa1225d8b654480cf58d884770b96a6d6092b5f

# Clean untracked files and directories
git clean -fd

# Verify reversion
git log --oneline -1
# Should show: 6aa1225 Update README.md
```

---

## Step 4: Reset Database Schema

```bash
# Start only PostgreSQL service
docker-compose up -d postgres

# Wait for PostgreSQL to be healthy
docker-compose ps

# Drop and recreate schema (WIPES ALL DATA)
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Copy init.sql to container
docker cp config/init.sql vatsim_postgres:/tmp/init.sql

# Execute initialization script
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -f /tmp/init.sql
```

---

## Step 5: Rebuild and Restart Services

```bash
# Rebuild containers with reverted code
docker-compose build

# Start all services
docker-compose up -d

# Verify all services are running
docker-compose ps
```

---

## Step 6: Verification

```bash
# Check application status
curl http://localhost:8001/api/status

# Check database tables
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "\dt"

# Check git status
git status
```

---

## Restore from Backup (If Needed)

If you need to restore the previous production state:

```bash
# Stop services
docker-compose down

# Start PostgreSQL
docker-compose up -d postgres

# Drop current schema
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Restore from backup
docker cp production_backup_YYYYMMDD_HHMMSS.sql vatsim_postgres:/tmp/backup.sql
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -f /tmp/backup.sql

# Restart all services
docker-compose up -d
```

---

## Post-Revertion Tasks

1. **Verify Application Functionality**
   - Test API endpoints
   - Check data ingestion
   - Monitor logs for errors

2. **Update Documentation**
   - Note the reversion in system logs
   - Update any deployment records

3. **Team Communication**
   - Notify team of completed reversion
   - Document any issues encountered

---

## Rollback Plan

If the reversion causes issues:

1. **Immediate Rollback**: Use the backup created in Step 1
2. **Investigation**: Check logs and identify root cause
3. **Alternative**: Consider partial reversion or targeted fixes

---

## File Locations

- **Backup files**: Root directory (production_backup_*.sql)
- **Database init**: `config/init.sql`
- **Docker config**: `docker-compose.yml`
- **Application logs**: Check container logs with `docker-compose logs`

---

## Support Commands

```bash
# Check container health
docker-compose ps

# View application logs
docker-compose logs app

# View database logs
docker-compose logs postgres

# Check disk space
df -h

# Check backup file size
ls -lh production_backup_*.sql
```

---

**Last Updated**: 2025-08-24  
**Target Commit**: 6aa1225d8b654480cf58d884770b96a6d6092b5f  
**Author**: System Administrator  
**Environment**: Production


