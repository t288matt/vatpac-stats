-- Backfill minimal controller_summaries for callsigns implicated in flight→controller mismatches
-- Sessionization: gap > 15 minutes splits sessions

BEGIN;

WITH flight_ctrl AS (
  SELECT fs.callsign AS flight_callsign,
         fs.logon_time,
         COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') AS completion_time,
         key AS controller_callsign
  FROM flight_summaries fs
  CROSS JOIN LATERAL jsonb_object_keys(fs.controller_callsigns) AS key
  WHERE fs.controller_callsigns IS NOT NULL
    AND fs.controller_callsigns <> '{}'::jsonb
), mism AS (
  SELECT fc.*
  FROM flight_ctrl fc
  WHERE NOT EXISTS (
    SELECT 1
    FROM controller_summaries cs
    WHERE cs.callsign = fc.controller_callsign
      AND cs.session_start_time <= fc.completion_time
      AND (cs.session_end_time IS NULL OR cs.session_end_time >= fc.logon_time)
      AND EXISTS (
        SELECT 1 FROM jsonb_array_elements(cs.aircraft_details) AS d
        WHERE d->>'callsign' = fc.flight_callsign
      )
  )
), callsign_window AS (
  SELECT controller_callsign,
         MIN(logon_time) AS min_logon,
         MAX(completion_time) AS max_completion
  FROM mism
  GROUP BY controller_callsign
), source_rows AS (
  SELECT callsign, last_updated, logon_time, cid, rating, facility, server
  FROM controllers
  UNION ALL
  SELECT callsign, last_updated, logon_time, cid, rating, facility, server
  FROM controllers_archive
), ctrl_rows AS (
  SELECT src.callsign,
         src.last_updated,
         src.logon_time,
         src.cid,
         src.rating,
         src.facility,
         src.server
  FROM callsign_window c
  JOIN source_rows src
    ON src.callsign = c.controller_callsign
   AND src.last_updated BETWEEN c.min_logon AND c.max_completion
), ordered AS (
  SELECT callsign,
         COALESCE(logon_time, last_updated) AS ts,
         last_updated,
         cid, rating, facility, server,
         LAG(last_updated) OVER (PARTITION BY callsign ORDER BY last_updated) AS prev_last
  FROM ctrl_rows
), segmented AS (
  SELECT *,
         CASE WHEN prev_last IS NULL OR (last_updated - prev_last) > INTERVAL '15 minutes' THEN 1 ELSE 0 END AS is_new
  FROM ordered
), labeled AS (
  SELECT callsign, ts, last_updated, cid, rating, facility, server,
         SUM(is_new) OVER (PARTITION BY callsign ORDER BY last_updated ROWS UNBOUNDED PRECEDING) AS seg_id
  FROM segmented
), sessions AS (
  SELECT callsign,
         MIN(ts) AS session_start_time,
         MAX(last_updated) AS session_end_time,
         (EXTRACT(EPOCH FROM (MAX(last_updated) - MIN(ts))) / 60.0)::int AS session_duration_minutes,
         MAX(cid) FILTER (WHERE cid IS NOT NULL) AS cid,
         MAX(rating) FILTER (WHERE rating IS NOT NULL) AS rating,
         MAX(facility) FILTER (WHERE facility IS NOT NULL) AS facility,
         MAX(server) FILTER (WHERE server IS NOT NULL) AS server
  FROM labeled
  GROUP BY callsign, seg_id
)
INSERT INTO controller_summaries (
  callsign, cid, name, session_start_time, session_end_time, session_duration_minutes,
  rating, facility, server, total_aircraft_handled, peak_aircraft_count, aircraft_details,
  created_at, updated_at
)
SELECT s.callsign, s.cid, NULL AS name, s.session_start_time, s.session_end_time, s.session_duration_minutes,
       s.rating, s.facility, s.server, 0, 0, '[]'::jsonb, NOW(), NOW()
FROM sessions s
WHERE NOT EXISTS (
  SELECT 1 FROM controller_summaries cs
  WHERE cs.callsign = s.callsign
    AND cs.session_start_time = s.session_start_time
);

COMMIT;


