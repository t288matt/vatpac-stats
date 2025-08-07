# Flight Status System Documentation

## Overview

The flight status system manages the lifecycle of flights in the VATSIM data collection system. It determines and tracks the current state of each flight from creation to completion.

## Status Values

### Valid Status Values

| Status | Description | Trigger | Database Constraint |
|--------|-------------|---------|-------------------|
| `'active'` | Currently flying | Updated in last API call | ✅ Required |
| `'stale'` | Recently seen but not in latest update | Not updated in last 2.5× API polling interval | ✅ Required |
| `'completed'` | Flight finished | Automatic cleanup (1 hour) | ✅ Required |
| `'cancelled'` | Flight cancelled | Manual/API update | ✅ Required |
| `'unknown'` | Status unclear | Fallback/error state | ✅ Required |

### Database Constraints

```sql
-- Check constraint ensures only valid status values
ALTER TABLE flights ADD CONSTRAINT check_flight_status 
CHECK (status IN ('active', 'stale', 'completed', 'cancelled', 'unknown'));

-- Default value for new flights
ALTER TABLE flights ALTER COLUMN status SET DEFAULT 'active';

-- Index for performance
CREATE INDEX idx_flights_status ON flights(status);
```

## Status Determination Logic

### 1. New Flight Creation

**Location:** `app/services/data_service.py` - `_process_flights_in_memory()`

```python
# Create flight record
flight_record = {
    'callsign': callsign,
    # ... other fields ...
    'status': 'active'  # Always starts as active
}
```

**Logic:**
- All new flights start with status `'active'`
- This happens when flight data is first received from VATSIM API
- No validation needed - this is the default state

### 2. Automatic Status Transitions (Cleanup Process)

**Location:** `app/services/data_service.py` - `_cleanup_old_data()`

```python
async def _cleanup_old_data(self):
    """Clean up old data to prevent database bloat"""
    try:
        db = SessionLocal()
        try:
            # Mark old flights as completed (older than 1 hour)
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
            old_flights = db.query(Flight).filter(
                and_(
                    Flight.last_updated < cutoff_time,
                    Flight.status == 'active'
                )
            ).all()
            
            for flight in old_flights:
                # Mark as completed instead of deleting
                flight.status = 'completed'
                # Store flight summary for analytics
                await self._store_flight_summary(flight)
```

**Cleanup Process Logic:**
- **Trigger:** Automatic cleanup runs every hour (`VATSIM_CLEANUP_INTERVAL: 3600`)
- **Purpose:** Prevents database bloat by marking old flights as completed
- **Condition:** Flights older than 1 hour with status `'active'`
- **Action:** Change status to `'completed'` and store flight summary
- **Preservation:** Flight data is kept, not deleted
- **Frequency:** Runs automatically every hour in the background

### 3. Manual Status Updates

**Current Implementation:**
- Manual status updates are not currently implemented
- Would require API endpoints for status management
- Could be triggered by VATSIM API events or user actions

**Proposed Implementation:**
```python
# Future API endpoint for manual status updates
@app.put("/api/flights/{callsign}/status")
async def update_flight_status(callsign: str, status: str):
    # Validate status value
    if status not in ['active', 'completed', 'cancelled', 'unknown']:
        raise HTTPException(400, "Invalid status value")
    
    # Update flight status
    db = SessionLocal()
    flight = db.query(Flight).filter(Flight.callsign == callsign).first()
    if flight:
        flight.status = status
        db.commit()
```

## Status Lifecycle

### Normal Flow
```
VATSIM API → New Flight → 'active' → (2.5× polling interval) → 'stale' → (1 hour) → 'completed'
```

### Manual Override Flow
```
'active' → 'cancelled' (manual)
'active' → 'unknown' (error state)
'active' → 'stale' (automatic - no recent updates)
'stale' → 'active' (automatic - received update)
```

### Error Recovery
```
'unknown' → 'active' (if flight reappears)
'unknown' → 'completed' (if cleanup runs)
'stale' → 'active' (if flight gets update)
'stale' → 'completed' (if cleanup runs)
```

## Data Integrity

### Constraints
1. **Check Constraint:** Only valid status values allowed
2. **Default Value:** New flights always start as `'active'`
3. **Index:** Fast queries by status
4. **Foreign Keys:** Maintain referential integrity

### Validation
```python
# Status validation in application code
VALID_STATUSES = ['active', 'stale', 'completed', 'cancelled', 'unknown']

def validate_flight_status(status: str) -> bool:
    return status in VALID_STATUSES
```

## Performance Considerations

### Indexes
- **Primary Index:** `idx_flights_status` for status queries
- **Composite Index:** `idx_flights_status_last_updated` for cleanup queries
- **Query Optimization:** Status-based filtering is fast

