# PostgreSQL Corruption Prevention Strategies

## Overview
This document outlines strategies to prevent PostgreSQL database corruption and ensure reliable database operations in the VATSIM data collection system.

## 1. Proper Database Initialization Strategy

### Current Problem
- `init.sql` script runs but doesn't create a complete PostgreSQL cluster
- Missing critical system directories (`global/`, system catalogs)
- Incomplete database initialization

### Solution
Use PostgreSQL's built-in initialization properly:

```yaml
# In docker-compose.yml
postgres:
  image: postgres:16-alpine
  environment:
    POSTGRES_DB: vatsim_data
    POSTGRES_USER: vatsim_user
    POSTGRES_PASSWORD: vatsim_password
  volumes:
    - ./database/vatsim:/var/lib/postgresql/data
    - ./config/init.sql:/docker-entrypoint-initdb.d/01-init.sql  # Only runs on empty DB
  # Remove ports until DB is stable
  # ports:
  #   - "5432:5432"
```

## 2. Database Backup Strategy

### Daily Backups
```bash
# Create automated backup script
pg_dump -U vatsim_user -d vatsim_data > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Volume Backups
```bash
# Backup the entire data directory
tar -czf postgres_backup_$(date +%Y%m%d).tar.gz ./database/vatsim/
```

## 3. Health Checks and Monitoring

### Enhanced Health Checks
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U vatsim_user -d vatsim_data && pg_ctl status"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

### Database Validation
```yaml
# Add startup probe
startup_probe:
  test: ["CMD-SHELL", "pg_isready -U vatsim_user -d vatsim_data"]
  initial_delay_seconds: 30
  period_seconds: 10
  failure_threshold: 3
```

## 4. Data Directory Protection

### Read-Only Mounts (for config files)
```yaml
volumes:
  - ./database/vatsim:/var/lib/postgresql/data
  - ./config/postgresql.conf:/var/lib/postgresql/data/postgresql.conf:ro
  - ./config/pg_hba.conf:/var/lib/postgresql/data/pg_hba.conf:ro
```

### Separate Config Volume
```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data
  - postgres_config:/etc/postgresql/postgresql.conf:ro
```

## 5. Version Control for Database Schema

### Migration Scripts
```bash
# Create numbered migration files
001_initial_schema.sql
002_add_flight_summaries.sql
003_add_controller_tracking.sql
```

### Schema Versioning
```sql
-- Add to your init.sql
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW()
);
INSERT INTO schema_version (version) VALUES (1);
```

## 6. Startup Sequence Protection

### Dependencies
```yaml
depends_on:
  postgres:
    condition: service_healthy
    restart: true  # Restart if postgres fails
```

### Restart Policies
```yaml
restart: unless-stopped
deploy:
  restart_policy:
    condition: on-failure
    delay: 5s
    max_attempts: 3
```

## 7. Environment Isolation

### Separate Development/Production
```yaml
# docker-compose.dev.yml
volumes:
  - ./database/dev:/var/lib/postgresql/data

# docker-compose.prod.yml  
volumes:
  - postgres_prod_data:/var/lib/postgresql/data
```

## 8. Monitoring and Alerting

### Log Aggregation
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### Database Metrics
```sql
-- Monitor database health
SELECT 
    schemaname,
    tablename,
    n_tup_ins,
    n_tup_upd,
    n_tup_del
FROM pg_stat_user_tables;
```

## Immediate Action Plan

1. **Start fresh** with proper initialization
2. **Implement daily backups** before adding external access
3. **Add comprehensive health checks**
4. **Test the complete startup sequence**
5. **Only then** add external port exposure for Metabase

## Implementation Priority

### Phase 1 (Critical)
- Proper database initialization
- Basic health checks
- Daily backups

### Phase 2 (Important)
- Enhanced monitoring
- Schema versioning
- Environment isolation

### Phase 3 (Nice to Have)
- Advanced metrics
- Automated recovery
- Performance optimization

## Notes

- **Never expose PostgreSQL ports** until database is fully stable
- **Always backup before major changes**
- **Test startup sequence** in development before production
- **Monitor database health** continuously
- **Use migration scripts** for schema changes

## Last Updated
2025-08-22 - Created after resolving PostgreSQL corruption issues

