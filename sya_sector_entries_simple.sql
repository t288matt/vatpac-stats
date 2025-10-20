-- sya_sector_entries_simple.sql
-- Simple query to find aircraft that entered SYA sector from outside airspace
-- between 0700z and 1200z on the most recent Monday

-- Count aircraft that entered SYA from outside airspace (no previous sector)
SELECT
    EXTRACT(HOUR FROM entry_timestamp) AS hour,
    COUNT(*) AS entries_from_outside
FROM flight_sector_occupancy fso
WHERE 
    -- Filter for Monday
    DATE(entry_timestamp) = (
        CASE
            WHEN EXTRACT(DOW FROM CURRENT_DATE) = 1 THEN CURRENT_DATE
            ELSE CURRENT_DATE - INTERVAL '1 day' * (EXTRACT(DOW FROM CURRENT_DATE) - 1)
        END
    )
    -- Between 0700-1200z
    AND EXTRACT(HOUR FROM entry_timestamp) >= 7
    AND EXTRACT(HOUR FROM entry_timestamp) < 12
    -- Only SYA sector
    AND sector_name = 'SYA'
    -- No previous sector entry for this flight on the same day
    AND NOT EXISTS (
        SELECT 1 
        FROM flight_sector_occupancy prev
        WHERE prev.callsign = fso.callsign
          AND prev.entry_timestamp < fso.entry_timestamp
          AND DATE(prev.entry_timestamp) = DATE(fso.entry_timestamp)
    )
GROUP BY EXTRACT(HOUR FROM entry_timestamp)
ORDER BY hour;

-- Detail list of these flights
SELECT
    callsign,
    to_char(entry_timestamp, 'HH24:MI') AS entry_time,
    entry_altitude,
    departure,
    arrival
FROM flight_sector_occupancy fso
WHERE 
    -- Filter for Monday
    DATE(entry_timestamp) = (
        CASE
            WHEN EXTRACT(DOW FROM CURRENT_DATE) = 1 THEN CURRENT_DATE
            ELSE CURRENT_DATE - INTERVAL '1 day' * (EXTRACT(DOW FROM CURRENT_DATE) - 1)
        END
    )
    -- Between 0700-1200z
    AND EXTRACT(HOUR FROM entry_timestamp) >= 7
    AND EXTRACT(HOUR FROM entry_timestamp) < 12
    -- Only SYA sector
    AND sector_name = 'SYA'
    -- No previous sector entry for this flight on the same day
    AND NOT EXISTS (
        SELECT 1 
        FROM flight_sector_occupancy prev
        WHERE prev.callsign = fso.callsign
          AND prev.entry_timestamp < fso.entry_timestamp
          AND DATE(prev.entry_timestamp) = DATE(fso.entry_timestamp)
    )
ORDER BY entry_timestamp;
