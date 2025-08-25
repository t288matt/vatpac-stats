-- Prevent Index Corruption Maintenance Script
-- This script implements the prevention measures identified in the root cause analysis
-- Run this script weekly to maintain database health and prevent index corruption

-- Set safe defaults for maintenance operations
SET statement_timeout = '300s';  -- 5 minute timeout for long operations
SET lock_timeout = '60s';        -- 1 minute timeout for locks
SET client_min_messages = 'warning';  -- Reduce noise, show important messages

-- Validate schema access before proceeding
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'public') THEN
        RAISE EXCEPTION 'Schema "public" does not exist or is not accessible';
    END IF;
    
    -- Check if we have access to pg_stat_user_indexes
    IF NOT EXISTS (SELECT 1 FROM pg_stat_user_indexes LIMIT 1) THEN
        RAISE EXCEPTION 'No access to pg_stat_user_indexes - check permissions';
    END IF;
END $$;

-- 1. ANALYZE all tables to update statistics for better query planning
-- This helps PostgreSQL make better decisions about index usage
ANALYZE controllers;
ANALYZE flights;
ANALYZE transceivers;
ANALYZE flight_summaries;
ANALYZE flights_archive;
ANALYZE controller_summaries;
ANALYZE controllers_archive;
ANALYZE flight_sector_occupancy;

-- 2. VACUUM ANALYZE to clean up dead tuples and update statistics
-- This prevents table bloat and maintains index efficiency
VACUUM ANALYZE controllers;
VACUUM ANALYZE flights;
VACUUM ANALYZE transceivers;
VACUUM ANALYZE flight_summaries;
VACUUM ANALYZE flights_archive;
VACUUM ANALYZE controller_summaries;
VACUUM ANALYZE controllers_archive;
VACUUM ANALYZE flight_sector_occupancy;

-- 3. Check for index bloat and fragmentation using PostgreSQL's actual statistics
-- This query identifies indexes that may need attention based on real data
SELECT 
    schemaname,
    relname as tablename,
    indexrelname as indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(i.indexrelid)) as index_size_pretty,
    pg_relation_size(i.indexrelid) as index_size_bytes,
    -- Use actual table bloat statistics instead of arbitrary estimates
    CASE 
        WHEN t.n_dead_tup > 0 THEN 
            ROUND((t.n_dead_tup::float / (t.n_live_tup + t.n_dead_tup)) * 100, 2)
        ELSE 0 
    END as table_bloat_percent,
    t.n_live_tup as live_tuples,
    t.n_dead_tup as dead_tuples,
    CASE 
        WHEN t.n_dead_tup > (t.n_live_tup * 0.3) THEN 'HIGH BLOAT - Consider REINDEX'
        WHEN t.n_dead_tup > (t.n_live_tup * 0.1) THEN 'MEDIUM BLOAT - Monitor'
        ELSE 'LOW BLOAT - OK'
    END as bloat_status
FROM pg_stat_user_indexes s
JOIN pg_index i ON s.indexrelid = i.indexrelid
JOIN pg_stat_user_tables t ON s.relid = t.relid
WHERE s.schemaname = 'public'
    AND t.n_live_tup > 0  -- Only show tables with data
ORDER BY table_bloat_percent DESC, index_size_bytes DESC;

-- 4. Check for unused indexes that can be dropped
-- This reduces maintenance overhead and potential corruption points
-- Updated for PostgreSQL 16 compatibility
SELECT 
    s.schemaname,
    s.relname as tablename,
    s.indexrelname as indexname,
    s.idx_scan,
    s.idx_tup_read,
    s.idx_tup_fetch,
    CASE 
        WHEN s.idx_scan = 0 THEN 'UNUSED - Consider dropping'
        WHEN s.idx_scan < 10 THEN 'RARELY USED - Monitor'
        ELSE 'REGULARLY USED - OK'
    END as usage_status
FROM pg_stat_user_indexes s
WHERE s.schemaname = 'public'
    AND s.idx_scan < 10  -- Show indexes with less than 10 scans
ORDER BY s.idx_scan ASC;

-- 5. Check for long-running transactions that could interfere with checkpoints
-- This helps identify potential checkpoint collision scenarios
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query_start,
    xact_start,
    backend_start,
    state_change,
    EXTRACT(EPOCH FROM (NOW() - query_start)) as duration_seconds,
    query
