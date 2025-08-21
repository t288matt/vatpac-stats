-- Top controllers (rank 1-3) by aircraft handled on all callsign types
-- Shows aggregated results per controller for all position types
-- Using the pre-calculated total_aircraft_handled field from controller_summaries table

SELECT 
    cs.name as controller_name,
    ROUND(SUM(cs.session_duration_minutes) / 60.0) as total_time_online_hours,
    COUNT(*) as total_sessions,
    ROUND(AVG(cs.total_aircraft_handled)) as avg_aircraft_per_session
FROM controller_summaries cs
WHERE cs.rating IN (1, 2, 3)  -- Only rank 1-3 controllers
    AND cs.total_aircraft_handled > 0  -- Ensure we have flights handled
GROUP BY cs.name
ORDER BY total_time_online_hours DESC
LIMIT 5;
