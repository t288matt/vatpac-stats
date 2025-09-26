# Utilities

This folder contains utility scripts for database maintenance and data processing.

## Flight Completion Reset

### `reset_flight_completion_times.sql`

A utility script to reset flight summary completion times, forcing reprocessing with new logic.

**What it does:**
- Sets `completion_time = NULL` for selected flight summaries
- Resets `enrichment_status = 'pending'` 
- Updates `updated_at` timestamp
- Forces the system to reprocess these flights with new completion time logic

**Usage Examples:**

1. **Reset all flights older than 2 days:**
   ```bash
   docker-compose exec postgres psql -U vatsim_user -d vatsim_data -f utilities/reset_flight_completion_times.sql
   ```

2. **Reset specific date range:**
   ```sql
   -- Modify the WHERE clause in the script:
   WHERE created_at BETWEEN '2025-09-20' AND '2025-09-25'
   ```

3. **Reset only recent flights:**
   ```sql
   -- Modify the WHERE clause in the script:
   WHERE created_at >= CURRENT_DATE - INTERVAL '1 day'
   ```

**What happens after running:**
- The system automatically detects records with `completion_time = NULL`
- Flight summary processing runs every 60 minutes
- Enrichment worker runs every 5 seconds
- All reset records get reprocessed with new logic

**Safety Features:**
- Only affects records that were already processed (`completion_time IS NOT NULL`)
- Date filtering prevents affecting very recent data
- Reversible - you can restore completion times if needed

**When to use:**
- After fixing bugs in completion time logic
- After improving enrichment algorithms  
- When completion times are incorrect or missing
- For testing new processing logic


