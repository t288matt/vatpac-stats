-- Longest Online FSS and CTR Controllers
-- 
-- This query finds which FSS (Flight Service Station) and CTR (Center) controllers
-- were online for the longest time, including total aircraft handled.
--
-- Usage:
--   docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f scripts/longest_online_fss_ctr_controllers.sql
--

-- Find longest online FSS and CTR controllers
WITH fss_ctr_controllers AS (
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
    WHERE callsign LIKE '%FSS%'  -- Flight Service Station controllers
        OR callsign LIKE '%CTR%'  -- Center controllers
        AND session_duration_minutes > 0  -- Must have valid session duration
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
    FROM fss_ctr_controllers
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
-- SUMMARY STATISTICS FOR FSS AND CTR CONTROLLERS
-- ============================================================================
-- This section provides summary statistics for all FSS and CTR controllers

WITH fss_ctr_stats AS (
    SELECT 
        session_duration_minutes,
        total_aircraft_handled,
        peak_aircraft_count,
        -- Categorize by controller type
        CASE 
            WHEN callsign LIKE '%FSS%' THEN 'FSS'
            WHEN callsign LIKE '%CTR%' THEN 'CTR'
            ELSE 'OTHER'
        END as controller_type
    FROM controller_summaries
    WHERE (callsign LIKE '%FSS%' OR callsign LIKE '%CTR%')
        AND session_duration_minutes > 0
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
FROM fss_ctr_stats
GROUP BY controller_type
ORDER BY avg_session_duration_minutes DESC;
