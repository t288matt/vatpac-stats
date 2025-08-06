# Flight Tracking Enhancement

## Overview

This enhancement ensures that every flight position update from the VATSIM API is preserved and retrievable, providing complete flight tracks and historical position data.

## Current System Analysis

The VATSIM data collection system already stores every flight position update, but the database schema needs optimization to ensure proper preservation and retrieval.

### Current Data Flow
```
VATSIM API → Flight Filter → Memory Cache → Database → Grafana
```

### Current Implementation
- **Line 350**: `timestamp_key = f"{callsign}_{int(time.time())}"` - Creates unique keys for each position update
- **Line 500**: `# Insert all flights as new records` - Each position becomes a separate database record
- **Line 510**: `flight = Flight(**data)` - Every position update is stored

## Enhancement: Preserve Every Flight Position Update

### 1. Database Schema Optimization

#### A. Add Unique Constraint
```sql
-- Add unique constraint to prevent duplicate records for same flight at same time
ALTER TABLE flights ADD CONSTRAINT unique_flight_timestamp 
UNIQUE (callsign, last_updated);

-- Add index for performance
CREATE INDEX idx_flights_callsign_timestamp ON flights(callsign, last_updated);
```

#### B. Add Flight Track Query Index
```sql
-- Add index for flight track queries
CREATE INDEX idx_flights_callsign_last_updated ON flights(callsign, last_updated);
```

### 2. Bulk Insert Logic Enhancement

#### A. Modify `_flush_memory_to_disk` Method
```python
# OPTIMIZED BATCH 2: Flights with bulk upsert
flights_data = list(self.cache['flights'].items())
if flights_data:
    # Prepare data for bulk upsert
    flights_values = [data for _, data in flights_data]
    
    # Use bulk upsert to handle duplicates gracefully
    try:
        # Try PostgreSQL-specific upsert first
        stmt = insert(Flight).values(flights_values)
        stmt = stmt.on_conflict_do_nothing()  # Ignore duplicates
        db.execute(stmt)
    except AttributeError:
        # Fallback to manual upsert for other databases
        for data in flights_values:
            existing = db.query(Flight).filter(
                and_(
                    Flight.callsign == data['callsign'],
                    Flight.last_updated == data['last_updated']
                )
            ).first()
            if not existing:
                flight = Flight(**data)
                db.add(flight)
    
    self.logger.info(f"Bulk inserted {len(flights_values)} flight positions")
```

### 3. Flight Track API Endpoint

#### A. Complete Flight Track Retrieval
```python
@app.get("/api/flights/{callsign}/track")
async def get_flight_track(
    callsign: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
):
    """Get complete flight track with all position updates"""
    try:
        db = SessionLocal()
        try:
            # Build query for flight positions
            query = db.query(Flight).filter(Flight.callsign == callsign)
            
            if start_time:
                query = query.filter(Flight.last_updated >= start_time)
            if end_time:
                query = query.filter(Flight.last_updated <= end_time)
            
            # Get all position updates ordered by time
            flight_positions = query.order_by(Flight.last_updated).all()
            
            return {
                "callsign": callsign,
                "positions": [
                    {
                        "timestamp": pos.last_updated.isoformat(),
                        "latitude": pos.position_lat,
                        "longitude": pos.position_lng,
                        "altitude": pos.altitude,
                        "heading": pos.heading,
                        "groundspeed": pos.groundspeed,
                        "cruise_tas": pos.cruise_tas,
                        "squawk": pos.squawk
                    } for pos in flight_positions
                ],
                "total_positions": len(flight_positions),
                "first_position": flight_positions[0].last_updated.isoformat() if flight_positions else None,
                "last_position": flight_positions[-1].last_updated.isoformat() if flight_positions else None
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error getting flight track: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving flight track")
```

### 4. Flight Statistics API Endpoint

