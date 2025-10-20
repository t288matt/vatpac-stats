-- Find flight summaries with time_online_minutes = 0 despite having actual flight duration
-- This query demonstrates the bug described in FLIGHT_SUMMARY_ZERO_MINUTES_FIX.md

-- Part 1: Show flight summaries with 0 minutes but non-zero logon-to-completion duration
SELECT 
    fs.id,
    fs.callsign,
    fs.cid,
    fs.departure,
    fs.arrival,
    fs.logon_time,
    fs.completion_time,
    fs.time_online_minutes,
    EXTRACT(EPOCH FROM (fs.completion_time - fs.logon_time))/60 AS actual_minutes_between_logon_completion,
    fs.created_at
FROM flight_summaries fs
WHERE fs.time_online_minutes = 0 
    AND fs.completion_time IS NOT NULL
    AND fs.logon_time IS NOT NULL
    AND fs.completion_time > fs.logon_time  -- Ensure there's an actual duration
ORDER BY fs.created_at DESC 
LIMIT 20;

-- Part 2: For each problematic flight, show how many records exist in flights/flights_archive
-- This should reveal if the completion_time matches only the first record's timestamp
SELECT 
    fs.id AS flight_summary_id,
    fs.callsign,
    fs.cid,
    fs.departure,
    fs.arrival,
    fs.logon_time,
    fs.completion_time,
    fs.time_online_minutes,
    (SELECT COUNT(*) FROM flights f 
     WHERE f.callsign = fs.callsign 
     AND f.cid = fs.cid 
     AND f.departure = fs.departure 
     AND f.arrival = fs.arrival) AS flights_count,
    (SELECT COUNT(*) FROM flights_archive fa 
     WHERE fa.callsign = fs.callsign 
     AND fa.cid = fs.cid 
     AND fa.departure = fs.departure 
     AND fa.arrival = fs.arrival) AS flights_archive_count,
    (SELECT MIN(last_updated) FROM (
        SELECT last_updated FROM flights f 
        WHERE f.callsign = fs.callsign 
        AND f.cid = fs.cid 
        AND f.departure = fs.departure 
        AND f.arrival = fs.arrival
        UNION ALL
        SELECT last_updated FROM flights_archive fa 
        WHERE fa.callsign = fs.callsign 
        AND fa.cid = fs.cid 
        AND fa.departure = fs.departure 
        AND fa.arrival = fs.arrival
    ) combined) AS first_record_timestamp,
    (SELECT MAX(last_updated) FROM (
        SELECT last_updated FROM flights f 
        WHERE f.callsign = fs.callsign 
        AND f.cid = fs.cid 
        AND f.departure = fs.departure 
        AND f.arrival = fs.arrival
        UNION ALL
        SELECT last_updated FROM flights_archive fa 
        WHERE fa.callsign = fs.callsign 
        AND fa.cid = fs.cid 
        AND fa.departure = fs.departure 
        AND fa.arrival = fs.arrival
    ) combined) AS last_record_timestamp,
    EXTRACT(EPOCH FROM (
        (SELECT MAX(last_updated) FROM (
            SELECT last_updated FROM flights f 
            WHERE f.callsign = fs.callsign 
            AND f.cid = fs.cid 
            AND f.departure = fs.departure 
            AND f.arrival = fs.arrival
            UNION ALL
            SELECT last_updated FROM flights_archive fa 
            WHERE fa.callsign = fs.callsign 
            AND fa.cid = fs.cid 
            AND fa.departure = fs.departure 
            AND fa.arrival = fs.arrival
        ) combined) - 
        (SELECT MIN(last_updated) FROM (
            SELECT last_updated FROM flights f 
            WHERE f.callsign = fs.callsign 
            AND f.cid = fs.cid 
            AND f.departure = fs.departure 
            AND f.arrival = fs.arrival
            UNION ALL
            SELECT last_updated FROM flights_archive fa 
            WHERE fa.callsign = fs.callsign 
            AND fa.cid = fs.cid 
            AND fa.departure = fs.departure 
            AND fa.arrival = fs.arrival
        ) combined)
    ))/60 AS actual_flight_minutes_from_records
FROM flight_summaries fs
WHERE fs.time_online_minutes = 0 
    AND fs.completion_time IS NOT NULL
    AND fs.logon_time IS NOT NULL
    AND fs.completion_time > fs.logon_time
ORDER BY fs.created_at DESC 
LIMIT 10;

-- Part 3: Detailed investigation of ONE specific example
-- Show the records for the most recent problematic flight
WITH problematic_flight AS (
    SELECT 
        fs.callsign,
        fs.cid,
        fs.departure,
        fs.arrival,
        fs.logon_time,
        fs.completion_time,
        fs.time_online_minutes
    FROM flight_summaries fs
    WHERE fs.time_online_minutes = 0 
        AND fs.completion_time IS NOT NULL
        AND fs.logon_time IS NOT NULL
        AND fs.completion_time > fs.logon_time
    ORDER BY fs.created_at DESC 
    LIMIT 1
)
SELECT 
    'flights' AS source_table,
    f.last_updated,
    f.logon_time,
    f.latitude,
    f.longitude,
    f.altitude,
    f.groundspeed,
    EXTRACT(EPOCH FROM (f.last_updated - pf.logon_time))/60 AS minutes_since_logon,
    CASE 
        WHEN f.last_updated = pf.completion_time THEN 'MATCHES COMPLETION_TIME'
        ELSE ''
    END AS completion_match
FROM flights f
INNER JOIN problematic_flight pf 
    ON f.callsign = pf.callsign 
    AND f.cid = pf.cid 
    AND f.departure = pf.departure 
    AND f.arrival = pf.arrival
UNION ALL
SELECT 
    'flights_archive' AS source_table,
    fa.last_updated,
    fa.logon_time,
    fa.latitude,
    fa.longitude,
    fa.altitude,
    fa.groundspeed,
    EXTRACT(EPOCH FROM (fa.last_updated - pf.logon_time))/60 AS minutes_since_logon,
    CASE 
        WHEN fa.last_updated = pf.completion_time THEN 'MATCHES COMPLETION_TIME'
        ELSE ''
    END AS completion_match
FROM flights_archive fa
INNER JOIN problematic_flight pf 
    ON fa.callsign = pf.callsign 
    AND fa.cid = pf.cid 
    AND fa.departure = pf.departure 
    AND fa.arrival = pf.arrival
ORDER BY last_updated ASC;

-- Part 4: Summary statistics of the problem
SELECT 
    COUNT(*) AS total_zero_minute_flights,
    COUNT(*) FILTER (WHERE completion_time > logon_time) AS flights_with_actual_duration,
    ROUND(AVG(EXTRACT(EPOCH FROM (completion_time - logon_time))/60), 2) AS avg_logon_completion_minutes,
    MIN(EXTRACT(EPOCH FROM (completion_time - logon_time))/60) AS min_logon_completion_minutes,
    MAX(EXTRACT(EPOCH FROM (completion_time - logon_time))/60) AS max_logon_completion_minutes
FROM flight_summaries
WHERE time_online_minutes = 0 
    AND completion_time IS NOT NULL
    AND logon_time IS NOT NULL;



