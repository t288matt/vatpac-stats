-- Query to find most popular routes by military aircraft from last week
-- Using flights table with RAAFVIRTUAL.ORG filter and deduplication

SELECT 
    f.departure,
    f.arrival,
    CONCAT(f.departure, ' → ', f.arrival) as route,
    COUNT(*) as total_flights,
    COUNT(DISTINCT f.cid) as unique_pilots,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 
        2
    ) as percentage_of_total_military_flights,
    ROUND(
        COUNT(DISTINCT f.cid) * 100.0 / SUM(COUNT(DISTINCT f.cid)) OVER (), 
        2
    ) as percentage_of_total_military_pilots
FROM (
    SELECT DISTINCT ON (callsign, logon_time) 
        callsign, departure, arrival, cid, remarks, logon_time
    FROM flights 
    WHERE remarks ILIKE '%RAAFVIRTUAL.ORG%'
        AND logon_time >= NOW() - INTERVAL '1 month'
        AND cid IS NOT NULL
        AND departure IS NOT NULL 
        AND arrival IS NOT NULL
        AND departure != ''
        AND arrival != ''
    ORDER BY callsign, logon_time, last_updated DESC
) f
GROUP BY f.departure, f.arrival
ORDER BY total_flights DESC, unique_pilots DESC;




