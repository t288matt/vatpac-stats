# Flight Completion System Documentation

## Overview

The Flight Completion System implements a **hybrid approach** to accurately mark flights as completed when they land, while providing a reliable fallback mechanism to prevent flights from remaining active indefinitely.

## Enhanced Status System

### **New Status Values**

The system now includes an enhanced status lifecycle with the following values:

| Status | Description | Trigger | Database Constraint |
|--------|-------------|---------|-------------------|
| `'active'` | Currently flying | Updated in last API call | ✅ Required |
| `'stale'` | Recently seen but not in latest update | Not updated in last 2.5× API polling interval | ✅ Required |
| `'landed'` | Aircraft has landed but pilot still connected | Landing detection criteria met | ✅ Required |
| `'completed'` | Flight finished (pilot logged off or cleanup timeout) | Pilot disconnect or 1-hour timeout | ✅ Required |
| `'cancelled'` | Flight cancelled | Manual/API update | ✅ Required |
| `'unknown'` | Status unclear | Fallback/error state | ✅ Required |

### **Enhanced Status Lifecycle**

```
VATSIM API → New Flight → 'active' → (2.5× polling interval) → 'stale' 
                                                                    ↓
                                                              (landing detected)
                                                                    ↓
                                                              'landed' → (pilot logs off) → 'completed'
                                                                    ↓
                                                              (1 hour stale) → 'completed'
```

**Key Changes:**
- **Landing Detection:** Sets status to `'landed'` instead of `'completed'`
- **Pilot Disconnect Detection:** Monitors for pilot logoff to transition to `'completed'`
- **Time-based Fallback:** Only marks as `'completed'` after 1 hour of being stale
- **Go-around Handling:** Aircraft remain in `'landed'` status even if they take off again

## System Architecture

### **Hybrid Completion Methods**

1. **Landing-Based Completion** (Primary Method)
   - Real-time detection of actual landings
   - Sets status to `'landed'` (pilot still connected)
   - High accuracy with configurable thresholds
   - **Elevation-aware detection** using airport elevation data

2. **Pilot Disconnect Detection** (Secondary Method)
   - Monitors VATSIM API for pilot disconnections
   - Transitions `'landed'` flights to `'completed'`
   - Runs every 30 seconds for real-time detection

3. **Time-Based Completion** (Fallback Method)
   - Automatic completion after 1-hour timeout
   - Safety net for edge cases and system failures
   - Prevents data accumulation and bloat

## Core Logic Flow

### **Primary Method: Landing-Based Completion**

#### **Detection Process**
```
Flight Active → Approaches Destination → Landing Conditions Met → Mark as 'landed'
```

#### **Landing Detection Criteria (Updated)**
1. **Distance**: Within `LANDING_DETECTION_RADIUS_NM` of destination airport (15.0nm)
2. **Altitude**: Below `LANDING_ALTITUDE_THRESHOLD_FT_ABOVE_AIRPORT` relative to airport elevation (1000ft)
3. **Speed**: Below `LANDING_SPEED_THRESHOLD_KTS` (20 knots)
4. **Airport Match**: Flight's arrival airport matches detected airport
5. **Elevation Calculation**: Uses existing airports table elevation data
6. **Duplicate Prevention**: No recent landing detection within `LANDING_DUPLICATE_PREVENTION_MINUTES`

#### **Process Flow**
1. **Movement Detection**: Traffic analysis service detects arrival movement
2. **Elevation Lookup**: Get airport elevation from airports table
3. **Altitude Calculation**: Calculate altitude relative to airport elevation
4. **Landing Validation**: Enhanced validation confirms actual landing vs approach
5. **Status Update**: Flight status changed to `'landed'` with landing timestamp
6. **Pilot Monitoring**: System continues to monitor for pilot disconnect

### **Secondary Method: Pilot Disconnect Detection**

#### **Detection Process**
```
Flight Landed → Pilot Disconnects from VATSIM → Mark as 'completed'
```

#### **Disconnect Detection Criteria**
1. **Status Check**: Flight status is `'landed'`
2. **VATSIM API Check**: Pilot not present in current VATSIM data
3. **Real-time Monitoring**: Runs every 30 seconds
4. **Immediate Transition**: Status changes to `'completed'` when disconnect detected

#### **Process Flow**
1. **VATSIM Data Fetch**: Get current connected pilots from VATSIM API
2. **Landed Flight Check**: Identify all flights with `'landed'` status
3. **Disconnect Detection**: Find landed flights whose pilots are no longer connected
4. **Status Transition**: Change status to `'completed'` and store flight summary
5. **Timestamp Recording**: Record exact disconnect time

