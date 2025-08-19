-- Simple Query: Most Popular VFR Routes
-- 
-- This query finds the most popular VFR routes by counting completed flights
-- between departure and arrival airports.
--
-- Usage:
--   docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f scripts/simple_popular_vfr_routes.sql
--

SELECT 
    CONCAT(departure, ' → ', arrival) as route,
    COUNT(*) as total_vfr_flights,
    COUNT(DISTINCT callsign) as unique_aircraft,
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
GROUP BY departure, arrival
HAVING COUNT(*) >= 3  -- Only show routes with at least 3 flights
ORDER BY total_vfr_flights DESC, unique_aircraft DESC
LIMIT 25;
