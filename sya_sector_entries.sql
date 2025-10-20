-- sya_sector_entries.sql
-- Find aircraft that entered SYA sector from outside airspace (no prior sector)
-- between 0700z and 1200z on the most recent Monday

WITH recent_monday AS (
    SELECT 
        -- Get only the most recent Monday (if today is Monday, use today)
        CASE
            WHEN EXTRACT(DOW FROM CURRENT_DATE) = 1 THEN CURRENT_DATE
            ELSE CURRENT_DATE - INTERVAL '1 day' * (EXTRACT(DOW FROM CURRENT_DATE) - 1)
        END AS monday_date
),
-- Get all sector entries for the time period
sector_entries AS (
    SELECT
        callsign,
        sector_name,
        entry_timestamp,
        departure,
        arrival,
        entry_altitude
    FROM flight_sector_occupancy
    WHERE 
        -- Filter for Monday
        DATE(entry_timestamp) = (SELECT monday_date FROM recent_monday)
        -- Between 0700-1200z
        AND EXTRACT(HOUR FROM entry_timestamp) >= 7
        AND EXTRACT(HOUR FROM entry_timestamp) < 12
        -- Only SYA sector
        AND sector_name = 'SYA'
),
-- Find previous sector for each flight before entering SYA
previous_sectors AS (
    SELECT
        se.callsign,
        se.entry_timestamp AS sya_entry_time,
        se.entry_altitude AS sya_entry_altitude,
        se.departure,
        se.arrival,
        -- Find previous sector entry (if any)
        (SELECT fso.sector_name
         FROM flight_sector_occupancy fso
         WHERE fso.callsign = se.callsign
           AND fso.entry_timestamp < se.entry_timestamp
           AND DATE(fso.entry_timestamp) = DATE(se.entry_timestamp)
         ORDER BY fso.entry_timestamp DESC
         LIMIT 1) AS previous_sector
    FROM sector_entries se
)

-- Main query: Count aircraft that entered SYA from no sector (outside airspace)
SELECT
    EXTRACT(HOUR FROM sya_entry_time) AS hour,
    COUNT(*) AS entries_from_outside,
    -- Also provide a breakdown of these flights' departure airports
    jsonb_object_agg(
        COALESCE(departure, 'UNKNOWN'),
        1
    ) FILTER (WHERE departure IS NOT NULL) AS departure_airports
FROM previous_sectors
WHERE previous_sector IS NULL  -- No previous sector = entered from outside airspace
GROUP BY EXTRACT(HOUR FROM sya_entry_time)
ORDER BY hour;

-- Detail query: List all flights that entered SYA from outside airspace
SELECT
    callsign,
    to_char(sya_entry_time, 'HH24:MI') AS entry_time,
    sya_entry_altitude AS entry_altitude,
    departure,
    arrival,
    previous_sector
FROM previous_sectors
WHERE previous_sector IS NULL  -- No previous sector = entered from outside airspace
ORDER BY sya_entry_time;
