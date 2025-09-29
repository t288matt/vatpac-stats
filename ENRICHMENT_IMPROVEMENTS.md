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

### 4. Processing Order Improvements

Prioritize processing based on:
1. Flights with known high ATC coverage
2. Recent flights (more likely to be viewed)
3. Flights with specific equipment types or in specific regions

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

## Implementation Phases

1. **Phase 1**: Implement the consolidated approach for both entities
   - For flights: Add wait_for_completion state and transition logic
   - For controllers: Keep current immediate processing
   - Implement simplified failure states

2. **Phase 2**: Simplify retry mechanisms
   - Reduce to single retry with 5-minute backoff
   - Improve error reporting and diagnostics
   - Add advisory locking to prevent duplicate processing

3. **Phase 3**: Optimize core processing logic
   - Review and optimize SQL queries in both detection services
   - Add better indexing for frequency matching
   - Implement targeted timeouts on expensive operations

## Conclusion

By treating flight and controller enrichment as symmetric, independent processes that each wait only for their own completion, we achieve:

1. **Simplicity**: Each entity follows the same pattern
2. **Efficiency**: No unnecessary delays or dependencies
3. **Reliability**: First-attempt success rate dramatically increases
4. **Clarity**: Clear distinction between normal results and technical failures

This approach recognizes that the absence of matching data is not a failure state, but a normal, expected outcome in many cases. The system will only retry for true technical issues, which should be rare, and will accurately report the enrichment status.
