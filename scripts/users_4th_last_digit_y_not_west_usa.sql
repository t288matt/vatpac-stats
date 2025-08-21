-- Users with 4th Last Digit of Name Being 'Y' Not Connected to West USA Server Over Past Week
-- 
-- This query finds all users (pilots and controllers) whose name has 'Y' as the 4th last character
-- and who have NOT connected to the USA-WEST server in the past week.
--
-- Usage:
--   docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f scripts/users_4th_last_digit_y_not_west_usa.sql
--

-- ============================================================================
-- USERS WITH 4TH LAST DIGIT OF NAME BEING 'Y' NOT CONNECTED TO WEST USA SERVER
-- ============================================================================

-- Main query: Find users with 4th last digit 'Y' not connected to USA-WEST server
SELECT DISTINCT ON (cid)
    cid,
    name,
    user_type,
    servers_connected_to,
    unique_servers_count,
    first_connection_utc,
    last_activity_utc,
    hours_between_first_last
FROM (
    -- Subquery to get all the data we need
    SELECT 
        aupw.cid,
        aupw.name,
        aupw.user_type,
        STRING_AGG(DISTINCT aupw.server, ', ' ORDER BY aupw.server) AS servers_connected_to,
        COUNT(DISTINCT aupw.server) AS unique_servers_count,
        MIN(aupw.logon_time) AT TIME ZONE 'UTC' AS first_connection_utc,
        MAX(aupw.last_updated) AT TIME ZONE 'UTC' AS last_activity_utc,
        EXTRACT(EPOCH FROM (MAX(aupw.last_updated) - MIN(aupw.logon_time)))/3600 AS hours_between_first_last
    FROM (
        -- Pilots from flights table
        SELECT 
            cid,
            name,
            'Pilot' AS user_type,
            server,
            logon_time,
            last_updated
        FROM flights 
        WHERE logon_time >= NOW() AT TIME ZONE 'UTC' - INTERVAL '7 days'
          AND cid IS NOT NULL
          AND name IS NOT NULL
          AND LENGTH(name) >= 4  -- Ensure name has at least 4 characters
          AND SUBSTRING(name FROM LENGTH(name) - 3 FOR 1) = 'Y'  -- 4th last character is 'Y'
        
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
        WHERE logon_time >= NOW() AT TIME ZONE 'UTC' - INTERVAL '7 days'
          AND cid IS NOT NULL
          AND name IS NOT NULL
          AND LENGTH(name) >= 4  -- Ensure name has at least 4 characters
          AND SUBSTRING(name FROM LENGTH(name) - 3 FOR 1) = 'Y'  -- 4th last character is 'Y'
    ) aupw
    WHERE aupw.cid NOT IN (
        -- Find users who have connected to USA-WEST server in the past week
        SELECT DISTINCT cid
        FROM (
            SELECT cid, server FROM flights 
            WHERE logon_time >= NOW() AT TIME ZONE 'UTC' - INTERVAL '7 days'
              AND cid IS NOT NULL
              AND server = 'USA-WEST'
            UNION ALL
            SELECT cid, server FROM controllers 
            WHERE logon_time >= NOW() AT TIME ZONE 'UTC' - INTERVAL '7 days'
              AND cid IS NOT NULL
              AND server = 'USA-WEST'
        ) west_users
    )
    GROUP BY aupw.cid, aupw.name, aupw.user_type
) final_results
ORDER BY 
    cid,  -- First order by CID for DISTINCT ON
    unique_servers_count DESC,  -- Then by servers count
    last_activity_utc DESC;     -- Then by most recent activity

-- ============================================================================
-- SUMMARY STATISTICS
-- ============================================================================

-- Count of users with 4th last digit 'Y' not connected to USA-WEST
SELECT 
    COUNT(DISTINCT cid) AS total_unique_users_4th_last_y_not_connected_to_west,
    COUNT(DISTINCT CASE WHEN user_type = 'Pilot' THEN cid END) AS unique_pilots_4th_last_y_not_connected_to_west,
    COUNT(DISTINCT CASE WHEN user_type = 'Controller' THEN cid END) AS unique_controllers_4th_last_y_not_connected_to_west
