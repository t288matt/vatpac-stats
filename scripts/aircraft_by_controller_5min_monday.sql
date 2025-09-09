-- Aircraft Count by Controller Every 5 Minutes (0800-1200 UTC) for Most Recent Monday
-- Shows which controllers have aircraft on their frequency

WITH recent_monday AS (
    -- Find the most recent Monday
    SELECT 
        CASE 
            WHEN EXTRACT(DOW FROM CURRENT_DATE) = 1 THEN CURRENT_DATE  -- Today is Monday
            ELSE CURRENT_DATE - INTERVAL '1 day' * (EXTRACT(DOW FROM CURRENT_DATE) - 1)  -- Go back to Monday
        END as monday_date
),
time_slots AS (
    -- Generate 5-minute time slots between 0800 and 1200 UTC
    SELECT 
        monday_date + INTERVAL '8 hours' + (generate_series(0, 47) * INTERVAL '5 minutes') as time_slot
    FROM recent_monday
)
SELECT 
    ROW_NUMBER() OVER (ORDER BY ts.time_slot, c.callsign) as row_id,
    c.callsign as controller_callsign,
    ROUND(t.frequency::numeric / 1000000, 3) as frequency_mhz,
    ts.time_slot,
    COUNT(DISTINCT ft.callsign) as unique_aircraft
FROM transceivers t
JOIN controllers c ON t.entity_id = c.id AND t.entity_type = 'atc'
CROSS JOIN time_slots ts
JOIN transceivers ft ON ft.frequency = t.frequency 
    AND ft.entity_type = 'flight'
    AND ft.timestamp >= ts.time_slot - INTERVAL '2.5 minutes'
    AND ft.timestamp < ts.time_slot + INTERVAL '2.5 minutes'
WHERE 
    -- Controller transceiver time window
    t.timestamp >= ts.time_slot - INTERVAL '2.5 minutes'
    AND t.timestamp < ts.time_slot + INTERVAL '2.5 minutes'
    -- Only frequencies in the aviation range (118-137 MHz = 118000000-137000000 Hz)
    AND t.frequency >= 118000000
    AND t.frequency <= 137000000
GROUP BY 
    c.callsign,
    t.frequency,
    ts.time_slot
HAVING 
    COUNT(DISTINCT ft.callsign) >= 3
ORDER BY 
    ts.time_slot,
    c.callsign;
