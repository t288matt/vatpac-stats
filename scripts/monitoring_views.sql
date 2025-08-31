-- Monitoring Views: 8 prioritized health metrics (PostgreSQL)
-- These views are SQL-only and read from existing tables:
-- flights, controllers, transceivers, flight_summaries, controller_summaries, flight_sector_occupancy
-- All timestamps are UTC (TIMESTAMPTZ) per schema.

-- 1) Ingestion freshness lag (global)
CREATE OR REPLACE VIEW monitoring_ingestion_freshness AS
WITH latest AS (
  SELECT
    (SELECT MAX(last_updated_api) FROM flights)  AS latest_flights_ts,
    (SELECT MAX(last_updated)     FROM controllers) AS latest_controllers_ts,
    (SELECT MAX("timestamp")      FROM transceivers) AS latest_transceivers_ts
)
SELECT
  latest.latest_flights_ts,
  latest.latest_controllers_ts,
  latest.latest_transceivers_ts,
  GREATEST(
    COALESCE(latest.latest_flights_ts,      TIMESTAMPTZ 'epoch'),
    COALESCE(latest.latest_controllers_ts,  TIMESTAMPTZ 'epoch'),
    COALESCE(latest.latest_transceivers_ts, TIMESTAMPTZ 'epoch')
  ) AS global_latest_ts,
  EXTRACT(EPOCH FROM (NOW() - GREATEST(
    COALESCE(latest.latest_flights_ts,      TIMESTAMPTZ 'epoch'),
    COALESCE(latest.latest_controllers_ts,  TIMESTAMPTZ 'epoch'),
    COALESCE(latest.latest_transceivers_ts, TIMESTAMPTZ 'epoch')
  )))::BIGINT AS global_lag_seconds
FROM latest;

-- 2) Flights freshness percentage (multi-window)
CREATE OR REPLACE VIEW monitoring_flights_freshness_pct AS
SELECT
  COUNT(*)::BIGINT                                       AS total_flights,
  COUNT(*) FILTER (WHERE last_updated_api >= NOW() - INTERVAL '2 minutes')::BIGINT AS fresh_2min,
  COUNT(*) FILTER (WHERE last_updated_api >= NOW() - INTERVAL '5 minutes')::BIGINT AS fresh_5min,
  COUNT(*) FILTER (WHERE last_updated_api >= NOW() - INTERVAL '10 minutes')::BIGINT AS fresh_10min,
  ROUND(100.0 * COUNT(*) FILTER (WHERE last_updated_api >= NOW() - INTERVAL '2 minutes') / NULLIF(COUNT(*),0), 2) AS pct_2min,
  ROUND(100.0 * COUNT(*) FILTER (WHERE last_updated_api >= NOW() - INTERVAL '5 minutes') / NULLIF(COUNT(*),0), 2) AS pct_5min,
  ROUND(100.0 * COUNT(*) FILTER (WHERE last_updated_api >= NOW() - INTERVAL '10 minutes') / NULLIF(COUNT(*),0), 2) AS pct_10min,
  MAX(last_updated_api)                                  AS most_recent_update
FROM flights;

-- 3) Controllers freshness percentage (multi-window)
CREATE OR REPLACE VIEW monitoring_controllers_freshness_pct AS
SELECT
  COUNT(*)::BIGINT                                       AS total_controllers,
  COUNT(*) FILTER (WHERE last_updated >= NOW() - INTERVAL '2 minutes')::BIGINT AS fresh_2min,
  COUNT(*) FILTER (WHERE last_updated >= NOW() - INTERVAL '5 minutes')::BIGINT AS fresh_5min,
  COUNT(*) FILTER (WHERE last_updated >= NOW() - INTERVAL '10 minutes')::BIGINT AS fresh_10min,
  ROUND(100.0 * COUNT(*) FILTER (WHERE last_updated >= NOW() - INTERVAL '2 minutes') / NULLIF(COUNT(*),0), 2) AS pct_2min,
  ROUND(100.0 * COUNT(*) FILTER (WHERE last_updated >= NOW() - INTERVAL '5 minutes') / NULLIF(COUNT(*),0), 2) AS pct_5min,
  ROUND(100.0 * COUNT(*) FILTER (WHERE last_updated >= NOW() - INTERVAL '10 minutes') / NULLIF(COUNT(*),0), 2) AS pct_10min,
  MAX(last_updated)                                      AS most_recent_update
FROM controllers;

-- 4) Flight summarization freshness
CREATE OR REPLACE VIEW monitoring_flight_summary_freshness AS
SELECT
  MAX(created_at)        AS last_summary_created_at,
  MAX(completion_time)   AS last_summary_completion_time,
  EXTRACT(EPOCH FROM (NOW() - MAX(created_at)))::BIGINT      AS age_since_last_created_seconds,
  EXTRACT(EPOCH FROM (NOW() - MAX(completion_time)))::BIGINT AS age_since_last_completion_seconds
FROM flight_summaries;

