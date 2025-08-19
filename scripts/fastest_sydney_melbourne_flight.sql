-- Fastest Flight Time Between Sydney and Melbourne
-- 
-- This query finds the fastest flight time from Sydney (YSSY) to Melbourne (YMML)
-- using flight_summaries table, requiring contact with both SY_TWR and ML_TWR.
--
-- Usage:
--   docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f scripts/fastest_sydney_melbourne_flight.sql
--

-- Find fastest SYD-MEL flights with contact to both SY_TWR and ML_TWR
WITH syd_mel_flights AS (
    SELECT 
        callsign,
        aircraft_type,
        name as pilot_name,
        departure,
        arrival,
        logon_time,
        completion_time,
        time_online_minutes,
        controller_callsigns,
        -- Check if contacted both SY_TWR and ML_TWR
        CASE 
            WHEN controller_callsigns::text LIKE '%SY_TWR%' AND controller_callsigns::text LIKE '%ML_TWR%' 
            THEN true 
            ELSE false 
        END as contacted_both_towers
    FROM flight_summaries
    WHERE departure = 'YSSY'  -- Sydney
        AND arrival = 'YMML'   -- Melbourne
        AND completion_time >= NOW() - INTERVAL '3 months'  -- Last 3 months
        AND time_online_minutes > 0  -- Valid flight duration (must be > 0)
        AND controller_callsigns IS NOT NULL  -- Must have controller data
),
filtered_flights AS (
    SELECT 
        callsign,
        aircraft_type,
        pilot_name,
        departure,
        arrival,
        logon_time,
        completion_time,
        time_online_minutes,
        controller_callsigns
    FROM syd_mel_flights
    WHERE contacted_both_towers = true  -- Must have contacted both towers
),
ranked_flights AS (
    SELECT 
        callsign,
        aircraft_type,
        pilot_name,
        departure,
        arrival,
        logon_time,
        completion_time,
        time_online_minutes,
        controller_callsigns,
        ROW_NUMBER() OVER (ORDER BY time_online_minutes ASC) as rank
    FROM filtered_flights
    WHERE time_online_minutes > 0  -- Additional safety check
)
SELECT 
    rank,
    callsign,
    pilot_name,
    aircraft_type,
    departure,
    arrival,
    logon_time as departure_time,
    completion_time as arrival_time,
    time_online_minutes as flight_duration_minutes,
    -- Count total unique controllers contacted
    (SELECT COUNT(*) FROM jsonb_object_keys(controller_callsigns)) as total_controllers,
    -- Calculate average speed (SYD-MEL is approximately 440nm) with NULLIF protection
    ROUND(440 / NULLIF(time_online_minutes / 60, 0), 1) as avg_speed_knots,
    -- Show which controllers were contacted
    controller_callsigns
FROM ranked_flights
ORDER BY time_online_minutes ASC
LIMIT 20;

-- ============================================================================
-- ALL FLIGHTS BETWEEN SYDNEY AND MELBOURNE FROM YESTERDAY
-- ============================================================================
-- This query finds all flights between Sydney (YSSY) and Melbourne (YMML) 
-- that completed yesterday, regardless of direction or controller contact
--
-- Usage: Run this section separately or modify the above query

-- Find all SYD-MEL flights from yesterday (both directions)
SELECT 
    callsign,
    aircraft_type,
    name as pilot_name,
    departure,
    arrival,
    logon_time as departure_time,
    completion_time as arrival_time,
    time_online_minutes as flight_duration_minutes,
    flight_rules,
    -- Count total unique controllers contacted
    CASE 
        WHEN controller_callsigns IS NOT NULL 
        THEN (SELECT COUNT(*) FROM jsonb_object_keys(controller_callsigns))
        ELSE 0 
    END as total_controllers,
    -- Calculate average speed (SYD-MEL is approximately 440nm) with NULLIF protection
    CASE 
        WHEN time_online_minutes > 0 
        THEN ROUND(440 / NULLIF(time_online_minutes / 60, 0), 1)
        ELSE NULL 
    END as avg_speed_knots,
    -- Show which controllers were contacted
    controller_callsigns,
    -- Show if contacted both towers (for validation)
    CASE 
        WHEN controller_callsigns::text LIKE '%SY_TWR%' AND controller_callsigns::text LIKE '%ML_TWR%' 
        THEN 'Both Towers' 
        WHEN controller_callsigns::text LIKE '%SY_TWR%' 
        THEN 'Sydney Only' 
        WHEN controller_callsigns::text LIKE '%ML_TWR%' 
        THEN 'Melbourne Only' 
        ELSE 'No Tower Contact' 
    END as tower_contact_status
FROM flight_summaries
WHERE (departure = 'YSSY' AND arrival = 'YMML')  -- Sydney to Melbourne
   OR (departure = 'YMML' AND arrival = 'YSSY')  -- Melbourne to Sydney
    AND completion_time >= CURRENT_DATE - INTERVAL '1 day'  -- Yesterday
    AND completion_time < CURRENT_DATE  -- Before today
    AND time_online_minutes > 0  -- Valid flight duration
    AND controller_callsigns IS NOT NULL  -- Must have controller data
    AND controller_callsigns::text LIKE '%SY_TWR%'  -- Must have contacted Sydney Tower
    AND controller_callsigns::text LIKE '%ML_TWR%'  -- Must have contacted Melbourne Tower
    AND (SELECT COUNT(*) FROM jsonb_object_keys(controller_callsigns)) >= 5  -- Must have contacted at least 5 controllers
ORDER BY completion_time DESC, time_online_minutes ASC;

-- ============================================================================
-- SUMMARY STATISTICS FOR FLIGHTS WITH BOTH TOWER CONTACTS
-- ============================================================================
-- This query provides summary statistics for flights that contacted both SY_TWR and ML_TWR

SELECT 
    COUNT(*) as total_flights_both_towers,
    COUNT(CASE WHEN departure = 'YSSY' THEN 1 END) as sydney_to_melbourne_both_towers,
    COUNT(CASE WHEN departure = 'YMML' THEN 1 END) as melbourne_to_sydney_both_towers,
    ROUND(AVG(time_online_minutes), 1) as avg_flight_duration_minutes,
    ROUND(MIN(time_online_minutes), 1) as fastest_flight_minutes,
    ROUND(MAX(time_online_minutes), 1) as slowest_flight_minutes,
    ROUND(AVG(CASE WHEN time_online_minutes > 0 THEN 440 / NULLIF(time_online_minutes / 60, 0) ELSE NULL END), 1) as avg_speed_knots
FROM flight_summaries
WHERE ((departure = 'YSSY' AND arrival = 'YMML') OR (departure = 'YMML' AND arrival = 'YSSY'))
    AND completion_time >= CURRENT_DATE - INTERVAL '1 day'  -- Yesterday
    AND completion_time < CURRENT_DATE  -- Before today
    AND time_online_minutes > 0  -- Valid flight duration
    AND controller_callsigns IS NOT NULL  -- Must have controller data
    AND controller_callsigns::text LIKE '%SY_TWR%'  -- Must have contacted Sydney Tower
    AND controller_callsigns::text LIKE '%ML_TWR%'  -- Must have contacted Melbourne Tower
    AND (SELECT COUNT(*) FROM jsonb_object_keys(controller_callsigns)) >= 5;  -- Must have contacted at least 5 controllers
