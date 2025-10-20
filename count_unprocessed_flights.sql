-- Count flights awaiting processing due to the 5-field exclusion defect
WITH canonical_sessions AS (
    -- First calculate session_start for all flights
    SELECT 
        callsign, 
        cid, 
        departure, 
        arrival,
        MIN(COALESCE(logon_time, last_updated)) OVER (
            PARTITION BY callsign, cid, departure, arrival
            ORDER BY COALESCE(logon_time, last_updated)
            RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) as session_start
    FROM (
        -- Get flights from both tables
        SELECT callsign, cid, departure, arrival, logon_time, last_updated 
        FROM flights
        WHERE NOW() >= last_updated + (8 * INTERVAL '1 hour')
        
        UNION ALL
        
        SELECT callsign, cid, departure, arrival, logon_time, last_updated 
        FROM flights_archive
        WHERE NOW() >= last_updated + (8 * INTERVAL '1 hour')
    ) combined_flights
),
processed_with_4_fields AS (
    -- These are sessions excluded by current 4-field logic
    SELECT DISTINCT 
        cs.callsign, 
        cs.cid, 
        cs.departure, 
        cs.arrival
    FROM canonical_sessions cs
    WHERE EXISTS (
        SELECT 1 
        FROM flight_summaries fs 
        WHERE fs.callsign = cs.callsign 
        AND COALESCE(fs.cid, 0) = COALESCE(cs.cid, 0)
        AND COALESCE(fs.departure, '') = COALESCE(cs.departure, '')
        AND COALESCE(fs.arrival, '') = COALESCE(cs.arrival, '')
    )
),
processed_with_5_fields AS (
    -- These are sessions correctly excluded with 5-field logic
    SELECT DISTINCT 
        cs.callsign, 
        cs.cid, 
        cs.departure, 
        cs.arrival,
        cs.session_start
    FROM canonical_sessions cs
    WHERE EXISTS (
        SELECT 1 
        FROM flight_summaries fs 
        WHERE fs.callsign = cs.callsign 
        AND COALESCE(fs.cid, 0) = COALESCE(cs.cid, 0)
        AND COALESCE(fs.departure, '') = COALESCE(cs.departure, '')
        AND COALESCE(fs.arrival, '') = COALESCE(cs.arrival, '')
        AND fs.logon_time = cs.session_start
    )
),
incorrectly_excluded AS (
    -- These are the sessions incorrectly excluded by 4-field logic
    -- but would not be excluded with 5-field logic (the bug!)
    SELECT 
        cs.callsign, 
        cs.cid, 
        cs.departure, 
        cs.arrival,
        cs.session_start
    FROM canonical_sessions cs
    JOIN processed_with_4_fields p4 ON
        cs.callsign = p4.callsign AND
        COALESCE(cs.cid, 0) = COALESCE(p4.cid, 0) AND
        COALESCE(cs.departure, '') = COALESCE(p4.departure, '') AND
        COALESCE(cs.arrival, '') = COALESCE(p4.arrival, '')
    WHERE NOT EXISTS (
        SELECT 1 
        FROM processed_with_5_fields p5
        WHERE p5.callsign = cs.callsign
        AND COALESCE(p5.cid, 0) = COALESCE(cs.cid, 0)
        AND COALESCE(p5.departure, '') = COALESCE(cs.departure, '')
        AND COALESCE(p5.arrival, '') = COALESCE(cs.arrival, '')
        AND p5.session_start = cs.session_start
    )
)
-- Get count and sample of incorrectly excluded flights
SELECT 
    COUNT(*) AS total_stuck_flights,
    (SELECT COUNT(*) FROM incorrectly_excluded WHERE session_start < NOW() - INTERVAL '48 hours') AS flights_older_than_48h
FROM incorrectly_excluded;


