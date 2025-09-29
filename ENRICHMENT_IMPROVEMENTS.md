# Enrichment System Improvements

## Current Enrichment System

The enrichment system processes two types of records:
1. **Flight Summaries**: Enriched with controller interaction data
2. **Controller Summaries**: Enriched with flight interaction data

### A. Flight Summary Enrichment

- Triggered when flight summaries are created by canonical processor
- Uses `ATCDetectionService` to find controller interactions
- Populates `controller_callsigns` JSONB field with interaction data
- Calculates coverage metrics like `controller_time_percentage`

### B. Controller Summary Enrichment

- Triggered when controller sessions end (after `CONTROLLER_COMPLETION_MINUTES` of inactivity)
- Uses `FlightDetectionService` to find flight interactions
- Populates `aircraft_details` JSONB field with interaction data
- Calculates metrics like `total_aircraft_handled` and `peak_aircraft_count`

## Current Issues

The current enrichment system has several inefficiencies for both flight and controller processing:

1. **Premature Processing**: Enrichment begins before all necessary data is available
2. **Excessive Retries**: Causes unnecessary database load and processing
3. **Duplicate Processing**: Multiple workers process the same data simultaneously
4. **Data Availability**: Transceiver and flight data may not be complete when enrichment starts

## Proposed Solution: Completion-Triggered Enrichment

### 1. New Enrichment Workflow

#### A. Flight Enrichment Flow

**Current Flow:**
```
Flight Summary Created → enrichment_status='pending' → Worker Claims → Process → Retry if Needed
```

**Proposed Flow:**
```
Flight Summary Created → enrichment_status='wait_for_completion' 
→ Flight Completes → enrichment_status='pending' 
→ Worker Claims → Process Once → Minimal Retries
```

#### B. Controller Enrichment Flow

**Current Flow:**
```
Controller Session Ends → Controller Summary Created with enrichment_status='pending'
→ Worker Claims → Process → Retry if Needed
```

**Proposed Flow:**
```
Controller Session Ends → Controller Summary Created with enrichment_status='pending'
→ Worker Claims → Process Once → Minimal Retries
```

**Rationale for Immediate Controller Processing:**
- Controller enrichment only needs transceiver data from when the controller was active
- All necessary data already exists when controller session is marked complete
- The system already waits 15 minutes (CONTROLLER_COMPLETION_MINUTES) of inactivity before marking a session complete
- No need for additional delay - process immediately for fastest results

### 2. Implementation Changes

#### A. Canonical Processing Changes
```python
# Current code (simplified)
async def create_or_update_flight_summary(session, flight_data):
    # Create or update summary
    await session.execute(text("""
        INSERT INTO flight_summaries (
            ... other fields ...,
            enrichment_status
        ) VALUES (
            ... other values ...,
            'pending'
        )
    """))

# Proposed change
async def create_or_update_flight_summary(session, flight_data):
    # Create or update summary
    await session.execute(text("""
        INSERT INTO flight_summaries (
            ... other fields ...,
            enrichment_status
        ) VALUES (
            ... other values ...,
            'wait_for_completion'
        )
    """))
```

#### B. New Completion Monitoring Task
```python
async def monitor_completed_flights():
    """Monitor for flights that have completion_time set but are still in wait_for_completion status."""
    while True:
        try:
            async with get_database_session() as session:
                # Find flights that have been completed but not yet queued for enrichment
                result = await session.execute(text("""
                    UPDATE flight_summaries
                    SET enrichment_status = 'pending',
                        updated_at = NOW()
                    WHERE enrichment_status = 'wait_for_completion'
                    AND completion_time IS NOT NULL
                    RETURNING id, callsign
                """))
                
                updated_flights = result.fetchall()
                if updated_flights:
                    logger.info(f"Queued {len(updated_flights)} completed flights for enrichment")
                
                await session.commit()
                
            # Check every minute
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Error in completion monitoring: {e}")
            await asyncio.sleep(60)
```

### 3. Enrichment Worker Improvements

#### A. Simplified Retry System for Both Flights and Controllers
- **Minimal Retries**: Maximum of 1 retry for both flights and controllers
- **Single Backoff Time**: Fixed 5-minute backoff for the single retry
- **Clear Error Reporting**: Detailed error messages on failure for diagnostics
- **Emphasis on First Attempt Success**: With proper completion-based triggering, first attempt should almost always succeed

#### B. Better Transaction Management
```python
async def run_once(self):
    """Process one enrichment job with improved transaction safety."""
    if not ENABLE_ENRICHMENT:
        logger.debug("Enrichment processing is disabled by configuration")
        return False
        
    # Use advisory locks to prevent race conditions
    async with get_database_session() as session:
        # Acquire advisory lock for enrichment (prevents duplicate processing)
        lock_acquired = await session.execute(text(
            "SELECT pg_try_advisory_xact_lock(:lock_key)"
        ), {"lock_key": 12345678})  # Unique lock key for enrichment
        
        if not lock_acquired.scalar():
            logger.debug("Another worker has the enrichment lock - skipping")
            return False
            
        # Claim and process in a single transaction
        # [... existing claim and process logic ...]
```

