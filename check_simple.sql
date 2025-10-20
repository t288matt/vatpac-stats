-- Simple check for unprocessed flights
WITH flights_waiting AS (
    SELECT 
        f.callsign, 
        f.cid, 
        f.departure, 
        f.arrival
    FROM flights f
    WHERE NOW() >= f.last_updated + (8 * INTERVAL '1 hour')
    AND f.logon_time IS NOT NULL
    
    UNION ALL
    
    SELECT 
        f.callsign, 
        f.cid, 
        f.departure, 
        f.arrival
    FROM flights_archive f
    WHERE NOW() >= f.last_updated + (8 * INTERVAL '1 hour')
    AND f.logon_time IS NOT NULL
)
SELECT 
    COUNT(DISTINCT (fw.callsign, fw.cid, fw.departure, fw.arrival)) AS total_unprocessed_flights
FROM flights_waiting fw
WHERE NOT EXISTS (
    SELECT 1 
    FROM flight_summaries fs 
    WHERE fs.callsign = fw.callsign 
    AND COALESCE(fs.cid, 0) = COALESCE(fw.cid, 0)
    AND COALESCE(fs.departure, '') = COALESCE(fw.departure, '')
    AND COALESCE(fs.arrival, '') = COALESCE(fw.arrival, '')
);


