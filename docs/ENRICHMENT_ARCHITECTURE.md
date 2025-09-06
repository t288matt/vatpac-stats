# Enrichment Architecture (Explicit-Bounds + Durable Worker)

## Overview
The enrichment pipeline associates completed flight summaries with controller interactions and mirrors those relationships in controller summaries. This document reflects the latest changes:

- Explicit-bounds prefiltering using actual transceiver time bounds
- Fallback to local DB transceivers when the VATSIM snapshot yields none
- Durable enrichment via in-row queue columns on `flight_summaries`
- Idempotent writes that avoid overwriting non-empty `controller_callsigns` with empty results
- Expanded diagnostics and debug artifacts for targeted RCA

## Components

- `DataService` (`app/services/data_service.py`):
  - Creates/updates `flight_summaries` rows via the canonical pipeline
  - Sets `enrichment_status='pending'` transactionally at upsert time

- `SummaryEnrichmentWorker` (`app/services/summary_enrichment_worker.py`):
  - Claims pending rows using `FOR UPDATE SKIP LOCKED`, sets `in_progress`, increments attempts
  - Calls `ATCDetectionService.detect_flight_atc_interactions_with_timeout(...)`
  - Writes results to `flight_summaries` and marks `completed`
  - Guard: only updates `controller_callsigns` when new detection is non-empty OR DB field is empty
  - Records `enrichment_completed_at`, `updated_at`; preserves idempotency

- `ATCDetectionService` (`app/services/atc_detection_service.py`):
  - Loads flight transceivers; derives `flight_start_time`/`flight_end_time` from data
  - Loads ATC transceivers in the same explicit window; falls back to DB query if snapshot is empty
  - Runs controller-specific proximity and frequency matching
  - Computes time metrics (total and airborne coverage)
  - Emits debug files for targeted callsigns (e.g., `FJI917`) under `/tmp`

- `detection_common` (`app/services/detection_common.py`):
  - Explicit-bounds `build_prefilter_and_loader(flight_start_time, flight_end_time, atc_start_time, atc_end_time, ...)`
  - Fail-fast guard on old anchor-based signature

## Data Model (Durable Queue-in-Row)

`flight_summaries` includes enrichment lifecycle fields:
- `enrichment_status TEXT` — pending | in_progress | completed
- `enrichment_attempts INT` — number of attempts
- `enrichment_run_after TIMESTAMPTZ` — backoff scheduling
- `enrichment_last_error TEXT` — diagnostic message
- `enrichment_completed_at TIMESTAMPTZ` — completion timestamp

An index on `(enrichment_status, enrichment_run_after)` enables efficient claims by the worker.

## Processing Flow

1) Summary upsert (canonical): set `enrichment_status='pending'` and commit.
2) Worker claim:
   - `SELECT ... FOR UPDATE SKIP LOCKED` where `enrichment_status='pending'` and `enrichment_run_after<=now()`
   - `UPDATE ... SET enrichment_status='in_progress', enrichment_attempts=enrichment_attempts+1`
3) Detection (timeout protected):
   - Load flight and ATC transceivers using explicit bounds
   - Fallback to DB ATC transceivers if snapshot is empty
   - Run proximity/frequency matching; compute metrics
4) Write-back:
   - If new `controller_callsigns` is non-empty OR existing DB value is empty → update JSON + metrics
   - Else → mark completed without overwriting existing non-empty JSON
   - Set `enrichment_completed_at=now()` and `updated_at=now()`
5) Commit.

## Failure Handling

- Timeout or error:
  - Increment `enrichment_attempts`
  - Set `enrichment_last_error`
  - Backoff: `enrichment_run_after=now()+backoff`
  - Leave `enrichment_status='pending'` (or mark failed after max attempts if configured)

- Broken pipe/client disconnects:
  - Worker is resilient; partial DB work during detection does not affect the row
  - Guard prevents overwriting non-empty JSON with empty data on retries

## Diagnostics

- Logging: detailed INFO/DEBUG across detection and worker
- Artifacts: `/tmp/atc_debug_<callsign>.json`, `/tmp/enrich_flight_<id>_<callsign>.json`
- Integrity SQL: flight→controller and controller→flight checks use dynamic windows (last 12h)

## Rationale

- Explicit-bounds windows prevent anchor drift and missed data near edges
- Durable, visible queue state improves operability without a separate table
- Idempotent write guard protects against transient detection failures
- Fallback ATC loading mitigates snapshot gaps

## Current Status

- Deployed and verified on `feature/enrichment-queue`
- Confirmed enrichments for `FJI917` and `CES561` include `ML-GUN_CTR` with correct metrics
- Queue observed to drain to zero pending after reset and worker run
