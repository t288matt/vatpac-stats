## Sector Cleanup Backlog – Analysis and Fix Plan

### Context
- Metric `oldest_open_age_minutes` showed 24+ minutes, which is expected for long sector stays. We added better health metrics focusing on stale opens (no flight updates > 5 min).
- Stale-open checks returned: 1000 open sectors stale, oldest ≈ 262 minutes (red).

### Symptoms (UTC)
- Stale open sectors: 1000
- Oldest stale age: 262 minutes
- Manual endpoint `POST /api/cleanup/stale-sectors` closed: 0

### Root Cause
1) Cleanup is event-driven in `app/main.py` and only runs after a successful data processing cycle. If the loop exits early or errors, cleanup may not run frequently enough.
   - Code: `app/main.py` calls `data_service.cleanup_stale_sectors()` only in the success path.
2) Implementation gap in `cleanup_stale_sectors`:
   - Uses a per-callsign “latest flight row” join and compares that timestamp to a fixed stale cutoff.
   - It does not evaluate each open sector entry against the per-callsign last update relative to the entry’s `entry_timestamp`.
   - If a callsign has a new flight record (< 5 min) but old open entries from a previous session exist, those entries will never be closed.

### Immediate Mitigation (SQL-only, safe to run now)
1) Close opens for callsigns with stale last update (> 5 min), aligning exit to the last known flight update:
```
WITH latest AS (
  SELECT callsign, MAX(last_updated) AS last_updated
  FROM flights
  GROUP BY callsign
)
UPDATE flight_sector_occupancy s
SET exit_timestamp = l.last_updated,
    duration_seconds = GREATEST(EXTRACT(EPOCH FROM (l.last_updated - s.entry_timestamp))::int, 0)
FROM latest l
WHERE s.exit_timestamp IS NULL
  AND s.callsign = l.callsign
  AND l.last_updated <= NOW() - INTERVAL '300 seconds'
  AND l.last_updated > s.entry_timestamp;
```
2) Close residual opens for callsigns with no remaining flight rows:
```
UPDATE flight_sector_occupancy s
SET exit_timestamp = NOW(),
    duration_seconds = GREATEST(EXTRACT(EPOCH FROM (NOW() - s.entry_timestamp))::int, 0)
WHERE s.exit_timestamp IS NULL
  AND NOT EXISTS (SELECT 1 FROM flights f WHERE f.callsign = s.callsign);
```

### Why the Endpoint Closed 0
- `POST /api/cleanup/stale-sectors` finds latest flight per callsign and closes entries if that latest is stale. If latest is fresh but there are older open entries, they are skipped. The mitigation SQL handles this by checking each open entry against the per-callsign latest timestamp and the entry time.

### Permanent Fix (simple, low-risk)
1) In `data_service.cleanup_stale_sectors`:
   - Replace the current query with the per-entry approach used in the mitigation SQL above (use last-known flight update per callsign and compare to each `s.entry_timestamp`).
   - Also add a pass to close entries where no flight rows remain.
2) Scheduling: run cleanup on a fixed cadence (e.g., every 60s) independent of the data-processing success path, or tie it to `SECTOR_UPDATE_INTERVAL`.
   - Keep `POST /api/cleanup/stale-sectors` for manual runs.
3) Monitoring: add dashboard metric
   - `stale_open_sectors` (should be 0) and `oldest_stale_open_minutes` (should be 0).

### Acceptance Criteria
- `stale_open_sectors` = 0 within minutes after fix and remains 0.
- `oldest_stale_open_minutes` = 0.
- Manual endpoint closes > 0 when stale rows exist, otherwise 0.

### Notes
- We already fixed flight-summary selection to use the session signature and added monitoring SQL views. This document focuses on sector cleanup only.




