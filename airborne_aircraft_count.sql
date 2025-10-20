-- airborne_aircraft_count.sql
-- Count airborne aircraft between 0700z-1200z in 5-minute intervals for each Monday

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
        COUNT(DISTINCT fp.callsign) AS airborne_count
    FROM flight_positions fp
    JOIN time_slots ts
      ON fp.timestamp >= ts.time_slot - INTERVAL '2.5 minutes'
     AND fp.timestamp < ts.time_slot + INTERVAL '2.5 minutes'
    WHERE fp.altitude > 0  -- Assuming altitude > 0 means airborne
      AND fp.on_ground = false  -- If there's an explicit on_ground flag
      AND EXTRACT(DOW FROM fp.timestamp) = 1  -- Monday only
      AND EXTRACT(HOUR FROM fp.timestamp) >= 7
      AND EXTRACT(HOUR FROM fp.timestamp) < 12
    GROUP BY ts.time_slot
)

SELECT
    TO_CHAR(ac.time_slot, 'YYYY-MM-DD') AS date,
    TO_CHAR(ac.time_slot, 'HH24:MI') AS time_interval,
    ac.airborne_count
FROM airborne_counts ac
ORDER BY ac.time_slot;