FROM (
    SELECT DISTINCT 
        aupw.cid,
        aupw.user_type
    FROM (
        -- Pilots from flights table
        SELECT 
            cid,
            'Pilot' AS user_type,
            server
        FROM flights 
        WHERE logon_time >= NOW() AT TIME ZONE 'UTC' - INTERVAL '7 days'
          AND cid IS NOT NULL
          AND name IS NOT NULL
          AND LENGTH(name) >= 4
          AND SUBSTRING(name FROM LENGTH(name) - 3 FOR 1) = 'Y'
        
        UNION ALL
        
        -- Controllers from controllers table
        SELECT 
            cid,
            'Controller' AS user_type,
            server
        FROM controllers 
        WHERE logon_time >= NOW() AT TIME ZONE 'UTC' - INTERVAL '7 days'
          AND cid IS NOT NULL
          AND name IS NOT NULL
          AND LENGTH(name) >= 4
          AND SUBSTRING(name FROM LENGTH(name) - 3 FOR 1) = 'Y'
    ) aupw
    WHERE aupw.cid NOT IN (
        SELECT DISTINCT cid
        FROM (
            SELECT cid FROM flights 
            WHERE logon_time >= NOW() AT TIME ZONE 'UTC' - INTERVAL '7 days'
              AND cid IS NOT NULL
              AND server = 'USA-WEST'
            UNION ALL
            SELECT cid FROM controllers 
            WHERE logon_time >= NOW() AT TIME ZONE 'UTC' - INTERVAL '7 days'
              AND cid IS NOT NULL
              AND server = 'USA-WEST'
        ) west_users
    )
) summary_stats;

-- Server distribution for users with 4th last digit 'Y' not connected to USA-WEST
SELECT 
    server,
    COUNT(DISTINCT cid) AS unique_users
FROM (
    -- Pilots from flights table
    SELECT 
        cid,
        server
    FROM flights 
    WHERE logon_time >= NOW() AT TIME ZONE 'UTC' - INTERVAL '7 days'
      AND cid IS NOT NULL
      AND name IS NOT NULL
      AND LENGTH(name) >= 4
      AND SUBSTRING(name FROM LENGTH(name) - 3 FOR 1) = 'Y'
    
    UNION ALL
    
    -- Controllers from controllers table
    SELECT 
        cid,
        server
    FROM controllers 
    WHERE logon_time >= NOW() AT TIME ZONE 'UTC' - INTERVAL '7 days'
      AND cid IS NOT NULL
      AND name IS NOT NULL
      AND LENGTH(name) >= 4
      AND SUBSTRING(name FROM LENGTH(name) - 3 FOR 1) = 'Y'
) aupw
WHERE aupw.cid NOT IN (
    SELECT DISTINCT cid
    FROM (
        SELECT cid FROM flights 
        WHERE logon_time >= NOW() AT TIME ZONE 'UTC' - INTERVAL '7 days'
          AND cid IS NOT NULL
          AND server = 'USA-WEST'
        UNION ALL
        SELECT cid FROM controllers 
        WHERE logon_time >= NOW() AT TIME ZONE 'UTC' - INTERVAL '7 days'
          AND cid IS NOT NULL
          AND server = 'USA-WEST'
    ) west_users
)
  AND aupw.server IS NOT NULL
GROUP BY server
ORDER BY unique_users DESC;

-- ============================================================================
-- NAME ANALYSIS
-- ============================================================================

-- Show the name pattern analysis for verification (unique by CID)
SELECT DISTINCT ON (cid)
    cid,
    name,
    LENGTH(name) AS name_length,
    SUBSTRING(name FROM LENGTH(name) - 3 FOR 1) AS fourth_last_character,
    SUBSTRING(name FROM LENGTH(name) - 2 FOR 1) AS third_last_character,
    SUBSTRING(name FROM LENGTH(name) - 1 FOR 1) AS second_last_character,
    SUBSTRING(name FROM LENGTH(name) FOR 1) AS last_character
FROM (
    -- Pilots from flights table
    SELECT 
        cid,
        name
    FROM flights 
    WHERE logon_time >= NOW() AT TIME ZONE 'UTC' - INTERVAL '7 days'
      AND cid IS NOT NULL
      AND name IS NOT NULL
      AND LENGTH(name) >= 4
      AND SUBSTRING(name FROM LENGTH(name) - 3 FOR 1) = 'Y'
    
    UNION ALL
    
    -- Controllers from controllers table
    SELECT 
        cid,
        name
    FROM controllers 
    WHERE logon_time >= NOW() AT TIME ZONE 'UTC' - INTERVAL '7 days'
      AND cid IS NOT NULL
      AND name IS NOT NULL
      AND LENGTH(name) >= 4
      AND SUBSTRING(name FROM LENGTH(name) - 3 FOR 1) = 'Y'
) name_analysis
ORDER BY cid, name;
