-- Query to find flights that never leave the ground (never reach 60 knots)
-- Based on airborne detection criteria: groundspeed >= 60 knots

WITH flight_max_speeds AS (
    -- Get the maximum groundspeed for each flight
    SELECT 
        callsign,
        DATE(last_updated) as flight_date,
        MAX(groundspeed) as max_groundspeed
    FROM flights 
    WHERE 
        groundspeed IS NOT NULL
        AND last_updated >= CURRENT_DATE - INTERVAL '30 days'  -- Last 30 days
    GROUP BY callsign, DATE(last_updated)
),
grounded_flights AS (
    -- Identify flights that never reached 60 knots
    SELECT 
        callsign,
        flight_date,
        max_groundspeed
    FROM flight_max_speeds
    WHERE max_groundspeed < 60
)
-- Count grounded flights per day
SELECT 
    flight_date,
    COUNT(*) as grounded_flights_count,
    ROUND(AVG(max_groundspeed), 1) as avg_max_speed_knots
FROM grounded_flights
GROUP BY flight_date
ORDER BY flight_date DESC;
