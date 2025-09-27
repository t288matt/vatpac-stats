-- Queries to find failed enrichment flights

-- 1. Basic count of failed enrichments
SELECT 'FAILED ENRICHMENT COUNT:' as query_type;
SELECT COUNT(*) as failed_count FROM flight_summaries WHERE enrichment_status = 'failed';

-- 2. All failed enrichment flights with details
SELECT 'ALL FAILED ENRICHMENTS:' as query_type;
SELECT 
    id,
    callsign,
    departure,
    arrival,
    enrichment_attempts,
    LEFT(enrichment_last_error, 100) as error_summary,
    created_at,
    updated_at
FROM flight_summaries 
WHERE enrichment_status = 'failed'
ORDER BY enrichment_attempts DESC, updated_at DESC;

-- 3. Failed enrichments by error type
SELECT 'FAILED BY ERROR TYPE:' as query_type;
SELECT 
    CASE 
        WHEN enrichment_last_error LIKE '%IMMEDIATE_FAIL%' THEN 'Immediate Fail (50+ attempts)'
        WHEN enrichment_last_error LIKE '%AUTO_FAILED%' THEN 'Auto Failed (Periodic cleanup)'
        WHEN enrichment_last_error LIKE '%Timeout%' THEN 'Timeout Error'
        WHEN enrichment_last_error LIKE '%Connection%' THEN 'Connection Error'
        WHEN enrichment_last_error LIKE '%Exception%' THEN 'Exception Error'
        WHEN enrichment_last_error LIKE '%deferred: missing completion_time%' THEN 'Missing Completion Time'
        ELSE 'Other Error'
    END as error_type,
    COUNT(*) as count,
    AVG(enrichment_attempts) as avg_attempts
FROM flight_summaries 
WHERE enrichment_status = 'failed'
GROUP BY 
    CASE 
        WHEN enrichment_last_error LIKE '%IMMEDIATE_FAIL%' THEN 'Immediate Fail (50+ attempts)'
        WHEN enrichment_last_error LIKE '%AUTO_FAILED%' THEN 'Auto Failed (Periodic cleanup)'
        WHEN enrichment_last_error LIKE '%Timeout%' THEN 'Timeout Error'
        WHEN enrichment_last_error LIKE '%Connection%' THEN 'Connection Error'
        WHEN enrichment_last_error LIKE '%Exception%' THEN 'Exception Error'
        WHEN enrichment_last_error LIKE '%deferred: missing completion_time%' THEN 'Missing Completion Time'
        ELSE 'Other Error'
    END
ORDER BY count DESC;

-- 4. Recent failed enrichments (last 24 hours)
SELECT 'RECENT FAILED ENRICHMENTS (24h):' as query_type;
SELECT 
    id,
    callsign,
    enrichment_attempts,
    LEFT(enrichment_last_error, 80) as error_summary,
    updated_at
FROM flight_summaries 
WHERE enrichment_status = 'failed'
  AND updated_at >= NOW() - INTERVAL '24 hours'
ORDER BY updated_at DESC
LIMIT 20;

-- 5. Failed enrichments by callsign pattern (identify problematic airlines)
SELECT 'FAILED BY CALLSIGN PATTERN:' as query_type;
SELECT 
    LEFT(callsign, 3) as airline_prefix,
    COUNT(*) as failed_count,
    AVG(enrichment_attempts) as avg_attempts,
    MAX(enrichment_attempts) as max_attempts
FROM flight_summaries 
WHERE enrichment_status = 'failed'
GROUP BY LEFT(callsign, 3)
ORDER BY failed_count DESC
LIMIT 10;

-- 6. Failed enrichments by route (identify problematic routes)
SELECT 'FAILED BY ROUTE:' as query_type;
SELECT 
    COALESCE(departure, 'NULL') as departure,
    COALESCE(arrival, 'NULL') as arrival,
    COUNT(*) as failed_count,
    AVG(enrichment_attempts) as avg_attempts
FROM flight_summaries 
WHERE enrichment_status = 'failed'
GROUP BY departure, arrival
ORDER BY failed_count DESC
LIMIT 10;

-- 7. Summary statistics
SELECT 'FAILED ENRICHMENT SUMMARY:' as query_type;
SELECT 
    COUNT(*) as total_failed,
    AVG(enrichment_attempts) as avg_attempts,
    MAX(enrichment_attempts) as max_attempts,
    MIN(updated_at) as oldest_failure,
    MAX(updated_at) as newest_failure
FROM flight_summaries 
WHERE enrichment_status = 'failed';
