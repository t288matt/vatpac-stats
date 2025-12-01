-- Find similar examples of flight_summaries duplication like the BUCK03 case
-- This script analyzes the database to find flights with multiple route formats
-- that would cause the same duplication issue described in the production report

-- 1. Find flights with multiple summary records (like BUCK03)
SELECT 
    callsign,
    cid,
    departure,
    arrival,
    logon_time,
    COUNT(*) as summary_count,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created,
    COUNT(DISTINCT route) as route_variations
FROM flight_summaries
GROUP BY callsign, cid, departure, arrival, logon_time
HAVING COUNT(*) > 1
ORDER BY summary_count DESC, callsign
LIMIT 20;

-- 2. Find flights with multiple route formats in the flights table (ROOT CAUSE)
WITH route_analysis AS (
    SELECT 
        callsign,
        cid,
        departure,
        arrival,
        logon_time,
        route,
        COUNT(*) as record_count,
        MIN(last_updated) as first_seen,
        MAX(last_updated) as last_seen
    FROM flights
    WHERE route IS NOT NULL 
      AND route != ''
      AND last_updated >= NOW() - INTERVAL '7 days'
    GROUP BY callsign, cid, departure, arrival, logon_time, route
),
flight_groups AS (
    SELECT 
        callsign,
        cid,
        departure,
        arrival,
        logon_time,
        COUNT(DISTINCT route) as route_count,
        SUM(record_count) as total_records,
        STRING_AGG(DISTINCT route, ' | ') as all_routes
    FROM route_analysis
    GROUP BY callsign, cid, departure, arrival, logon_time
    HAVING COUNT(DISTINCT route) > 1
)
SELECT *
FROM flight_groups
ORDER BY route_count DESC, total_records DESC
LIMIT 15;

-- 3. Find specific examples like BUCK03 (high duplication factor)
SELECT 
    callsign,
    cid,
    departure,
    arrival,
    logon_time,
    COUNT(*) as summary_count,
    COUNT(DISTINCT route) as route_variations,
    STRING_AGG(DISTINCT route, ' | ') as all_routes
FROM flight_summaries
GROUP BY callsign, cid, departure, arrival, logon_time
HAVING COUNT(*) >= 50  -- High duplication threshold
ORDER BY summary_count DESC
LIMIT 10;

-- 4. Analyze the UPDATE WHERE clause issue
-- Find flights where the UPDATE WHERE clause would fail to match
-- due to multiple records with same (callsign, cid, departure, arrival, logon_time)
-- but different route formats
WITH flight_route_groups AS (
    SELECT 
        f.callsign,
        f.cid,
        f.departure,
        f.arrival,
        COALESCE(f.logon_time, f.last_updated) as logon_time,
        f.route,
        COUNT(*) as record_count
    FROM flights f
    WHERE f.last_updated >= NOW() - INTERVAL '7 days'
      AND f.route IS NOT NULL
      AND f.route != ''
    GROUP BY f.callsign, f.cid, f.departure, f.arrival, 
             COALESCE(f.logon_time, f.last_updated), f.route
),
problematic_flights AS (
    SELECT 
        callsign,
        cid,
        departure,
        arrival,
        logon_time,
        COUNT(DISTINCT route) as route_variations,
        SUM(record_count) as total_records,
        STRING_AGG(DISTINCT route, ' | ') as all_routes
    FROM flight_route_groups
    GROUP BY callsign, cid, departure, arrival, logon_time
    HAVING COUNT(DISTINCT route) > 1
)
SELECT *
FROM problematic_flights
ORDER BY route_variations DESC, total_records DESC
LIMIT 10;

-- 5. Check for recent BUCK03-like patterns (October 2024)
SELECT 
    callsign,
    cid,
    departure,
    arrival,
    logon_time,
    COUNT(*) as summary_count,
    COUNT(DISTINCT route) as route_variations,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created
FROM flight_summaries
WHERE created_at >= '2024-10-01'
  AND created_at < '2024-11-01'
GROUP BY callsign, cid, departure, arrival, logon_time
HAVING COUNT(*) >= 10  -- Moderate duplication threshold
ORDER BY summary_count DESC
LIMIT 10;

-- 6. Summary statistics
SELECT 
    COUNT(*) as total_summaries,
    COUNT(DISTINCT callsign) as unique_flights,
    COUNT(DISTINCT CONCAT(callsign, '|', cid, '|', departure, '|', arrival, '|', logon_time)) as unique_sessions,
    AVG(duplicate_count) as avg_duplicates_per_session,
    (COUNT(*) - COUNT(DISTINCT CONCAT(callsign, '|', cid, '|', departure, '|', arrival, '|', logon_time))) as total_duplicates,
    ROUND(((COUNT(*) - COUNT(DISTINCT CONCAT(callsign, '|', cid, '|', departure, '|', arrival, '|', logon_time)))::DECIMAL / COUNT(*)) * 100, 2) as duplication_percentage
FROM (
    SELECT 
        callsign,
        cid,
        departure,
        arrival,
        logon_time,
        COUNT(*) as duplicate_count
    FROM flight_summaries
    GROUP BY callsign, cid, departure, arrival, logon_time
) session_counts;

-- 7. Find the exact BUCK03 case if it exists
SELECT 
    callsign,
    cid,
    departure,
    arrival,
    logon_time,
    COUNT(*) as summary_count,
    COUNT(DISTINCT route) as route_variations,
    STRING_AGG(DISTINCT route, ' | ') as all_routes,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created
FROM flight_summaries
WHERE callsign = 'BUCK03'
GROUP BY callsign, cid, departure, arrival, logon_time
ORDER BY summary_count DESC;

-- 8. Find flights with exactly 210 summaries (like the report mentions)
SELECT 
    callsign,
    cid,
    departure,
    arrival,
    logon_time,
    COUNT(*) as summary_count,
    COUNT(DISTINCT route) as route_variations,
    STRING_AGG(DISTINCT route, ' | ') as all_routes
FROM flight_summaries
GROUP BY callsign, cid, departure, arrival, logon_time
HAVING COUNT(*) = 210
ORDER BY callsign;









