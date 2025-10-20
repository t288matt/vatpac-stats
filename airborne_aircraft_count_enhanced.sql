-- airborne_aircraft_count_enhanced.sql
-- Count airborne aircraft between 0700z-1200z in 5-minute intervals for each Monday
-- This version provides multiple approaches based on possible database structures

-- Method 1: Using flight_positions table (if it exists)
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
      AND (fp.on_ground = false OR fp.on_ground IS NULL)  -- If there's an explicit on_ground flag
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

-- Method 2: Using transceivers table (if flight_positions doesn't exist)
/*
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
        COUNT(DISTINCT ft.callsign) AS airborne_count
    FROM transceivers ft
    JOIN time_slots ts
      ON ft.timestamp >= ts.time_slot - INTERVAL '2.5 minutes'
     AND ft.timestamp < ts.time_slot + INTERVAL '2.5 minutes'
    WHERE ft.entity_type = 'flight'
      AND ft.altitude > 0  -- Assuming altitude > 0 means airborne
      AND (ft.on_ground = false OR ft.on_ground IS NULL)
      AND EXTRACT(DOW FROM ft.timestamp) = 1  -- Monday only
      AND EXTRACT(HOUR FROM ft.timestamp) >= 7
      AND EXTRACT(HOUR FROM ft.timestamp) < 12
    GROUP BY ts.time_slot
)

SELECT
    TO_CHAR(ac.time_slot, 'YYYY-MM-DD') AS date,
    TO_CHAR(ac.time_slot, 'HH24:MI') AS time_interval,
    ac.airborne_count
FROM airborne_counts ac
ORDER BY ac.time_slot;
*/

-- Method 3: Using flight_data table (another possibility)
/*
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
        COUNT(DISTINCT fd.callsign) AS airborne_count
    FROM flight_data fd
    JOIN time_slots ts
      ON fd.timestamp >= ts.time_slot - INTERVAL '2.5 minutes'
     AND fd.timestamp < ts.time_slot + INTERVAL '2.5 minutes'
    WHERE fd.altitude > 0  -- Assuming altitude > 0 means airborne
      AND (fd.status = 'airborne' OR fd.on_ground = false OR fd.flying = true)
      AND EXTRACT(DOW FROM fd.timestamp) = 1  -- Monday only
      AND EXTRACT(HOUR FROM fd.timestamp) >= 7
      AND EXTRACT(HOUR FROM fd.timestamp) < 12
    GROUP BY ts.time_slot
)

SELECT
    TO_CHAR(ac.time_slot, 'YYYY-MM-DD') AS date,
    TO_CHAR(ac.time_slot, 'HH24:MI') AS time_interval,
    ac.airborne_count
FROM airborne_counts ac
ORDER BY ac.time_slot;
*/