### Cleanup Performance
- **Batch Processing:** Updates multiple flights in single transaction
- **Time-based Filtering:** Uses indexed `last_updated` field
- **Summary Storage:** Preserves data without keeping all records

## Monitoring and Analytics

### Status Distribution Queries
```sql
-- Current status distribution
SELECT status, COUNT(*) as count 
FROM flights 
GROUP BY status;

-- Status transitions over time
SELECT 
    DATE(created_at) as date,
    status,
    COUNT(*) as count
FROM flights 
GROUP BY DATE(created_at), status
ORDER BY date DESC;
```

### Health Metrics
- **Active Flights:** Count of `status = 'active'`
- **Completion Rate:** Flights transitioning to `'completed'`
- **Error Rate:** Flights with `status = 'unknown'`
- **Cleanup Performance:** Time taken for status transitions

## Troubleshooting

### Common Issues

1. **Invalid Status Values**
   ```sql
   -- Check for invalid status values
SELECT DISTINCT status FROM flights 
WHERE status NOT IN ('active', 'stale', 'completed', 'cancelled', 'unknown');
   ```

2. **Stuck Flights**
   ```sql
   -- Find flights that should be completed but aren't
   SELECT callsign, last_updated, status 
   FROM flights 
   WHERE last_updated < NOW() - INTERVAL '2 hours' 
   AND status = 'active';
   ```

3. **Cleanup Not Running**
   ```bash
   # Check cleanup logs
   docker-compose logs app | grep "cleanup"
   ```

### Recovery Procedures

1. **Manual Status Correction**
   ```sql
   -- Fix stuck flights
   UPDATE flights 
   SET status = 'completed' 
   WHERE last_updated < NOW() - INTERVAL '2 hours' 
   AND status = 'active';
   ```

2. **Reset Unknown Status**
   ```sql
   -- Reset unknown status to active if flight is recent
   UPDATE flights 
   SET status = 'active' 
   WHERE status = 'unknown' 
   AND last_updated > NOW() - INTERVAL '30 minutes';
   ```

## Stale Status Management

### Stale Detection
- **Timeout Calculation:** `STALE_FLIGHT_TIMEOUT_MULTIPLIER × VATSIM_POLLING_INTERVAL`
- **Default Behavior:** 2.5 × 10 seconds = 25 seconds
- **Automatic Transition:** Active flights become stale if not updated within timeout
- **Database Update:** Status changed from 'active' to 'stale'

### Stale Recovery
- **Automatic Recovery:** Stale flights return to 'active' if they receive an update
- **Recovery Window:** Stale flights can recover within the 1-hour cleanup window
- **No Data Loss:** Flight data preserved during stale period
- **Dashboard Visibility:** Stale flights remain visible in dashboard with status field

### Configuration
- **Configurable Timeout:** `STALE_FLIGHT_TIMEOUT_MULTIPLIER` environment variable
- **Default Value:** 2.5 (2.5 times the API polling interval)
- **Recommended Range:** 2.0 to 3.0 for optimal performance
- **Dynamic Adjustment:** Can be changed without restart

## Future Enhancements

### Planned Features
1. **API Status Management:** Endpoints for manual status updates
2. **Event-driven Status:** Real-time status changes based on VATSIM events
3. **Advanced Analytics:** Status transition patterns and predictions
4. **Status History:** Track all status changes with timestamps
5. **Automated Alerts:** Notifications for unusual status patterns

### Schema Extensions
```sql
-- Future: Status history table
CREATE TABLE flight_status_history (
    id SERIAL PRIMARY KEY,
    flight_id INTEGER REFERENCES flights(id),
    old_status VARCHAR(20),
    new_status VARCHAR(20),
    changed_at TIMESTAMP DEFAULT NOW(),
    changed_by VARCHAR(50),
    reason TEXT
);
```

## Configuration

### Environment Variables
```yaml
# Status system configuration
VATSIM_CLEANUP_INTERVAL: 3600    # Cleanup frequency (seconds)
FLIGHT_COMPLETION_TIMEOUT: 3600   # Time before marking as completed (seconds)
STALE_FLIGHT_TIMEOUT_MULTIPLIER: 2.5  # Stale timeout multiplier (× API polling interval)
STATUS_VALIDATION_ENABLED: true   # Enable status validation
```

### Database Settings
```sql
-- Status-related settings
SET session_replication_role = replica;  -- For bulk updates
SET synchronous_commit = off;           -- For performance
```

This documentation provides a complete overview of the flight status system, including its logic, implementation, monitoring, and troubleshooting procedures. 