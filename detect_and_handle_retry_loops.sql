-- Detect and Handle Infinite Retry Loops in Enrichment System
-- This script identifies problematic flights and marks them as failed to prevent infinite retries

BEGIN;

-- 1. Identify flights in infinite retry loops
WITH retry_loop_flights AS (
    SELECT 
        id,
        callsign,
        enrichment_attempts,
        enrichment_last_error,
        created_at,
        updated_at,
        -- Calculate time spent retrying
        EXTRACT(EPOCH FROM (NOW() - created_at))/3600 as hours_retrying
    FROM flight_summaries 
    WHERE enrichment_status = 'pending'
    AND enrichment_attempts >= 20  -- High retry count
    AND completion_time IS NOT NULL
    AND created_at < NOW() - INTERVAL '2 hours'  -- Been retrying for >2 hours
)
SELECT 'INFINITE RETRY LOOP CANDIDATES:' as status;

SELECT 
    COUNT(*) as total_stuck_flights,
    AVG(enrichment_attempts) as avg_attempts,
    MAX(enrichment_attempts) as max_attempts,
    AVG(hours_retrying) as avg_hours_retrying
FROM retry_loop_flights;

-- Show top 10 worst offenders
SELECT 'TOP 10 WORST RETRY LOOPS:' as status;
SELECT 
    id,
    callsign,
    enrichment_attempts,
    ROUND(EXTRACT(EPOCH FROM (NOW() - created_at))/3600, 1) as hours_retrying,
    LEFT(enrichment_last_error, 50) as error_preview
FROM retry_loop_flights
ORDER BY enrichment_attempts DESC
LIMIT 10;

-- 2. Mark flights with excessive retries as 'failed' to stop infinite loops
UPDATE flight_summaries
SET enrichment_status = 'failed',
    enrichment_last_error = COALESCE(enrichment_last_error, '') || ' | MARKED_FAILED: Infinite retry loop detected (attempts >= 50)',
    updated_at = NOW()
WHERE enrichment_status = 'pending'
  AND enrichment_attempts >= 50
  AND completion_time IS NOT NULL
  AND created_at < NOW() - INTERVAL '1 hour';

SELECT 'Flights marked as FAILED to stop infinite loops:' as status, ROW_COUNT() as count;

-- 3. Reset moderate retry loops (20-49 attempts) with longer backoff
UPDATE flight_summaries
SET enrichment_attempts = 0,
    enrichment_run_after = NOW() + INTERVAL '1 hour',  -- Long backoff
    enrichment_last_error = COALESCE(enrichment_last_error, '') || ' | RESET_WITH_BACKOFF: Retry loop prevention',
    updated_at = NOW()
WHERE enrichment_status = 'pending'
  AND enrichment_attempts BETWEEN 20 AND 49
  AND completion_time IS NOT NULL
  AND created_at < NOW() - INTERVAL '30 minutes';

SELECT 'Flights reset with 1-hour backoff:' as status, ROW_COUNT() as count;

-- 4. Show final state
SELECT 'AFTER CLEANUP:' as status;
SELECT 
    enrichment_status,
    COUNT(*) as count,
    ROUND(AVG(enrichment_attempts), 1) as avg_attempts,
    MAX(enrichment_attempts) as max_attempts
FROM flight_summaries 
GROUP BY enrichment_status 
ORDER BY enrichment_status;

COMMIT;

-- 5. Create a view for ongoing monitoring
CREATE OR REPLACE VIEW retry_loop_monitor AS
SELECT 
    id,
    callsign,
    enrichment_status,
    enrichment_attempts,
    ROUND(EXTRACT(EPOCH FROM (NOW() - created_at))/3600, 1) as hours_since_created,
    ROUND(EXTRACT(EPOCH FROM (NOW() - updated_at))/60, 1) as minutes_since_updated,
    enrichment_run_after,
    LEFT(enrichment_last_error, 100) as error_summary
FROM flight_summaries 
WHERE enrichment_attempts >= 10
  AND enrichment_status IN ('pending', 'failed')
ORDER BY enrichment_attempts DESC, created_at ASC;

SELECT 'MONITORING VIEW CREATED: retry_loop_monitor' as status;
SELECT 'Use: SELECT * FROM retry_loop_monitor; to monitor ongoing issues' as info;
