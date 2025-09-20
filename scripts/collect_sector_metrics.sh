#!/bin/sh
# Collect sector metrics every minute for 24 hours and append to /logs/sector_metrics.csv
# Run inside postgres container; /logs is mounted to host logs directory.

DB_URL="postgresql://vatsim_user:vatsim_password@localhost:5432/vatsim_data"
OUT_FILE="/logs/sector_metrics.csv"
INTERVAL=60
DURATION_SECONDS=86400  # 24 hours

# Create header if file doesn't exist
if [ ! -f "$OUT_FILE" ]; then
  echo "timestamp,total_rows,with_exit,without_exit,positive_count,zero_count,negative_count,avg_positive_seconds" > "$OUT_FILE"
fi

start_ts=$(date +%s)
end_ts=$((start_ts + DURATION_SECONDS))

while [ $(date +%s) -lt $end_ts ]; do
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  total_rows=$(psql "$DB_URL" -t -A -c "SELECT COUNT(*) FROM flight_sector_occupancy;")
  with_exit=$(psql "$DB_URL" -t -A -c "SELECT COUNT(*) FROM flight_sector_occupancy WHERE exit_timestamp IS NOT NULL;")
  without_exit=$(psql "$DB_URL" -t -A -c "SELECT COUNT(*) FROM flight_sector_occupancy WHERE exit_timestamp IS NULL;")
  positive_count=$(psql "$DB_URL" -t -A -c "SELECT COUNT(*) FROM flight_sector_occupancy WHERE duration_seconds > 0;")
  zero_count=$(psql "$DB_URL" -t -A -c "SELECT COUNT(*) FROM flight_sector_occupancy WHERE duration_seconds = 0;")
  negative_count=$(psql "$DB_URL" -t -A -c "SELECT COUNT(*) FROM flight_sector_occupancy WHERE duration_seconds < 0;")
  avg_positive_seconds=$(psql "$DB_URL" -t -A -c "SELECT COALESCE(ROUND(AVG(duration_seconds) FILTER (WHERE duration_seconds > 0),2),0) FROM flight_sector_occupancy;")

  # Trim whitespace
  total_rows=$(echo "$total_rows" | tr -d '[:space:]')
  with_exit=$(echo "$with_exit" | tr -d '[:space:]')
  without_exit=$(echo "$without_exit" | tr -d '[:space:]')
  positive_count=$(echo "$positive_count" | tr -d '[:space:]')
  zero_count=$(echo "$zero_count" | tr -d '[:space:]')
  negative_count=$(echo "$negative_count" | tr -d '[:space:]')
  avg_positive_seconds=$(echo "$avg_positive_seconds" | tr -d '[:space:]')

  echo "$ts,$total_rows,$with_exit,$without_exit,$positive_count,$zero_count,$negative_count,$avg_positive_seconds" >> "$OUT_FILE"

  sleep $INTERVAL
done

echo "Completed metrics collection to $OUT_FILE"
