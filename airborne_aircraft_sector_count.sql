-- airborne_aircraft_sector_count.sql
-- Count airborne aircraft between 0700z-1200z in 5-minute intervals using sector data
-- Uses flight_sector_occupancy table to determine airborne aircraft more accurately

WITH date_range AS (
    SELECT 
        -- Get only the most recent Monday (if today is Monday, use today)
        CASE
            WHEN EXTRACT(DOW FROM CURRENT_DATE) = 1 THEN CURRENT_DATE
            ELSE CURRENT_DATE - INTERVAL '1 day' * (EXTRACT(DOW FROM CURRENT_DATE) - 1)
        END AS monday_date
),
time_slots AS (
    SELECT
        monday_date,
        monday_date + INTERVAL '7 hours' + (generate_series(0, 60) * INTERVAL '5 minutes') AS time_slot
    FROM date_range
),
-- Count aircraft in each time slot based on their sector occupancy data
airborne_counts AS (
    SELECT
        DATE(ts.time_slot) AS count_date,
        ts.time_slot,
        COUNT(DISTINCT fso.callsign) AS airborne_count
    FROM time_slots ts
    LEFT JOIN flight_sector_occupancy fso ON
        -- Flight was in a sector at the specified time slot if:
        -- 1. It entered the sector before or at the time slot AND
        -- 2. Either it hasn't exited yet OR it exited after the time slot
        DATE(fso.entry_timestamp) = DATE(ts.time_slot) AND
        fso.entry_timestamp <= ts.time_slot AND
        (fso.exit_timestamp IS NULL OR fso.exit_timestamp > ts.time_slot) AND
        -- Ensure the aircraft is actually airborne (has altitude data)
        fso.entry_altitude > 1000
    WHERE
        -- Filter for Monday
        EXTRACT(DOW FROM ts.time_slot) = 1
        -- Between 0700z-1200z
        AND EXTRACT(HOUR FROM ts.time_slot) >= 7
        AND EXTRACT(HOUR FROM ts.time_slot) < 12
    GROUP BY
        DATE(ts.time_slot),
        ts.time_slot
)

SELECT
    TO_CHAR(ac.count_date, 'YYYY-MM-DD') AS date,
    TO_CHAR(ac.time_slot, 'HH24:MI') AS time_interval,
    EXTRACT(HOUR FROM ac.time_slot) * 60 + EXTRACT(MINUTE FROM ac.time_slot) AS minutes_since_midnight,
    ac.airborne_count AS airborne_aircraft
FROM airborne_counts ac
ORDER BY ac.count_date, minutes_since_midnight;