#### C. Process Optimization
- Improve detection algorithm efficiency with better indexing
- Add more precise timeout controls for expensive operations
- Use materialized views for frequently accessed data

## Benefits

1. **Reduced Database Load**: Fewer retries and more efficient processing
2. **Higher Success Rate**: Processing happens when all data is available
3. **More Reliable Results**: Fewer partial or failed enrichments
4. **Better Resource Usage**: Processing is more evenly distributed

## Redefining Failure Concepts

The current definition of "failure" is too broad and doesn't distinguish between different scenarios:

### Current Failure States:
- **Permanent Failure**: After MAX_ENRICHMENT_RETRIES attempts (currently 5), marked as `enrichment_status='failed'`
- **Temporary Failure**: Exceptions during processing, status reset to 'pending' with backoff

### Proposed Failure Classification:

#### 1. Success States (NOT Failures):
- **Completed with ATC Interactions**: Successfully processed with ATC interactions found
- **Completed with No ATC Interactions**: Successfully processed with no ATC interactions found
  - This is a NORMAL, EXPECTED outcome for many flights
  - Status should be `enrichment_status='completed'` with empty result structures
- **No Matching Data**: When no ATC data exists that matches the flight
  - This is a NORMAL, VALID outcome, NOT a failure
  - Status should be `enrichment_status='completed'` with empty result structures

#### 2. True Failures (Technical Issues Only):
- **Transient Technical Errors**: Database timeouts, locks, connection issues
  - These should be RARE
  - Remain as `enrichment_status='pending'` with backoff
  - Limited retries (2 max)

- **Permanent Technical Errors**: After maximum retries of technical issues
  - Change to `enrichment_status='technical_failure'`
  - Provide detailed error diagnostics
  - Can be reset by admin action
  
#### 3. Data Corruption (Special Case):
- **Severe Data Integrity Issues**: Corrupted records, schema violations
  - Only for truly corrupted data, not simply "no matches found"
  - Mark as `enrichment_status='data_error'` 
  - No automatic retries
  - Requires manual intervention

#### 4. New Status Flow:
```
wait_for_completion → pending → [processing] → 
  → completed (normal success path, INCLUDING "no matches found")
  → pending + backoff (RARE: only for technical errors like timeouts/locks)
  → technical_failure (VERY RARE: only after max retries of technical issues)
  → data_error (EXCEPTIONAL: only for true data corruption)
```

This classification provides:
- Clear distinction between successful empty results and actual failures
- Better diagnostics on failure types
- More targeted retry strategies based on failure category
- Clearer reporting on system health

## Implementation Progress

### Phase 1: Implement the consolidated approach (COMPLETED)

✅ **For flights**: 
- Added `wait_for_completion` state for newly created flight summaries
- Implemented automatic transition to `pending` when flight completes
- Updated API status endpoint to include `wait_for_completion` counts

✅ **For controllers**:
- Kept current immediate processing (no changes needed)
- Controllers are already complete when created

🔄 **Pending**:
- Implement simplified failure states

### Phase 2: Simplify retry mechanisms (PENDING)

#### Planned Implementation Details

1. **Reduce to single retry with fixed backoff**:
   - Modify `MAX_ENRICHMENT_RETRIES` to 1 (from current 5)
   - Replace exponential backoff with fixed 5-minute delay
   - Update SQL query that checks retry count:
   ```sql
   -- Current check
   SELECT enrichment_attempts, enrichment_status
   FROM flight_summaries  -- or controller_summaries
   WHERE id = :id
   FOR UPDATE
   
   -- Will be modified to fail permanently after just 1 retry
   ```

2. **Improve error reporting and diagnostics**:
   - Add structured error information in JSON format:
   ```python
   error_info = {
       "error_type": "database_timeout",  # or "lock_contention", etc.
       "timestamp": datetime.now(timezone.utc),
       "details": str(e),
       "retry_count": attempts + 1
   }
   
   # Store in database
   await session.execute(text("""
       UPDATE flight_summaries
       SET enrichment_error = :error_info
       WHERE id = :id
   """), {"id": summary_id, "error_info": json.dumps(error_info)})
   ```

