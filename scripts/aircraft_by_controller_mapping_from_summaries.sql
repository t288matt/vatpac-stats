-- Map frequencies to controller callsigns using controller_summaries.frequencies_used
-- Count unique flight callsigns per 5-minute slot (0800-1200 UTC) for the most recent Monday
-- Uses mapping derived from the most-recent controller session for each frequency

WITH recent_monday AS (
    SELECT
        CASE
            WHEN EXTRACT(DOW FROM CURRENT_DATE) = 1 THEN CURRENT_DATE
            ELSE CURRENT_DATE - INTERVAL '1 day' * (EXTRACT(DOW FROM CURRENT_DATE) - 1)
        END AS monday_date
),
time_slots AS (
    SELECT
        monday_date + INTERVAL '8 hours' + (generate_series(0, 47) * INTERVAL '5 minutes') AS time_slot
    FROM recent_monday
),
flight_counts AS (
    SELECT
        ts.time_slot,
        ft.frequency,
        COUNT(DISTINCT ft.callsign) AS unique_callsigns
    FROM transceivers ft
    JOIN time_slots ts
      ON ft.timestamp >= ts.time_slot - INTERVAL '3 minutes'
     AND ft.timestamp <  ts.time_slot + INTERVAL '3 minutes'
    WHERE ft.entity_type = 'flight'
      AND ft.frequency BETWEEN 118000000 AND 137000000
      AND ft.frequency NOT IN (120500000, 121700000, 126500000)
      AND NOT (ft.frequency BETWEEN 121500000 AND 121500999)
    GROUP BY
        ft.frequency,
        ts.time_slot
),
mapping_raw AS (
    -- explode frequencies_used JSONB array; normalize to integer Hz where possible
    SELECT
        cs.callsign,
        cs.session_start_time,
        -- extract numeric text from the json element and convert MHz string like '118.100' to Hz bigint
        CASE
            WHEN NULLIF(regexp_replace(fq_elem, '[^0-9\.]', '', 'g'), '') = '' THEN NULL
            WHEN POSITION('.' IN regexp_replace(fq_elem, '[^0-9\.]', '', 'g')) > 0 THEN (round(regexp_replace(fq_elem, '[^0-9\.]', '', 'g')::numeric,3) * 1000000)::bigint
            ELSE regexp_replace(fq_elem, '[^0-9\.]', '', 'g')::bigint
        END AS frequency
    FROM controller_summaries cs
    CROSS JOIN LATERAL (
        SELECT jsonb_array_elements_text(cs.frequencies_used) AS fq_elem
    ) fq_elem
    WHERE cs.frequencies_used IS NOT NULL
),
mapping_ranked AS (
    -- pick the most recent controller session for each frequency
    SELECT
        frequency,
        callsign,
        session_start_time,
        ROW_NUMBER() OVER (PARTITION BY frequency ORDER BY session_start_time DESC) AS rn
    FROM mapping_raw
    WHERE frequency IS NOT NULL
),
mapping AS (
    SELECT frequency, callsign AS controller_callsign
    FROM mapping_ranked
    WHERE rn = 1
)

SELECT
    ROW_NUMBER() OVER (ORDER BY fc.time_slot, m.controller_callsign) AS row_id,
    m.controller_callsign,
    ROUND(m.frequency::numeric / 1000000, 3) AS controller_frequency_mhz,
    fc.time_slot,
    fc.unique_callsigns
FROM flight_counts fc
JOIN mapping m ON fc.frequency = m.frequency
WHERE fc.unique_callsigns >= 3
ORDER BY fc.time_slot, m.controller_callsign;
