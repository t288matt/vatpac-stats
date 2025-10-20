-- airborne_aircraft_count_final.sql
-- Count airborne aircraft between 0700z-1200z in 5-minute intervals for each Monday
-- Based on actual database structure found in codebase

WITH recent_monday AS (
    SELECT
        CASE
            WHEN EXTRACT(DOW FROM CURRENT_DATE) = 1 THEN CURRENT_DATE
            ELSE CURRENT_DATE - INTERVAL '1 day' * (EXTRACT(DOW FROM CURRENT_DATE) - 1)
        END AS monday_date
),
time_slots AS (
    SELECT
        monday_date + INTERVAL '7 hours' + (generate_series(0, 60) * INTERVAL '5 minutes') AS time_slot
    FROM recent_monday
),
airborne_counts AS (
    SELECT
        ts.time_slot,
        COUNT(DISTINCT f.callsign) AS airborne_count
    FROM flights f
    JOIN time_slots ts
      ON f.last_updated >= ts.time_slot - INTERVAL '2.5 minutes'
     AND f.last_updated < ts.time_slot + INTERVAL '2.5 minutes'
    WHERE f.altitude > 1000  -- Altitude > 1000 indicates airborne based on scripts/highest_sustained_groundspeed.sql
      AND f.groundspeed >= 60  -- Groundspeed >= 60 indicates aircraft is moving (from data_service.py)
      AND EXTRACT(DOW FROM f.last_updated) = 1  -- Monday only
      AND EXTRACT(HOUR FROM f.last_updated) >= 7
      AND EXTRACT(HOUR FROM f.last_updated) < 12
    GROUP BY ts.time_slot
)

SELECT
    TO_CHAR(ac.time_slot, 'YYYY-MM-DD') AS date,
    TO_CHAR(ac.time_slot, 'HH24:MI') AS time_interval,
    ac.airborne_count AS airborne_aircraft
FROM airborne_counts ac
ORDER BY ac.time_slot;

