## Production Integrity Repair Runbook (SQL-only)

### Introduction
This runbook provides operators with a safe, SQL-only procedure to repair and validate the bidirectional links between flight summaries and controller summaries. It is designed to be executed against production with minimal risk and without changing application code or restarting services. The steps are idempotent and can be applied iteratively in batches to converge the system back to a 0/0 integrity state.

### Why this is required
The platform maintains two complementary data sets:
- `flight_summaries.controller_callsigns` (JSONB object keyed by controller callsign)
- `controller_summaries.aircraft_details` (JSONB array of aircraft objects)

For analytical correctness and user trust, any reference present on one side must be reciprocated by an overlapping reference on the other side. Historical data loads, schema or logic changes, deduplication of legacy summaries, or timing races during deployments can leave the datasets temporarily out of sync. This runbook remediates those inconsistencies without altering the canonical processing pipeline.

### Background and context
- The application now uses a canonical sessionization pipeline (driven by `session_selector`) to unify selection, upsert, archive, and delete operations in a single transaction, guarded by advisory transaction locks.
- Historical data (e.g., rehydrated records from `flights_archive`) and earlier logic could create duplicate `flight_summaries` or missing reciprocal links.
- The daily integrity service (see `docker-compose.yml` service `integrity`) executes read-only checks to surface mismatches, and `scripts/report_integrity.py` can be used for alerting (non-zero exit on mismatch).
- This runbook complements the daily checks by providing the corrective steps to prune invalid links and backfill missing ones.

### Definitions
- "Integrity mismatch":
  - Flight → Controller missing: flight references a controller but no overlapping controller summary references that flight.
  - Controller → Flight missing: controller summary references a flight but no overlapping flight summary references that controller.
- Overlap window: `flight_summaries.[logon_time, completion_time]` intersects `controller_summaries.[session_start_time, session_end_time]` (open-ended if end is NULL).
- All timestamps are UTC. The data model uses JSONB to store link details.

### Preconditions
- All times are UTC.
- Production is running via Docker Compose and the `postgres` service mounts `./scripts` read-only.
- You have appropriate backup/restore capability and a maintenance window if required.

### Integrity checks (counts)
Run both queries; both must be zero when finished.

```sh
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -f /scripts/flight_to_controller_integrity.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -f /scripts/controller_to_flight_integrity.sql
```

### Safe execution guidance
- Start with a 14-day window; run prune then backfill; re-check counts.
- Repeat the statements in small batches (e.g., 5k rows) until counts reach zero for the window.
- Expand the window to 30/60/90 days as needed, then remove the date filter to converge whole history.
- Always re-run integrity checks between steps; everything is transactional and idempotent.

Note: The provided scripts operate on full history. To time-box/batch, temporarily add date predicates in the CTEs when running in production, or copy the script and adjust a windowed variant for operational use.

### Repair sequence
1) Prune invalid links (controller → flight missing reciprocal flight)
```sh
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -f /scripts/prune_controller_aircraft_without_flight.sql
```

2) Prune invalid links (flight → controller missing reciprocal controller session)
```sh
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -f /scripts/prune_invalid_flight_controller_links.sql
```

3) Backfill flight side from controller sessions (ensure controllers present on flight summaries)
```sh
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -f /scripts/backfill_flight_add_missing_controllers.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -f /scripts/backfill_flight_callsigns_from_controller_summaries.sql
```

4) Backfill controller side from flights (ensure flights present on controller summaries)
```sh
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -f /scripts/backfill_controllers_from_flight_callsigns.sql
```

5) Re-check integrity counts
```sh
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -f /scripts/flight_to_controller_integrity.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -f /scripts/controller_to_flight_integrity.sql
```

6) Optional deduplication (historical clean-up)
```sh
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -f /scripts/dedupe_flight_summaries.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -f /scripts/dedupe_controller_summaries.sql
```

### Root causes typically addressed by this runbook
- Legacy duplicates in `flight_summaries` (pre-canonical keying) that were later merged.
- Backfills performed only on one side (flight or controller) without reciprocals.
- Timing windows during deployments where integrity checks ran between pipeline phases.
- Rehydration of historical data for testing or migration without corresponding reciprocal insertions.

### Safety principles
- Prune scripts only remove links proven to have no valid overlap on the other side.
- Backfill scripts only add links when a valid overlap is detected.
- All steps are ACID and can be re-run safely; prefer batching during peak hours.

### Monitoring and alerting
- Daily: `integrity` service runs both SQL checks and logs timestamps in UTC.
- On-demand: run `scripts/report_integrity.py` (exits non-zero if mismatches exist) in CI/CD or operational dashboards.

