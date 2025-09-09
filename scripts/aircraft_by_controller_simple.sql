-- Simplified version: Aircraft Count by Controller Every 5 Minutes
-- This version finds controllers active during each time slot and counts aircraft on their frequency

WITH recent_monday AS (
    SELECT 
        CASE 
            WHEN EXTRACT(DOW FROM CURRENT_DATE) = 1 THEN CURRENT_DATE
            ELSE CURRENT_DATE - INTERVAL '1 day' * (EXTRACT(DOW FROM CURRENT_DATE) - 1)
        END as monday_date
),
time_slots AS (
    SELECT 
        monday_date + INTERVAL '8 hours' + (generate_series(0, 47) * INTERVAL '5 minutes') as time_slot
    FROM recent_monday
),
active_controllers AS (
    -- Find controllers active during each time slot
    SELECT DISTINCT
        c.callsign as controller_callsign,
        ROUND(t.frequency::numeric / 1000000, 3) as frequency_mhz,
        ts.time_slot
    FROM transceivers t
    JOIN controllers c ON t.entity_id = c.id
    CROSS JOIN time_slots ts
    WHERE 
        t.entity_type = 'atc'
        AND t.timestamp >= ts.time_slot - INTERVAL '2.5 minutes'
        AND t.timestamp < ts.time_slot + INTERVAL '2.5 minutes'
        AND t.frequency >= 118000000
        AND t.frequency <= 137000000
)
SELECT 
    ROW_NUMBER() OVER (ORDER BY ac.time_slot, ac.controller_callsign) as id,
    ac.controller_callsign,
    ac.frequency_mhz,
    ac.time_slot::text as time_slot,
    COUNT(DISTINCT ft.callsign) as unique_aircraft
FROM active_controllers ac
JOIN transceivers ft ON ft.frequency = (ac.frequency_mhz * 1000000)::bigint
    AND ft.entity_type = 'flight'
    AND ft.timestamp >= ac.time_slot - INTERVAL '2.5 minutes'
    AND ft.timestamp < ac.time_slot + INTERVAL '2.5 minutes'
GROUP BY 
    ac.controller_callsign,
    ac.frequency_mhz,
    ac.time_slot
HAVING 
    COUNT(DISTINCT ft.callsign) >= 3
ORDER BY 
    ac.time_slot,
    ac.controller_callsign;