### **Fallback Method: Time-Based Completion**

#### **Detection Process**
```
Flight Landed → No Pilot Disconnect for 1 Hour → Mark as 'completed'
```

#### **Time-Based Criteria**
1. **Age Check**: Flight `last_updated` older than `TIME_BASED_TIMEOUT_HOURS` (1 hour)
2. **Status Check**: Flight status is `'landed'`
3. **No Disconnect**: No recent pilot disconnect detection for this flight
4. **Automatic Process**: Runs every `CLEANUP_INTERVAL_SECONDS`

#### **Process Flow**
1. **Timeout Check**: Identify landed flights exceeding 1-hour threshold
2. **Disconnect Check**: Verify no recent pilot disconnect detection exists
3. **Fallback Completion**: Mark flight as `'completed'` with current timestamp
4. **Summary Storage**: Flight summary created with time-based completion data

## Configuration Variables

### **System Configuration**

| Variable | Default | Description |
|----------|---------|-------------|
| `LANDED_STATUS_ENABLED` | `"true"` | Enable landed status system |
| `PILOT_DISCONNECT_DETECTION_ENABLED` | `"true"` | Enable pilot disconnect detection |
| `DISCONNECT_DETECTION_INTERVAL_SECONDS` | `30` | How often to check for disconnects |

### **Landing-Based Completion Variables**

| Variable | Default | Description |
|----------|---------|-------------|
| `LANDING_DETECTION_ENABLED` | `"true"` | Enable landing-based completion |
| `LANDING_DETECTION_RADIUS_NM` | `15.0` | Distance for landing detection (nautical miles) |
| `LANDING_ALTITUDE_THRESHOLD_FT_ABOVE_AIRPORT` | `1000` | Max altitude above airport for landing (feet) |
| `LANDING_SPEED_THRESHOLD_KTS` | `20` | Max speed for landing (knots) |
| `LANDING_DUPLICATE_PREVENTION_MINUTES` | `5` | Prevent duplicate landing detections |

### **Time-Based Completion Variables**

| Variable | Default | Description |
|----------|---------|-------------|
| `TIME_BASED_FALLBACK_ENABLED` | `"true"` | Enable time-based completion |
| `TIME_BASED_TIMEOUT_HOURS` | `1` | Hours before time-based completion |
| `TIME_BASED_CLEANUP_INTERVAL_SECONDS` | `3600` | Cleanup process frequency |

## Database Schema Changes

### **Flight Table Extensions**
```sql
-- Update status constraint to include 'landed'
ALTER TABLE flights DROP CONSTRAINT IF EXISTS check_flight_status;
ALTER TABLE flights ADD CONSTRAINT check_flight_status 
CHECK (status IN ('active', 'stale', 'landed', 'completed', 'cancelled', 'unknown'));

-- Add index for landed status queries
CREATE INDEX idx_flights_status_landed ON flights(status) WHERE status = 'landed';

-- Add pilot disconnect tracking fields
ALTER TABLE flights ADD COLUMN pilot_disconnected_at TIMESTAMP;
ALTER TABLE flights ADD COLUMN disconnect_method VARCHAR(20); -- 'detected', 'timeout'
```

### **TrafficMovement Table Extensions**
```sql
-- Add completion tracking fields to TrafficMovement
ALTER TABLE traffic_movements ADD COLUMN flight_completion_triggered BOOLEAN DEFAULT FALSE;
ALTER TABLE traffic_movements ADD COLUMN completion_timestamp TIMESTAMP;
ALTER TABLE traffic_movements ADD COLUMN completion_confidence FLOAT;

-- Add indexes for completion queries
CREATE INDEX idx_traffic_movements_completion ON traffic_movements(aircraft_callsign, movement_type, flight_completion_triggered);
CREATE INDEX idx_traffic_movements_completion_time ON traffic_movements(completion_timestamp);
```

## Detailed Logic Implementation

### **Step 1: Landing Detection Process**

#### **1.1 Movement Detection**
- Traffic analysis service monitors all active flights
- Calculates distance to destination airport using Haversine formula
- **Looks up airport elevation from existing airports table**
- **Calculates altitude relative to airport elevation**
- Checks altitude and speed thresholds against airport configuration
- Validates airport match with flight plan arrival field

