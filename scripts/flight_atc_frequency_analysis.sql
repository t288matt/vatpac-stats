-- Enhanced Flight ATC Frequency Analysis
-- 
-- This query calculates what percentage of time flights are on the same frequency as ATC
-- during their time in sectors. It works with actual frequency change events, not artificial time buckets.
--
-- Features:
-- - Handles any number of sectors (1, 2, 3, 100+)
-- - Works with actual frequency change timestamps
-- - Calculates real overlap periods between flight and ATC frequency usage
-- - Robust against missing or invalid data
--
-- Usage:
--   docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f scripts/flight_atc_frequency_analysis.sql
--

-- Get flight frequency usage periods with actual start/end times
WITH flight_frequency_periods AS (
    SELECT 
        callsign,
        frequency,
        timestamp as start_time,
        LEAD(timestamp) OVER (PARTITION BY callsign ORDER BY timestamp) as end_time,
        entity_type
    FROM transceivers 
    WHERE entity_type = 'flight'
        AND frequency IS NOT NULL
),

-- Get ATC frequency usage periods
atc_frequency_periods AS (
    SELECT 
        callsign,
        frequency,
        timestamp as start_time,
        LEAD(timestamp) OVER (PARTITION BY callsign ORDER BY timestamp) as end_time,
        entity_type
    FROM transceivers 
    WHERE entity_type = 'atc'
        AND frequency IS NOT NULL
),

-- Calculate overlap periods between flight and ATC on same frequency
frequency_overlaps AS (
    SELECT 
        ffp.callsign as flight_callsign,
        ffp.frequency,
        ffp.start_time as flight_start,
        ffp.end_time as flight_end,
        afp.callsign as atc_callsign,
        afp.start_time as atc_start,
        afp.end_time as atc_end,
        
        -- Calculate actual overlap period
        GREATEST(ffp.start_time, afp.start_time) as overlap_start,
        LEAST(COALESCE(ffp.end_time, NOW()), COALESCE(afp.end_time, NOW())) as overlap_end,
        
        -- Calculate overlap duration in seconds
        EXTRACT(EPOCH FROM (
            LEAST(COALESCE(ffp.end_time, NOW()), COALESCE(afp.end_time, NOW())) - 
            GREATEST(ffp.start_time, afp.start_time)
        )) as overlap_seconds
        
    FROM flight_frequency_periods ffp
    JOIN atc_frequency_periods afp ON 
        ffp.frequency = afp.frequency
        AND ffp.start_time < COALESCE(afp.end_time, NOW())
        AND COALESCE(ffp.end_time, NOW()) > afp.start_time
),

-- Get sector occupancy with total duration
sector_durations AS (
    SELECT 
        callsign,
        sector_name,
        entry_timestamp,
        exit_timestamp,
        duration_seconds,
        entry_timestamp as sector_start,
        COALESCE(exit_timestamp, NOW()) as sector_end
    FROM flight_sector_occupancy
    WHERE exit_timestamp IS NOT NULL
        AND duration_seconds > 0
),

-- Calculate frequency usage within each sector
sector_frequency_analysis AS (
    SELECT 
        sd.callsign,
        sd.sector_name,
        sd.duration_seconds,
        sd.entry_timestamp,
        sd.exit_timestamp,
        
        -- Total time on any frequency in this sector
        COALESCE(SUM(
            EXTRACT(EPOCH FROM (
                LEAST(ffp.end_time, sd.sector_end) - 
                GREATEST(ffp.start_time, sd.sector_start)
            ))
        ), 0) as total_frequency_time_seconds,
        
        -- Total time on same frequency as ATC in this sector
        COALESCE(SUM(
            CASE WHEN fo.overlap_seconds > 0 THEN
                EXTRACT(EPOCH FROM (
                    LEAST(fo.overlap_end, sd.sector_end) - 
                    GREATEST(fo.overlap_start, sd.sector_start)
                ))
            ELSE 0 END
        ), 0) as atc_overlap_time_seconds
        
    FROM sector_durations sd
    
    -- Left join to get frequency usage periods that overlap with sector
    LEFT JOIN flight_frequency_periods ffp ON 
        sd.callsign = ffp.callsign
        AND ffp.start_time < sd.sector_end
        AND COALESCE(ffp.end_time, NOW()) > sd.sector_start
    
    -- Left join to get ATC overlap periods
    LEFT JOIN frequency_overlaps fo ON 
        sd.callsign = fo.flight_callsign
        AND fo.overlap_start < sd.sector_end
        AND fo.overlap_end > sd.sector_start
    
    GROUP BY sd.callsign, sd.sector_name, sd.duration_seconds, sd.entry_timestamp, sd.exit_timestamp
)

