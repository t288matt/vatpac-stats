# Detection Contract and Root-Cause Fix Plan

Purpose
-------
Summarise the root cause of `flight <-> controller` reciprocity mismatches and provide a low-risk, testable remediation plan that preserves the current two-service architecture while removing contract drift.

Background / Problem Summary
----------------------------
- The system implements two detection directions:
  - Flight → Controller (`ATCDetectionService`) and
  - Controller → Flight (`FlightDetectionService`).
- Mismatches occur because the two directions compute slightly different time windows, load transceiver records with different limits/policies, and use different caching and timeout fallbacks. Those asymmetries allow one side to observe an overlap the other misses.

Concrete code observations
-------------------------
- `ATCDetectionService` reads `FLIGHT_DETECTION_TIME_WINDOW_SECONDS` and `VATSIM_POLLING_INTERVAL` (see `app/services/atc_detection_service.py`).
- `FlightDetectionService` also uses `FLIGHT_DETECTION_TIME_WINDOW_SECONDS` but computes windows and performs pre-filtering differently (see `app/services/flight_detection_service.py`).
- Some record-loading paths apply a `LIMIT 10000` to avoid large queries (controller→flight fetch path), risking silent truncation under spike load.
- `VATSIMService` provides a cached transceivers snapshot via `_transceivers_cache` updated by `_transceivers_refresher_loop`. Detection code prefers the cache and falls back to on-demand only when cache is empty.
- Detection calls are wrapped with `asyncio.wait_for` timeouts (30–45s); when timeouts occur the code returns empty results and summaries are still created.

High-level design goal
----------------------
Keep the two-service architecture (scale and fault isolation) but enforce a single shared contract for detection behaviour: identical window math, identical transceiver-loading semantics, and strong cache-freshness rules. Make enrichment (heavy work) eventual so summary creation is not blocked or made inconsistent by transient failures.

Recommended changes (ordered, with rationale)
--------------------------------------------
1) Introduce a single, minimal helper module `app/services/detection_common.py` (VERY LOW RISK)
   - Expose deterministic functions used by both services:
     - `compute_detection_window(reference_time, time_window_seconds, polling_interval_seconds) -> (start, end)`
     - `compute_prefilter_windows(reference_time, time_window_seconds) -> dict` (flight/atc start/end values used by SQL)
     - `transceiver_load_strategy(window_start, window_end, last_cache_fetch) -> {force_on_demand, page_size}`
   - Replace ad-hoc window calculations in `ATCDetectionService` and `FlightDetectionService` with calls to these functions.
   - Add unit tests that assert identical windows for the same input.

Rationale: small, reviewable change that removes window-drift at source.

2) Make transceiver loading deterministic (LOW→MEDIUM RISK)
   - Remove hard-coded `LIMIT` usage and use either server-side cursors or deterministic pagination with a configurable `TRANSCEIVERS_LOAD_PAGE_SIZE`.
   - Keep a safety cap for single-run memory but ensure both services use the same pre-filter queries and paging parameters.

Rationale: prevents silent truncation of records during spikes.

3) Harden `VATSIMService` cache policy (LOW RISK)
   - Add `TRANSCEIVERS_CACHE_TTL_SECONDS` (default 120s). If a detection window overlaps data newer than `(_transceivers_last_fetch - TTL)`, force an on-demand fetch or merge on-demand results with the cache before linking.
   - Log cache age and when forced refreshes occur.

Rationale: cached snapshots speed normal work but must not mask recent controller activity.

4) Make enrichment eventual (MEDIUM RISK, HIGH BENEFIT)
   - During canonical summary processing (`DataService._process_completed_flights_canonical`) create minimal summary rows and enqueue enrichment work to a lightweight `summary_enrichment_queue` table instead of calling heavy detection inline.
   - Implement a worker (`app/services/summary_enrichment_worker.py`) which pulls N jobs, runs `ATCDetectionService.detect_flight_atc_interactions_with_timeout(...)`, and writes results back to `flight_summaries.controller_callsigns` with retries and exponential backoff.

Rationale: removes timeouts and transient failures as a source of non-reciprocity and keeps summary creation fast.

