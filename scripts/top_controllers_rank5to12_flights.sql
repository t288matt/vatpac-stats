-- Top 10 controllers (rank 5-12) by number of flights handled
-- Using controller_summaries table for completed ATC sessions
-- Last week only

SELECT 
    cs.name as controller_name,
    cs.rating as controller_rating,
    SUM(cs.total_aircraft_handled) as total_flights_handled,
    COUNT(*) as total_sessions
FROM controller_summaries cs
WHERE cs.session_start_time >= NOW() - INTERVAL '1 week'
    AND cs.rating BETWEEN 5 AND 12  -- Only rank 5 through 12 controllers
    AND cs.total_aircraft_handled IS NOT NULL
    AND cs.total_aircraft_handled > 0
GROUP BY cs.name, cs.rating
ORDER BY total_flights_handled DESC
LIMIT 10;
