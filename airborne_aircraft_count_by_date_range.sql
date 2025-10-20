-- airborne_aircraft_count_by_date_range.sql
-- Count airborne aircraft between 0700z-1200z in 5-minute intervals for each Monday
-- Shows data for all Mondays within a specified date range
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
        COUNT(DISTINCT f.callsign) AS airborne_count
    FROM flights f
    JOIN time_slots ts
      ON f.last_updated >= ts.time_slot - INTERVAL '2.5 minutes'
     AND f.last_updated < ts.time_slot + INTERVAL '2.5 minutes'
     AND DATE(f.last_updated) = ts.monday_date
    WHERE f.altitude > 1000  -- Altitude > 1000 indicates airborne based on scripts/highest_sustained_groundspeed.sql
      AND f.groundspeed >= 60  -- Groundspeed >= 60 indicates aircraft is moving (from data_service.py)
      AND EXTRACT(DOW FROM f.last_updated) = 1  -- Monday only
      AND EXTRACT(HOUR FROM f.last_updated) >= 7
      AND EXTRACT(HOUR FROM f.last_updated) < 12
    GROUP BY ts.monday_date, ts.time_slot
)

SELECT
    TO_CHAR(ac.monday_date, 'YYYY-MM-DD') AS date,
    TO_CHAR(ac.time_slot, 'HH24:MI') AS time_interval,
    EXTRACT(HOUR FROM ac.time_slot) * 60 + EXTRACT(MINUTE FROM ac.time_slot) AS minutes_since_midnight,
    ac.airborne_count AS airborne_aircraft
FROM airborne_counts ac
ORDER BY minutes_since_midnight;
