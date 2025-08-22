-- Top 5 controller sessions by number of aircraft handled
-- Shows individual sessions with the largest aircraft counts
-- Using the pre-calculated total_aircraft_handled field from controller_summaries table

SELECT 
    cs.callsign as controller_callsign,
    cs.name as controller_name,
    cs.total_aircraft_handled as unique_flights_handled,
    cs.session_duration_minutes as session_duration_minutes,
    cs.session_start_time as session_start_time
FROM controller_summaries cs
WHERE cs.rating IN (1, 2, 3)  -- Only rank 1-3 controllers
    AND cs.total_aircraft_handled > 0  -- Ensure we have flights handled
ORDER BY cs.total_aircraft_handled DESC
LIMIT 5;

-- Alternative query if you want to see the aircraft details for each controller:
-- SELECT 
--     cs.callsign as controller_callsign,
--     cs.name as controller_name,
--     cs.rating as controller_rating,
--     cs.total_aircraft_handled as unique_flights_handled,
--     cs.aircraft_details as flight_details,
--     cs.session_start_time as session_start_time
-- FROM controller_summaries cs
-- WHERE cs.rating = 4
--     AND cs.session_start_time >= NOW() - INTERVAL '1 week'
--     AND cs.total_aircraft_handled > 0
-- ORDER BY cs.total_aircraft_handled DESC
-- LIMIT 5;
