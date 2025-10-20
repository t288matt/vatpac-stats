-- Query to find military aircraft airborne time statistics
-- Using flights table with RAAFVIRTUAL.ORG filter and deduplication

SELECT 
    f.aircraft_type, 
    COUNT(DISTINCT CONCAT(f.callsign, '|', f.cid, '|', f.logon_time)) as total_flights,
    SUM(EXTRACT(EPOCH FROM (f.last_updated - f.logon_time)) / 60.0) as total_airborne_minutes, 
    ROUND(SUM(EXTRACT(EPOCH FROM (f.last_updated - f.logon_time)) / 3600.0), 2) as total_airborne_hours, 
    ROUND(AVG(EXTRACT(EPOCH FROM (f.last_updated - f.logon_time)) / 3600.0), 2) as avg_airborne_hours_per_flight 
FROM (
    SELECT DISTINCT ON (callsign, logon_time) 
        callsign, aircraft_type, cid, logon_time, last_updated, remarks
    FROM flights 
    WHERE remarks ILIKE '%RAAFVIRTUAL.ORG%'
        AND logon_time >= NOW() - INTERVAL '30 days'
        AND cid IS NOT NULL
    ORDER BY callsign, logon_time, last_updated DESC
) f
GROUP BY f.aircraft_type 
ORDER BY total_airborne_hours DESC NULLS LAST;