-- 5) Flight summarization backlog (multi-window, presence-based and missing-summary counts)
CREATE OR REPLACE VIEW monitoring_flight_summary_backlog AS
WITH base AS (
  SELECT id, callsign, logon_time, last_updated_api
  FROM flights
  WHERE logon_time IS NOT NULL
)
SELECT
  -- Flights still present past thresholds (presence-based indicator)
  COUNT(*) FILTER (WHERE logon_time <= NOW() - INTERVAL '4 hours')  AS flights_present_4h,
  COUNT(*) FILTER (WHERE logon_time <= NOW() - INTERVAL '8 hours')  AS flights_present_8h,
  COUNT(*) FILTER (WHERE logon_time <= NOW() - INTERVAL '12 hours') AS flights_present_12h,
  -- Flights past thresholds with no exact-match summary (callsign + logon_time)
  COUNT(*) FILTER (
    WHERE logon_time <= NOW() - INTERVAL '4 hours'
      AND NOT EXISTS (
        SELECT 1 FROM flight_summaries fs
        WHERE fs.callsign = base.callsign AND fs.logon_time = base.logon_time
      )
  ) AS unsummarized_exact_4h,
  COUNT(*) FILTER (
    WHERE logon_time <= NOW() - INTERVAL '8 hours'
      AND NOT EXISTS (
        SELECT 1 FROM flight_summaries fs
        WHERE fs.callsign = base.callsign AND fs.logon_time = base.logon_time
      )
  ) AS unsummarized_exact_8h,
  COUNT(*) FILTER (
    WHERE logon_time <= NOW() - INTERVAL '12 hours'
      AND NOT EXISTS (
        SELECT 1 FROM flight_summaries fs
        WHERE fs.callsign = base.callsign AND fs.logon_time = base.logon_time
      )
  ) AS unsummarized_exact_12h
FROM base;

-- 6) Sector cleanup health (open entries beyond thresholds)
CREATE OR REPLACE VIEW monitoring_sector_cleanup AS
SELECT
  COUNT(*)                                             AS open_total,
  COUNT(*) FILTER (WHERE NOW() - entry_timestamp > INTERVAL '5 minutes')  AS open_over_5m,
  COUNT(*) FILTER (WHERE NOW() - entry_timestamp > INTERVAL '10 minutes') AS open_over_10m,
  COALESCE(MAX(NOW() - entry_timestamp), INTERVAL '0 seconds')            AS oldest_open_age,
  EXTRACT(EPOCH FROM COALESCE(MAX(NOW() - entry_timestamp), INTERVAL '0 seconds'))::BIGINT AS oldest_open_age_seconds
FROM flight_sector_occupancy
WHERE exit_timestamp IS NULL;

-- 7) Flight↔Controller integrity mismatches (24h window)
CREATE OR REPLACE VIEW monitoring_integrity_mismatches AS
WITH params AS (
  SELECT NOW() - INTERVAL '24 hours' AS window_start,
         NOW()                       AS window_end
),
flight_ctrl AS (
  SELECT
    fs.id AS flight_summary_id,
    fs.callsign AS flight_callsign,
    fs.logon_time,
    COALESCE(fs.completion_time, NOW()) AS completion_time,
    key AS controller_callsign
  FROM flight_summaries fs
  CROSS JOIN LATERAL jsonb_object_keys(fs.controller_callsigns) AS key
  WHERE fs.controller_callsigns IS NOT NULL
    AND fs.controller_callsigns <> '{}'::jsonb
    AND fs.logon_time <= (SELECT window_end FROM params)
    AND COALESCE(fs.completion_time, NOW()) >= (SELECT window_start FROM params)
),
ctrl_flights AS (
  SELECT
    cs.id AS controller_summary_id,
    cs.callsign AS controller_callsign,
    cs.session_start_time,
    COALESCE(cs.session_end_time, NOW()) AS session_end_time,
    d->>'callsign' AS flight_callsign
  FROM controller_summaries cs
  CROSS JOIN LATERAL jsonb_array_elements(cs.aircraft_details) AS d
  WHERE cs.session_start_time <= (SELECT window_end FROM params)
    AND COALESCE(cs.session_end_time, NOW()) >= (SELECT window_start FROM params)
),
ftc_mismatches AS (
  SELECT COUNT(*) AS cnt
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
),
ctf_mismatches AS (
  SELECT COUNT(*) AS cnt
  FROM ctrl_flights cf
  LEFT JOIN flight_summaries fs
    ON fs.callsign = cf.flight_callsign
   AND fs.logon_time <= cf.session_end_time
   AND COALESCE(fs.completion_time, NOW()) >= cf.session_start_time
  WHERE fs.id IS NULL
     OR fs.controller_callsigns IS NULL
     OR fs.controller_callsigns = '{}'::jsonb
     OR NOT (fs.controller_callsigns ? cf.controller_callsign)
)
SELECT
  (SELECT cnt FROM ftc_mismatches) AS flight_to_controller_mismatch_count,
  (SELECT cnt FROM ctf_mismatches) AS controller_to_flight_mismatch_count;

-- 8) Recent ingest throughput (1m and 10m windows)
CREATE OR REPLACE VIEW monitoring_recent_ingest_throughput AS
SELECT
  -- Flights
  COUNT(*) FILTER (WHERE last_updated_api >= NOW() - INTERVAL '10 minutes')::BIGINT AS flights_last_10min,
  COUNT(*) FILTER (WHERE last_updated_api >= NOW() - INTERVAL '1 minute')::BIGINT  AS flights_last_1min,
  -- Controllers
  (SELECT COUNT(*) FROM controllers WHERE last_updated >= NOW() - INTERVAL '10 minutes')::BIGINT AS controllers_last_10min,
  (SELECT COUNT(*) FROM controllers WHERE last_updated >= NOW() - INTERVAL '1 minute')::BIGINT  AS controllers_last_1min,
  -- Transceivers
  (SELECT COUNT(*) FROM transceivers WHERE "timestamp" >= NOW() - INTERVAL '10 minutes')::BIGINT AS transceivers_last_10min,
  (SELECT COUNT(*) FROM transceivers WHERE "timestamp" >= NOW() - INTERVAL '1 minute')::BIGINT  AS transceivers_last_1min
FROM flights;


