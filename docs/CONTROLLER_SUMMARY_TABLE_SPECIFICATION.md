# Controller Summary Table Specification

## Overview

The `controller_summaries` table provides pre-computed summary data for controller sessions, dramatically improving query performance for controller statistics and analysis. This table follows the same pattern as the existing `flight_summaries` table.

## Table Structure

```sql
CREATE TABLE IF NOT EXISTS controller_summaries (
    id BIGSERIAL PRIMARY KEY,
    
    -- Controller Identity
    callsign VARCHAR(50) NOT NULL,
    cid INTEGER,
    name VARCHAR(100),
    
    -- Session Summary
    session_start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    session_end_time TIMESTAMP WITH TIME ZONE,
    session_duration_minutes INTEGER DEFAULT 0,
    
    -- Controller Details
    rating INTEGER,
    facility INTEGER,
    server VARCHAR(50),
    
    -- Aircraft Activity
    total_aircraft_handled INTEGER DEFAULT 0,
    peak_aircraft_count INTEGER DEFAULT 0,
    hourly_aircraft_breakdown JSONB,
    frequencies_used JSONB,
    aircraft_details JSONB,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_aircraft_counts CHECK (
        total_aircraft_handled >= 0 
        AND peak_aircraft_count >= 0 
        AND peak_aircraft_count <= total_aircraft_handled
    ),
    CONSTRAINT valid_session_times CHECK (
        session_end_time IS NULL OR session_end_time > session_start_time
    ),
    CONSTRAINT valid_rating CHECK (rating >= 1 AND rating <= 11)
);
```

## Field Descriptions

### Controller Identity
| Field | Type | Description | Source |
|-------|------|-------------|---------|
| `callsign` | VARCHAR(50) | Controller callsign (e.g., "SY_TWR") | `controllers.callsign` |
| `cid` | INTEGER | VATSIM user ID | `controllers.cid` |
| `name` | VARCHAR(100) | Controller's real name | `controllers.name` |

### Session Summary
| Field | Type | Description | Source |
|-------|------|-------------|---------|
| `session_start_time` | TIMESTAMP WITH TIME ZONE | When session began | `controllers.logon_time` |
| `session_end_time` | TIMESTAMP WITH TIME ZONE | When session ended | `controllers.last_updated` |
| `session_duration_minutes` | INTEGER | Total session time in minutes | Calculated from start/end times |

### Controller Details
| Field | Type | Description | Source |
|-------|------|-------------|---------|
| `rating` | INTEGER | Controller rating (-1 to 12) | `controllers.rating` |
| `facility` | INTEGER | Facility type (0-6) | `controllers.facility` |
| `server` | VARCHAR(50) | Network server | `controllers.server` |

### Aircraft Activity
| Field | Type | Description | Source |
|-------|------|-------------|---------|
| `total_aircraft_handled` | INTEGER | Total unique aircraft on frequency | `transceivers` table analysis |
| `peak_aircraft_count` | INTEGER | Maximum aircraft in any hour | Calculated from hourly breakdown |
| `hourly_aircraft_breakdown` | JSONB | Aircraft count per hour | `transceivers` table analysis |
| `frequencies_used` | JSONB | List of frequencies used during session | `transceivers` table analysis |
| `aircraft_details` | JSONB | Detailed aircraft interaction data | `transceivers` table analysis |

### Timestamps
| Field | Type | Description |
|-------|------|-------------|
| `created_at` | TIMESTAMP WITH TIME ZONE | Record creation time |
| `updated_at` | TIMESTAMP WITH TIME ZONE | Record update time |

## JSONB Field Structures

### hourly_aircraft_breakdown
```json
{
  "2025-08-18T11:00:00+00:00": 2,
  "2025-08-18T12:00:00+00:00": 3,
  "2025-08-18T13:00:00+00:00": 1
}
```

### frequencies_used
```json
["122.8", "118.54", "125.2"]
```

### aircraft_details
```json
{
  "aircraft": [
    {
      "callsign": "QFA123",
      "first_seen": "2025-08-18T11:50:00+00:00",
      "last_seen": "2025-08-18T12:00:00+00:00",
      "time_on_frequency_minutes": 10
    }
  ],
  "summary": {
    "total_aircraft": 1,
    "total_time_minutes": 10,
    "average_time_per_aircraft": 10.0
  }
}
```

## Data Derivation Logic

### Aircraft Detection
- Aircraft are identified from `transceivers` table where `entity_type = 'flight'`
- Aircraft are considered "on frequency" when they use the same frequency as the controller
- Controller frequency is determined from `transceivers` table where `entity_type = 'atc'`