### Operational notes
- All scripts are wrapped in transactions and update `updated_at` where applicable.
- Backfill scripts only add missing links; prune scripts only remove provably invalid links.
- If concurrency is high, prefer running during low-traffic hours and in smaller batches.

### Rollback
Standard PostgreSQL point-in-time recovery (PITR) or restore from backup/snapshot.

### Appendix: Referenced scripts (verbatim)

#### scripts/flight_to_controller_integrity.sql
```sql
-- Flight -> Controller bidirectional integrity check
-- Returns flights whose controller references are not reciprocated by any overlapping controller session

WITH params AS (
  SELECT 
    TIMESTAMPTZ '2025-08-29 12:00:00+00' AS window_start,
    TIMESTAMPTZ '2025-08-30 00:00:00+00' AS window_end
),
flight_ctrl AS (
  SELECT
    fs.id AS flight_summary_id,
    fs.callsign AS flight_callsign,
    fs.logon_time,
    COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') AS completion_time,
    key AS controller_callsign
  FROM flight_summaries fs
  CROSS JOIN LATERAL jsonb_object_keys(fs.controller_callsigns) AS key
  CROSS JOIN params p
  WHERE fs.controller_callsigns IS NOT NULL
    AND fs.controller_callsigns <> '{}'::jsonb
    -- Restrict to flights overlapping the target window
    AND fs.logon_time <= p.window_end
    AND COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') >= p.window_start
)
SELECT fc.*
FROM flight_ctrl fc
WHERE NOT EXISTS (
  SELECT 1
  FROM controller_summaries cs
  WHERE cs.callsign = fc.controller_callsign
    AND cs.session_start_time <= fc.completion_time
    AND (cs.session_end_time IS NULL OR cs.session_end_time >= fc.logon_time)
    AND EXISTS (
      SELECT 1
      FROM jsonb_array_elements(cs.aircraft_details) AS d
      WHERE d->>'callsign' = fc.flight_callsign
    )
);
```

#### scripts/controller_to_flight_integrity.sql
```sql
-- Controller -> Flight bidirectional integrity check
-- Returns controller session flight references not reciprocated by any overlapping flight summary

WITH params AS (
  SELECT 
    TIMESTAMPTZ '2025-08-29 12:00:00+00' AS window_start,
    TIMESTAMPTZ '2025-08-30 00:00:00+00' AS window_end
),
ctrl_flights AS (
  SELECT
    cs.id AS controller_summary_id,
    cs.callsign AS controller_callsign,
    cs.session_start_time,
    COALESCE(cs.session_end_time, NOW() AT TIME ZONE 'UTC') AS session_end_time,
    d->>'callsign' AS flight_callsign
  FROM controller_summaries cs
  CROSS JOIN LATERAL jsonb_array_elements(cs.aircraft_details) AS d
  CROSS JOIN params p
  WHERE cs.session_start_time <= p.window_end
    AND COALESCE(cs.session_end_time, NOW() AT TIME ZONE 'UTC') >= p.window_start
)
SELECT cf.*
FROM ctrl_flights cf
LEFT JOIN flight_summaries fs
  ON fs.callsign = cf.flight_callsign
  AND fs.logon_time <= cf.session_end_time
  AND COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') >= cf.session_start_time
WHERE fs.id IS NULL
   OR fs.controller_callsigns IS NULL
   OR fs.controller_callsigns = '{}'::jsonb
   OR NOT (fs.controller_callsigns ? cf.controller_callsign);
```

#### scripts/prune_controller_aircraft_without_flight.sql
```sql
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
```

#### scripts/prune_invalid_flight_controller_links.sql
```sql
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
```

#### scripts/backfill_flight_add_missing_controllers.sql
```sql
-- Add missing controller keys to flight_summaries for overlaps present in controller_summaries

BEGIN;

WITH ctrl_flights AS (
  SELECT
    cs.callsign AS controller_callsign,
    cs.session_start_time,
    COALESCE(cs.session_end_time, NOW() AT TIME ZONE 'UTC') AS session_end_time,
    d->>'callsign' AS flight_callsign
  FROM controller_summaries cs
  CROSS JOIN LATERAL jsonb_array_elements(cs.aircraft_details) AS d
)
, cf_overlaps AS (
  SELECT DISTINCT
    fs.id AS flight_summary_id,
    cf.controller_callsign
  FROM ctrl_flights cf
  JOIN flight_summaries fs
    ON fs.callsign = cf.flight_callsign
   AND fs.logon_time <= cf.session_end_time
   AND COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') >= cf.session_start_time
)
, missing AS (
  SELECT o.flight_summary_id, o.controller_callsign
  FROM cf_overlaps o
  JOIN flight_summaries fs ON fs.id = o.flight_summary_id
  WHERE fs.controller_callsigns IS NULL
     OR fs.controller_callsigns = '{}'::jsonb
     OR NOT (fs.controller_callsigns ? o.controller_callsign)
)
UPDATE flight_summaries fs
SET controller_callsigns = COALESCE(fs.controller_callsigns, '{}'::jsonb) || jsonb_build_object(m.controller_callsign, '{}'::jsonb),
    updated_at = NOW()
FROM missing m
WHERE fs.id = m.flight_summary_id;

COMMIT;
```

