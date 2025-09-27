-- Check current database cache performance
-- Run this first to see if cache pre-warming would help

SELECT 
    'Current Cache Performance' as check_type,
    datname as database_name,
    round(100.0 * blks_hit / (blks_hit + blks_read), 2) AS cache_hit_ratio_percent,
    blks_hit as blocks_hit,
    blks_read as blocks_read,
    CASE 
        WHEN round(100.0 * blks_hit / (blks_hit + blks_read), 2) > 95 THEN 'Excellent - No pre-warming needed'
        WHEN round(100.0 * blks_hit / (blks_hit + blks_read), 2) > 90 THEN 'Good - Pre-warming may help slightly'
        WHEN round(100.0 * blks_hit / (blks_hit + blks_read), 2) > 80 THEN 'Fair - Pre-warming recommended'
        ELSE 'Poor - Pre-warming strongly recommended'
    END as recommendation
FROM pg_stat_database 
WHERE datname = 'vatsim_data';

-- Also check table-level statistics
SELECT 
    'Table Cache Statistics' as check_type,
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_tuples,
    n_dead_tup as dead_tuples
FROM pg_stat_user_tables 
WHERE schemaname = 'public'
ORDER BY n_live_tup DESC;

