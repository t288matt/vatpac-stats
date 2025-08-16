-- Quick Database Status Check
-- Run this to see if data is flowing into the database

-- 1. Check current table counts
SELECT 
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_rows,
    n_dead_tup as dead_rows
FROM pg_stat_user_tables 
ORDER BY n_live_tup DESC;

-- 2. Check recent activity in flights table
SELECT 
    COUNT(*) as total_flights,
    COUNT(CASE WHEN last_updated_api >= NOW() - INTERVAL '1 hour' THEN 1 END) as flights_last_hour,
    COUNT(CASE WHEN last_updated_api >= NOW() - INTERVAL '10 minutes' THEN 1 END) as flights_last_10min,
    COUNT(CASE WHEN last_updated_api >= NOW() - INTERVAL '1 minute' THEN 1 END) as flights_last_minute,
    MAX(last_updated_api) as most_recent_update
FROM flights;

-- 3. Check recent activity in controllers table
SELECT 
    COUNT(*) as total_controllers,
    COUNT(CASE WHEN last_updated >= NOW() - INTERVAL '1 hour' THEN 1 END) as controllers_last_hour,
    COUNT(CASE WHEN last_updated >= NOW() - INTERVAL '10 minutes' THEN 1 END) as controllers_last_10min,
    COUNT(CASE WHEN last_updated >= NOW() - INTERVAL '1 minute' THEN 1 END) as controllers_last_minute,
    MAX(last_updated) as most_recent_update
FROM controllers;

-- 4. Check recent activity in transceivers table
SELECT 
    COUNT(*) as total_transceivers,
    COUNT(CASE WHEN last_updated >= NOW() - INTERVAL '1 hour' THEN 1 END) as transceivers_last_hour,
    COUNT(CASE WHEN last_updated >= NOW() - INTERVAL '10 minutes' THEN 1 END) as transceivers_last_10min,
    COUNT(CASE WHEN last_updated >= NOW() - INTERVAL '1 minute' THEN 1 END) as transceivers_last_minute,
    MAX(last_updated) as most_recent_update
FROM transceivers;

-- 5. Check sector tracking activity
SELECT 
    COUNT(*) as total_sector_entries,
    COUNT(CASE WHEN exit_timestamp IS NULL THEN 1 END) as open_sectors,
    COUNT(CASE WHEN exit_timestamp IS NOT NULL THEN 1 END) as closed_sectors,
    COUNT(CASE WHEN entry_timestamp >= NOW() - INTERVAL '1 hour' THEN 1 END) as sectors_last_hour,
    COUNT(CASE WHEN entry_timestamp >= NOW() - INTERVAL '10 minutes' THEN 1 END) as sectors_last_10min,
    COUNT(CASE WHEN entry_timestamp >= NOW() - INTERVAL '1 minute' THEN 1 END) as sectors_last_minute
FROM flight_sector_occupancy;

-- 6. Show sample of recent flights
SELECT 
    callsign,
    latitude,
    longitude,
    altitude,
    last_updated_api,
    EXTRACT(EPOCH FROM (NOW() - last_updated_api))/60 as minutes_ago
FROM flights 
WHERE last_updated_api >= NOW() - INTERVAL '10 minutes'
ORDER BY last_updated_api DESC 
LIMIT 5;

-- 7. Show sample of recent sector entries
SELECT 
    callsign,
    sector_name,
    entry_timestamp,
    CASE WHEN exit_timestamp IS NULL THEN 'OPEN' ELSE 'CLOSED' END as status,
    EXTRACT(EPOCH FROM (NOW() - entry_timestamp))/60 as minutes_since_entry
FROM flight_sector_occupancy 
WHERE entry_timestamp >= NOW() - INTERVAL '10 minutes'
ORDER BY entry_timestamp DESC 
LIMIT 5;

-- 8. Check if cleanup process is working (look for recent sector exits)
SELECT 
    COUNT(*) as recent_sector_exits,
    AVG(EXTRACT(EPOCH FROM (exit_timestamp - entry_timestamp))/60) as avg_duration_minutes
FROM flight_sector_occupancy 
WHERE exit_timestamp >= NOW() - INTERVAL '1 hour'
AND exit_timestamp IS NOT NULL;

-- 9. Check database size and growth
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