#### scripts/backfill_flight_callsigns_from_controller_summaries.sql
```sql
-- Backfill flight_summaries.controller_callsigns from controller_summaries
-- Strategy: For each flight summary lacking ATC data, find overlapping controller sessions
-- that list the flight in cs.aircraft_details and aggregate controller callsigns into a JSONB object.

BEGIN;

WITH candidate AS (
  SELECT fs.id,
         fs.callsign,
         fs.logon_time,
         COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') AS completion_time
  FROM flight_summaries fs
  WHERE fs.controller_callsigns IS NULL OR fs.controller_callsigns = '{}'::jsonb
), matches AS (
  SELECT
    c.id AS flight_summary_id,
    cs.callsign AS controller_callsign
  FROM candidate c
  JOIN controller_summaries cs
    ON cs.session_start_time <= c.completion_time
   AND (cs.session_end_time IS NULL OR cs.session_end_time >= c.logon_time)
  WHERE EXISTS (
    SELECT 1
    FROM jsonb_array_elements(cs.aircraft_details) AS d
    WHERE d->>'callsign' = c.callsign
  )
), agg AS (
  SELECT flight_summary_id,
         jsonb_object_agg(controller_callsign, '{}'::jsonb) AS controller_map
  FROM matches
  GROUP BY flight_summary_id
)
UPDATE flight_summaries fs
SET controller_callsigns = COALESCE(fs.controller_callsigns, '{}'::jsonb) || a.controller_map,
    updated_at = NOW()
FROM agg a
WHERE fs.id = a.flight_summary_id;

COMMIT;
```

#### scripts/backfill_controllers_from_flight_callsigns.sql
```sql
-- Backfill controller_summaries.aircraft_details from flight_summaries.controller_callsigns
-- For each flight summary referencing a controller, ensure the overlapping controller session
-- contains that flight in its aircraft_details JSON array.

BEGIN;

WITH flight_ctrl AS (
  SELECT fs.id AS flight_summary_id,
         fs.callsign AS flight_callsign,
         fs.logon_time,
         COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') AS completion_time,
         key AS controller_callsign
  FROM flight_summaries fs
  CROSS JOIN LATERAL jsonb_object_keys(fs.controller_callsigns) AS key
  WHERE fs.controller_callsigns IS NOT NULL
    AND fs.controller_callsigns <> '{}'::jsonb
), overlap AS (
  SELECT 
    fc.flight_callsign,
    fc.controller_callsign,
    cs.id AS controller_summary_id,
    cs.aircraft_details
  FROM flight_ctrl fc
  JOIN controller_summaries cs
    ON cs.callsign = fc.controller_callsign
   AND cs.session_start_time <= fc.completion_time
   AND (cs.session_end_time IS NULL OR cs.session_end_time >= fc.logon_time)
), missing AS (
  SELECT DISTINCT 
    controller_summary_id,
    controller_callsign,
    flight_callsign
  FROM overlap o
  WHERE NOT EXISTS (
    SELECT 1
    FROM jsonb_array_elements(COALESCE(o.aircraft_details, '[]'::jsonb)) AS d
    WHERE d->>'callsign' = o.flight_callsign
  )
)
UPDATE controller_summaries cs
SET aircraft_details = COALESCE(cs.aircraft_details, '[]'::jsonb) || jsonb_build_array(jsonb_build_object('callsign', m.flight_callsign)),
    updated_at = NOW()
FROM missing m
WHERE cs.id = m.controller_summary_id;

COMMIT;
```

#### scripts/dedupe_flight_summaries.sql
```sql
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
```

#### scripts/dedupe_controller_summaries.sql
```text
File not present in this repository snapshot. If required, add the script and re-run this runbook to embed it here.
```

