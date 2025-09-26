-- Reset Flight Completion Times Utility
-- This script resets flight summaries to force reprocessing with new logic
-- 
-- USAGE:
-- 1. Reset all flights older than 2 days:
--    docker-compose exec postgres psql -U vatsim_user -d vatsim_data -f utilities/reset_flight_completion_times.sql
--
-- 2. Reset specific date range (modify WHERE clause):
--    WHERE created_at BETWEEN '2025-09-20' AND '2025-09-25'
--
-- 3. Reset only recent flights (last 24 hours):
--    WHERE created_at >= CURRENT_DATE - INTERVAL '1 day'

-- Reset flight summaries to NULL completion_time for reprocessing
UPDATE flight_summaries 
SET 
    completion_time = NULL,
    enrichment_status = 'pending',
    updated_at = NOW()
WHERE created_at < CURRENT_DATE - INTERVAL '2 days'
  AND completion_time IS NOT NULL;

-- Show the results
SELECT 
    COUNT(*) as records_reset,
    'Flight summaries reset to NULL completion_time' as status
FROM flight_summaries 
WHERE created_at < CURRENT_DATE - INTERVAL '2 days'
  AND completion_time IS NULL;

-- Show current processing status
SELECT 
  'Records with NULL completion_time' as status,
  COUNT(*) as count
FROM flight_summaries 
WHERE completion_time IS NULL

UNION ALL

SELECT 
  'Records created in last 2 days' as status,
  COUNT(*) as count
FROM flight_summaries 
WHERE created_at >= CURRENT_DATE - INTERVAL '2 days'
  AND completion_time IS NULL

UNION ALL

SELECT 
  'Total records in last 24h' as status,
  COUNT(*) as count
FROM flight_summaries 
WHERE updated_at >= NOW() - INTERVAL '24 hours';