3. **Add advisory locking to prevent duplicate processing**:
   - Implement PostgreSQL advisory locks in the worker's run_once method:
   ```python
   async def run_once(self):
       """Process one enrichment job with improved transaction safety."""
       if not ENABLE_ENRICHMENT:
           return False
           
       async with get_database_session() as session:
           # Acquire advisory lock for enrichment (prevents duplicate processing)
           lock_acquired = await session.execute(text(
               "SELECT pg_try_advisory_xact_lock(:lock_key)"
           ), {"lock_key": 12345678})  # Unique lock key for enrichment
           
           if not lock_acquired.scalar():
               logger.debug("Another worker has the enrichment lock - skipping")
               return False
               
           # Proceed with claiming and processing
           # ...
   ```

4. **Implement new failure classification**:
   - Add new status values in database schema:
   ```sql
   ALTER TYPE enrichment_status_enum ADD VALUE 'technical_failure' AFTER 'failed';
   ALTER TYPE enrichment_status_enum ADD VALUE 'data_error' AFTER 'technical_failure';
   ```
   
   - Update worker code to use these new statuses:
   ```python
   # For technical failures after max retries
   if attempts >= MAX_ENRICHMENT_RETRIES:
       await session.execute(text("""
           UPDATE flight_summaries
           SET enrichment_status = 'technical_failure',
               enrichment_error = :error_info,
               updated_at = NOW()
           WHERE id = :id
       """), {"id": summary_id, "error_info": json.dumps(error_info)})
   
   # For data corruption issues
   if is_data_corruption_error(e):
       await session.execute(text("""
           UPDATE flight_summaries
           SET enrichment_status = 'data_error',
               enrichment_error = :error_info,
               updated_at = NOW()
           WHERE id = :id
       """), {"id": summary_id, "error_info": json.dumps(error_info)})
   ```

### Phase 3: Optimize core processing logic (PENDING)

- Review and optimize SQL queries in both detection services
- Add better indexing for frequency matching
- Implement targeted timeouts on expensive operations

## Implementation Details

### Phase 1 Implementation (2025-09-29)

The following changes were made to implement completion-triggered enrichment:

1. **Modified flight summary creation**:
   ```sql
   UPDATE flight_summaries
   SET
       enrichment_status = 'wait_for_completion',  -- Changed from 'pending'
       enrichment_attempts = COALESCE(enrichment_attempts, 0),
       enrichment_run_after = NOW(),
       updated_at = NOW()
   ```

2. **Added automatic transition in canonical processor**:
   ```sql
   UPDATE flight_summaries
   SET
       -- Other fields...
       
       -- Transition from wait_for_completion to pending when flight is completed
       enrichment_status = CASE 
           WHEN enrichment_status = 'wait_for_completion' THEN 'pending'
           ELSE enrichment_status
       END,
       enrichment_run_after = CASE 
           WHEN enrichment_status = 'wait_for_completion' THEN NOW()
           ELSE enrichment_run_after
       END
   ```

3. **Updated API status endpoint**:
   ```sql
   SELECT
     (SELECT count(*) FROM flight_summaries WHERE enrichment_status='wait_for_completion') AS flight_waiting,
     -- Other counts...
   ```

## Bulk Processing Capabilities

The enrichment system is designed to handle bulk processing of hundreds of flight or controller completions:

### Current Design Strengths

1. **Robust Queue Management**:
   - Uses `FOR UPDATE SKIP LOCKED` for non-blocking row access
   - Records processed in orderly FIFO sequence
   - No database contention even with large queues

2. **Single-Threaded by Design**:
   - One worker processing one record at a time (5-second intervals)
   - Intentionally single-threaded for deterministic behavior
   - This is a design choice, not a technical limitation

3. **Database-Friendly Processing**:
   - Only locks ONE record at a time per worker
   - Locks are held briefly (30-second timeout maximum)
   - No accumulation of locks that could overwhelm the database

4. **Self-Healing Queue**:
   - Skipped records remain in pending state
   - No special requeuing logic needed
   - Worker automatically picks up available records

### Performance Characteristics

- Processing rate: ~12 records per minute (single worker)
- Large queue handling: Can process thousands of records
- No database overwhelm: Only 1 lock per worker at any time

### Bulk Processing Recommendations

For bulk reprocessing scenarios (hundreds of records):
1. Use the `ENABLE_ENRICHMENT` toggle to control processing
2. Monitor queue size and processing rate
3. No changes needed to handle bulk loads - system is designed for this

## Conclusion

By treating flight and controller enrichment as symmetric, independent processes that each wait only for their own completion, we achieve:

1. **Simplicity**: Each entity follows the same pattern
2. **Efficiency**: No unnecessary delays or dependencies
3. **Reliability**: First-attempt success rate dramatically increases
4. **Clarity**: Clear distinction between normal results and technical failures
5. **Scalability**: Graceful handling of bulk processing scenarios

This approach recognizes that the absence of matching data is not a failure state, but a normal, expected outcome in many cases. The system will only retry for true technical issues, which should be rare, and will accurately report the enrichment status.
