-- corrected_controller_slots_aligned.sql
-- Align controller-generated slots to the canonical 5-minute grid and
-- convert frequencies robustly. This ensures controller_slots.time_slot
-- matches time_slots.time_slot so joins succeed.

WITH recent_monday AS (
    SELECT
        CASE
            WHEN EXTRACT(DOW FROM CURRENT_DATE) = 1 THEN CURRENT_DATE
            ELSE CURRENT_DATE - INTERVAL '1 day' * (EXTRACT(DOW FROM CURRENT_DATE) - 1)
        END AS monday_date
),
time_slots AS (
    SELECT
        monday_date + INTERVAL '7 hours' + (generate_series(0, 60) * INTERVAL '5 minutes') AS time_slot
    FROM recent_monday
),
controller_slots AS (
    SELECT
        cs.callsign,
        CASE
            WHEN rf.raw_freq = '' THEN NULL
            WHEN POSITION('.' IN rf.raw_freq) > 0 THEN (round(rf.raw_freq::numeric, 3) * 1000000)::bigint
            ELSE rf.raw_freq::bigint
        END AS frequency,
        generate_series(
            -- Align session start to nearest 5-minute grid used by time_slots
            to_timestamp(floor(EXTRACT(EPOCH FROM GREATEST(cs.session_start_time, rm.monday_date + INTERVAL '7 hours'))/300)*300)::timestamptz,
            LEAST(COALESCE(cs.session_end_time, rm.monday_date + INTERVAL '12 hours'), rm.monday_date + INTERVAL '12 hours'),
            INTERVAL '5 minutes'
        ) AS time_slot
    FROM controller_summaries cs
    CROSS JOIN recent_monday rm
    CROSS JOIN LATERAL (
        SELECT regexp_replace(jsonb_array_elements_text(cs.frequencies_used), '[^0-9\.]', '', 'g') AS raw_freq
    ) rf
    WHERE cs.frequencies_used IS NOT NULL
      AND cs.session_start_time < rm.monday_date + INTERVAL '12 hours'
      AND (cs.session_end_time IS NULL OR cs.session_end_time > rm.monday_date + INTERVAL '7 hours')
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
)

SELECT
    ROW_NUMBER() OVER (ORDER BY cs.time_slot, cs.callsign) AS id,
    cs.time_slot      AS time,
    cs.callsign       AS series,
    COALESCE(fc.unique_callsigns, 0) AS value
FROM controller_slots cs
LEFT JOIN flight_counts fc
  ON fc.frequency BETWEEN cs.frequency - 5000 AND cs.frequency + 5000
 AND cs.time_slot = fc.time_slot
WHERE cs.frequency BETWEEN 118000000 AND 137000000
  AND cs.frequency NOT IN (120500000, 121700000, 126500000)
  AND NOT (cs.frequency BETWEEN 121500000 AND 121500999)
  AND cs.callsign NOT ILIKE '%DEL%'
  AND cs.callsign NOT ILIKE '%TWR%'
  AND cs.callsign NOT ILIKE '%GND%'
  AND COALESCE(fc.unique_callsigns, 0) >= 3
ORDER BY cs.time_slot, cs.callsign;
