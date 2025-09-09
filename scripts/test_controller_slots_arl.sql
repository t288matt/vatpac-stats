-- Test: controller-derived slots joined to flight counts for BN-ARL_CTR
WITH recent_monday AS (
    SELECT
        CASE
            WHEN EXTRACT(DOW FROM CURRENT_DATE) = 1 THEN CURRENT_DATE
            ELSE CURRENT_DATE - INTERVAL '1 day' * (EXTRACT(DOW FROM CURRENT_DATE) - 1)
        END AS monday_date
),
controller_slots AS (
    SELECT
        cs.callsign,
        CASE
            WHEN NULLIF(regexp_replace(fq_elem, '[^0-9\.]', '', 'g'), '') = '' THEN NULL
            WHEN POSITION('.' IN regexp_replace(fq_elem, '[^0-9\.]', '', 'g')) > 0 THEN (round(regexp_replace(fq_elem, '[^0-9\.]', '', 'g')::numeric,3) * 1000000)::bigint
            ELSE regexp_replace(fq_elem, '[^0-9\.]', '', 'g')::bigint
        END AS frequency,
        generate_series(
            to_timestamp(floor(EXTRACT(EPOCH FROM GREATEST(cs.session_start_time, rm.monday_date + INTERVAL '8 hours'))/300)*300)::timestamptz,
            LEAST(COALESCE(cs.session_end_time, rm.monday_date + INTERVAL '12 hours'), rm.monday_date + INTERVAL '12 hours'),
            INTERVAL '5 minutes'
        ) AS time_slot
    FROM controller_summaries cs
    CROSS JOIN recent_monday rm
    CROSS JOIN LATERAL (
        SELECT jsonb_array_elements_text(cs.frequencies_used) AS fq_elem
    ) fq
    WHERE cs.frequencies_used IS NOT NULL
      AND cs.session_start_time < rm.monday_date + INTERVAL '12 hours'
      AND (cs.session_end_time IS NULL OR cs.session_end_time > rm.monday_date + INTERVAL '8 hours')
),
flight_counts AS (
    SELECT
        ts.time_slot,
        ft.frequency,
        COUNT(DISTINCT ft.callsign) AS unique_callsigns
    FROM transceivers ft
    JOIN (SELECT monday_date + INTERVAL '8 hours' + (generate_series(0,47)*INTERVAL '5 minutes') AS time_slot FROM recent_monday) ts ON ft.timestamp >= ts.time_slot - INTERVAL '3 minutes' AND ft.timestamp < ts.time_slot + INTERVAL '3 minutes'
    WHERE ft.entity_type = 'flight'
      AND ft.frequency BETWEEN 118000000 AND 137000000
      AND ft.frequency NOT IN (120500000, 121700000, 126500000)
      AND NOT (ft.frequency BETWEEN 121500000 AND 121500999)
    GROUP BY ft.frequency, ts.time_slot
)

SELECT cs.callsign,
       cs.time_slot,
       ROUND(cs.frequency::numeric/1000000,3) AS freq_mhz,
       COALESCE(fc.unique_callsigns,0) AS unique_callsigns
FROM controller_slots cs
LEFT JOIN flight_counts fc ON cs.frequency = fc.frequency AND cs.time_slot = fc.time_slot
WHERE cs.callsign = 'BN-ARL_CTR'
ORDER BY cs.time_slot;
