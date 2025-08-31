-- One-time dedupe for flight_summaries by session signature
-- Signature: (callsign, cid, departure, arrival, logon_time)
-- Strategy:
-- 1) Identify duplicate groups (count > 1)
-- 2) Choose a keeper row per group:
--    - highest completion_time; tiebreaker: lowest id
-- 3) Merge fields into keeper if needed (controller_callsigns JSONB union)
-- 4) Delete non-keeper rows

BEGIN;

WITH dupe_groups AS (
  SELECT callsign, cid, departure, arrival, logon_time,
         COUNT(*) AS c
  FROM flight_summaries
  GROUP BY 1,2,3,4,5
  HAVING COUNT(*) > 1
), ranked AS (
  SELECT fs.id,
         fs.callsign, fs.cid, fs.departure, fs.arrival, fs.logon_time,
         fs.completion_time,
         ROW_NUMBER() OVER (
           PARTITION BY fs.callsign, fs.cid, fs.departure, fs.arrival, fs.logon_time
           ORDER BY fs.completion_time DESC NULLS LAST, fs.id ASC
         ) AS rn
  FROM flight_summaries fs
  JOIN dupe_groups g
    ON g.callsign = fs.callsign
   AND g.cid = fs.cid
   AND g.departure = fs.departure
   AND g.arrival = fs.arrival
   AND g.logon_time = fs.logon_time
), keepers AS (
  SELECT * FROM ranked WHERE rn = 1
), victims AS (
  SELECT * FROM ranked WHERE rn > 1
), merged_json AS (
  -- Compute merged controller_callsigns per group
  SELECT k.id AS keeper_id,
         jsonb_strip_nulls(
            COALESCE(kcc.controller_callsigns, '{}'::jsonb) ||
            COALESCE(vcc.merged_victim_json, '{}'::jsonb)
         ) AS merged_controller_callsigns
  FROM keepers k
  LEFT JOIN LATERAL (
    SELECT controller_callsigns FROM flight_summaries fs WHERE fs.id = k.id
  ) kcc(controller_callsigns) ON TRUE
  LEFT JOIN LATERAL (
    SELECT COALESCE(jsonb_object_agg(j.key, j.value), '{}'::jsonb) AS merged_victim_json
    FROM (
      SELECT (jsonb_each(fs.controller_callsigns)).key AS key,
             (jsonb_each(fs.controller_callsigns)).value AS value
      FROM victims v
      JOIN flight_summaries fs ON fs.id = v.id
      WHERE v.callsign = k.callsign
        AND v.cid = k.cid
        AND v.departure = k.departure
        AND v.arrival = k.arrival
        AND v.logon_time = k.logon_time
    ) AS j
  ) vcc ON TRUE
)
-- Update keeper rows with merged JSON and max completion_time
UPDATE flight_summaries dst
SET controller_callsigns = mj.merged_controller_callsigns,
    completion_time = GREATEST(
      dst.completion_time,
      (SELECT MAX(fs2.completion_time) FROM victims v2 JOIN flight_summaries fs2 ON fs2.id = v2.id
        WHERE v2.callsign = dst.callsign AND v2.cid = dst.cid AND v2.departure = dst.departure AND v2.arrival = dst.arrival AND v2.logon_time = dst.logon_time)
    ),
    updated_at = NOW()
FROM merged_json mj
JOIN keepers k ON k.id = mj.keeper_id
WHERE dst.id = k.id;

-- Delete victims
DELETE FROM flight_summaries fs
WHERE fs.id IN (
  SELECT v.id FROM (
    SELECT r.id
    FROM (
      SELECT fs.id,
             ROW_NUMBER() OVER (
               PARTITION BY fs.callsign, fs.cid, fs.departure, fs.arrival, fs.logon_time
               ORDER BY fs.completion_time DESC NULLS LAST, fs.id ASC
             ) AS rn
      FROM flight_summaries fs
      JOIN (
        SELECT callsign, cid, departure, arrival, logon_time
        FROM flight_summaries
        GROUP BY 1,2,3,4,5
        HAVING COUNT(*) > 1
      ) g
      ON g.callsign = fs.callsign
     AND g.cid = fs.cid
     AND g.departure = fs.departure
     AND g.arrival = fs.arrival
     AND g.logon_time = fs.logon_time
    ) r
    WHERE r.rn > 1
  ) v
);

COMMIT;


