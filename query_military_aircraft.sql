-- Query to find most popular military aircraft and count flights
-- Using flights table for active flights with deduplication
-- Comprehensive military aircraft list including fighters, bombers, transport, helicopters, etc.

SELECT 
    f.aircraft_type,
    COUNT(*) as total_flights,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 
        2
    ) as percentage_of_total_flights
FROM (
    SELECT DISTINCT ON (callsign, logon_time) 
        callsign, aircraft_type, remarks, logon_time
    FROM flights 
    WHERE remarks ILIKE '%RAAFVIRTUAL.ORG%'
        AND logon_time >= NOW() - INTERVAL '7 days'
    ORDER BY callsign, logon_time, last_updated DESC
) f
GROUP BY f.aircraft_type
ORDER BY total_flights DESC;
