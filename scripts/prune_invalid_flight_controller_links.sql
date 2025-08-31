-- Remove controller keys from flight_summaries that have no overlapping controller_summaries session

BEGIN;

WITH keys AS (
  SELECT fs.id,
         fs.logon_time,
         COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') AS completion_time,
         key AS controller_callsign
  FROM flight_summaries fs
  CROSS JOIN LATERAL jsonb_object_keys(fs.controller_callsigns) AS key
  WHERE fs.controller_callsigns IS NOT NULL
    AND fs.controller_callsigns <> '{}'::jsonb
), bad AS (
  SELECT k.id, k.controller_callsign
  FROM keys k
  WHERE NOT EXISTS (
    SELECT 1
    FROM controller_summaries cs
    WHERE cs.callsign = k.controller_callsign
      AND cs.session_start_time <= k.completion_time
      AND (cs.session_end_time IS NULL OR cs.session_end_time >= k.logon_time)
  )
)
UPDATE flight_summaries fs
SET controller_callsigns = fs.controller_callsigns - b.controller_callsign,
    updated_at = NOW()
FROM bad b
WHERE fs.id = b.id;

COMMIT;


