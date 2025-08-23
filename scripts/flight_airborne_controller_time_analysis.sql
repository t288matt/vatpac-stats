-- Flight Airborne Controller Time Analysis
-- Shows percentage of time flights spent on controller frequencies while airborne
-- Uses the new airborne_controller_time_percentage field

-- Query 1: Basic overview of flights with airborne controller time percentages
SELECT 
    f.callsign,
    f.departure,
    f.arrival,
    f.aircraft_type,
    f.logon_time,
    f.last_updated,
    EXTRACT(EPOCH FROM (f.last_updated - f.logon_time))/60 as duration_minutes,
    fs.airborne_controller_time_percentage,
    fs.controller_time_percentage,
    fs.primary_enroute_sector,
    fs.total_enroute_sectors
FROM flights f
LEFT JOIN flight_summaries fs ON f.callsign = fs.callsign
WHERE fs.airborne_controller_time_percentage IS NOT NULL
    AND fs.airborne_controller_time_percentage > 0
ORDER BY fs.airborne_controller_time_percentage DESC
LIMIT 20;

-- Query 2: Flights with highest airborne controller time percentages
SELECT 
    f.callsign,
    f.departure,
    f.arrival,
    f.aircraft_type,
    fs.airborne_controller_time_percentage,
    fs.controller_time_percentage,
    fs.time_online_minutes,
    fs.total_enroute_sectors,
    fs.primary_enroute_sector
FROM flights f
JOIN flight_summaries fs ON f.callsign = fs.callsign
WHERE fs.airborne_controller_time_percentage IS NOT NULL
    AND fs.airborne_controller_time_percentage > 0
    AND fs.airborne_controller_time_percentage <= 100
ORDER BY fs.airborne_controller_time_percentage DESC
LIMIT 15;

-- Query 3: Comparison of controller time vs airborne controller time
SELECT 
    f.callsign,
    f.departure,
    f.arrival,
    fs.controller_time_percentage,
    fs.airborne_controller_time_percentage,
    CASE 
        WHEN fs.controller_time_percentage > 0 THEN 
            ROUND((fs.airborne_controller_time_percentage / fs.controller_time_percentage * 100), 2)
        ELSE 0 
    END as airborne_percentage_of_controller_time,
    fs.total_enroute_sectors,
    fs.primary_enroute_sector
FROM flights f
JOIN flight_summaries fs ON f.callsign = fs.callsign
WHERE fs.controller_time_percentage > 0
    AND fs.airborne_controller_time_percentage IS NOT NULL
ORDER BY fs.airborne_controller_time_percentage DESC
LIMIT 20;

-- Query 4: Flights by sector with airborne controller time
SELECT 
    fs.primary_enroute_sector,
    COUNT(*) as total_flights,
    AVG(fs.airborne_controller_time_percentage) as avg_airborne_controller_time,
    MAX(fs.airborne_controller_time_percentage) as max_airborne_controller_time,
    MIN(fs.airborne_controller_time_percentage) as min_airborne_controller_time
FROM flight_summaries fs
WHERE fs.airborne_controller_time_percentage IS NOT NULL
    AND fs.primary_enroute_sector IS NOT NULL
GROUP BY fs.primary_enroute_sector
HAVING COUNT(*) >= 3
ORDER BY avg_airborne_controller_time DESC;

-- Query 5: Detailed breakdown for a specific flight (example: VOZ215)
SELECT 
    f.callsign,
    f.departure,
    f.arrival,
    f.aircraft_type,
    f.logon_time,
    f.last_updated,
    EXTRACT(EPOCH FROM (f.last_updated - f.logon_time))/60 as duration_minutes,
    fs.airborne_controller_time_percentage,
    fs.controller_time_percentage,
    fs.time_online_minutes,
    fs.total_enroute_sectors,
    fs.primary_enroute_sector,
    fs.sector_breakdown
FROM flights f
JOIN flight_summaries fs ON f.callsign = fs.callsign
WHERE f.callsign = 'VOZ215'
ORDER BY f.logon_time DESC
LIMIT 1;

-- Query 6: Summary statistics for all flights with airborne controller time
SELECT 
    COUNT(*) as total_flights_with_airborne_time,
    COUNT(CASE WHEN airborne_controller_time_percentage > 0 THEN 1 END) as flights_with_positive_airborne_time,
    ROUND(AVG(airborne_controller_time_percentage), 2) as avg_airborne_controller_time,
    ROUND(MAX(airborne_controller_time_percentage), 2) as max_airborne_controller_time,
    ROUND(MIN(airborne_controller_time_percentage), 2) as min_airborne_controller_time,
    ROUND(STDDEV(airborne_controller_time_percentage), 2) as stddev_airborne_controller_time
FROM flight_summaries
WHERE airborne_controller_time_percentage IS NOT NULL;
