-- Check Index Usage Statistics in PostgreSQL
-- This script shows which indexes are being used and which are unused
-- Run this to identify indexes that can be safely dropped

-- 1. Show all indexes with their usage statistics
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as "Index Scans",
    idx_tup_read as "Tuples Read",
    idx_tup_fetch as "Tuples Fetched",
    CASE 
        WHEN idx_scan = 0 THEN 'UNUSED'
        WHEN idx_scan < 10 THEN 'RARELY USED'
        WHEN idx_scan < 100 THEN 'OCCASIONALLY USED'
        ELSE 'FREQUENTLY USED'
    END as "Usage Status"
FROM pg_stat_user_indexes 
ORDER BY idx_scan ASC, tablename, indexname;

-- 2. Show only unused indexes (idx_scan = 0)
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as "Index Scans",
    'UNUSED - Consider dropping' as "Recommendation"
FROM pg_stat_user_indexes 
WHERE idx_scan = 0
ORDER BY tablename, indexname;

-- 3. Show indexes with very low usage (less than 5 scans)
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as "Index Scans",
    idx_tup_read as "Tuples Read",
    'LOW USAGE - Monitor or consider dropping' as "Recommendation"
FROM pg_stat_user_indexes 
WHERE idx_scan < 5 AND idx_scan > 0
ORDER BY idx_scan ASC, tablename, indexname;

-- 4. Show most frequently used indexes
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as "Index Scans",
    idx_tup_read as "Tuples Read",
    idx_tup_fetch as "Tuples Fetched",
    'HIGH USAGE - Keep this index' as "Recommendation"
FROM pg_stat_user_indexes 
WHERE idx_scan > 100
ORDER BY idx_scan DESC, tablename, indexname;

-- 5. Show index size information
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as "Index Size",
    idx_scan as "Index Scans",
    CASE 
        WHEN idx_scan = 0 THEN 'UNUSED - Consider dropping'
        WHEN idx_scan < 10 THEN 'RARELY USED - Monitor'
        ELSE 'ACTIVELY USED - Keep'
    END as "Recommendation"
FROM pg_stat_user_indexes 
ORDER BY pg_relation_size(indexrelid) DESC, idx_scan ASC;

-- 6. Summary of index usage across all tables
SELECT 
    tablename,
    COUNT(*) as "Total Indexes",
    COUNT(CASE WHEN idx_scan = 0 THEN 1 END) as "Unused Indexes",
    COUNT(CASE WHEN idx_scan > 0 THEN 1 END) as "Used Indexes",
    SUM(CASE WHEN idx_scan = 0 THEN pg_relation_size(indexrelid) ELSE 0 END) as "Unused Index Size (bytes)",
    pg_size_pretty(SUM(CASE WHEN idx_scan = 0 THEN pg_relation_size(indexrelid) ELSE 0 END)) as "Unused Index Size (readable)"
FROM pg_stat_user_indexes 
GROUP BY tablename
ORDER BY "Unused Index Size (bytes)" DESC;

-- 7. Check for duplicate indexes (same columns, different names)
-- This can help identify redundant indexes
WITH duplicate_indexes AS (
    SELECT 
        tablename,
        indexdef,
        COUNT(*) as count,
        array_agg(indexname) as index_names
    FROM pg_indexes 
    WHERE schemaname = 'public'
    GROUP BY tablename, indexdef
    HAVING COUNT(*) > 1
)
SELECT 
    tablename,
    indexdef,
    count as "Duplicate Count",
    index_names as "Index Names",
    'DUPLICATE INDEXES - Consider dropping one' as "Recommendation"
FROM duplicate_indexes
ORDER BY tablename, count DESC;

-- 8. Show index creation time and last usage
-- This helps identify old indexes that might be legacy
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_stat_get_last_analyze_time(indexrelid) as "Last Analyzed",
    pg_stat_get_last_vacuum_time(indexrelid) as "Last Vacuumed",
    idx_scan as "Total Scans",
    CASE 
        WHEN idx_scan = 0 THEN 'NEVER USED'
        ELSE 'USED'
    END as "Usage Status"
FROM pg_stat_user_indexes 
ORDER BY pg_stat_get_last_analyze_time(indexrelid) ASC NULLS LAST;



