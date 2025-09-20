# Airborne controller time percentage — bug report

Date: 2025-09-20 (UTC)

## Summary

The `airborne_controller_time_percentage` field in `flight_summaries` is incorrectly 0 for all recent summaries. The root cause is a defect in the ATC detection metrics calculation where the flight `completion_time` is not supplied to the function that computes the airborne denominator. As a result the enroute record count is computed over a zero-length interval and the computed percentage is forced to 0.

## Root cause (plain English)

- The enrichment worker calls ATC detection which loads flight transceivers and determines the flight `completion_time`.
- The function that calculates the airborne percentage (`_calculate_atc_metrics`) does not receive the `completion_time` value and therefore uses a fallback that ends up using `flight_end = logon_time` for the COUNT of airborne transceiver records.
- The COUNT over a zero-length interval returns 0 -> denominator = 0 -> code sets `airborne_controller_time_percentage = 0.0` for every flight.

## Key code locations

- Caller (computes completion_time but does not pass it):
  - `app/services/atc_detection_service.py` — `_detect_flight_atc_interactions_internal` (loads flight transceivers and determines flight start/end)

- Faulty calculation (uses undefined `completion_time` fallback):
  - `app/services/atc_detection_service.py` — `_calculate_atc_metrics`

Relevant excerpt from `_calculate_atc_metrics` (where the enroute count is computed):

```python
async with get_database_session() as session:
    enroute_count_res = await session.execute(text("""
        SELECT COUNT(*) FROM transceivers t
        WHERE t.entity_type = 'flight'
          AND t.callsign = :callsign
          AND t.timestamp >= :flight_start
          AND t.timestamp <= :flight_end
          AND t.height_msl IS NOT NULL
          AND t.height_msl > :alt_m
    """), {
        "callsign": flight_callsign,
        "flight_start": logon_time,
        "flight_end": completion_time if 'completion_time' in locals() else logon_time,
        "alt_m": AIRBORNE_ALT_M
    })
```

Note: `completion_time` is referenced but never provided to `_calculate_atc_metrics`.

## Evidence (DB queries executed)

1) Minutes-weighted average query (periods yesterday, 7d, 30d, 90d) — returned:

```
 period    | avg_airborne_atc_percentage
-----------+-----------------------------
 yesterday | 0.00
 last_7_days | 0.00
 last_30_days | 0.00
 last_90_days | 0.00
```

2) Diagnostics counts for summaries (last 90 days):

```
 total_summaries | airborne_null | airborne_zero | zero_minutes
 --------------: | ------------: | ------------: | ----------:
           1103  |            0  |         1103  |         38
```

3) Basic distribution of `airborne_controller_time_percentage` (last 90 days):

```
 median_pct | min_pct | max_pct
 ----------:| -------:| -------:
         0  |   0.00  |   0.00
```

These DB results show that every summary that has a stored airborne value is 0.

## Why the bug explains your symptom

- The code computes the airborne denominator (number of enroute transceiver records above 1500 ft) using `flight_start = logon_time` and `flight_end = completion_time if 'completion_time' in locals() else logon_time`.
- Because `completion_time` is not in the local scope of `_calculate_atc_metrics`, `flight_end` becomes equal to `flight_start` (logon_time) and the COUNT returns 0.
- The code then sets `airborne_controller_time_percentage` to `0.0` when denominator <= 0.

## Recommended fix (high-level)

- Ensure `_calculate_atc_metrics` receives the flight `completion_time` (or computes it itself) so the enroute COUNT uses the full flight window.
- Two minimal options:
  1. Modify the call site in `_detect_flight_atc_interactions_internal` to pass `completion_time` into `_calculate_atc_metrics`, and update `_calculate_atc_metrics` signature to accept `completion_time`.
  2. Inside `_calculate_atc_metrics`, call `_get_flight_completion_time(...)` to retrieve the correct completion time before performing the enroute COUNT.

- After applying the fix, re-run enrichment for affected summaries (all summaries since Aug 28 per prior plan or the set you choose) and validate results.

## Files to change

- `app/services/atc_detection_service.py` — update `_calculate_atc_metrics` signature or add a completion_time retrieval; update call site in `_detect_flight_atc_interactions_internal` where `_calculate_atc_metrics` is invoked.

## Suggested PR blurb

"Fix airborne percentage calculation by using actual flight completion_time when computing enroute transceiver counts; previously completion_time was missing so denominator became zero and the field was set to 0 for all flights. Re-run enrichment to repopulate historical values."

## Next steps (suggested, not performed)

- Implement the minimal code change to pass/obtain `completion_time` in `_calculate_atc_metrics`.
- Re-run enrichment (worker will naturally reprocess rows with NULL or run a targeted reset-and-requeue for Aug 28+ rows as previously planned).
- Run the minutes-weighted average query again and sample a few flight summaries to confirm values ~14% as expected.


---

Report generated from live code inspection and DB diagnostics run on 2025-09-20.
