-- Fastest Flight Time Between Sydney and Melbourne (Monday Completion)
-- 
-- This query finds the fastest flight time from Melbourne (YMML) to Sydney (YSSY)
-- for flights that complete on a Monday, requiring contact with:
-- - SY_TWR (Sydney Tower)
-- - ML_TWR (Melbourne Tower) 
-- - Two GND controllers (any ground positions)
--
-- Uses total_enroute_time_minutes for actual flight time (not total time online)
--
-- Usage:
--   docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f scripts/fastest_sydney_melbourne_monday.sql
--

-- Find fastest SYD-MEL flights with required controller contacts on Monday completion
WITH syd_mel_monday_flights AS (
    SELECT 
        callsign,
        aircraft_type,
        name as pilot_name,
        departure,
        arrival,
        logon_time,
        completion_time,
        total_enroute_time_minutes,  -- Actual flight time between sectors (not total time online)
        controller_callsigns,
        -- Extract day of week from completion time (1 = Monday in PostgreSQL)
        EXTRACT(DOW FROM completion_time) as completion_day,
        -- Check if contacted SY_TWR
        CASE 
            WHEN controller_callsigns ? 'SY_TWR' THEN true 
            ELSE false 
        END as contacted_sy_twr,
        -- Check if contacted ML_TWR
        CASE 
            WHEN controller_callsigns ? 'ML_TWR' THEN true 
            ELSE false 
        END as contacted_ml_twr,
        -- Count GND controllers (any position containing 'GND')
        CASE 
            WHEN EXISTS (
                SELECT 1 FROM jsonb_object_keys(controller_callsigns) AS controller 
                WHERE controller LIKE '%GND%'
            ) THEN (
                SELECT COUNT(*) FROM jsonb_object_keys(controller_callsigns) AS controller 
                WHERE controller LIKE '%GND%'
            )
            ELSE 0 
        END as gnd_controller_count
    FROM flight_summaries
    WHERE departure = 'YMML'   -- Melbourne
        AND arrival = 'YSSY'   -- Sydney
        AND completion_time >= NOW() - INTERVAL '6 months'  -- Last 6 months for Monday data
        AND total_enroute_time_minutes > 0  -- Valid flight duration (must be > 0)
        AND controller_callsigns IS NOT NULL  -- Must have controller data
        AND EXTRACT(DOW FROM completion_time) = 1  -- Must complete on Monday (1 = Monday)
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
        total_enroute_time_minutes,  -- Actual flight time between sectors
        controller_callsigns,
        completion_day,
        contacted_sy_twr,
        contacted_ml_twr,
        gnd_controller_count
    FROM syd_mel_monday_flights
    WHERE contacted_sy_twr = true  -- Must have contacted SY_TWR
        AND contacted_ml_twr = true  -- Must have contacted ML_TWR
        AND gnd_controller_count >= 2  -- Must have contacted at least 2 GND controllers
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
        total_enroute_time_minutes,  -- Actual flight time between sectors
        controller_callsigns,
        completion_day,
        contacted_sy_twr,
        contacted_ml_twr,
        gnd_controller_count,
        ROW_NUMBER() OVER (ORDER BY total_enroute_time_minutes ASC) as rank
    FROM filtered_flights
    WHERE total_enroute_time_minutes > 0  -- Additional safety check
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
    total_enroute_time_minutes as flight_duration_minutes,
    -- Format completion day
    CASE completion_day
        WHEN 0 THEN 'Sunday'
        WHEN 1 THEN 'Monday'
        WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
    END as completion_day_name,
    -- Controller contact verification
    contacted_sy_twr as contacted_sydney_tower,
    contacted_ml_twr as contacted_melbourne_tower,
    gnd_controller_count as ground_controllers_contacted,
    -- Count total unique controllers contacted
    (SELECT COUNT(*) FROM jsonb_object_keys(controller_callsigns)) as total_controllers,
    -- Calculate average speed (SYD-MEL is approximately 440nm) with NULLIF protection
    ROUND(440 / NULLIF(total_enroute_time_minutes / 60, 0), 1) as avg_speed_knots,
    -- Show which controllers were contacted
    controller_callsigns
FROM ranked_flights
ORDER BY total_enroute_time_minutes ASC
LIMIT 20;

-- ============================================================================
-- SUMMARY STATISTICS FOR MONDAY SYD-MEL FLIGHTS
-- ============================================================================
-- This section provides summary statistics for all Monday SYD-MEL flights
-- that meet the controller contact requirements

WITH monday_syd_mel_stats AS (
    SELECT 
        total_enroute_time_minutes,  -- Actual flight time between sectors
        aircraft_type,
        (SELECT COUNT(*) FROM jsonb_object_keys(controller_callsigns)) as total_controllers
    FROM flight_summaries
    WHERE departure = 'YMML'
        AND arrival = 'YSSY'
        AND completion_time >= NOW() - INTERVAL '6 months'
        AND EXTRACT(DOW FROM completion_time) = 1
        AND total_enroute_time_minutes > 0
        AND controller_callsigns IS NOT NULL
        AND controller_callsigns ? 'SY_TWR'
        AND controller_callsigns ? 'ML_TWR'
        AND (
            SELECT COUNT(*) FROM jsonb_object_keys(controller_callsigns) AS controller 
            WHERE controller LIKE '%GND%'
        ) >= 2
)
SELECT 
    COUNT(*) as total_monday_flights,
    ROUND(AVG(total_enroute_time_minutes), 1) as avg_flight_time_minutes,
    MIN(total_enroute_time_minutes) as fastest_flight_minutes,
    MAX(total_enroute_time_minutes) as slowest_flight_minutes,
    ROUND(STDDEV(total_enroute_time_minutes), 1) as std_dev_minutes,
    ROUND(AVG(total_controllers), 1) as avg_controllers_contacted,
    COUNT(DISTINCT aircraft_type) as unique_aircraft_types
FROM monday_syd_mel_stats;
