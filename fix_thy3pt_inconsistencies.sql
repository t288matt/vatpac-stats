-- Fix data inconsistencies for THY3PT flight (YPAM to YBTL)
-- First, review the flight data before making changes
SELECT 
    id, callsign, departure, arrival, 
    logon_time, completion_time,
    time_online_minutes, 
    total_enroute_time_minutes, 
    sector_breakdown,
    enrichment_status, 
    enrichment_attempts,
    enrichment_completed_at
FROM flight_summaries 
WHERE callsign = 'THY3PT' 
  AND departure = 'YPAM' 
  AND arrival = 'YBTL'
  AND id = 15133;  -- Use the specific ID from the report

-- Calculate correct time_online_minutes from the timestamps
-- This shows the correct calculation but doesn't update anything yet
SELECT 
    callsign,
    EXTRACT(EPOCH FROM (completion_time - logon_time))/60 AS calculated_minutes,
    time_online_minutes AS recorded_minutes
FROM flight_summaries
WHERE id = 15133;

-- Calculate correct total sector time from the sector breakdown
-- This shows the correct sum but doesn't update anything yet
SELECT 
    callsign,
    sector_breakdown,
    total_enroute_time_minutes,
    (SELECT SUM(value::int) FROM jsonb_each_text(sector_breakdown) AS s) AS correct_sector_sum
FROM flight_summaries
WHERE id = 15133;

-- Fix the inconsistencies:
-- 1. Update time_online_minutes based on logon_time and completion_time
-- 2. Update total_enroute_time_minutes based on sector_breakdown sum
-- 3. Reset for reprocessing to fix other issues like aircraft_short
BEGIN;

-- Update the time_online_minutes to match the actual duration
UPDATE flight_summaries
SET time_online_minutes = FLOOR(EXTRACT(EPOCH FROM (completion_time - logon_time))/60)::INT
WHERE id = 15133
  AND time_online_minutes = 0
  AND completion_time IS NOT NULL
  AND logon_time IS NOT NULL;

-- Update total_enroute_time_minutes to match the sum of sector_breakdown
UPDATE flight_summaries
SET total_enroute_time_minutes = (
    SELECT SUM(value::int) 
    FROM jsonb_each_text(sector_breakdown) AS s
)
WHERE id = 15133
  AND sector_breakdown IS NOT NULL
  AND sector_breakdown <> '{}'::jsonb;

-- Reset for reprocessing to fix remaining issues (like aircraft_short)
UPDATE flight_summaries
SET enrichment_status = 'pending',
    enrichment_attempts = 0,
    enrichment_run_after = NOW(),
    enrichment_last_error = 'Reset due to data validation issues (time and sector inconsistencies)',
    updated_at = NOW()
WHERE id = 15133;

-- Verify the changes
SELECT 
    id, callsign, 
    time_online_minutes, 
    total_enroute_time_minutes,
    sector_breakdown,
    enrichment_status
FROM flight_summaries 
WHERE id = 15133;

COMMIT;






