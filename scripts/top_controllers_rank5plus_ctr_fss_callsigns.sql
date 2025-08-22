-- Top controllers (rank 5 and above) by aircraft handled on CTR/FSS callsigns
-- Shows aggregated results per controller for callsigns ending with CTR or FSS
-- Using the pre-calculated total_aircraft_handled field from controller_summaries table

SELECT 
    cs.name as controller_name,
    SUM(cs.total_aircraft_handled) as total_flights_handled,
    COUNT(*) as total_sessions,
    AVG(cs.session_duration_minutes) as avg_session_duration_minutes
FROM controller_summaries cs
WHERE cs.total_aircraft_handled > 0  -- Ensure we have flights handled
    AND (cs.callsign LIKE '%CTR' OR cs.callsign LIKE '%FSS')  -- Only CTR or FSS callsigns
GROUP BY cs.name
ORDER BY total_flights_handled DESC
LIMIT 5;