FROM pg_stat_activity 
WHERE state != 'idle'
    AND query_start < NOW() - INTERVAL '5 minutes'
ORDER BY query_start ASC;

-- 6. Monitor checkpoint activity
-- This shows recent checkpoint performance and frequency
SELECT 
    name,
    setting,
    unit,
    context,
    category
FROM pg_settings 
WHERE name IN (
    'checkpoint_timeout',
    'max_wal_size',
    'min_wal_size',
    'checkpoint_completion_target',
    'checkpoint_warning'
);

-- 7. Check WAL statistics to monitor write patterns
-- This helps identify if WAL is being written too frequently
SELECT 
    pg_current_wal_lsn() as current_wal_lsn,
    pg_walfile_name(pg_current_wal_lsn()) as current_wal_file,
    pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), '0/0')) as total_wal_size;

-- 8. Monitor table and index sizes for growth patterns
-- This helps identify tables that may need more aggressive maintenance
SELECT 
    t.schemaname,
    t.tablename,
    pg_size_pretty(pg_total_relation_size(t.schemaname||'.'||t.tablename)) as total_size,
    pg_size_pretty(pg_relation_size(t.schemaname||'.'||t.tablename)) as table_size,
    pg_size_pretty(pg_total_relation_size(t.schemaname||'.'||t.tablename) - pg_relation_size(t.schemaname||'.'||t.tablename)) as index_size
FROM pg_tables t
WHERE t.schemaname = 'public'
ORDER BY pg_total_relation_size(t.schemaname||'.'||t.tablename) DESC;

-- 9. Check for potential deadlocks or lock conflicts
-- This identifies situations that could lead to corruption
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    wait_event_type,
    wait_event,
    query
FROM pg_stat_activity 
WHERE wait_event_type IS NOT NULL
    AND state != 'idle';

-- 10. Summary of maintenance actions needed
-- This provides a clear action plan based on the above checks
-- Using SELECT statements for connection pooler compatibility

-- Summary header
SELECT '=== INDEX CORRUPTION PREVENTION SUMMARY ===' as summary;

-- Count high bloat indexes using actual table statistics
SELECT 
    'High bloat indexes (>30% dead tuples)' as metric,
    COUNT(*) as count,
    CASE 
        WHEN COUNT(*) > 0 THEN 'ACTION REQUIRED: Run REINDEX on high bloat indexes'
        ELSE 'No high bloat indexes detected'
    END as action
FROM (
    SELECT 1 FROM pg_stat_user_indexes s
    JOIN pg_index i ON s.indexrelid = i.indexrelid
    JOIN pg_stat_user_tables t ON s.relid = t.relid
    WHERE s.schemaname = 'public'
    AND t.n_live_tup > 0
    AND t.n_dead_tup > (t.n_live_tup * 0.3)  -- More than 30% dead tuples
) bloat_check;

-- Count unused indexes
SELECT 
    'Unused indexes' as metric,
    COUNT(*) as count,
    CASE 
        WHEN COUNT(*) > 0 THEN 'ACTION REQUIRED: Consider dropping unused indexes'
        ELSE 'No unused indexes detected'
    END as action
FROM pg_stat_user_indexes 
WHERE schemaname = 'public' AND idx_scan = 0;

-- Count long-running transactions
SELECT 
    'Long-running transactions (>5min)' as metric,
    COUNT(*) as count,
    CASE 
        WHEN COUNT(*) > 0 THEN 'WARNING: Long-running transactions detected - monitor for checkpoint conflicts'
        ELSE 'No long-running transactions detected'
    END as action
FROM pg_stat_activity 
WHERE state != 'idle' 
AND query_start < NOW() - INTERVAL '5 minutes';

-- Count lock conflicts
SELECT 
    'Lock conflicts' as metric,
    COUNT(*) as count,
    CASE 
        WHEN COUNT(*) > 0 THEN 'WARNING: Lock conflicts detected - monitor for potential corruption'
        ELSE 'No lock conflicts detected'
    END as action
FROM pg_stat_activity 
WHERE wait_event_type IS NOT NULL AND state != 'idle';

-- Summary footer
SELECT '=== END SUMMARY ===' as summary;
