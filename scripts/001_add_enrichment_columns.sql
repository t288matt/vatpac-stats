-- Migration: add enrichment columns to summary tables

ALTER TABLE flight_summaries
  ADD COLUMN IF NOT EXISTS enrichment_status TEXT DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS enrichment_attempts INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS enrichment_run_after TIMESTAMPTZ DEFAULT now(),
  ADD COLUMN IF NOT EXISTS enrichment_last_error TEXT,
  ADD COLUMN IF NOT EXISTS enrichment_completed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_flight_enrichment_status_run_after ON flight_summaries (enrichment_status, enrichment_run_after);

ALTER TABLE controller_summaries
  ADD COLUMN IF NOT EXISTS enrichment_status TEXT DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS enrichment_attempts INT DEFAULT 0,
  ADD COLUMN IF NOT EXISTS enrichment_run_after TIMESTAMPTZ DEFAULT now(),
  ADD COLUMN IF NOT EXISTS enrichment_last_error TEXT,
  ADD COLUMN IF NOT EXISTS enrichment_completed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_controller_enrichment_status_run_after ON controller_summaries (enrichment_status, enrichment_run_after);


