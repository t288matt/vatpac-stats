-- Test Scenarios 1-5: Flight ATC Frequency Analysis
-- 
-- This script tests the first 5 scenarios to verify our calculations
-- match the expected results from the scenario documentation
--

-- First, let's see what data we have to work with
SELECT 
    'Data Overview' as test_type,
    COUNT(*) as total_sector_records,
    COUNT(DISTINCT callsign) as unique_flights,
    COUNT(DISTINCT sector_name) as unique_sectors
FROM flight_sector_occupancy;

-- Check if we have transceiver data
SELECT 
    'Transceiver Data' as test_type,
    COUNT(*) as total_transceiver_records,
    COUNT(DISTINCT callsign) as unique_callsigns,
    COUNT(DISTINCT entity_type) as entity_types
FROM transceivers;

-- Now let's test the enhanced query with actual data
WITH flight_sector_timeline AS (
    SELECT 
        callsign,
        sector_name,
        entry_timestamp,
        exit_timestamp,
        duration_seconds,
        -- Create time buckets for analysis (1-minute intervals)
        generate_series(
            entry_timestamp, 
            exit_timestamp, 
            INTERVAL '1 minute'
        ) as time_bucket
    FROM flight_sector_occupancy
    WHERE exit_timestamp IS NOT NULL
        AND duration_seconds > 0  -- Ensure valid sector duration
        AND callsign IN (
            SELECT DISTINCT callsign 
            FROM flight_sector_occupancy 
            LIMIT 3  -- Test with first 3 flights
        )
),

frequency_usage_by_minute AS (
    SELECT 
        fst.callsign,
        fst.sector_name,
        fst.time_bucket,
        fst.duration_seconds,
        
        -- Check if flight was on frequency at this minute
        CASE WHEN ft.frequency IS NOT NULL THEN 1 ELSE 0 END as on_frequency,
        
        -- Check if ATC was on same frequency at this minute
        CASE WHEN atc.callsign IS NOT NULL THEN 1 ELSE 0 END as atc_on_same_frequency,
        
        -- Get the actual frequency
        ft.frequency
        
    FROM flight_sector_timeline fst
    
    -- Left join to get frequency usage (if any)
    LEFT JOIN transceivers ft ON 
        fst.callsign = ft.callsign 
        AND ft.entity_type = 'flight'
        AND ft.timestamp BETWEEN fst.time_bucket AND fst.time_bucket + INTERVAL '1 minute'
    
    -- Left join to get ATC on same frequency (if any)
    LEFT JOIN transceivers atc ON 
        ft.frequency = atc.frequency
        AND atc.entity_type = 'atc'
        AND atc.timestamp BETWEEN fst.time_bucket AND fst.time_bucket + INTERVAL '1 minute'
)

-- Calculate comprehensive percentages for any combination
SELECT 
    callsign,
    sector_name,
    COUNT(*) as total_minutes_in_sector,
    SUM(on_frequency) as minutes_on_frequency,
    SUM(atc_on_same_frequency) as minutes_on_atc_frequency,
    
    -- Percentage of sector time on any frequency
    ROUND(
        (SUM(on_frequency)::numeric / COUNT(*)::numeric) * 100.0, 
        2
    ) as percentage_on_frequency,
    
    -- Percentage of sector time on ATC frequency
    ROUND(
        (SUM(atc_on_same_frequency)::numeric / COUNT(*)::numeric) * 100.0, 
        2
    ) as percentage_on_atc_frequency,
    
    -- Percentage of frequency time that overlaps with ATC
    CASE 
        WHEN SUM(on_frequency) > 0 THEN
            ROUND(
                (SUM(atc_on_same_frequency)::numeric / SUM(on_frequency)::numeric) * 100.0, 
                2
            )
        ELSE 0
    END as percentage_frequency_time_with_atc,
    
    -- Additional metrics
    ROUND(duration_seconds / 60.0, 1) as sector_duration_minutes
    
FROM frequency_usage_by_minute
GROUP BY callsign, sector_name, duration_seconds
ORDER BY callsign, sector_name;

-- ============================================================================
-- SCENARIO VALIDATION
-- ============================================================================

/*
SCENARIO 1: Simple Two-Sector Flight
- Sector A: 30 min total, 0-15 min no ATC, 15-30 min on ATC
- Sector B: 20 min total, 0-10 min on ATC, 10-20 min no ATC
- Expected: Sector A = 50%, Sector B = 50%, Overall = 50%

SCENARIO 2: Early ATC Contact
- Sector A: 45 min total, 0-5 min no ATC, 5-45 min on ATC
- Expected: Overall = 89%

SCENARIO 3: Late ATC Contact
- Sector A: 60 min total, 0-50 min no ATC, 50-60 min on ATC
- Expected: Overall = 17%

SCENARIO 4: Mid-Sector Frequency Change
- Sector A: 40 min total, 0-10 min no ATC, 10-25 min on ATC, 25-40 min no ATC
- Expected: Overall = 37.5%

SCENARIO 5: Multiple Frequency Switches
- Sector A: 90 min total, 0-15 no ATC, 15-30 on ATC, 30-45 no ATC, 45-75 on ATC, 75-90 no ATC
- Expected: Overall = 50%
*/
