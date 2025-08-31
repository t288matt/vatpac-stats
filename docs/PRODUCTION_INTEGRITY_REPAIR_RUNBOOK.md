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


