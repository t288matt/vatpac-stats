-- sya_sector_both_types.sql
-- Find both types of SYA entries: from outside airspace AND from other sectors
-- between 0700z and 1200z on Monday

-- Summary: Both types of SYA entries counted separately in 15-minute segments
SELECT
    hour,
    minute_segment,
    CONCAT(
        hour::text, 
        ':', 
        LPAD(minute_segment::text, 2, '0')
    ) AS time_segment,
    COUNT(*) FILTER (WHERE has_previous_sector = false) AS entries_from_outside,
    COUNT(*) FILTER (WHERE has_previous_sector = true) AS transitions_from_other_sectors,
    COUNT(*) AS total_sya_entries
FROM (
    SELECT
        entry_timestamp,
        callsign,
        EXTRACT(HOUR FROM entry_timestamp) AS hour,
        EXTRACT(MINUTE FROM entry_timestamp)::int / 15 * 15 AS minute_segment,
        -- Check if this flight had a previous sector entry on the same day
        EXISTS (
            SELECT 1 
            FROM flight_sector_occupancy prev
            WHERE prev.callsign = fso.callsign
              AND prev.entry_timestamp < fso.entry_timestamp
              AND DATE(prev.entry_timestamp) = DATE(fso.entry_timestamp)
        ) AS has_previous_sector
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
) AS sya_entries
GROUP BY 
    hour,
    minute_segment
ORDER BY hour, minute_segment;

-- Detailed list: All SYA entries with type and source information
SELECT
    callsign,
    to_char(entry_timestamp, 'HH24:MI') AS entry_time,
    entry_altitude,
    departure,
    arrival,
    CASE
        WHEN EXISTS (
            SELECT 1 
            FROM flight_sector_occupancy prev
            WHERE prev.callsign = fso.callsign
              AND prev.entry_timestamp < fso.entry_timestamp
              AND DATE(prev.entry_timestamp) = DATE(fso.entry_timestamp)
        ) THEN 'Transition from Other Sector'
        ELSE 'Entry from Outside Airspace'
    END AS entry_type,
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
ORDER BY entry_timestamp;