-- Final results with percentages
SELECT 
    callsign,
    sector_name,
    ROUND(duration_seconds / 60.0, 1) as sector_duration_minutes,
    ROUND(total_frequency_time_seconds / 60.0, 1) as frequency_time_minutes,
    ROUND(atc_overlap_time_seconds / 60.0, 1) as atc_overlap_time_minutes,
    
    -- Percentage of sector time on any frequency
    ROUND(
        (total_frequency_time_seconds / NULLIF(duration_seconds, 0)) * 100.0, 
        2
    ) as percentage_on_frequency,
    
    -- Percentage of sector time on ATC frequency
    ROUND(
        (atc_overlap_time_seconds / NULLIF(duration_seconds, 0)) * 100.0, 
        2
    ) as percentage_on_atc_frequency,
    
    -- Percentage of frequency time that overlaps with ATC
    CASE 
        WHEN total_frequency_time_seconds > 0 THEN
            ROUND(
                (atc_overlap_time_seconds / total_frequency_time_seconds) * 100.0, 
                2
            )
        ELSE 0
    END as percentage_frequency_time_with_atc,
    
    entry_timestamp,
    exit_timestamp
    
FROM sector_frequency_analysis
ORDER BY callsign, entry_timestamp;

-- ============================================================================
-- ALTERNATIVE: Quick summary across all sectors for a specific flight
-- ============================================================================

-- Uncomment and modify the callsign below for specific flight analysis
/*
WITH flight_frequency_summary AS (
    SELECT 
        callsign,
        COUNT(DISTINCT frequency) as unique_frequencies_used,
        SUM(
            EXTRACT(EPOCH FROM (
                COALESCE(end_time, NOW()) - start_time
            ))
        ) as total_frequency_time_seconds,
        MIN(start_time) as first_frequency_use,
        MAX(COALESCE(end_time, NOW())) as last_frequency_use
    FROM flight_frequency_periods
    WHERE callsign = 'YOUR_FLIGHT_CALLSIGN'  -- Replace with actual callsign
    GROUP BY callsign
)
SELECT 
    ffs.callsign,
    ffs.unique_frequencies_used,
    ROUND(ffs.total_frequency_time_seconds / 60.0, 2) as total_frequency_time_minutes,
    
    -- Count ATC overlaps
    COUNT(DISTINCT fo.atc_callsign) as unique_atc_controllers,
    ROUND(SUM(fo.overlap_seconds) / 60.0, 2) as total_atc_overlap_minutes,
    
    -- Overall percentage of frequency time with ATC
    ROUND(
        (SUM(fo.overlap_seconds) / NULLIF(ffs.total_frequency_time_seconds, 0)) * 100.0, 
        2
    ) as overall_percentage_with_atc
    
FROM flight_frequency_summary ffs
LEFT JOIN frequency_overlaps fo ON 
    ffs.callsign = fo.flight_callsign
GROUP BY ffs.callsign, ffs.unique_frequencies_used, ffs.total_frequency_time_seconds;
*/

-- ============================================================================
-- EXAMPLE OUTPUT FORMAT:
-- ============================================================================
/*
callsign | sector_name | sector_duration_minutes | frequency_time_minutes | atc_overlap_time_minutes | percentage_on_frequency | percentage_on_atc_frequency | percentage_frequency_time_with_atc | entry_timestamp | exit_timestamp
---------|-------------|------------------------|----------------------|-------------------------|------------------------|----------------------------|-----------------------------------|-----------------|---------------
QFA123   | SYA         | 25.0                   | 25.0                  | 10.0                    | 100.00                  | 40.00                      | 40.00                              | 2025-01-27 14:00:00+00 | 2025-01-27 14:25:00+00
QFA123   | BLA         | 20.0                   | 20.0                  | 5.0                     | 100.00                  | 25.00                      | 25.00                              | 2025-01-27 14:25:00+00 | 2025-01-27 14:45:00+00
QFA123   | WOL         | 45.0                   | 45.0                  | 30.0                    | 100.00                  | 66.67                      | 66.67                              | 2025-01-27 14:45:00+00 | 2025-01-27 15:30:00+00
*/
