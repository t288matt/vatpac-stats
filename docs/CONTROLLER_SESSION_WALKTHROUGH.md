# Controller Session Walkthrough - Complete System Flow

## 🚀 **COMPLETE WALKTHROUGH: From Controller Logon to Session Closing (Fully Fleshed Out)**

### **The Four Different Intervals - Explained in Detail:**

1. **VATSIM API Polling**: **60 seconds** - Keeps controller data fresh from VATSIM network
2. **Controller Summary Processing**: **60 minutes** - Processes completed controller sessions
3. **Task Monitoring**: **5 minutes** - Ensures background tasks keep running
4. **Reconnection Threshold**: **5 minutes** - Merges brief disconnections into one session

### **The Complete Flow - Step by Step:**

#### **Step 1: Application Startup and Initialization**
```python
# In DataService.initialize() - lines 121-125
await self.start_scheduled_flight_processing()
if self.config.controller_summary.enabled:
    await self.start_scheduled_controller_processing()
```

**What Happens:**
- Data service initializes and starts all scheduled tasks
- Controller summary processing task begins running in background
- System is now ready to process controllers

#### **Step 2: Controller Logs On to VATSIM Network**
**What Happens:**
- Controller connects to VATSIM network (e.g., "SY_APP" with CID 873048)
- VATSIM API receives the connection and includes it in their data feed
- Controller's `logon_time` is recorded when they first connect

**Python Functions Involved:**
- `VATSIMService.get_current_data()` - Gets live data from VATSIM API
- `DataService._process_controllers()` - Processes and stores controller data
- Controller record gets inserted into `controllers` table with:
  - `callsign`: "SY_APP"
  - `cid`: 873048
  - `logon_time`: 18:47:00 UTC
  - `last_updated`: 18:47:00 UTC (same as logon_time initially)

#### **Step 3: Every 60 Seconds - VATSIM Data Updates (Continuous)**
**What Happens:**
- **Function**: `run_data_ingestion()` → `DataService.process_vatsim_data()`
- **Action**: System polls VATSIM API every 60 seconds for fresh data
- **Controller Status**: If controller is still online, their `last_updated` timestamp gets refreshed
- **Result**: Controller stays "active" in the system as long as they're online

**Example Timeline:**
- **18:47:00**: Controller logs on, `last_updated` = 18:47:00
- **18:48:00**: 60-second update, `last_updated` = 18:48:00
- **18:49:00**: 60-second update, `last_updated` = 18:49:00
- **18:50:00**: 60-second update, `last_updated` = 18:50:00
- **...continues every 60 seconds while controller is online**

#### **Step 4: Every 60 Minutes - Controller Summary Processing (Scheduled)**
**What Happens:**
- **Function**: `_scheduled_controller_processing_loop()` runs every 60 minutes
- **Purpose**: Look for controllers who have been offline long enough to process
- **Action**: Calls `process_completed_controllers()` to find and process completed sessions

**Python Functions Involved:**
```python
# In _scheduled_controller_processing_loop() - lines 1975-1990
while True:
    try:
        # Process completed controllers
        result = await self.process_completed_controllers()
        
        # Wait for next interval (60 minutes)
        await asyncio.sleep(interval_seconds)  # 3600 seconds = 60 minutes
```

**Example Timeline:**
- **18:47:00**: Controller logs on
- **19:47:00**: First summary processing cycle (60 minutes later)
- **20:47:00**: Second summary processing cycle (120 minutes later)
- **21:47:00**: Third summary processing cycle (180 minutes later)

#### **Step 5: Identify Completed Controllers (30-Minute Threshold)**
**What Happens:**
- **Function**: `_identify_completed_controllers(completion_minutes=30)`
- **Logic**: Find controllers where `last_updated < (now - 30 minutes)`
- **Key Point**: Only if their (callsign, cid) combination hasn't been summarized yet

**Python Functions Involved:**
```python
# In _identify_completed_controllers() - lines 1366-1388
completion_threshold = datetime.now(timezone.utc) - timedelta(minutes=completion_minutes)  # 30 minutes

query = """
    SELECT DISTINCT callsign, cid, logon_time
    FROM controllers 
    WHERE last_updated < :completion_threshold
    AND (callsign, cid) NOT IN (
        SELECT DISTINCT callsign, cid FROM controller_summaries
    )
"""
```

**Example with Controller 873048:**
- **18:47:00**: Controller logs on
- **19:17:00**: Controller logs off (30 minutes later)
- **19:47:00**: System checks for completed controllers
- **Query Result**: Finds controller 873048 because:
  - `last_updated` (19:17:00) < `completion_threshold` (19:17:00)
  - (callsign="SY_APP", cid=873048) not in controller_summaries yet

#### **Step 6: The 5-Minute Reconnection Logic (Session Merging)**
**What Happens:**
- **Function**: `_create_controller_summaries()` processes each completed controller
- **Purpose**: Check if controller had brief disconnections within 5 minutes
- **Action**: Merge multiple controller records into one session if they're within 5 minutes