5) Observability & tests (LOW RISK)
   - Add logs that include the detection windows and number of transceiver rows loaded per detection call.
   - Add tests:
     - Unit tests for `detection_common` covering boundary cases.
     - Integration test that inserts deterministic flight/controller/transceiver records and asserts the two detection directions report the same mappings.
   - Add metrics and dashboard panels: `enrichment_queue_depth`, `hourly_mismatch_count`, `avg_detection_latency`, `transceivers_loaded_per_window`.

Rollout plan (safe, incremental)
--------------------------------
1. Implement `detection_common.py` and update both `ATCDetectionService` and `FlightDetectionService` to use it; add unit tests. Deploy to staging and run existing integrity scripts. (Low risk)
2. Implement deterministic transceiver loading (server-side cursor or pagination). Validate against integration tests. (Medium risk)
3. Add cache TTL policy and logging. Deploy to staging. (Low risk)
4. Implement enrichment queue and worker; change canonical pipeline to enqueue (feature flag). Deploy to staging and monitor. (Medium risk)
5. Remove feature flag and decommission inline enrichment once stable. (Low risk)

Files to change (initial PRs)
---------------------------
- `app/services/detection_common.py` (new)
- `app/services/atc_detection_service.py` (use helper)
- `app/services/flight_detection_service.py` (use helper)
- `app/services/vatsim_service.py` (cache TTL logic)
- `app/services/data_service.py` (switch enrichment to enqueue) — feature-flagged
- `tests/unit/...` and `tests/integration/...` (new tests)

Detection contract: function semantics
-------------------------------------
- `compute_detection_window(reference_time, time_window_seconds, polling_interval_seconds)` must:
  - Return UTC datetimes truncated to seconds.
  - Define `start = reference_time - time_window_seconds` and `end = reference_time + time_window_seconds + polling_interval_seconds`.
  - Document inclusive conditions (`timestamp >= start AND timestamp <= end`) used by queries.

Why not merge the services
--------------------------
- Merging would remove contract drift but increases blast radius and removes ability to scale/operate independent workloads (lightweight transceiver linking vs heavy enrichment). A small shared contract + queue provides the correctness of a single code path without those operational disadvantages.

Next step (I propose)
---------------------
I will implement step 1 (create `app/services/detection_common.py`, update both detection services to use it, and add unit tests) in a small PR. This is low-risk and will immediately eliminate the most common root cause (window drift). Confirm and I'll start.


Enrichment completion (how we know enrichment is done)
-----------------------------------------------------
- Canonical signal: the summary row's `enrichment_status` becomes `completed`.
  - Worker writes enrichment results (e.g. `controller_callsigns` / `aircraft_details`) and sets `enrichment_status='completed'` in a single DB transaction. A committed transaction == canonical completion.
- Secondary signals:
  - `enrichment_completed_at` timestamp (set at completion).
  - `enrichment_attempts`, `enrichment_last_error` for history/diagnostics.
  - Monitoring metrics: `enrichment_queue_depth`, `avg_enrichment_latency`, `enrichment_failures`.
- Integrity checks: the periodic flight↔controller integrity SQL will show mismatches dropping to zero once enrichment completes successfully.

Symmetric enrichment (flight + controller) and no-new-table option
-----------------------------------------------------------------
We recommend symmetrical behaviour for both `flight_summaries` and `controller_summaries`. You can implement durable enrichment without adding a separate queue table by using per-summary enrichment columns:

- On both summary tables add these columns:
  - `enrichment_status TEXT DEFAULT 'pending'`
  - `enrichment_attempts INT DEFAULT 0`
  - `enrichment_run_after TIMESTAMPTZ DEFAULT now()`
  - `enrichment_last_error TEXT NULL`
  - `enrichment_completed_at TIMESTAMPTZ NULL`

