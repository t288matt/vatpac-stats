## Polling Interval Decoupling: Phased Implementation Plan

### Objective
- Reduce external API calls for ATC and transceivers while keeping flight freshness unchanged.
- Replace the single `VATSIM_POLLING_INTERVAL` dependency with explicit, purpose-led intervals.

### Constraints and Current State
- VATSIM v3 `vatsim-data.json` bundles flights and controllers, so their fetch rate is inherently coupled.
- Transceivers are served from a separate endpoint and can be decoupled.
- Detection loops currently use `FLIGHT_DETECTION_TIME_WINDOW_SECONDS` as both a matching window and a run cadence.

### New Environment Variables (proposed)
- `VATSIM_TRANSCEIVERS_POLLING_INTERVAL` (seconds): cadence for background refresh of transceiver data.
- `ATC_DETECTION_RUN_INTERVAL_SECONDS`: cadence for the ATC detection scheduled loop.
- `ATC_DETECTION_TIME_WINDOW_SECONDS`: matching tolerance for ATC frequency/time proximity (decoupled from flight detection).
- Keep `VATSIM_POLLING_INTERVAL` for `vatsim-data.json` (flights + controllers) to preserve flight freshness.

---

### Phase 0 — Design confirmation (No code)
- Confirm the requirement that flight freshness stays at current interval.
- Acknowledge controllers are fetched together with flights (cannot be reduced independently in v3).
- Approve proposed variables and defaults:
  - `VATSIM_TRANSCEIVERS_POLLING_INTERVAL`: 300
  - `ATC_DETECTION_RUN_INTERVAL_SECONDS`: 180
  - `ATC_DETECTION_TIME_WINDOW_SECONDS`: 180

Acceptance criteria
- Stakeholders confirm constraints and variable set.

---

### Phase 1 — Introduce configuration knobs (No behavior change)
Steps
- Add variables in `docker-compose.yml` with comments and defaults.
- Load new variables in `app/config.py` into appropriate config sections.
- Do not wire them into logic yet.

Acceptance criteria
- App builds and boots with unchanged behavior.
- New config values are visible via a diagnostic endpoint/log but not used.

Rollback
- Remove the three variables; no code paths depend on them.

---

### Phase 2 — Decouple transceivers fetching (Behavior change: fewer calls)
Steps
- Add a background task in `vatsim_service` to refresh transceivers at `VATSIM_TRANSCEIVERS_POLLING_INTERVAL` and cache latest snapshot in memory.
- Modify `get_current_data()` to: fetch `vatsim-data.json` as before; attach the latest cached transceivers snapshot; avoid calling the transceivers endpoint on every cycle.
- Ensure timestamps from the transceiver payload are preserved for accurate timing.

Acceptance criteria
- Flight freshness unchanged; controllers still aligned with flights.
- Transceivers endpoint hit rate reduced to the configured interval (verify via logs/metrics).
- API responses and downstream processing still include transceivers.

Risks
- Stale transceivers if background task fails. Mitigate with error handling and last-success timestamps.

Rollback
- Revert to direct transceiver fetch in `get_current_data()`; disable background refresher.

---

### Phase 3 — Decouple ATC detection cadence from window (Behavior change: CPU/load)
Steps
- Introduce `ATC_DETECTION_RUN_INTERVAL_SECONDS` for the scheduled ATC detection loop in `data_service`.
- Keep `ATC_DETECTION_TIME_WINDOW_SECONDS` solely as the matching tolerance; do not use it as the run interval.
- Validate minimums (e.g., run interval >= 30s; window >= 30s).

Acceptance criteria
- ATC detection runs at new cadence while matching tolerance remains at the desired window.
- No change to flight detection cadence and window.

Rollback
- Point the ATC detection loop back to using the existing window value or prior default.

---

### Phase 4 — Accuracy safeguards for ATC time calculations
Steps
- In `atc_detection_service`, prefer real timestamp differences from transceiver records when computing minutes, falling back to `VATSIM_TRANSCEIVERS_POLLING_INTERVAL` only if needed.
- Add logging/metrics to compare derived interval vs. actual deltas.

Acceptance criteria
- Reported controller contact times remain within expected tolerance after slowing transceivers.

Rollback
- Revert to prior polling-interval-based conversion.

---

### Phase 5 — Documentation and tests
Steps
- Update `docs/CONFIGURATION.md` and `docs/ATC_DETECTION_SERVICE_IMPLEMENTATION.md` to reflect new variables and constraints.
- Add unit tests for config loading and scheduled loop interval selection.
- Add an integration test asserting reduced transceiver call rate (via log inspection) with preserved flight freshness.

Acceptance criteria
- Green tests locally and in CI.
- Docs clearly guide operators on tuning intervals.

---

### Phase 6 — Staged rollout
Steps
- Deploy with Phase 2 only; monitor API call rates and system load.
- Enable Phase 3 and 4 in a maintenance window; monitor ATC detection outputs.

Operational metrics to watch
- External call rate to `transceivers-data.json` vs. baseline.
- Processing latency for ingestion and detection loops.
- Accuracy deltas in ATC coverage metrics.

Rollback plan
- Feature-flag or revert commit to return to single-interval behavior.

---

### Summary of what changes and what stays the same
- Unchanged: `VATSIM_POLLING_INTERVAL` for flights + controllers.
- Reduced: Transceivers external calls (via background refresher).
- Tunable: ATC detection run cadence and window.


