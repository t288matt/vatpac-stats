-- Test Flight ABC123 - Comprehensive ATC Frequency Analysis Test
-- This creates a fictional flight with predictable outcomes to validate our logic

-- Clean up any existing test data
DELETE FROM flight_sector_occupancy WHERE callsign = 'ABC123';
DELETE FROM transceivers WHERE callsign = 'ABC123';
DELETE FROM transceivers WHERE callsign LIKE 'ATC_ABC%';

-- Create a simple, predictable flight scenario
-- Flight ABC123 flies through 2 sectors with known ATC coverage

-- Insert sector data for ABC123
INSERT INTO flight_sector_occupancy (callsign, sector_name, entry_timestamp, exit_timestamp, duration_seconds, entry_lat, entry_lon)
VALUES 
('ABC123', 'SECT_X', '2025-01-27 10:00:00+00', '2025-01-27 10:20:00+00', 1200, -33.8688, 151.2093),
('ABC123', 'SECT_Y', '2025-01-27 10:20:00+00', '2025-01-27 10:35:00+00', 900, -33.8688, 151.2093);

-- Insert flight transceiver data - ABC123 is on frequency for entire flight
INSERT INTO transceivers (callsign, transceiver_id, frequency, entity_type, timestamp, position_lat, position_lon)
VALUES 
-- Sector X: 20 minutes (10:00-10:20)
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:00:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:01:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:02:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:03:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:04:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:05:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:06:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:07:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:08:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:09:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:10:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:11:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:12:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:13:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:14:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:15:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:16:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:17:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:18:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:19:00+00', -33.8688, 151.2093),

-- Sector Y: 15 minutes (10:20-10:35)
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:20:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:21:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:22:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:23:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:24:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:25:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:26:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:27:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:28:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:29:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:30:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:31:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:32:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:33:00+00', -33.8688, 151.2093),
('ABC123', 1, 118500000, 'flight', '2025-01-27 10:34:00+00', -33.8688, 151.2093);

-- Insert ATC data with PREDICTABLE patterns
INSERT INTO transceivers (callsign, transceiver_id, frequency, entity_type, timestamp, position_lat, position_lon)
VALUES 
-- Sector X: ATC from 10:05-10:15 (10 minutes = 50% of sector time)
('ATC_ABC_X', 1, 118500000, 'atc', '2025-01-27 10:05:00+00', -33.8688, 151.2093),
('ATC_ABC_X', 1, 118500000, 'atc', '2025-01-27 10:06:00+00', -33.8688, 151.2093),
('ATC_ABC_X', 1, 118500000, 'atc', '2025-01-27 10:07:00+00', -33.8688, 151.2093),
('ATC_ABC_X', 1, 118500000, 'atc', '2025-01-27 10:08:00+00', -33.8688, 151.2093),
('ATC_ABC_X', 1, 118500000, 'atc', '2025-01-27 10:09:00+00', -33.8688, 151.2093),
('ATC_ABC_X', 1, 118500000, 'atc', '2025-01-27 10:10:00+00', -33.8688, 151.2093),
('ATC_ABC_X', 1, 118500000, 'atc', '2025-01-27 10:11:00+00', -33.8688, 151.2093),
('ATC_ABC_X', 1, 118500000, 'atc', '2025-01-27 10:12:00+00', -33.8688, 151.2093),
('ATC_ABC_X', 1, 118500000, 'atc', '2025-01-27 10:13:00+00', -33.8688, 151.2093),
('ATC_ABC_X', 1, 118500000, 'atc', '2025-01-27 10:14:00+00', -33.8688, 151.2093),

-- Sector Y: ATC from 10:25-10:30 (5 minutes = 33.33% of sector time)
('ATC_ABC_Y', 1, 118500000, 'atc', '2025-01-27 10:25:00+00', -33.8688, 151.2093),
('ATC_ABC_Y', 1, 118500000, 'atc', '2025-01-27 10:26:00+00', -33.8688, 151.2093),
('ATC_ABC_Y', 1, 118500000, 'atc', '2025-01-27 10:27:00+00', -33.8688, 151.2093),
('ATC_ABC_Y', 1, 118500000, 'atc', '2025-01-27 10:28:00+00', -33.8688, 151.2093),
('ATC_ABC_Y', 1, 118500000, 'atc', '2025-01-27 10:29:00+00', -33.8688, 151.2093);

