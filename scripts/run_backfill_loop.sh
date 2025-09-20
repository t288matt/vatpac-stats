#!/bin/bash
set -euo pipefail
DB_URL="postgresql://vatsim_user:vatsim_password@localhost:5432/vatsim_data"
max_iter=200
for i in $(seq 1 $max_iter); do
  echo "--- iteration ${i} ---"
  # Recompute durations for up to 500 rows where exit exists but duration non-positive
  psql "$DB_URL" -c "WITH to_fix AS (SELECT id FROM flight_sector_occupancy WHERE exit_timestamp IS NOT NULL AND (duration_seconds IS NULL OR duration_seconds <= 0) LIMIT 500) UPDATE flight_sector_occupancy fso SET duration_seconds = EXTRACT(EPOCH FROM (exit_timestamp - entry_timestamp))::INTEGER FROM to_fix t WHERE fso.id = t.id RETURNING fso.id;" | sed -n '1,2p'

  # Run backfill pass (will try flights -> flights_archive -> flight_summaries)
  psql "$DB_URL" -f /scripts/backfill_fso_by_entry_candidate.sql

  # Check remaining counts
  remaining=$(psql "$DB_URL" -t -c "SELECT COUNT(*) FROM flight_sector_occupancy WHERE exit_timestamp IS NOT NULL AND (duration_seconds IS NULL OR duration_seconds <= 0);")
  no_exit=$(psql "$DB_URL" -t -c "SELECT COUNT(*) FROM flight_sector_occupancy WHERE exit_timestamp IS NULL;")
  remaining_count=$(echo "$remaining" | tr -d '[:space:]')
  no_exit_count=$(echo "$no_exit" | tr -d '[:space:]')
  echo "remaining_recompute=${remaining_count}, remaining_no_exit=${no_exit_count}"

  if [ "$remaining_count" = "0" ] && [ "$no_exit_count" = "0" ]; then
    echo "Backfill loop completed: no remaining recompute or open entries"
    exit 0
  fi

  sleep 1
done

echo "Reached max iterations ($max_iter); exiting"
exit 0
