-- Longest Online Controllers (All Types)
-- 
-- This query finds which controllers were online for the longest time,
-- including total aircraft handled, for all controller types.
--
-- Usage:
--   docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f scripts/longest_online_controllers.sql
--

-- Find longest online controllers of any type
WITH all_controllers AS (
    SELECT 
        callsign,
        name as controller_name,
        cid,
        rating,
        facility,
        server,
        session_start_time,
        session_end_time,
        session_duration_minutes,
        total_aircraft_handled,
        peak_aircraft_count,
        frequencies_used,
        aircraft_details
    FROM controller_summaries
    WHERE session_duration_minutes > 0  -- Must have valid session duration
        AND session_start_time >= NOW() - INTERVAL '1 month'  -- Last month
),
ranked_controllers AS (
    SELECT 
        callsign,
        controller_name,
        cid,
        rating,
        facility,
        server,
        session_start_time,
        session_end_time,
        session_duration_minutes,
        total_aircraft_handled,
        peak_aircraft_count,
        frequencies_used,
        aircraft_details,
        -- Rank by session duration (longest first)
        ROW_NUMBER() OVER (ORDER BY session_duration_minutes DESC) as duration_rank,
        -- Rank by aircraft handled (most first)
        ROW_NUMBER() OVER (ORDER BY total_aircraft_handled DESC) as aircraft_rank
    FROM all_controllers
    WHERE session_duration_minutes > 0  -- Additional safety check
)
SELECT 
    duration_rank,
    callsign,
    controller_name,
    cid,
    rating,
    facility,
    server,
    session_start_time,
    session_end_time,
    session_duration_minutes,
    total_aircraft_handled,
    peak_aircraft_count,
    -- Calculate average aircraft per hour
    ROUND(total_aircraft_handled::numeric / NULLIF(session_duration_minutes / 60, 0), 1) as avg_aircraft_per_hour,
    -- Show which frequencies were used
    frequencies_used,
    -- Show aircraft interaction details
    aircraft_details
FROM ranked_controllers
ORDER BY session_duration_minutes DESC
LIMIT 20;

-- ============================================================================
-- SUMMARY STATISTICS FOR ALL CONTROLLERS
-- ============================================================================
-- This section provides summary statistics for all controllers

WITH controller_stats AS (
    SELECT 
        session_duration_minutes,
        total_aircraft_handled,
        peak_aircraft_count,
        -- Categorize by controller type based on callsign
        CASE 
            WHEN callsign LIKE '%GND%' THEN 'GND'
            WHEN callsign LIKE '%TWR%' THEN 'TWR'
            WHEN callsign LIKE '%APP%' THEN 'APP'
            WHEN callsign LIKE '%CTR%' THEN 'CTR'
            WHEN callsign LIKE '%FSS%' THEN 'FSS'
            WHEN callsign LIKE '%DEL%' THEN 'DEL'
            ELSE 'OTHER'
        END as controller_type
    FROM controller_summaries
    WHERE session_duration_minutes > 0
        AND session_start_time >= NOW() - INTERVAL '1 month'
)
SELECT 
    controller_type,
    COUNT(*) as total_sessions,
    ROUND(AVG(session_duration_minutes), 1) as avg_session_duration_minutes,
    MIN(session_duration_minutes) as shortest_session_minutes,
    MAX(session_duration_minutes) as longest_session_minutes,
    ROUND(STDDEV(session_duration_minutes), 1) as std_dev_minutes,
    ROUND(AVG(total_aircraft_handled), 1) as avg_aircraft_handled,
    MIN(total_aircraft_handled) as min_aircraft_handled,
    MAX(total_aircraft_handled) as max_aircraft_handled,
    ROUND(AVG(peak_aircraft_count), 1) as avg_peak_aircraft,
    -- Calculate efficiency (aircraft per hour)
    ROUND(AVG(total_aircraft_handled::numeric / NULLIF(session_duration_minutes / 60, 0)), 1) as avg_efficiency_aircraft_per_hour
FROM controller_stats
GROUP BY controller_type
ORDER BY avg_session_duration_minutes DESC;

