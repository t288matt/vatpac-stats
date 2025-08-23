-- Test Scenarios 1-5 with Actual Test Data
-- This script creates test data matching our scenarios and verifies the SQL calculations

-- Clean up any existing test data
DELETE FROM flight_sector_occupancy WHERE callsign LIKE 'TEST%';
DELETE FROM transceivers WHERE callsign LIKE 'TEST%';

-- ============================================================================
-- SCENARIO 1: Simple Two-Sector Flight
-- Sector A: 30 min total, 0-15 min no ATC, 15-30 min on ATC
-- Sector B: 20 min total, 0-10 min on ATC, 10-20 min no ATC
-- Expected: Sector A = 50%, Sector B = 50%, Overall = 50%
-- ============================================================================

-- Insert sector data for TEST001
INSERT INTO flight_sector_occupancy (callsign, sector_name, entry_timestamp, exit_timestamp, duration_seconds, entry_lat, entry_lon)
VALUES 
('TEST001', 'SECT_A', '2025-01-27 14:00:00+00', '2025-01-27 14:30:00+00', 1800, -33.8688, 151.2093),
('TEST001', 'SECT_B', '2025-01-27 14:30:00+00', '2025-01-27 14:50:00+00', 1200, -33.8688, 151.2093);

-- Insert transceiver data for TEST001 - covering the ENTIRE time period in each sector
INSERT INTO transceivers (callsign, transceiver_id, frequency, entity_type, timestamp, position_lat, position_lon)
VALUES 
-- Sector A: 0-30 min (30 minutes total)
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:00:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:01:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:02:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:03:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:04:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:05:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:06:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:07:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:08:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:09:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:10:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:11:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:12:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:13:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:14:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:15:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:16:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:17:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:18:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:19:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:20:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:21:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:22:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:23:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:24:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:25:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:26:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:27:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:28:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:29:00+00', -33.8688, 151.2093),

-- Sector B: 0-20 min (20 minutes total)
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:30:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:31:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:32:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:33:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:34:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:35:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:36:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:37:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:38:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:39:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:40:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:41:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:42:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:43:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:44:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:45:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:46:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:47:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:48:00+00', -33.8688, 151.2093),
('TEST001', 1, 118500000, 'flight', '2025-01-27 14:49:00+00', -33.8688, 151.2093);

-- Insert ATC data for TEST001 - ONLY during the specified ATC periods
INSERT INTO transceivers (callsign, transceiver_id, frequency, entity_type, timestamp, position_lat, position_lon)
VALUES 
-- Sector A: ATC on frequency from 14:15-14:30 (15 minutes = 50% of sector time)
('ATC_A', 1, 118500000, 'atc', '2025-01-27 14:15:00+00', -33.8688, 151.2093),
('ATC_A', 1, 118500000, 'atc', '2025-01-27 14:16:00+00', -33.8688, 151.2093),
('ATC_A', 1, 118500000, 'atc', '2025-01-27 14:17:00+00', -33.8688, 151.2093),
('ATC_A', 1, 118500000, 'atc', '2025-01-27 14:18:00+00', -33.8688, 151.2093),
('ATC_A', 1, 118500000, 'atc', '2025-01-27 14:19:00+00', -33.8688, 151.2093),
('ATC_A', 1, 118500000, 'atc', '2025-01-27 14:20:00+00', -33.8688, 151.2093),
('ATC_A', 1, 118500000, 'atc', '2025-01-27 14:21:00+00', -33.8688, 151.2093),
('ATC_A', 1, 118500000, 'atc', '2025-01-27 14:22:00+00', -33.8688, 151.2093),
('ATC_A', 1, 118500000, 'atc', '2025-01-27 14:23:00+00', -33.8688, 151.2093),
('ATC_A', 1, 118500000, 'atc', '2025-01-27 14:24:00+00', -33.8688, 151.2093),
('ATC_A', 1, 118500000, 'atc', '2025-01-27 14:25:00+00', -33.8688, 151.2093),
('ATC_A', 1, 118500000, 'atc', '2025-01-27 14:26:00+00', -33.8688, 151.2093),
('ATC_A', 1, 118500000, 'atc', '2025-01-27 14:27:00+00', -33.8688, 151.2093),
('ATC_A', 1, 118500000, 'atc', '2025-01-27 14:28:00+00', -33.8688, 151.2093),
('ATC_A', 1, 118500000, 'atc', '2025-01-27 14:29:00+00', -33.8688, 151.2093),

-- Sector B: ATC on frequency from 14:30-14:40 (10 minutes = 50% of sector time)
('ATC_B', 1, 118500000, 'atc', '2025-01-27 14:30:00+00', -33.8688, 151.2093),
('ATC_B', 1, 118500000, 'atc', '2025-01-27 14:31:00+00', -33.8688, 151.2093),
('ATC_B', 1, 118500000, 'atc', '2025-01-27 14:32:00+00', -33.8688, 151.2093),
('ATC_B', 1, 118500000, 'atc', '2025-01-27 14:33:00+00', -33.8688, 151.2093),
('ATC_B', 1, 118500000, 'atc', '2025-01-27 14:34:00+00', -33.8688, 151.2093),
('ATC_B', 1, 118500000, 'atc', '2025-01-27 14:35:00+00', -33.8688, 151.2093),
('ATC_B', 1, 118500000, 'atc', '2025-01-27 14:36:00+00', -33.8688, 151.2093),
('ATC_B', 1, 118500000, 'atc', '2025-01-27 14:37:00+00', -33.8688, 151.2093),
('ATC_B', 1, 118500000, 'atc', '2025-01-27 14:38:00+00', -33.8688, 151.2093),
('ATC_B', 1, 118500000, 'atc', '2025-01-27 14:39:00+00', -33.8688, 151.2093);

-- Now run our analysis query on the test data
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
    WHERE callsign = 'TEST001'
),

frequency_usage_by_minute AS (
    SELECT 
        fst.callsign,
        fst.sector_name,
        fst.time_bucket,
        fst.duration_seconds,
        CASE WHEN ft.frequency IS NOT NULL THEN 1 ELSE 0 END as on_frequency,
        CASE WHEN atc.callsign IS NOT NULL THEN 1 ELSE 0 END as atc_on_same_frequency,
        ft.frequency
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

-- Expected Results:
-- Sector A: 30 min total, 15 min on ATC = 50%
-- Sector B: 20 min total, 10 min on ATC = 50%
-- Overall: 50 min total, 25 min on ATC = 50%
