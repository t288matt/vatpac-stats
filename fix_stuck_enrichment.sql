-- Fix stuck enrichment flights
-- These flights have excessive retry counts and are likely stuck in a loop

BEGIN;

-- Option 1: Reset stuck flights with high attempt counts (recommended)
-- Reset flights with 50+ attempts to pending with immediate retry
UPDATE flight_summaries 
SET 
    enrichment_attempts = 0,
    enrichment_status = 'pending',
    enrichment_run_after = NOW(),
    enrichment_last_error = NULL,
    updated_at = NOW()
WHERE enrichment_attempts >= 50 
  AND enrichment_status = 'pending'
  AND completion_time IS NOT NULL;

-- Get count of reset flights
SELECT COUNT(*) as flights_reset 
FROM flight_summaries 
WHERE enrichment_attempts = 0 
  AND enrichment_status = 'pending' 
  AND updated_at >= NOW() - INTERVAL '1 minute';

-- Option 2: Alternative - Mark extremely stuck flights as completed with minimal data
-- (Uncomment if Option 1 doesn't work)
/*
UPDATE flight_summaries 
SET 
    enrichment_status = 'completed',
    enrichment_completed_at = NOW(),
    controller_callsigns = '{}',
    controller_time_percentage = 0,
    airborne_controller_time_percentage = 0,
    time_online_minutes = 0,
    total_enroute_time_minutes = 0,
    enrichment_last_error = 'Auto-completed: excessive retries',
    updated_at = NOW()
WHERE enrichment_attempts >= 100 
  AND enrichment_status = 'pending'
  AND completion_time IS NOT NULL;
*/

COMMIT;

-- Verify the fix
SELECT 
    enrichment_status,
    COUNT(*) as count,
    AVG(enrichment_attempts) as avg_attempts,
    MAX(enrichment_attempts) as max_attempts
FROM flight_summaries 
WHERE completion_time IS NOT NULL
GROUP BY enrichment_status 
ORDER BY enrichment_status;
