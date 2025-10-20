-- airborne_aircraft_count_adjusted.sql
-- Count airborne aircraft between 0700z-1200z in 5-minute intervals for each Monday
-- With adjusted filters to capture more potential airborne aircraft
-- Based on actual database structure found in codebase

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
airborne_counts AS (
    SELECT
        ts.monday_date,
        ts.time_slot,
        -- Original strict count (altitude > 1000 AND groundspeed >= 60)
        COUNT(DISTINCT CASE 
            WHEN f.altitude > 1000 AND f.groundspeed >= 60 THEN f.callsign 
            ELSE NULL 
        END) AS strict_count,
        -- Relaxed count (altitude > 0 OR groundspeed >= 30)
        COUNT(DISTINCT CASE 
            WHEN (f.altitude > 0 OR f.altitude IS NULL) AND 
                 (f.groundspeed >= 30 OR f.groundspeed IS NULL) THEN f.callsign 
            ELSE NULL 
        END) AS relaxed_count,
        -- Total count of aircraft in the timeframe
        COUNT(DISTINCT f.callsign) AS total_count
    FROM flights f
    JOIN time_slots ts
      ON f.last_updated >= ts.time_slot - INTERVAL '2.5 minutes'
     AND f.last_updated < ts.time_slot + INTERVAL '2.5 minutes'
     AND DATE(f.last_updated) = ts.monday_date
    WHERE EXTRACT(DOW FROM f.last_updated) = 1  -- Monday only
      AND EXTRACT(HOUR FROM f.last_updated) >= 7
      AND EXTRACT(HOUR FROM f.last_updated) < 12
    GROUP BY ts.monday_date, ts.time_slot
)

SELECT
    TO_CHAR(ac.monday_date, 'YYYY-MM-DD') AS date,
    TO_CHAR(ac.time_slot, 'HH24:MI') AS time_interval,
    EXTRACT(HOUR FROM ac.time_slot) * 60 + EXTRACT(MINUTE FROM ac.time_slot) AS minutes_since_midnight,
    ac.strict_count AS original_aircraft_count,
    ac.relaxed_count AS relaxed_aircraft_count,
    ac.total_count AS total_aircraft_count,
    CASE
        WHEN ac.strict_count < (ac.relaxed_count * 0.5) AND ac.relaxed_count >= 5 
        THEN 'LIKELY DATA ISSUE' 
        ELSE '' 
    END AS anomaly_flag
FROM airborne_counts ac
ORDER BY ac.monday_date, minutes_since_midnight;

