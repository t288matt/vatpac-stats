-- airborne_aircraft_sector_breakdown.sql
-- Count airborne aircraft between 0700z-1200z with detailed sector information
-- Provides both total aircraft count and breakdown by sector

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
-- Count aircraft in each sector for each time slot
sector_aircraft_counts AS (
    SELECT
        DATE(ts.time_slot) AS count_date,
        ts.time_slot,
        fso.sector_name,
        COUNT(DISTINCT fso.callsign) AS aircraft_in_sector
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
        ts.time_slot,
        fso.sector_name
),
-- Create total counts across all sectors
total_aircraft_counts AS (
    SELECT
        count_date,
        time_slot,
        SUM(aircraft_in_sector) AS total_airborne_count
    FROM sector_aircraft_counts
    GROUP BY count_date, time_slot
),
-- Create array of sectors with counts for each time slot
sector_breakdown AS (
    SELECT
        sac.count_date,
        sac.time_slot,
        jsonb_object_agg(
            COALESCE(sac.sector_name, 'UNKNOWN'), 
            sac.aircraft_in_sector
        ) AS sectors_breakdown
    FROM sector_aircraft_counts sac
    WHERE sac.sector_name IS NOT NULL
    GROUP BY sac.count_date, sac.time_slot
)

SELECT
    TO_CHAR(tac.count_date, 'YYYY-MM-DD') AS date,
    TO_CHAR(tac.time_slot, 'HH24:MI') AS time_interval,
    EXTRACT(HOUR FROM tac.time_slot) * 60 + EXTRACT(MINUTE FROM tac.time_slot) AS minutes_since_midnight,
    tac.total_airborne_count AS airborne_aircraft,
    sb.sectors_breakdown AS sector_counts
FROM total_aircraft_counts tac
LEFT JOIN sector_breakdown sb ON
    tac.count_date = sb.count_date AND
    tac.time_slot = sb.time_slot
ORDER BY tac.count_date, minutes_since_midnight;