- Transactional enqueue pattern (no new table):
  - During summary upsert, in the same DB transaction set `enrichment_status='pending'` and commit. That atomically "enqueues" the work with the summary.
  - Worker claims pending summaries using `SELECT ... FOR UPDATE SKIP LOCKED` and updates the row to `in_progress` before running enrichment.
  - On success, worker writes enrichment fields and sets `enrichment_status='completed'` and `enrichment_completed_at=now()` in one UPDATE and commits.
  - On failure worker sets `enrichment_attempts=attempts+1`, `enrichment_run_after=now()+backoff`, and records `enrichment_last_error`.

This avoids an extra table and keeps the queue durable and visible. If you need richer job metadata later (dead-letter history, job priorities), you can migrate to a separate `summary_enrichment_queue` table.

Worker claim example (summary-table approach)
--------------------------------------------
1. Claim: `SELECT id FROM flight_summaries WHERE enrichment_status='pending' AND enrichment_run_after <= now() LIMIT 1 FOR UPDATE SKIP LOCKED` inside a TX.
2. `UPDATE flight_summaries SET enrichment_status='in_progress', enrichment_attempts = enrichment_attempts + 1 WHERE id = :id` and COMMIT the claim.
3. Run enrichment logic (use `detection_common`, ensure cache freshness or force on-demand fetch).
4. On success: `UPDATE flight_summaries SET controller_callsigns = :jsonb, enrichment_status='completed', enrichment_completed_at = now() WHERE id = :id` (idempotent guard optional).
5. On failure: set `enrichment_run_after = now() + backoff`, `enrichment_last_error = :err`, and either leave `enrichment_status='pending'` or set `failed` after max attempts.

Observability & monitoring
---------------------------
- Track these metrics and alert thresholds before rollout:
  - `enrichment_queue_depth` (count rows where enrichment_status != 'completed' and run_after <= now())
  - `avg_enrichment_latency` (time between enqueue and enrichment_completed_at)
  - `enrichment_failures` (attempts > 0 per minute)
  - `hourly_mismatch_count` (via integrity SQL)
- Logs: worker logs must include callsign, summary id, window start/end, transceivers rows loaded, duration, and status (success/failure).
- Admin tooling: SQL or API endpoints to list pending/failed enrichments, force-run, and requeue selected summaries.

Migration SQL (summary-table approach)
-------------------------------------
Run these DDL statements to add the fields (example for flights; do same for controllers):

```sql
ALTER TABLE flight_summaries
  ADD COLUMN IF NOT EXISTS enrichment_status TEXT DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS enrichment_attempts INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS enrichment_run_after TIMESTAMPTZ DEFAULT now(),
  ADD COLUMN IF NOT EXISTS enrichment_last_error TEXT,
  ADD COLUMN IF NOT EXISTS enrichment_completed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_flight_enrichment_status_run_after ON flight_summaries (enrichment_status, enrichment_run_after);
```

Run equivalent on `controller_summaries` for symmetry.

Runbook snippets (admin quick actions)
-------------------------------------
- View pending enrichments:
  - `SELECT id, callsign, enrichment_attempts, enrichment_run_after FROM flight_summaries WHERE enrichment_status != 'completed' ORDER BY enrichment_run_after LIMIT 100;`
- Force requeue a failed summary:
  - `UPDATE flight_summaries SET enrichment_status='pending', enrichment_run_after = now(), enrichment_last_error = NULL WHERE id = :id;`
- Manually run enrichment for one summary (for debugging):
  - Use `docker compose exec -T postgres psql -U vatsim_user -d vatsim_data -c "<SELECT row and run local worker code>"` or call internal API endpoint if exposed.

Next steps (practical)
----------------------
1. Implement `detection_common.py` and unit tests (window math + prefilter values). (I can do this now.)
2. Add the enrichment columns to both summary tables (migration SQL above) and modify `DataService` to set `enrichment_status='pending'` transactionally during upsert. Deploy to staging. (I can prepare the patch + migration.)
3. Implement a simple single-threaded worker that claims pending rows and performs enrichment, with backoff and logging. Run in staging, observe metrics and integrity checks. (I can implement.)
4. Remove inline enrichment calls once worker is validated and archive gating is changed to `enrichment_status='completed'`.

If you want, I'll implement step 1 (shared helper + tests) and step 2 (migration + transactional enqueue) next. Which do you want me to start with?