#### scripts/rehydrate_test_sessions.sql
```sql
-- Rehydrate ~50 archived sessions back into flights for pipeline testing
-- WARNING: Use in non-production or with caution; inserts rows into flights

BEGIN;

CREATE TEMP TABLE tmp_sessions AS
SELECT 
  callsign,
  cid,
  departure,
  arrival,
  MIN(logon_time) AS session_start,
  MAX(last_updated) AS session_end
FROM flights_archive
WHERE last_updated <= NOW() - INTERVAL '8 hours'
GROUP BY callsign, cid, departure, arrival
ORDER BY session_end DESC
LIMIT 50;

-- Optional: clean any existing rows in flights for these windows to avoid duplication
DELETE FROM flights f
USING tmp_sessions t
WHERE f.callsign = t.callsign
  AND f.cid = t.cid
  AND f.departure = t.departure
  AND f.arrival = t.arrival
  AND f.last_updated BETWEEN t.session_start AND t.session_end;

-- Insert from archive back to flights for the selected windows
INSERT INTO flights (
  callsign, aircraft_type, departure, arrival, logon_time,
  route, flight_rules, aircraft_faa, planned_altitude, aircraft_short,
  cid, name, server, pilot_rating, military_rating,
  latitude, longitude, altitude, groundspeed, heading,
  last_updated, deptime, 
  revision_id, assigned_transponder, transponder, qnh_i_hg, qnh_mb, last_updated_api
)
SELECT 
  fa.callsign, fa.aircraft_type, fa.departure, fa.arrival, fa.logon_time,
  fa.route, fa.flight_rules, fa.aircraft_faa, fa.planned_altitude, fa.aircraft_short,
  fa.cid, fa.name, fa.server, fa.pilot_rating, fa.military_rating,
  fa.latitude, fa.longitude, fa.altitude, fa.groundspeed, fa.heading,
  fa.last_updated, fa.deptime,
  NULL::integer AS revision_id, NULL::varchar(10) AS assigned_transponder, NULL::varchar(10) AS transponder,
  NULL::float AS qnh_i_hg, NULL::integer AS qnh_mb, NULL::timestamp with time zone AS last_updated_api
FROM flights_archive fa
JOIN tmp_sessions t
  ON fa.callsign = t.callsign
 AND fa.cid = t.cid
 AND fa.departure = t.departure
 AND fa.arrival = t.arrival
WHERE fa.last_updated BETWEEN t.session_start AND t.session_end;

COMMIT;
```

#### scripts/report_integrity.py
```python
#!/usr/bin/env python3
import asyncio
import sys
from sqlalchemy import text
from app.database import get_database_session

async def main():
    async with get_database_session() as session:
        q1 = text("""
        WITH flight_ctrl AS (
          SELECT fs.id AS flight_summary_id,
                 fs.callsign AS flight_callsign,
                 fs.logon_time,
                 COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') AS completion_time,
                 key AS controller_callsign
          FROM flight_summaries fs
          CROSS JOIN LATERAL jsonb_object_keys(fs.controller_callsigns) AS key
          WHERE fs.controller_callsigns IS NOT NULL
            AND fs.controller_callsigns <> '{}'::jsonb
        )
        SELECT COUNT(*) AS c FROM flight_ctrl fc WHERE NOT EXISTS (
          SELECT 1 FROM controller_summaries cs
          WHERE cs.callsign = fc.controller_callsign
            AND cs.session_start_time <= fc.completion_time
            AND (cs.session_end_time IS NULL OR cs.session_end_time >= fc.logon_time)
            AND EXISTS (
              SELECT 1 FROM jsonb_array_elements(cs.aircraft_details) AS d
              WHERE d->>'callsign' = fc.flight_callsign
            )
        );
        """)
        q2 = text("""
        WITH ctrl_flights AS (
          SELECT cs.id AS controller_summary_id,
                 cs.callsign AS controller_callsign,
                 cs.session_start_time,
                 COALESCE(cs.session_end_time, NOW() AT TIME ZONE 'UTC') AS session_end_time,
                 d->>'callsign' AS flight_callsign
          FROM controller_summaries cs
          CROSS JOIN LATERAL jsonb_array_elements(cs.aircraft_details) AS d
        )
        SELECT COUNT(*) AS c FROM ctrl_flights cf LEFT JOIN flight_summaries fs
          ON fs.callsign = cf.flight_callsign
         AND fs.logon_time <= cf.session_end_time
         AND COALESCE(fs.completion_time, NOW() AT TIME ZONE 'UTC') >= cf.session_start_time
        WHERE fs.id IS NULL
           OR fs.controller_callsigns IS NULL
           OR fs.controller_callsigns = '{}'::jsonb
           OR NOT (fs.controller_callsigns ? cf.controller_callsign);
        """)
        r1 = await session.execute(q1)
        r2 = await session.execute(q2)
        c1 = r1.scalar() or 0
        c2 = r2.scalar() or 0
        result = {"flight_to_controller_mismatches": c1, "controller_to_flight_mismatches": c2}
        print(result)
        if c1 > 0 or c2 > 0:
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```


