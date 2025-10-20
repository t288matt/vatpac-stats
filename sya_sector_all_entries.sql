-- sya_sector_all_entries.sql
-- Complete analysis of SYA sector entries between 0700z and 1200z on Monday
-- Shows entries from outside airspace AND transitions from other sectors

-- Summary: All SYA entries broken down by source
SELECT
    EXTRACT(HOUR FROM entry_timestamp) AS hour,
    COUNT(*) AS total_sya_entries,
    COUNT(*) FILTER (WHERE has_previous_sector = false) AS entries_from_outside,
    COUNT(*) FILTER (WHERE has_previous_sector = true) AS transitions_from_other_sectors,
    -- Show which sectors aircraft came from
    jsonb_object_agg(
        COALESCE(previous_sector, 'OUTSIDE_AIRSPACE'),
        1
    ) AS entry_sources
FROM (
    SELECT
        entry_timestamp,
        callsign,
        -- Check if this flight had a previous sector entry on the same day
        EXISTS (
            SELECT 1 
            FROM flight_sector_occupancy prev
            WHERE prev.callsign = fso.callsign
              AND prev.entry_timestamp < fso.entry_timestamp
              AND DATE(prev.entry_timestamp) = DATE(fso.entry_timestamp)
        ) AS has_previous_sector,
        -- Get the previous sector name (if any)
        (
            SELECT prev.sector_name
            FROM flight_sector_occupancy prev
            WHERE prev.callsign = fso.callsign
              AND prev.entry_timestamp < fso.entry_timestamp
              AND DATE(prev.entry_timestamp) = DATE(fso.entry_timestamp)
            ORDER BY prev.entry_timestamp DESC
            LIMIT 1
        ) AS previous_sector
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
GROUP BY EXTRACT(HOUR FROM entry_timestamp)
ORDER BY hour;

-- Detailed list: All SYA entries with source information
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
        ) THEN 'Sector Transition'
        ELSE 'Entry from Outside'
    END AS entry_type,
    (
        SELECT prev.sector_name
        FROM flight_sector_occupancy prev
        WHERE prev.callsign = fso.callsign
          AND prev.entry_timestamp < fso.entry_timestamp
          AND DATE(prev.entry_timestamp) = DATE(fso.entry_timestamp)
        ORDER BY prev.entry_timestamp DESC
        LIMIT 1
    ) AS previous_sector
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

