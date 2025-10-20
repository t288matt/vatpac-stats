-- airborne_aircraft_relaxed_criteria.sql
-- Count airborne aircraft with more relaxed criteria to ensure we're not missing data
-- Uses continuous tracking with less stringent altitude/speed requirements

WITH date_range AS (
    SELECT 
        date_value AS monday_date
    FROM generate_series(
        '2025-09-01'::date, -- Start date (modify as needed)
        '2025-10-31'::date, -- End date (modify as needed)
        '7 days'::interval
    ) AS date_value
    WHERE EXTRACT(DOW FROM date_value) = 1 -- Only keep Mondays
),
time_slots AS (
    SELECT
        monday_date,
        monday_date + INTERVAL '7 hours' + (generate_series(0, 60) * INTERVAL '5 minutes') AS time_slot
    FROM date_range
),
-- Identify flight segments with very relaxed criteria
flight_segments AS (
    SELECT
        f.callsign,
        DATE(f.last_updated) AS flight_date,
        -- Use more relaxed criteria for what counts as "airborne"
        -- (any altitude above 0 OR any speed above 30)
        MIN(f.last_updated) AS first_seen,
        MAX(f.last_updated) AS last_seen,
        MAX(f.altitude) AS max_altitude,
        MAX(f.groundspeed) AS max_groundspeed,
        COUNT(*) AS position_reports
    FROM flights f
    WHERE EXTRACT(DOW FROM f.last_updated) = 1  -- Monday only
      AND EXTRACT(HOUR FROM f.last_updated) BETWEEN 6 AND 13
    GROUP BY f.callsign, DATE(f.last_updated)
),
-- Separate the flight segments into different categories based on confidence
categorized_segments AS (
    SELECT
        callsign,
        flight_date,
        first_seen,
        last_seen,
        CASE
            -- High confidence: clearly airborne
            WHEN max_altitude > 1000 AND max_groundspeed >= 60 THEN 'high_confidence'
            -- Medium confidence: likely airborne
            WHEN (max_altitude > 500 AND max_groundspeed >= 30) OR max_altitude > 2000 THEN 'medium_confidence'
            -- Low confidence: might be airborne
            WHEN max_altitude > 0 OR max_groundspeed >= 30 THEN 'low_confidence'
            -- Not airborne
            ELSE 'not_airborne'
        END AS confidence_level,
        position_reports
    FROM flight_segments
    WHERE position_reports >= 2  -- Must have at least 2 position reports
),
-- Count aircraft in each time slot by confidence level
airborne_counts AS (
    SELECT
        ts.monday_date,
        ts.time_slot,
        COUNT(DISTINCT CASE WHEN cs.confidence_level = 'high_confidence' THEN cs.callsign ELSE NULL END) AS high_confidence_count,
        COUNT(DISTINCT CASE WHEN cs.confidence_level IN ('high_confidence', 'medium_confidence') THEN cs.callsign ELSE NULL END) AS medium_confidence_count,
        COUNT(DISTINCT CASE WHEN cs.confidence_level IN ('high_confidence', 'medium_confidence', 'low_confidence') THEN cs.callsign ELSE NULL END) AS any_airborne_count,
        COUNT(DISTINCT cs.callsign) AS total_aircraft_count
    FROM time_slots ts
    LEFT JOIN categorized_segments cs
      ON ts.monday_date = cs.flight_date
      AND ts.time_slot >= cs.first_seen
      AND ts.time_slot <= cs.last_seen
    GROUP BY ts.monday_date, ts.time_slot
)

SELECT
    TO_CHAR(ac.monday_date, 'YYYY-MM-DD') AS date,
    TO_CHAR(ac.time_slot, 'HH24:MI') AS time_interval,
    EXTRACT(HOUR FROM ac.time_slot) * 60 + EXTRACT(MINUTE FROM ac.time_slot) AS minutes_since_midnight,
    ac.high_confidence_count AS definitely_airborne,
    ac.medium_confidence_count AS probably_airborne,
    ac.any_airborne_count AS possibly_airborne,
    ac.total_aircraft_count AS total_aircraft,
    CASE 
        WHEN ac.high_confidence_count = 0 AND ac.medium_confidence_count = 0 AND ac.any_airborne_count = 0 THEN 'LIKELY DATA GAP'
        WHEN ac.high_confidence_count = 0 AND ac.medium_confidence_count > 0 THEN 'PARTIAL DATA'
        ELSE ''
    END AS data_quality_flag
FROM airborne_counts ac
ORDER BY ac.monday_date, minutes_since_midnight;

