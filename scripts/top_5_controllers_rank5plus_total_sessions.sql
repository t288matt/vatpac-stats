-- Top 5 controllers (rank 5 and above) by total flights handled across all sessions
-- Shows aggregated results per controller, not individual sessions
-- Using the pre-calculated total_aircraft_handled field from controller_summaries table

SELECT 
    cs.name as controller_name,
    SUM(cs.total_aircraft_handled) as total_flights_handled,
    COUNT(*) as total_sessions,
    AVG(cs.session_duration_minutes) as avg_session_duration_minutes
FROM controller_summaries cs
WHERE cs.rating >= 5  -- Only rank 5 and above controllers
    AND cs.total_aircraft_handled > 0  -- Ensure we have flights handled
GROUP BY cs.name
ORDER BY total_flights_handled DESC
LIMIT 5;
