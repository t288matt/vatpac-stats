-- sya_sector_transitions_corrected.sql
-- Find aircraft that were already in another sector and then entered SYA
-- between 0700z and 1200z on Monday

-- Count aircraft that entered SYA from other sectors
SELECT
    EXTRACT(HOUR FROM entry_timestamp) AS hour,
    COUNT(*) AS transitions_from_other_sectors
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
    -- MUST have a previous sector entry for this flight on the same day
    AND EXISTS (
        SELECT 1 
        FROM flight_sector_occupancy prev
        WHERE prev.callsign = fso.callsign
          AND prev.entry_timestamp < fso.entry_timestamp
          AND DATE(prev.entry_timestamp) = DATE(fso.entry_timestamp)
    )
GROUP BY EXTRACT(HOUR FROM entry_timestamp)
ORDER BY hour;

-- Detail list of aircraft that transitioned from other sectors into SYA
SELECT
    callsign,
    to_char(entry_timestamp, 'HH24:MI') AS entry_time,
    entry_altitude,
    departure,
    arrival,
    -- Show which sector they came from
    (
        SELECT prev.sector_name
        FROM flight_sector_occupancy prev
        WHERE prev.callsign = fso.callsign
          AND prev.entry_timestamp < fso.entry_timestamp
          AND DATE(prev.entry_timestamp) = DATE(fso.entry_timestamp)
        ORDER BY prev.entry_timestamp DESC
        LIMIT 1
    ) AS from_sector
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
    -- MUST have a previous sector entry for this flight on the same day
    AND EXISTS (
        SELECT 1 
        FROM flight_sector_occupancy prev
        WHERE prev.callsign = fso.callsign
          AND prev.entry_timestamp < fso.entry_timestamp
          AND DATE(prev.entry_timestamp) = DATE(fso.entry_timestamp)
    )
ORDER BY entry_timestamp;