#### **1.2 Landing Validation**
```python
# Pseudo-logic for elevation-aware landing validation
def validate_landing(flight, distance, altitude, speed, airport_elevation):
    # Calculate altitude above airport
    altitude_above_airport = altitude - airport_elevation
    
    if distance > LANDING_DETECTION_RADIUS_NM:  # 15.0nm
        return False
    
    if altitude_above_airport > LANDING_ALTITUDE_THRESHOLD_FT_ABOVE_AIRPORT:  # 1000ft
        return False
    
    if speed > LANDING_SPEED_THRESHOLD_KTS:  # 20 knots
        return False
    
    if flight.arrival != detected_airport:
        return False
    
    return True
```

#### **1.3 Status Update**
- Landing movement created with `flight_completion_triggered = True`
- **Flight status changed to `'landed'`** (not `'completed'`)
- Landing timestamp recorded from movement detection
- **Binary confidence scoring**: 1.0 for landing detected, 0.0 for not detected

### **Step 2: Pilot Disconnect Detection Process**

#### **2.1 VATSIM API Monitoring**
- Fetches current VATSIM data every 30 seconds
- Compares connected pilots with landed flights
- Identifies pilots who have disconnected

#### **2.2 Disconnect Detection**
```python
# Pseudo-logic for pilot disconnect detection
def detect_pilot_disconnects():
    # Get all landed flights
    landed_flights = get_flights_with_status('landed')
    
    # Get current VATSIM data
    vatsim_data = fetch_vatsim_data()
    connected_callsigns = extract_callsigns(vatsim_data.flights)
    
    # Check for disconnected pilots
    for flight in landed_flights:
        if flight.callsign not in connected_callsigns:
            # Pilot has disconnected
            mark_flight_completed(flight, 'detected')
```

#### **2.3 Completion Trigger**
- Pilot disconnect detected for landed flight
- Flight status changed to `'completed'`
- Disconnect timestamp recorded
- Flight summary created and stored

### **Step 3: Time-Based Fallback Process**

#### **3.1 Timeout Detection**
- Scans all landed flights in database
- Calculates time since landing using `landed_at` field
- Identifies flights exceeding 1-hour timeout threshold

#### **3.2 Fallback Completion**
- Marks flight as `'completed'` with current timestamp
- Creates flight summary with time-based completion reason
- Logs fallback completion for monitoring and analytics

## Configuration Scenarios

### **Scenario 1: High-Accuracy Mode**
```yaml
LANDED_STATUS_ENABLED: "true"
PILOT_DISCONNECT_DETECTION_ENABLED: "true"
LANDING_DETECTION_RADIUS_NM: 15.0
LANDING_ALTITUDE_THRESHOLD_FT_ABOVE_AIRPORT: 1000
LANDING_SPEED_THRESHOLD_KTS: 20
TIME_BASED_TIMEOUT_HOURS: 1
DISCONNECT_DETECTION_INTERVAL_SECONDS: 30
```
**Result**: Very precise landing detection with real-time disconnect monitoring

### **Scenario 2: Conservative Mode**
```yaml
LANDED_STATUS_ENABLED: "true"
PILOT_DISCONNECT_DETECTION_ENABLED: "true"
LANDING_DETECTION_RADIUS_NM: 20.0
LANDING_ALTITUDE_THRESHOLD_FT_ABOVE_AIRPORT: 1500
LANDING_SPEED_THRESHOLD_KTS: 25
TIME_BASED_TIMEOUT_HOURS: 1
DISCONNECT_DETECTION_INTERVAL_SECONDS: 60
```
**Result**: Broader landing detection with less frequent disconnect checks

### **Scenario 3: Landing-Only Mode**
```yaml
LANDED_STATUS_ENABLED: "true"
PILOT_DISCONNECT_DETECTION_ENABLED: "false"
LANDING_DETECTION_RADIUS_NM: 15.0
LANDING_ALTITUDE_THRESHOLD_FT_ABOVE_AIRPORT: 1000
LANDING_SPEED_THRESHOLD_KTS: 20
```
**Result**: Only landing detection, no disconnect monitoring (relies on time-based fallback)

## Performance Considerations

### **Processing Frequency**
- **Landing Detection**: Real-time (every API polling cycle - 10 seconds)
- **Pilot Disconnect Detection**: Every 30 seconds
- **Time-Based Cleanup**: Every `CLEANUP_INTERVAL_SECONDS` (default: 1 hour)

