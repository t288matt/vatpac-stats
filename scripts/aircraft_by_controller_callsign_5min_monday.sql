-- Map frequencies to controller callsigns and count unique flight callsigns
-- per 5-minute slot (0800-1200 UTC) for the most recent Monday.
-- Excludes 120.5, 121.5 (range), 121.7, 126.5 and only shows counts >= 3.

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
flights_per_slot AS (
    SELECT
        ts.time_slot,
        ft.frequency,
        ft.callsign
    FROM transceivers ft
    JOIN time_slots ts
      ON ft.timestamp >= ts.time_slot - INTERVAL '5 minutes'
     AND ft.timestamp <  ts.time_slot + INTERVAL '5 minutes'
    WHERE ft.entity_type = 'flight'
      AND ft.frequency BETWEEN 118000000 AND 137000000
      AND ft.frequency NOT IN (120500000, 121700000, 126500000)
      AND NOT (ft.frequency BETWEEN 121500000 AND 121500999)
),
controllers_per_slot AS (
    SELECT DISTINCT
        ts.time_slot,
        atc.frequency,
        c.callsign AS controller_callsign
    FROM transceivers atc
    JOIN controllers c ON atc.entity_id = c.id
    JOIN time_slots ts
      ON atc.timestamp >= ts.time_slot - INTERVAL '5 minutes'
     AND atc.timestamp <  ts.time_slot + INTERVAL '5 minutes'
    WHERE atc.entity_type = 'atc'
      AND atc.frequency BETWEEN 118000000 AND 137000000
      AND atc.frequency NOT IN (120500000, 121700000, 126500000)
      AND NOT (atc.frequency BETWEEN 121500000 AND 121500999)
)

SELECT
    ROW_NUMBER() OVER (ORDER BY cps.time_slot, cps.controller_callsign) AS row_id,
    cps.controller_callsign,
    ROUND(cps.frequency::numeric / 1000000, 3) AS controller_frequency_mhz,
    cps.time_slot,
    COUNT(DISTINCT fps.callsign) AS unique_callsigns
FROM controllers_per_slot cps
LEFT JOIN flights_per_slot fps
  ON fps.frequency = cps.frequency
 AND fps.time_slot = cps.time_slot
GROUP BY
    cps.controller_callsign,
    cps.frequency,
    cps.time_slot
HAVING COUNT(DISTINCT fps.callsign) >= 3
ORDER BY
    cps.time_slot,
    cps.controller_callsign;
