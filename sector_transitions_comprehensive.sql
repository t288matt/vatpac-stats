-- sector_transitions_comprehensive.sql
-- Analyze all sector entries and transitions for SYA sector
-- Shows entries from outside airspace vs. transitions from other sectors
-- For the most recent Monday between 0700z and 1200z

WITH recent_monday AS (
    SELECT 
        -- Get only the most recent Monday (if today is Monday, use today)
        CASE
            WHEN EXTRACT(DOW FROM CURRENT_DATE) = 1 THEN CURRENT_DATE
            ELSE CURRENT_DATE - INTERVAL '1 day' * (EXTRACT(DOW FROM CURRENT_DATE) - 1)
        END AS monday_date
),
-- Get all sector entries for the time period
all_sector_entries AS (
    SELECT
        id,
        callsign,
        sector_name,
        entry_timestamp,
        exit_timestamp,
        entry_altitude,
        exit_altitude,
        departure,
        arrival,
        -- Calculate row number to find adjacent sector entries
        ROW_NUMBER() OVER (PARTITION BY callsign ORDER BY entry_timestamp) AS entry_sequence
    FROM flight_sector_occupancy
    WHERE 
        -- Filter for Monday
        DATE(entry_timestamp) = (SELECT monday_date FROM recent_monday)
        -- Only consider entries between 0700-1200z
        -- (but we gather all sector data for each flight to analyze transitions)
),
-- Join each sector entry with its previous entry (if any) to detect transitions
sector_transitions AS (
    SELECT
        curr.id,
        curr.callsign,
        curr.sector_name AS current_sector,
        curr.entry_timestamp,
        curr.exit_timestamp,
        curr.entry_altitude,
        curr.exit_altitude,
        curr.departure,
        curr.arrival,
        prev.sector_name AS previous_sector,
        prev.exit_timestamp AS previous_exit_timestamp,
        -- Calculate time between exiting previous sector and entering current one
        EXTRACT(EPOCH FROM (curr.entry_timestamp - prev.exit_timestamp)) AS transition_seconds
    FROM all_sector_entries curr
    LEFT JOIN all_sector_entries prev ON
        curr.callsign = prev.callsign AND
        curr.entry_sequence = prev.entry_sequence + 1
)

-- Main summary: SYA sector entries broken down by entry type
SELECT
    EXTRACT(HOUR FROM entry_timestamp) AS hour,
    COUNT(*) FILTER (WHERE current_sector = 'SYA') AS total_sya_entries,
    COUNT(*) FILTER (WHERE current_sector = 'SYA' AND previous_sector IS NULL) AS entries_from_outside,
    COUNT(*) FILTER (WHERE current_sector = 'SYA' AND previous_sector IS NOT NULL) AS transitions_from_other_sectors,
    -- Breakdown of which sectors aircraft came from before entering SYA
    jsonb_object_agg(
        COALESCE(previous_sector, 'OUTSIDE_AIRSPACE'), 
        1
    ) FILTER (WHERE current_sector = 'SYA') AS entry_sources
FROM sector_transitions
WHERE 
    current_sector = 'SYA' AND
    EXTRACT(HOUR FROM entry_timestamp) >= 7 AND
    EXTRACT(HOUR FROM entry_timestamp) < 12
GROUP BY EXTRACT(HOUR FROM entry_timestamp)
ORDER BY hour;

-- Detailed list of all SYA entries
SELECT
    callsign,
    to_char(entry_timestamp, 'HH24:MI') AS entry_time,
    entry_altitude,
    departure,
    arrival,
    COALESCE(previous_sector, 'OUTSIDE_AIRSPACE') AS entry_source,
    CASE
        WHEN previous_sector IS NULL THEN 'New Entry'
        ELSE 'Sector Transition' 
    END AS entry_type,
    transition_seconds
FROM sector_transitions
WHERE 
    current_sector = 'SYA' AND
    EXTRACT(HOUR FROM entry_timestamp) >= 7 AND
    EXTRACT(HOUR FROM entry_timestamp) < 12
ORDER BY entry_timestamp;
