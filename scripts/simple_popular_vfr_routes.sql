-- Simple Query: Top 10 Most Popular VFR Routes in Past Month
-- 
-- This query finds the 10 most popular VFR routes by unique pilots
-- who have flown between departure and arrival airports in the last 30 days.
-- Only includes routes with 3 or more unique VFR aircraft.
--
-- Usage:
--   docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f scripts/simple_popular_vfr_routes.sql
--

SELECT 
    CONCAT(departure, ' → ', arrival) as route,
    COUNT(DISTINCT callsign) as unique_pilots,
    COUNT(*) as total_vfr_flights,
    ROUND(AVG(time_online_minutes), 1) as avg_flight_duration_minutes,
    ROUND(AVG(controller_time_percentage), 1) as avg_atc_contact_percentage,
    MIN(completion_time) as first_flight_date,
    MAX(completion_time) as last_flight_date
FROM flight_summaries 
WHERE flight_rules = 'V'  -- VFR flights only
    AND departure IS NOT NULL 
    AND arrival IS NOT NULL
    AND departure != ''
    AND arrival != ''
    AND departure != arrival  -- Exclude flights that don't actually go anywhere
    AND completion_time >= NOW() - INTERVAL '30 days'  -- Last 30 days only
GROUP BY departure, arrival
HAVING COUNT(DISTINCT callsign) >= 3  -- Only show routes with at least 3 unique pilots
ORDER BY unique_pilots DESC, total_vfr_flights DESC
LIMIT 10;
