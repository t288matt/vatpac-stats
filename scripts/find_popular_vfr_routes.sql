-- Find Most Popular VFR Routes
-- 
-- This query analyzes completed VFR flights to identify the most popular routes
-- based on the number of flights flown on each route.
--
-- Usage:
--   docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f scripts/find_popular_vfr_routes.sql
--

-- Option 1: Most popular VFR routes by flight count (recommended for overall popularity)
SELECT 
    CONCAT(departure, ' → ', arrival) as route,
    departure,
    arrival,
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
HAVING COUNT(*) >= 5  -- Only show routes with at least 5 flights
ORDER BY total_vfr_flights DESC, avg_flight_duration_minutes DESC
LIMIT 20;

-- Option 2: Most popular VFR routes by unique aircraft count
SELECT 
    CONCAT(departure, ' → ', arrival) as route,
    departure,
    arrival,
    COUNT(DISTINCT callsign) as unique_aircraft,
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
GROUP BY departure, arrival
HAVING COUNT(DISTINCT callsign) >= 3  -- Only show routes with at least 3 unique aircraft
ORDER BY unique_aircraft DESC, total_vfr_flights DESC
LIMIT 20;

-- Option 3: VFR route popularity by time period (last 30 days)
SELECT 
    CONCAT(departure, ' → ', arrival) as route,
    departure,
    arrival,
    COUNT(*) as vfr_flights_last_30_days,
    COUNT(DISTINCT callsign) as unique_aircraft_last_30_days,
    ROUND(AVG(time_online_minutes), 1) as avg_flight_duration_minutes,
    ROUND(AVG(controller_time_percentage), 1) as avg_atc_contact_percentage
FROM flight_summaries 
WHERE flight_rules = 'V'  -- VFR flights only
    AND departure IS NOT NULL 
    AND arrival IS NOT NULL
    AND departure != ''
    AND arrival != ''
    AND departure != arrival  -- Exclude flights that don't actually go anywhere
    AND completion_time >= NOW() - INTERVAL '30 days'  -- Last 30 days
GROUP BY departure, arrival
HAVING COUNT(*) >= 2  -- Only show routes with at least 2 flights in last 30 days
ORDER BY vfr_flights_last_30_days DESC, unique_aircraft_last_30_days DESC
LIMIT 20;

-- Option 4: VFR route popularity by aircraft type (most common VFR aircraft)
SELECT 
    aircraft_short,
    COUNT(*) as total_vfr_flights,
    COUNT(DISTINCT CONCAT(departure, ' → ', arrival)) as unique_routes_flown,
    ROUND(AVG(time_online_minutes), 1) as avg_flight_duration_minutes,
    ROUND(AVG(controller_time_percentage), 1) as avg_atc_contact_percentage
FROM flight_summaries 
WHERE flight_rules = 'V'  -- VFR flights only
    AND aircraft_short IS NOT NULL
    AND aircraft_short != ''
GROUP BY aircraft_short
HAVING COUNT(*) >= 10  -- Only show aircraft types with at least 10 VFR flights
ORDER BY total_vfr_flights DESC, unique_routes_flown DESC
LIMIT 15;
