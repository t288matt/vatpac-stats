-- Unique Callsign Count by Frequency Every 5 Minutes (0800-1200 UTC) for Most Recent Monday
-- Using only transceivers table as requested

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
    ROW_NUMBER() OVER (ORDER BY ts.time_slot, t.frequency) as row_id,
    -- Convert frequency from Hz to MHz for readability
    ROUND(t.frequency::numeric / 1000000, 3) as frequency_mhz,
    ts.time_slot,
    COUNT(DISTINCT t.callsign) as unique_callsigns
FROM transceivers t
CROSS JOIN time_slots ts
WHERE 
    -- Only flight entities (not ATC)
    t.entity_type = 'flight'
    -- Time window: 5-minute slot ± 2.5 minutes to capture aircraft active in that period
    AND t.timestamp >= ts.time_slot - INTERVAL '2.5 minutes'
    AND t.timestamp < ts.time_slot + INTERVAL '2.5 minutes'
    -- Only frequencies in the aviation range (118-137 MHz = 118000000-137000000 Hz)
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

-- Alternative query with exact time matching (more precise but may miss some aircraft)
-- Uncomment below and comment above if you prefer exact timestamp matching

/*
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
    ROUND(t.frequency::numeric / 1000000, 3) as frequency_mhz,
    ts.time_slot,
    COUNT(DISTINCT t.callsign) as unique_callsigns
FROM transceivers t
CROSS JOIN time_slots ts
WHERE 
    t.entity_type = 'flight'
    -- Exact time matching - only aircraft active at the exact 5-minute mark
    AND DATE_TRUNC('minute', t.timestamp) = DATE_TRUNC('minute', ts.time_slot)
    AND t.frequency >= 118000000
    AND t.frequency <= 137000000
GROUP BY 
    t.frequency,
    ts.time_slot
ORDER BY 
    ts.time_slot,
    t.frequency;
*/