-- Verify our test data
SELECT '=== DATA VERIFICATION ===' as info;
SELECT 'Sector Data' as data_type, COUNT(*) as count FROM flight_sector_occupancy WHERE callsign = 'ABC123'
UNION ALL
SELECT 'Flight Transceivers' as data_type, COUNT(*) as count FROM transceivers WHERE callsign = 'ABC123' AND entity_type = 'flight'
UNION ALL
SELECT 'ATC Transceivers' as data_type, COUNT(*) as count FROM transceivers WHERE callsign LIKE 'ATC_ABC%' AND entity_type = 'atc';

-- Show expected vs actual sector times
SELECT '=== SECTOR TIME VERIFICATION ===' as info;
SELECT 
    sector_name,
    entry_timestamp,
    exit_timestamp,
    duration_seconds,
    ROUND(duration_seconds / 60.0, 1) as expected_minutes,
    EXTRACT(EPOCH FROM (exit_timestamp - entry_timestamp))/60 as calculated_minutes
FROM flight_sector_occupancy 
WHERE callsign = 'ABC123'
ORDER BY sector_name;

-- Now test our analysis logic
SELECT '=== ATC FREQUENCY ANALYSIS RESULTS ===' as info;
WITH flight_sector_timeline AS (
    SELECT 
        callsign,
        sector_name,
        entry_timestamp,
        exit_timestamp,
        duration_seconds,
        generate_series(
            entry_timestamp, 
            exit_timestamp, 
            INTERVAL '1 minute'
        ) as time_bucket
    FROM flight_sector_occupancy
    WHERE callsign = 'ABC123'
),

frequency_usage_by_minute AS (
    SELECT 
        fst.callsign,
        fst.sector_name,
        fst.time_bucket,
        fst.duration_seconds,
        CASE WHEN ft.frequency IS NOT NULL THEN 1 ELSE 0 END as on_frequency,
        CASE WHEN atc.callsign IS NOT NULL THEN 1 ELSE 0 END as atc_on_same_frequency
    FROM flight_sector_timeline fst
    LEFT JOIN transceivers ft ON 
        fst.callsign = ft.callsign 
        AND ft.entity_type = 'flight'
        AND ft.timestamp BETWEEN fst.time_bucket AND fst.time_bucket + INTERVAL '1 minute'
    LEFT JOIN transceivers atc ON 
        ft.frequency = atc.frequency
        AND atc.entity_type = 'atc'
        AND atc.timestamp BETWEEN fst.time_bucket AND fst.time_bucket + INTERVAL '1 minute'
)

SELECT 
    callsign,
    sector_name,
    COUNT(*) as total_minutes_in_sector,
    SUM(on_frequency) as minutes_on_frequency,
    SUM(atc_on_same_frequency) as minutes_on_atc_frequency,
    ROUND((SUM(on_frequency)::numeric / COUNT(*)::numeric) * 100.0, 2) as percentage_on_frequency,
    ROUND((SUM(atc_on_same_frequency)::numeric / COUNT(*)::numeric) * 100.0, 2) as percentage_on_atc_frequency,
    CASE 
        WHEN SUM(on_frequency) > 0 THEN
            ROUND((SUM(atc_on_same_frequency)::numeric / SUM(on_frequency)::numeric) * 100.0, 2)
        ELSE 0
    END as percentage_frequency_time_with_atc,
    ROUND(duration_seconds / 60.0, 1) as sector_duration_minutes
FROM frequency_usage_by_minute
GROUP BY callsign, sector_name, duration_seconds
ORDER BY callsign, sector_name;

-- Expected Results Summary:
-- Sector X: 20 min total, 10 min on ATC = 50%
-- Sector Y: 15 min total, 5 min on ATC = 33.33%
-- Overall: 35 min total, 15 min on ATC = 42.86%