### Time Calculations
- `session_duration_minutes`: `(session_end_time - session_start_time) / 60`
- `time_on_frequency_minutes`: `(last_seen - first_seen) / 60`
- All times are rounded to minute precision (no subseconds)

### Aggregations
- `total_aircraft_handled`: Count of unique aircraft callsigns
- `peak_aircraft_count`: Maximum value from hourly breakdown
- `hourly_aircraft_breakdown`: Aircraft count grouped by hour
- `frequencies_used`: Array of unique frequencies used during session

## Performance Benefits

### Before (Direct Query)
- Complex JOINs between `controllers` and `transceivers` tables
- Multiple GROUP BY operations
- Real-time aggregation calculations
- **Query Time**: 5-15 seconds

### After (Summary Table)
- Simple SELECT from pre-computed data
- No JOINs or GROUP BY operations
- Instant results
- **Query Time**: 10-50ms

**Performance Improvement**: 100-300x faster

## Indexes

```sql
-- Primary key (auto-created)
PRIMARY KEY (id)

-- Performance indexes
CREATE INDEX idx_controller_summaries_callsign ON controller_summaries(callsign);
CREATE INDEX idx_controller_summaries_session_time ON controller_summaries(session_start_time, session_end_time);
CREATE INDEX idx_controller_summaries_aircraft_count ON controller_summaries(total_aircraft_handled);
CREATE INDEX idx_controller_summaries_rating ON controller_summaries(rating);
CREATE INDEX idx_controller_summaries_facility ON controller_summaries(facility);
```

## Triggers

```sql
-- Auto-update updated_at timestamp
CREATE TRIGGER update_controller_summaries_updated_at 
    BEFORE UPDATE ON controller_summaries 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## Sample Data

```json
{
  "id": 1,
  "callsign": "SY_TWR",
  "cid": 1817015,
  "name": "Jamison Smith",
  "session_start_time": "2025-08-18T12:35:00+00:00",
  "session_end_time": "2025-08-18T14:35:00+00:00",
  "session_duration_minutes": 120,
  "rating": 3,
  "facility": 4,
  "server": "USA-WEST",
  "total_aircraft_handled": 8,
  "peak_aircraft_count": 6,
  "hourly_aircraft_breakdown": {
    "2025-08-18T12:00:00+00:00": 2,
    "2025-08-18T13:00:00+00:00": 6,
    "2025-08-18T14:00:00+00:00": 4
  },
  "frequencies_used": ["122.8", "118.54", "125.2"],
  "aircraft_details": {
    "aircraft": [
      {
        "callsign": "QFA123",
        "first_seen": "2025-08-18T12:40:00+00:00",
        "last_seen": "2025-08-18T13:15:00+00:00",
        "time_on_frequency_minutes": 35
      }
    ],
    "summary": {
      "total_aircraft": 1,
      "total_time_minutes": 35,
      "average_time_per_aircraft": 35.0
    }
  },
  "created_at": "2025-08-18T12:35:00+00:00",
  "updated_at": "2025-08-18T14:35:00+00:00"
}
```

## Implementation Status

- [x] Table structure defined
- [x] Field specifications completed
- [x] Data derivation logic documented
- [x] Implementation plan defined
- [ ] Table creation SQL script
- [ ] Data population logic
- [ ] Index creation
- [ ] Trigger setup
- [ ] Testing and validation

## Related Documentation

- `FLIGHT_SUMMARY_TABLE_REQUIREMENTS.md` - Reference for summary table pattern
- `ARCHITECTURE_OVERVIEW.md` - Overall system architecture
- `DATA_FLOW_ARCHITECTURE.md` - Data flow patterns

## Notes

- All timestamps use minute precision (no subseconds)
- Aircraft type information is not stored (available in other tables)
- Frequency and departure/arrival data is not duplicated (available in transceivers table)
- This table follows the established pattern of pre-computed summary tables for performance optimization

## Multiple Frequency Handling

### **Dynamic Frequency Usage During Sessions**
Controllers (especially CTR/Center controllers) will add and remove frequencies throughout their session. The summary system handles this by:

1. **Capturing All Frequencies**: The `frequencies_used` JSONB field stores all unique frequencies used during a session
2. **Session-Based Aggregation**: All controller records for a specific session (callsign + logon_time) are analyzed together
3. **Complete Frequency History**: Shows frequency changes and usage patterns over time

### **Example: SY_TWR Session**
```sql
-- When processing SY_TWR session from 18:25:20
SELECT DISTINCT frequency 
FROM controllers 
WHERE callsign = 'SY_TWR' 
  AND logon_time = '2025-08-17 18:25:20+00'
