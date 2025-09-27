-- PRODUCTION Enrichment Recovery Script
-- Run this in production to clean up existing stuck flights
-- Safe to run - only resets problematic flights to allow normal processing

BEGIN;

-- Show current state
SELECT 'BEFORE RECOVERY:' as status;
SELECT 
    enrichment_status,
    COUNT(*) as count,
    ROUND(AVG(enrichment_attempts), 1) as avg_attempts,
    MAX(enrichment_attempts) as max_attempts
FROM flight_summaries 
GROUP BY enrichment_status 
ORDER BY enrichment_status;

-- 1. Reset flights stuck in 'in_progress' for >5 minutes (if any)
UPDATE flight_summaries
SET enrichment_status = 'pending',
    enrichment_run_after = NOW(),
    enrichment_last_error = 'PRODUCTION RECOVERY: Reset stuck in_progress flight',
    updated_at = NOW()
WHERE enrichment_status = 'in_progress' 
  AND updated_at < NOW() - INTERVAL '5 minutes';

SELECT 'Stuck in_progress flights reset:' as status, ROW_COUNT() as count;

-- 2. Reset flights with excessive attempts (50+ attempts)
UPDATE flight_summaries 
SET enrichment_attempts = 0,
    enrichment_status = 'pending',
    enrichment_run_after = NOW(),
    enrichment_last_error = 'PRODUCTION RECOVERY: Reset excessive attempts',
    updated_at = NOW()
WHERE enrichment_attempts >= 50
  AND enrichment_status = 'pending'
  AND completion_time IS NOT NULL;

SELECT 'High-attempt flights reset:' as status, ROW_COUNT() as count;

-- Show state after recovery
SELECT 'AFTER RECOVERY:' as status;
SELECT 
    enrichment_status,
    COUNT(*) as count,
    ROUND(AVG(enrichment_attempts), 1) as avg_attempts,
    MAX(enrichment_attempts) as max_attempts
FROM flight_summaries 
GROUP BY enrichment_status 
ORDER BY enrichment_status;

-- Show how many flights are now ready for immediate processing
SELECT 'Ready for processing:' as status, COUNT(*) as count
FROM flight_summaries 
WHERE enrichment_status = 'pending' 
  AND enrichment_run_after <= NOW()
  AND completion_time IS NOT NULL;

COMMIT;

SELECT 'PRODUCTION RECOVERY COMPLETE' as status, NOW() as completed_at;
