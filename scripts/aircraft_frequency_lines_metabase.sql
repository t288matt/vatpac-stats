-- Metabase-friendly: one row per time_slot+frequency for line series per frequency
-- time_slot (timestamp), frequency_mhz (series), unique_callsigns (value)

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
controllers_per_slot AS (
    SELECT DISTINCT
        ts.time_slot,
        atc.frequency,
        c.callsign AS controller_callsign
    FROM transceivers atc
    JOIN controllers c ON atc.entity_id = c.id
    JOIN time_slots ts
      ON atc.timestamp >= ts.time_slot - INTERVAL '3 minutes'
     AND atc.timestamp <  ts.time_slot + INTERVAL '3 minutes'
    WHERE atc.entity_type = 'atc'
      AND atc.frequency BETWEEN 118000000 AND 137000000
      AND atc.frequency NOT IN (120500000, 121700000, 126500000)
      AND NOT (atc.frequency BETWEEN 121500000 AND 121500999)
)

SELECT
    ROW_NUMBER() OVER (ORDER BY cps.time_slot, cps.controller_callsign) AS id,
    cps.time_slot AS time,
    cps.controller_callsign AS series,
    SUM(fc.unique_callsigns) AS value
FROM flight_counts fc
JOIN controllers_per_slot cps
  ON fc.frequency = cps.frequency
 AND fc.time_slot = cps.time_slot
WHERE cps.controller_callsign IS NOT NULL
  AND cps.controller_callsign NOT ILIKE '%DEL%'
GROUP BY
    cps.time_slot,
    cps.controller_callsign
HAVING SUM(fc.unique_callsigns) >= 3
ORDER BY cps.time_slot, series;
