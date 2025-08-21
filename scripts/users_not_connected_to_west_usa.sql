-- Users Not Connected to West USA Server Over Past Week
-- 
-- This query finds all users (pilots and controllers) who have NOT connected to
-- the USA-WEST server in the past week, but have connected to other servers.
--
-- Usage:
--   docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f scripts/users_not_connected_to_west_usa.sql
--

-- ============================================================================
-- USERS NOT CONNECTED TO WEST USA SERVER OVER PAST WEEK
-- ============================================================================

-- Get the date 7 days ago (UTC)
WITH week_ago AS (
    SELECT NOW() AT TIME ZONE 'UTC' - INTERVAL '7 days' AS cutoff_date
),

-- Find all unique users (pilots and controllers) from the past week
all_users_past_week AS (
    -- Pilots from flights table
    SELECT 
        cid,
        name,
        'Pilot' AS user_type,
        server,
        logon_time,
        last_updated
    FROM flights 
    WHERE logon_time >= (SELECT cutoff_date FROM week_ago)
      AND cid IS NOT NULL
      AND name IS NOT NULL
    
    UNION ALL
    
    -- Controllers from controllers table
    SELECT 
        cid,
        name,
        'Controller' AS user_type,
        server,
        logon_time,
        last_updated
    FROM controllers 
    WHERE logon_time >= (SELECT cutoff_date FROM week_ago)
      AND cid IS NOT NULL
      AND name IS NOT NULL
),

-- Find users who have connected to USA-WEST server in the past week
users_connected_to_west AS (
    SELECT DISTINCT cid
    FROM all_users_past_week
    WHERE server = 'USA-WEST'
),

-- Find users who have NOT connected to USA-WEST server in the past week
users_not_connected_to_west AS (
    SELECT DISTINCT 
        aupw.cid,
        aupw.name,
        aupw.user_type,
        STRING_AGG(DISTINCT aupw.server, ', ' ORDER BY aupw.server) AS servers_connected_to,
        COUNT(DISTINCT aupw.server) AS unique_servers_count,
        MIN(aupw.logon_time) AS first_connection,
        MAX(aupw.last_updated) AS last_activity
    FROM all_users_past_week aupw
    WHERE aupw.cid NOT IN (SELECT cid FROM users_connected_to_west)
    GROUP BY aupw.cid, aupw.name, aupw.user_type
)

-- Main query results
SELECT 
    cid,
    name,
    user_type,
    servers_connected_to,
    unique_servers_count,
    first_connection AT TIME ZONE 'UTC' AS first_connection_utc,
    last_activity AT TIME ZONE 'UTC' AS last_activity_utc,
    EXTRACT(EPOCH FROM (last_activity - first_connection))/3600 AS hours_between_first_last
FROM users_not_connected_to_west
ORDER BY 
    unique_servers_count DESC,  -- Users connected to most different servers first
    last_activity DESC;         -- Most recent activity second

-- ============================================================================
-- SUMMARY STATISTICS
-- ============================================================================

-- Count of users not connected to USA-WEST
SELECT 
    COUNT(*) AS total_users_not_connected_to_west,
    COUNT(CASE WHEN user_type = 'Pilot' THEN 1 END) AS pilots_not_connected_to_west,
    COUNT(CASE WHEN user_type = 'Controller' THEN 1 END) AS controllers_not_connected_to_west
FROM users_not_connected_to_west;

-- Server distribution for users not connected to USA-WEST
SELECT 
    server,
    COUNT(DISTINCT cid) AS unique_users
FROM all_users_past_week aupw
WHERE aupw.cid NOT IN (SELECT cid FROM users_connected_to_west)
  AND aupw.server IS NOT NULL
GROUP BY server
ORDER BY unique_users DESC;
