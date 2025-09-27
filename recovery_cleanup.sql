-- Recovery script to clean up existing stuck enrichment flights
-- This addresses the backlog of flights with excessive retry counts

BEGIN;

-- Step 1: Show current state before cleanup
SELECT 'BEFORE CLEANUP:' as status;
SELECT 
    enrichment_status,
    COUNT(*) as count,
    ROUND(AVG(enrichment_attempts), 2) as avg_attempts,
    MAX(enrichment_attempts) as max_attempts
FROM flight_summaries 
GROUP BY enrichment_status 
ORDER BY enrichment_status;

-- Step 2: Reset flights with excessive retry counts (100+)
UPDATE flight_summaries 
SET 
    enrichment_attempts = 0,
    enrichment_status = 'pending',
    enrichment_run_after = NOW(),
    enrichment_last_error = 'Reset due to excessive retries - recovery script',
    updated_at = NOW()
WHERE enrichment_attempts >= 100 
  AND enrichment_status = 'pending'
  AND completion_time IS NOT NULL;

-- Show how many were reset
SELECT 'FLIGHTS RESET (100+ attempts):' as status;
SELECT COUNT(*) as flights_reset 
FROM flight_summaries 
WHERE enrichment_last_error = 'Reset due to excessive retries - recovery script';

-- Step 3: Reset flights stuck in 'in_progress' for too long
UPDATE flight_summaries
SET enrichment_status = 'pending',
    enrichment_run_after = NOW(),
    enrichment_last_error = 'Recovered from stuck in_progress status - recovery script',
    updated_at = NOW()
WHERE enrichment_status = 'in_progress' 
  AND updated_at < NOW() - INTERVAL '5 minutes';

-- Show recovery results
SELECT 'STUCK IN_PROGRESS RECOVERED:' as status;
SELECT COUNT(*) as flights_recovered
FROM flight_summaries 
WHERE enrichment_last_error = 'Recovered from stuck in_progress status - recovery script';

-- Step 4: Show state after cleanup
SELECT 'AFTER CLEANUP:' as status;
SELECT 
    enrichment_status,
    COUNT(*) as count,
    ROUND(AVG(enrichment_attempts), 2) as avg_attempts,
    MAX(enrichment_attempts) as max_attempts
FROM flight_summaries 
GROUP BY enrichment_status 
ORDER BY enrichment_status;

-- Step 5: Show distribution of remaining high-attempt flights
SELECT 'REMAINING HIGH-ATTEMPT FLIGHTS:' as status;
SELECT 
    CASE 
        WHEN enrichment_attempts >= 50 THEN '50+ attempts'
        WHEN enrichment_attempts >= 20 THEN '20-49 attempts'
        WHEN enrichment_attempts >= 10 THEN '10-19 attempts'
        WHEN enrichment_attempts >= 5 THEN '5-9 attempts'
        ELSE '0-4 attempts'
    END as attempt_range,
    COUNT(*) as count
FROM flight_summaries 
WHERE enrichment_status = 'pending'
GROUP BY 
    CASE 
        WHEN enrichment_attempts >= 50 THEN '50+ attempts'
        WHEN enrichment_attempts >= 20 THEN '20-49 attempts'
        WHEN enrichment_attempts >= 10 THEN '10-19 attempts'
        WHEN enrichment_attempts >= 5 THEN '5-9 attempts'
        ELSE '0-4 attempts'
    END
ORDER BY count DESC;

COMMIT;

-- Final summary
SELECT 'RECOVERY COMPLETE' as status;
SELECT NOW() as completed_at;