**Python Functions Involved:**
```python
# In _create_controller_summaries() - lines 1415-1430
# Configuration for session merging - configurable threshold for reconnections
reconnection_threshold_minutes = int(os.getenv("CONTROLLER_RECONNECTION_THRESHOLD_MINUTES", "5"))

# Get all records for this controller including potential reconnections within 5 minutes
controller_records = await session.execute(text("""
    SELECT DISTINCT callsign, cid, logon_time
    FROM controllers 
    WHERE callsign = :callsign 
    AND (
        logon_time = :logon_time  -- Original session
        OR (
            logon_time > :logon_time 
            AND logon_time <= :reconnection_window
        )
    )
    ORDER BY created_at
"""), {
    "callsign": callsign,
    "logon_time": logon_time,
    "reconnection_threshold": reconnection_threshold_minutes  # 5 minutes
})
```

**Real-World Example - Controller with Brief Disconnection:**
- **18:47:00**: Controller logs on as "SY_APP" (logon_time)
- **19:17:00**: Controller loses internet connection (disconnects)
- **19:19:00**: Controller reconnects (2 minutes later)
- **22:06:00**: Controller logs off

**SQL Query Results:**
- **Record 1**: logon_time = 18:47:00 (original session)
- **Record 2**: logon_time = 19:19:00 (reconnection within 5 minutes)
- **Result**: 2 records found, will be merged into one session

#### **Step 7: Session Duration Calculation and Merging**
**What Happens:**
- **Function**: Calculate total session duration across all merged records
- **Logic**: From first logon time to last update time
- **Result**: One comprehensive session covering all activity

**Python Functions Involved:**
```python
# In _create_controller_summaries() - lines 1435-1445
records = controller_records.fetchall()

# Get first and last records across merged sessions
first_record = records[0]      # logon_time = 18:47:00
last_record = records[-1]      # last_updated = 22:06:00

# Calculate total session duration including reconnections
session_duration_minutes = int((last_record.last_updated - first_record.logon_time).total_seconds() / 60)
# Result: (22:06:00 - 18:47:00) = 3 hours 19 minutes = 199 minutes

# Log whether sessions were merged
if len(records) > 1:
    self.logger.debug(f"✅ Created merged summary for controller {callsign} (duration: {session_duration_minutes} min, {len(records)} sessions merged)")
```

**Example Output:**
- **Duration**: 199 minutes (3 hours 19 minutes)
- **Sessions Merged**: 2 (original + reconnection)
- **Log Message**: "✅ Created merged summary for controller SY_APP (duration: 199 min, 2 sessions merged)"

#### **Step 8: Aircraft Interaction Data Collection**
**What Happens:**
- **Function**: `_get_aircraft_interactions()` calls `FlightDetectionService`
- **Purpose**: Find which aircraft the controller actually handled during their session
- **Action**: Uses controller type detection to determine proximity ranges

**Python Functions Involved:**
```python
# In _get_aircraft_interactions() - lines 1552-1580
# Use the Flight Detection Service for accurate controller-pilot pairing
# This ensures dynamic geographic proximity validation based on controller type and proper frequency matching
# Controller types get appropriate ranges: Ground/Tower (15nm), Approach (60nm), Center (400nm), FSS (1000nm)

# Log controller type and proximity range for debugging
controller_info = self.flight_detection_service.controller_type_detector.get_controller_info(callsign)
self.logger.info(f"Controller {callsign} detected as {controller_info['type']} with {controller_info['proximity_threshold']}nm proximity range")

flight_data = await self.flight_detection_service.detect_controller_flight_interactions_with_timeout(
    callsign, session_start, session_end, timeout_seconds=30.0
)
```

**Controller Type Detection Example:**
- **Callsign**: "SY_APP" → **Type**: "Approach" → **Range**: 60 nautical miles
- **System**: Looks for aircraft within 60nm of controller during session
- **Result**: Comprehensive list of aircraft the controller handled

#### **Step 9: Summary Record Creation**
**What Happens:**
- **Function**: Creates comprehensive summary with all session data
- **Data**: Session duration, aircraft counts, frequencies used, interaction details
- **Storage**: Inserts into `controller_summaries` table