#### A. Flight Summary and Statistics
```python
@app.get("/api/flights/{callsign}/stats")
async def get_flight_stats(callsign: str):
    """Get flight statistics and summary"""
    try:
        db = SessionLocal()
        try:
            # Get all positions for this flight
            positions = db.query(Flight).filter(
                Flight.callsign == callsign
            ).order_by(Flight.last_updated).all()
            
            if not positions:
                raise HTTPException(status_code=404, detail="Flight not found")
            
            # Calculate statistics
            first_pos = positions[0]
            last_pos = positions[-1]
            
            # Calculate flight duration
            duration_minutes = int((last_pos.last_updated - first_pos.last_updated).total_seconds() / 60)
            
            # Find max altitude and speed
            max_altitude = max(pos.altitude or 0 for pos in positions)
            max_speed = max(pos.speed or 0 for pos in positions)
            
            return {
                "callsign": callsign,
                "total_positions": len(positions),
                "duration_minutes": duration_minutes,
                "first_seen": first_pos.last_updated.isoformat(),
                "last_seen": last_pos.last_updated.isoformat(),
                "departure": first_pos.departure,
                "arrival": first_pos.arrival,
                "aircraft_type": first_pos.aircraft_type,
                "max_altitude": max_altitude,
                "max_speed": max_speed,
                "route": first_pos.route
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error getting flight stats: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving flight statistics")
```

## Benefits

### Preserves Current System Strengths
- ✅ **Memory optimization** with `BoundedCache`
- ✅ **Australian flight filtering** 
- ✅ **Complete VATSIM API field mapping**
- ✅ **Centralized error handling**
- ✅ **Bulk database operations**
- ✅ **SSD wear optimization**

### Adds Flight Tracking Capabilities
- ✅ **Every position update preserved**
- ✅ **Complete flight tracks available**
- ✅ **Flight statistics and analytics**
- ✅ **No schema changes to existing tables**
- ✅ **Backward compatible**

## Use Cases

### Flight Track API
- **Grafana dashboards** - Show flight tracks on maps
- **Flight analysis** - See where aircraft went
- **ATC monitoring** - Track aircraft movements
- **Historical analysis** - Review past flights

### Flight Statistics API
- **Flight summaries** - Quick overview without loading all position records
- **Performance metrics** - Max altitude, speed, duration
- **Flight lists** - Show all flights with basic stats
- **Analytics** - Aggregate data for reports

## Implementation Steps

1. **Run database migration** to add unique constraint
2. **Update bulk insert logic** to handle duplicates gracefully  
3. **Add flight track API endpoints**
4. **Test with existing data**

## Migration Script

```sql
-- tools/add_flight_tracking_migration.sql

-- Add unique constraint to prevent duplicate flight records
ALTER TABLE flights ADD CONSTRAINT unique_flight_timestamp 
UNIQUE (callsign, last_updated);

-- Add index for performance
CREATE INDEX idx_flights_callsign_timestamp ON flights(callsign, last_updated);

-- Add index for flight track queries
CREATE INDEX idx_flights_callsign_last_updated ON flights(callsign, last_updated);

-- Add comment for documentation
COMMENT ON CONSTRAINT unique_flight_timestamp ON flights IS 'Prevents duplicate flight records for same callsign and timestamp';
```

## API Examples

### Get Flight Track
```bash
curl http://localhost:8001/api/flights/ABC123/track
```

### Get Flight Statistics
```bash
curl http://localhost:8001/api/flights/ABC123/stats
```

### Get Flight Track with Time Range
```bash
curl "http://localhost:8001/api/flights/ABC123/track?start_time=2024-01-01T10:00:00&end_time=2024-01-01T11:00:00"
```

## Performance Considerations

- **Indexing**: Proper indexes ensure fast flight track queries
- **Memory Usage**: Flight tracks can be large, consider pagination for long flights
- **Storage**: Each position update is ~1KB, 1000 flights × 100 positions = ~100MB/day
- **Query Optimization**: Use time ranges to limit data retrieval

## Monitoring

- **Track API Performance**: Monitor response times for flight track queries
- **Storage Growth**: Monitor database size growth from position data
- **Query Patterns**: Track most requested flights for optimization
- **Error Rates**: Monitor API error rates for flight tracking endpoints 