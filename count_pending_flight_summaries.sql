-- Count flights awaiting flight summary processing from both tables
-- This query identifies canonical sessions that don't have corresponding flight summaries yet

WITH canonical_sessions AS (
    -- Get all canonical sessions from both flights and flights_archive tables
    SELECT 
        callsign, 
        cid, 
        departure, 
        arrival,
        MIN(COALESCE(logon_time, last_updated)) as session_start,
        MAX(last_updated) as session_end
    FROM (
        -- Active flights table
        SELECT callsign, cid, departure, arrival, COALESCE(logon_time, last_updated) as logon_time, last_updated 
        FROM flights 
        WHERE NOW() >= last_updated + (8 * INTERVAL '1 hour')  -- Only completed flights (8 hours)
        
        UNION ALL
        
        -- Archived flights table  
        SELECT callsign, cid, departure, arrival, COALESCE(logon_time, last_updated) as logon_time, last_updated 
        FROM flights_archive 
        WHERE NOW() >= last_updated + (8 * INTERVAL '1 hour')  -- Only completed flights (8 hours)
    ) combined_flights
    GROUP BY callsign, cid, departure, arrival
),
pending_sessions AS (
    -- Find canonical sessions that don't have flight summaries yet
    SELECT cs.*
    FROM canonical_sessions cs
    WHERE NOT EXISTS (
        SELECT 1 
        FROM flight_summaries fs 
        WHERE fs.callsign = cs.callsign 
        AND COALESCE(fs.cid, 0) = COALESCE(cs.cid, 0)
        AND COALESCE(fs.departure, '') = COALESCE(cs.departure, '')
        AND COALESCE(fs.arrival, '') = COALESCE(cs.arrival, '')
    )
)
SELECT 
    COUNT(*) as pending_flight_summaries
FROM pending_sessions;
