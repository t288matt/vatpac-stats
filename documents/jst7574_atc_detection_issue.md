Title: Flight-side ATC Detection Mismatch (JST7574) — Root Cause & Proposal

Summary
-------
We observed asymmetric detection: `controller_summaries` (controller-side) shows `SY_GND` contacted `JST7574` during 2025-09-07 03:53–04:26 on 121.7 MHz, but `flight_summaries` for `JST7574` (id=5754) has an empty `controller_callsigns` JSONB.

Evidence
--------
- Controller record: `controller_summaries.id=661 (SY_GND)`
  - session_start: 2025-09-07 03:12:29
  - session_end:   2025-09-07 04:40:45
  - `aircraft_details` contains an entry for `JST7574` with first_seen ~2025-09-07T03:53:19 and last_seen ~2025-09-07T04:26:25 on frequency 121.7 MHz.
- Controller transceiver rows exist for `SY_GND` in the session window.
- Flight transceiver rows exist for `JST7574` in the same window (23 rows between 03:53:19 and 04:26:25). Example IDs: 795644 .. 797986.
- `flight_summaries.id=5754` shows: departure=YSSY, arrival=YBHM, logon_time=2025-09-07 02:10:22, controller_callsigns = {}.
- `flights` table rows for `JST7574` (recent entries) differ: e.g., some have arrival=PHNL and logon_time=2025-09-06 05:00:48; no `flights` row matches (YSSY,YBHM,2025-09-07 02:10:22).
- Exact vs windowed transceiver queries:
  - Windowed (03:00–05:00) returned 39 `transceivers` rows for JST7574.
  - Exact-flight query (requires `flights` match) returned 0 rows.
- Statistics: In last 24 hours, exact-flight lookup succeeds ~4.44% (19/428) of flight_summaries.

Root Cause
----------
The flight-side ATC detection requires an exact matching `flights` row (callsign + departure + arrival + exact logon_time) before selecting flight transceivers. For `JST7574` there is no `flights` row that matches those fields (arrival differs and logon_time differs), so `_get_flight_transceivers` returns zero rows. The controller-side detection is implemented as a windowed scan (select all flight transceivers between controller session start/end) and therefore finds JST7574 transceivers directly. This design asymmetry causes the controller to list the flight while the flight-side summary never records the controller.

Why the exact check exists (intent)
----------------------------------
- To disambiguate callsigns (same callsign reused across days or flights) and map transceivers to a specific flight record.
- To reduce scanning of transceiver rows for performance.
- To provide deterministic binding between `flights` rows and transceiver sets.

Why it fails in practice
------------------------
- Real-world discrepancies: small differences in stored logon_time, departure/arrival canonicalization, or timing of inserts cause the exact EXISTS predicate to fail.
- Race conditions: transceivers may exist but the `flights` table row was not inserted/updated yet, or the flight_summary used different computed departure/arrival.
- Data/archival differences: the `flights` row used for matching may have been archived or not present in the active table.

Impact
------
- Controller-side reports are more complete (windowed scan), but flight summaries miss controller assignments.
- Inconsistent user-facing data (controllers listed in controllers UI but not in flight summaries).

Proposed Fix (safe incremental approach)
---------------------------------------
Goal: preserve precision when possible, but fall back to a robust windowed scan when necessary.

1) Implementation plan (ATCDetectionService._get_flight_transceivers)
   - Keep the current exact-flight query as the primary path.
   - If the exact query returns zero rows, run a fallback windowed query using the `flight_summaries` logon_time/completion_time ± `FALLBACK_MARGIN` (configurable, default 300s).
   - Limit fallback rows (e.g., LIMIT 10000; keep existing safeguards).
   - If multiple candidate flights or ambiguous matches exist, pick the candidate with the largest overlap of transceiver timestamps with flight_summary times (or highest median proximity), else leave blank and emit a diagnostic.
   - Log which path was used and counts (exact vs fallback) with flight id/callsign and basic metrics.

   Example fallback SQL (simplified):

   SELECT t.callsign, t.frequency, t.timestamp, t.position_lat, t.position_lon
   FROM transceivers t
   WHERE t.entity_type = 'flight'
     AND t.callsign = :flight_callsign
     AND t.timestamp BETWEEN (:logon_time - INTERVAL '5 minutes') AND (:completion_time + INTERVAL '5 minutes')
   ORDER BY t.timestamp
   LIMIT :max_rows;

2) Logging & monitoring
   - Add structured logs indicating path used: exact-match / fallback-window / no-data.
   - Add a metric counting fallback usage rate; alert if above threshold (e.g., >10%).

3) Minor code hygiene
   - Avoid double JSON encoding before inserting controller_callsigns into JSONB: pass native dict/JSON to the DB driver.

4) Tests
   - Unit/integration tests reproducing the JST7574 case: create transceivers, flights rows that don’t match exact fields, ensure fallback finds transceivers and detection returns controllers.

Why this is safe
----------------
- Keeps fast, precise path for majority of cases where exact match works.
- Fallback only runs when exact match fails, limiting performance/regression risk.
- Configurable margins and limits prevent runaway queries and false positives.

Alternative (bigger) option
---------------------------
- Replace exact-check with always-windowed detection but implement robust scoring/assignment logic to map transceivers to specific flight rows. This is more work and riskier (may increase false-positives and DB load), but yields consistent behavior.

Example timeline to deliver
---------------------------
- 0.5 day: implement fallback and logging; add config options and basic unit tests.
- 0.25 day: run integration test for JST7574 locally and confirm flight_summary gets controllers when re-run.
- 0.25 day: add metrics and a short-run monitoring job to measure fallback frequency.

Next steps (pick one)
---------------------
- I can implement the fallback + logging changes now and run the JST7574 case. (Will edit `app - Copy/services/atc_detection_service.py` and run tests/diagnostics.)
- Or I can produce the exact diff/PR for you to review and apply.

Appendix: SQL I ran during diagnosis
-----------------------------------
- Windowed transceivers for JST7574 between 03:00 and 05:00: many rows found (IDs listed).
- Exact-flight transceiver query (EXISTS join on flights with departure/arrival/logon_time from flight_summaries.id=5754): zero rows.
- Controller_summaries.id=661 `aircraft_details` contains JST7574 first_seen/last_seen timestamps overlapping flight_summary completion_time.
- Last 24h stats: exact-match success rate ≈ 4.44% (19/428).