**Python Functions Involved:**
```python
# In _create_controller_summaries() - lines 1447-1470
# Create merged summary data
summary_data = {
    "callsign": callsign,                    # "SY_APP"
    "cid": first_record.cid,                 # 873048
    "name": first_record.name,               # "Matt D"
    "session_start_time": first_record.logon_time,      # 18:47:00
    "session_end_time": adjusted_end_time,              # 22:06:00
    "session_duration_minutes": session_duration_minutes,  # 199
    "rating": first_record.rating,           # Controller rating
    "facility": first_record.facility,       # Facility type
    "server": first_record.server,           # Network server
    "total_aircraft_handled": aircraft_data["total_aircraft"],  # From Flight Detection Service
    "peak_aircraft_count": aircraft_data["peak_count"],         # Peak aircraft count
    "hourly_aircraft_breakdown": json.dumps(aircraft_data["hourly_breakdown"]),  # Hourly breakdown
    "frequencies_used": json.dumps(frequencies_used),           # All frequencies used
    "aircraft_details": json.dumps(aircraft_data["details"])    # Detailed interaction data
}

# Insert merged summary
await session.execute(text("""
    INSERT INTO controller_summaries (
        callsign, cid, name, session_start_time, session_end_time,
        session_duration_minutes, rating, facility, server,
        total_aircraft_handled, peak_aircraft_count,
        hourly_aircraft_breakdown, frequencies_used, aircraft_details
        ) VALUES (
        :callsign, :cid, :name, :session_start_time, :session_end_time,
        :session_duration_minutes, :rating, :facility, :server,
        :total_aircraft_handled, :peak_aircraft_count,
        :hourly_aircraft_breakdown, :frequencies_used, :aircraft_details
    )
"""), summary_data)
```

#### **Step 10: Archive and Cleanup**
**What Happens:**
- **Function**: `_archive_completed_controllers()` moves old records to archive
- **Action**: `_delete_completed_controllers()` removes old records from main table
- **Result**: Main `controllers` table stays fast and efficient

**Python Functions Involved:**
```python
# In process_completed_controllers() - lines 1335-1340
# Step 3: Archive completed records (only if summaries were created)
records_archived = await self._archive_completed_controllers(successful_controllers)

# Step 4: Delete completed records (only if summaries were created)
records_deleted = await self._delete_completed_controllers(successful_controllers)
```

### **The Complete Function Call Chain (Fully Fleshed Out):**

```
VATSIM API (every 60s)
    ↓
run_data_ingestion() → DataService.process_vatsim_data()
    ↓
DataService._process_controllers() (updates last_updated every 60s)
    ↓
[Controller stays active in controllers table with fresh timestamps]
    ↓
_scheduled_controller_processing_loop() (every 60 minutes)
    ↓
DataService.process_completed_controllers()
    ↓
DataService._identify_completed_controllers(completion_minutes=30)
    ↓
SQL Query: Find controllers offline for >30 minutes
    ↓
DataService._create_controller_summaries()
    ↓
[5-MINUTE RECONNECTION LOGIC APPLIED HERE]
    ↓
SQL Query: Find all records within 5-minute reconnection window
    ↓
Calculate total session duration across merged records
    ↓
DataService._get_aircraft_interactions() → FlightDetectionService
    ↓
ControllerTypeDetector.get_controller_info() → Determine proximity range
    ↓
detect_controller_flight_interactions_with_timeout() → Find aircraft handled
    ↓
Create comprehensive summary data (duration, aircraft counts, frequencies)
    ↓
INSERT INTO controller_summaries table
    ↓
DataService._archive_completed_controllers() → Move to archive
    ↓
DataService._delete_completed_controllers() → Clean up main table
    ↓
[Controller session completely processed and summarized]
```

### **Configuration Values from Docker Compose (Fully Explained):**

```yaml
CONTROLLER_SUMMARY_INTERVAL: "60"                    # 60 minutes between summary processing cycles
CONTROLLER_COMPLETION_MINUTES: "30"                  # 30 minutes before controller is considered "completed"
CONTROLLER_RECONNECTION_THRESHOLD_MINUTES: "5"       # 5 minutes to merge reconnections into one session
```

**Why These Values Make Sense:**
- **60-minute summary interval**: Efficient processing, not overwhelming the system
- **30-minute completion threshold**: Controllers are processed within 1-2 summary cycles
- **5-minute reconnection threshold**: Handles real-world network issues without fragmenting sessions

### **Real-World Example - Complete Session Lifecycle:**

**Controller 873048 (Matt D) using "SY_APP":**

1. **18:47:00**: Logs on → Record created in `controllers` table
2. **18:48:00 - 19:16:00**: Every 60 seconds, `last_updated` refreshed
3. **19:17:00**: Brief disconnection (internet issue)
4. **19:19:00**: Reconnects (2 minutes later) → New record created
5. **19:20:00 - 22:05:00**: Every 60 seconds, `last_updated` refreshed
6. **22:06:00**: Logs off → `last_updated` stops updating
7. **22:36:00**: 30 minutes pass, controller marked as "completed"
8. **23:47:00**: Next 60-minute summary cycle (60 minutes after 22:47)
9. **System Processing**:
   - Finds controller 873048 as completed
   - Applies 5-minute reconnection logic
   - Merges 2 records (18:47:00 + 19:19:00) into one session
   - Calculates total duration: 199 minutes (18:47:00 to 22:06:00)
   - Creates comprehensive summary with all aircraft interactions
   - Archives old records, cleans up main table

**Final Result**: **1 complete summary** covering all 199 minutes of controller activity, including the brief disconnection, with comprehensive aircraft interaction data.

---

**Document Created**: January 2025  
**Purpose**: Complete controller session processing walkthrough  
**Status**: Complete and comprehensive
