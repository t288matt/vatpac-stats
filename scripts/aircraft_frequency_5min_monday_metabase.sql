-- Metabase-friendly version: Unique Callsign Count by Frequency Every 5 Minutes
-- This version is optimized for Metabase visualization

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
)
SELECT 
    ROW_NUMBER() OVER (ORDER BY ts.time_slot, t.frequency) as id,
    ROUND(t.frequency::numeric / 1000000, 3) as frequency_mhz,
    ts.time_slot::text as time_slot,
    COUNT(DISTINCT t.callsign) as unique_callsigns
FROM transceivers t
CROSS JOIN time_slots ts
WHERE 
    t.entity_type = 'flight'
    AND t.timestamp >= ts.time_slot - INTERVAL '2.5 minutes'
    AND t.timestamp < ts.time_slot + INTERVAL '2.5 minutes'
    AND t.frequency >= 118000000
    AND t.frequency <= 137000000
    -- Exclude specific frequencies
    AND t.frequency NOT IN (120500000, 121700000, 126500000)
    AND t.frequency NOT BETWEEN 121500000 AND 121500999
GROUP BY 
    t.frequency,
    ts.time_slot
HAVING 
    COUNT(DISTINCT t.callsign) >= 3
ORDER BY 
    ts.time_slot,
    t.frequency;