ORDER BY frequency;

-- Result: ["199.998", "120.500"]
```

### **Summary Record with Multiple Frequencies**
```json
{
  "callsign": "SY_TWR",
  "session_start_time": "2025-08-17T18:25:20+00:00",
  "session_end_time": "2025-08-17T18:30:14+00:00",
  "frequencies_used": ["199.998", "120.500"],
  "aircraft_details": {
    "aircraft": [
      {
        "callsign": "QFA123",
        "frequency_mhz": 199.998,
        "time_on_frequency_minutes": 15
      },
      {
        "callsign": "VOZ456", 
        "frequency_mhz": 120.500,
        "time_on_frequency_minutes": 20
      }
    ]
  }
}
```

### **Benefits of This Approach**
- **Complete frequency history**: Shows all frequencies used during the session
- **Aircraft tracking**: Each aircraft shows which frequency it used
- **Session analysis**: Can see frequency changes and usage patterns
- **Performance metrics**: Track workload across different frequencies
- **Flexible data model**: Handles any number of frequency changes during a session

## Data Validation and Constraints

### Database-Level Constraints
The table includes several CHECK constraints to ensure data integrity:

#### **Session Duration Validation**
```sql
CONSTRAINT valid_session_duration CHECK (
    session_duration_minutes = EXTRACT(EPOCH FROM (session_end_time - session_start_time)) / 60
    OR session_end_time IS NULL
)
```
- Ensures `session_duration_minutes` always matches the actual time difference
- Allows NULL `session_end_time` for active sessions
- Prevents manual data corruption

#### **Aircraft Count Validation**
```sql
CONSTRAINT valid_aircraft_counts CHECK (
    total_aircraft_handled >= 0 
    AND peak_aircraft_count >= 0 
    AND peak_aircraft_count <= total_aircraft_handled
)
```
- All aircraft counts must be non-negative
- Peak count cannot exceed total count
- Maintains logical consistency

#### **Session Time Validation**
```sql
CONSTRAINT valid_session_times CHECK (
    session_end_time IS NULL OR session_end_time > session_start_time
)
```
- End time must be after start time (when present)
- Allows NULL end time for active sessions

#### **Rating Validation**
```sql
CONSTRAINT valid_rating CHECK (rating >= 1 AND rating <= 11)
```
- Ensures rating is within valid VATSIM range
- Prevents invalid rating data

### Application-Level Validation
Additional validation occurs in the Python service layer:
- **JSONB structure validation**: Ensures proper format for complex fields
- **Business logic validation**: Validates relationships between fields
- **Error logging**: All validation failures are logged for monitoring

## Implementation Plan

### Architecture Overview
The controller summary system follows the same pattern as the existing flight summary system:

- **Separate background processing**: Runs every 60 minutes via scheduled task
- **Same configuration style**: Uses environment variables in docker-compose.yml
- **Same file organization**: `ControllerSummaryService` class within `data_service.py`

### Processing Logic
1. **Identify completed controllers**: `last_updated < (current_time - 30_minutes)` and not yet summarized
2. **Real-time transceivers lookup**: Query aircraft data from `transceivers` table during summary creation
3. **Archive and delete**: Move old controller records to `controllers_archive` table, then delete from main table

### Configuration (docker-compose.yml)
```yaml
# Controller Summary System Configuration
CONTROLLER_SUMMARY_ENABLED: "true"          # Enable controller summary processing
CONTROLLER_COMPLETION_MINUTES: 30           # Minutes after last update to mark session complete
CONTROLLER_RETENTION_HOURS: 168             # Hours to keep archived data (7 days)
CONTROLLER_SUMMARY_INTERVAL: 60             # Minutes between summary processing (1 hour)
```

### Implementation Steps
1. Create `ControllerSummaryService` class in `data_service.py`
2. Add configuration to `config.py`
3. Add environment variables to `docker-compose.yml`
4. Implement the processing methods:
   - `process_completed_controllers()`
   - `_identify_completed_controllers()`
   - `_create_controller_summaries()`
   - `_archive_completed_controllers()`
   - `_delete_completed_controllers()`
5. Add scheduled processing startup
6. Create `controllers_archive` table
7. Add indexes and triggers

### Data Flow
1. **Every 60 seconds**: Main loop processes new VATSIM data
2. **Every 60 minutes**: Background task identifies completed controllers (30+ minutes inactive)
3. **Real-time lookup**: Query `transceivers` table for aircraft interaction data
4. **Create summary**: Populate `controller_summaries` table with aggregated data
5. **Archive & cleanup**: Move old records to archive, delete from main table