### **Database Impact**
- **Landing Detection**: Minimal (only when landing detected)
- **Disconnect Detection**: Low (only when disconnect detected)
- **Time-Based Cleanup**: Batch processing of old flights
- **Transaction Management**: Small, frequent transactions for status updates

### **Memory Usage**
- **Landing Detection**: Low (processes only active flights)
- **Disconnect Detection**: Low (processes only landed flights)
- **Time-Based Cleanup**: Moderate (scans all landed flights)

## Monitoring and Analytics

### **Completion Metrics**
- **Landing-based transitions**: Count and percentage
- **Pilot disconnect completions**: Count and percentage
- **Time-based completions**: Count and percentage
- **Completion accuracy**: Landing vs disconnect vs time-based ratios

### **Status Distribution**
- **Active flights**: Currently flying
- **Landed flights**: Aircraft that have landed but pilots still connected
- **Completed flights**: Aircraft where pilots have disconnected
- **Stale flights**: Recently seen but not in latest update

### **Health Checks**
- **Completion rate**: Expected vs actual completion rates
- **System latency**: Time from landing detection to status update
- **Disconnect detection accuracy**: Manual vs automatic disconnect detection
- **Error rates**: Failed status transitions

## Error Handling

### **Landing Detection Errors**
- **Invalid coordinates**: Skip flights with invalid position data
- **Missing airport data**: Use default thresholds for unknown airports
- **Missing elevation data**: Default to 0 feet elevation
- **Database errors**: Log errors and continue processing

### **Disconnect Detection Errors**
- **VATSIM API failures**: Fall back to time-based completion
- **Database timeouts**: Retry with smaller batch sizes
- **System overload**: Implement backoff strategies

### **Time-Based Completion Errors**
- **Database timeouts**: Retry with smaller batch sizes
- **Transaction failures**: Rollback and retry
- **System overload**: Implement backoff strategies

## Testing Strategy

### **Unit Tests**
- Landing detection validation logic
- Elevation-aware altitude calculation
- Pilot disconnect detection logic
- Time-based completion logic
- Configuration parsing

### **Integration Tests**
- End-to-end status transition workflows
- Database transaction handling
- Performance under load
- Error recovery scenarios

### **Acceptance Tests**
- Real-world flight completion scenarios
- Airport-specific configuration testing
- Performance benchmarks
- Accuracy validation

## Migration Plan

### **Phase 1: Database Schema**
1. Add new status values and constraints
2. Create new indexes for landed status queries
3. Add pilot disconnect tracking fields
4. Migrate existing data to new schema

### **Phase 2: Landing Detection Enhancement**
1. Enhance existing arrival detection logic
2. Add elevation-aware altitude calculation
3. Implement landed status transitions
4. Update completion triggering

### **Phase 3: Pilot Disconnect Detection**
1. Implement VATSIM API monitoring
2. Add disconnect detection logic
3. Configure monitoring and analytics
4. Test disconnect detection accuracy

### **Phase 4: Time-Based Fallback Enhancement**
1. Update time-based completion to handle landed status
2. Add hybrid coordination system
3. Configure monitoring and analytics
4. Optimize performance

## Benefits

### **Accuracy Improvements**
- **Real-time landed status**: Aircraft marked as landed immediately upon landing
- **Pilot disconnect tracking**: Clear distinction between landed and completed flights
- **Elevation-aware detection**: Works for all airports regardless of elevation
- **Reduced false positives**: No more flights marked completed while pilots still connected
- **Better analytics**: Accurate flight duration and completion statistics

### **Data Quality**
- **Precise completion times**: Exact disconnect timestamps
- **Better flight tracking**: Clear distinction between active, landed, and completed flights
- **Improved reporting**: More accurate traffic movement statistics
- **Enhanced user experience**: Dashboard shows accurate flight status

### **Operational Benefits**
- **ATC awareness**: Controllers can see which aircraft have landed but pilots still connected
- **Network monitoring**: Better understanding of pilot behavior patterns
- **System reliability**: More accurate status tracking
- **Real-time updates**: Dashboard shows accurate flight status

## Conclusion

The enhanced flight completion system provides **maximum accuracy** through elevation-aware landing detection and real-time pilot disconnect monitoring while ensuring **complete reliability** through time-based fallback. The system is **fully configurable** to adapt to different operational requirements and provides comprehensive monitoring and analytics for system optimization.

This approach leverages existing infrastructure while providing much more accurate flight completion detection, significantly improving the overall quality and reliability of the VATSIM data collection system. 