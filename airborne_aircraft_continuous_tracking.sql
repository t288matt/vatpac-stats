-- airborne_aircraft_continuous_tracking.sql
-- Count airborne aircraft between 0700z-1200z in 5-minute intervals
-- Using continuous flight tracking logic that interpolates between position reports
-- This ensures aircraft flying from 0902-0907 are properly counted at the 0905 time slot

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
-- First, identify flight segments where aircraft are airborne
flight_segments AS (
    SELECT
        f.callsign,
        DATE(f.last_updated) AS flight_date,
        -- Find the minimum and maximum timestamps for each flight on each date
        MIN(f.last_updated) FILTER (WHERE f.altitude > 1000 AND f.groundspeed >= 60) AS first_airborne,
        MAX(f.last_updated) FILTER (WHERE f.altitude > 1000 AND f.groundspeed >= 60) AS last_airborne
    FROM flights f
    WHERE EXTRACT(DOW FROM f.last_updated) = 1  -- Monday only
      AND EXTRACT(HOUR FROM f.last_updated) >= 6  -- Start from 6am to catch early flights
      AND EXTRACT(HOUR FROM f.last_updated) < 13  -- End at 1pm to catch late flights
      AND f.altitude > 1000  -- Basic airborne check
      AND f.groundspeed >= 60  -- Moving at flight speed
    GROUP BY f.callsign, DATE(f.last_updated)
    HAVING COUNT(*) > 1  -- Must have at least 2 position reports to be considered a valid segment
),
-- Count airborne aircraft in each time slot based on the flight segments
airborne_counts AS (
    SELECT
        ts.monday_date,
        ts.time_slot,
        COUNT(DISTINCT fs.callsign) AS airborne_count
    FROM time_slots ts
    LEFT JOIN flight_segments fs
      ON ts.monday_date = fs.flight_date
      AND ts.time_slot >= fs.first_airborne
      AND ts.time_slot <= fs.last_airborne
    GROUP BY ts.monday_date, ts.time_slot
)

SELECT
    TO_CHAR(ac.monday_date, 'YYYY-MM-DD') AS date,
    TO_CHAR(ac.time_slot, 'HH24:MI') AS time_interval,
    EXTRACT(HOUR FROM ac.time_slot) * 60 + EXTRACT(MINUTE FROM ac.time_slot) AS minutes_since_midnight,
    ac.airborne_count AS airborne_aircraft
FROM airborne_counts ac
ORDER BY ac.monday_date, minutes_since_midnight;

