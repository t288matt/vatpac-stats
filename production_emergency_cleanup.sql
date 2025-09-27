-- EMERGENCY PRODUCTION CLEANUP
-- Fix the massive rescheduling loop by cleaning up backoff flights
-- Run this immediately in production

BEGIN;

-- 1. Mark all flights with 20-49 attempts as permanently failed (disable reset_with_backoff)
UPDATE flight_summaries
SET enrichment_status = 'failed',
    enrichment_last_error = 'EMERGENCY_FIX: High retry count (20-49 attempts) - disabled reset_with_backoff',
    updated_at = NOW()
WHERE enrichment_attempts BETWEEN 20 AND 49
AND enrichment_status = 'pending'
AND completion_time IS NOT NULL;

-- 2. Mark all flights with 50+ attempts as permanently failed (already should be, but ensure)
UPDATE flight_summaries
SET enrichment_status = 'failed',
    enrichment_last_error = 'EMERGENCY_FIX: Infinite retry loop (50+ attempts) - permanently failed',
    updated_at = NOW()
WHERE enrichment_attempts >= 50
AND enrichment_status = 'pending'
AND completion_time IS NOT NULL;

-- 3. Reset flights with 10-19 attempts to longer backoff (4-8 hours instead of immediate retry)
UPDATE flight_summaries
SET enrichment_run_after = NOW() + INTERVAL '4 hours',
    enrichment_last_error = COALESCE(enrichment_last_error, '') || ' | EMERGENCY_FIX: Extended backoff to reduce load',
    updated_at = NOW()
WHERE enrichment_attempts BETWEEN 10 AND 19
AND enrichment_status = 'pending'
AND enrichment_run_after <= NOW()
AND completion_time IS NOT NULL;

-- 4. Reset flights with 5-9 attempts to moderate backoff (1-2 hours)
UPDATE flight_summaries
SET enrichment_run_after = NOW() + INTERVAL '1 hour',
    enrichment_last_error = COALESCE(enrichment_last_error, '') || ' | EMERGENCY_FIX: Moderate backoff to reduce load',
    updated_at = NOW()
WHERE enrichment_attempts BETWEEN 5 AND 9
AND enrichment_status = 'pending'
AND enrichment_run_after <= NOW()
AND completion_time IS NOT NULL;

-- 5. Show the impact
SELECT 
    'Before cleanup' as status,
    COUNT(*) as count,
    MIN(enrichment_attempts) as min_attempts,
    MAX(enrichment_attempts) as max_attempts,
    COUNT(CASE WHEN enrichment_run_after <= NOW() THEN 1 END) as ready_for_processing
FROM flight_summaries 
WHERE enrichment_status = 'pending'
AND completion_time IS NOT NULL;

COMMIT;

-- Show final status
SELECT 
    'After cleanup' as status,
    COUNT(*) as total_pending,
    COUNT(CASE WHEN enrichment_attempts = 0 THEN 1 END) as zero_attempts,
    COUNT(CASE WHEN enrichment_attempts BETWEEN 1 AND 4 THEN 1 END) as low_attempts,
    COUNT(CASE WHEN enrichment_attempts BETWEEN 5 AND 9 THEN 1 END) as moderate_attempts,
    COUNT(CASE WHEN enrichment_attempts BETWEEN 10 AND 19 THEN 1 END) as high_attempts,
    COUNT(CASE WHEN enrichment_attempts >= 20 THEN 1 END) as very_high_attempts,
    COUNT(CASE WHEN enrichment_run_after <= NOW() THEN 1 END) as ready_for_processing
FROM flight_summaries 
WHERE enrichment_status = 'pending'
AND completion_time IS NOT NULL;
