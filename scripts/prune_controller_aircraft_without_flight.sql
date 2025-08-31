-- Remove aircraft entries from controller_summaries when no overlapping flight summary exists

BEGIN;

WITH ctrl_rows AS (
  SELECT cs.id AS controller_summary_id,
         cs.session_start_time,
         COALESCE(cs.session_end_time, NOW() AT TIME ZONE 'UTC') AS session_end_time,
         d->>'callsign' AS flight_callsign
  FROM controller_summaries cs
  CROSS JOIN LATERAL jsonb_array_elements(COALESCE(cs.aircraft_details, '[]'::jsonb)) AS d
), bad AS (
  SELECT cr.controller_summary_id, cr.flight_callsign
  FROM ctrl_rows cr
  LEFT JOIN flight_summaries fs
    ON fs.callsign = cr.flight_callsign
   AND fs.logon_time <= cr.session_end_time
   AND COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') >= cr.session_start_time
  WHERE fs.id IS NULL
)
UPDATE controller_summaries cs
SET aircraft_details = (
  SELECT jsonb_agg(x)
  FROM jsonb_array_elements(COALESCE(cs.aircraft_details, '[]'::jsonb)) AS x
  WHERE (x->>'callsign') NOT IN (
    SELECT flight_callsign FROM bad b WHERE b.controller_summary_id = cs.id
  )
),
updated_at = NOW()
WHERE EXISTS (
  SELECT 1 FROM bad b WHERE b.controller_summary_id = cs.id
);

COMMIT;


