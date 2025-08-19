# 🔍 Flight-Transceiver Interaction System Investigation

This document provides a comprehensive analysis of the current flight processing system and identifies the exact locations where flight-specific transceiver interaction variables should be implemented.

## 🎯 **Current System Analysis**

### **1. Main Data Flow Architecture**

```
VATSIM API → VATSIM Service → Data Service → Database
     │              │              │           │
     ▼              ▼              ▼           ▼
Raw JSON    Parsed Data    Business    Stored
Response    Objects        Logic       Records
```

**Key Components:**
- **`VATSIMService`**: Fetches and parses raw VATSIM data
- **`DataService`**: Main orchestrator for data processing
- **`FlightDetectionService`**: Handles flight-controller interactions
- **`ATCDetectionService`**: Handles ATC-flight interactions (reverse direction)

### **2. Current Flight Processing Flow**

#### **A. Data Ingestion (Main Entry Point)**
**Location**: `app/main.py` lines 155-200
```python
async def run_data_ingestion():
    """Run the data ingestion process"""
    while True:
        # Process VATSIM data without verbose logging
        await data_service.process_vatsim_data()
        await asyncio.sleep(config.vatsim.polling_interval)
```

**Frequency**: Every 60 seconds (configurable via `VATSIM_POLLING_INTERVAL`)

#### **B. Flight Data Processing**
**Location**: `app/services/data_service.py` lines 200-300
```python
async def _process_flights(self, flights_data: List[Dict[str, Any]]) -> int:
    # 1. Geographic boundary filtering
    if self.geographic_boundary_filter.config.enabled:
        filtered_flights = self.geographic_boundary_filter.filter_flights_list(flights_data)
    
    # 2. Bulk database insertion
    session.add_all([Flight(**flight_data) for flight_data in bulk_flights])
    
    # 3. Sector occupancy tracking
    await self._track_sector_occupancy(flight_dict, session)
```

**Current Processing Steps:**
1. **Geographic Filtering**: Filters flights based on Australian airspace boundaries
2. **Data Validation**: Ensures required fields are present
3. **Database Storage**: Bulk inserts flight records
4. **Sector Tracking**: Updates sector occupancy data

#### **C. Transceiver Processing**
**Location**: `app/services/data_service.py` lines 400-500
```python
async def _process_transceivers(self, transceivers_data: List[Dict[str, Any]]) -> int:
    # 1. Geographic boundary filtering
    if self.geographic_boundary_filter.config.enabled:
        filtered_transceivers = self.geographic_boundary_filter.filter_transceivers_list(transceivers_data)
    
    # 2. Entity linking (flight vs ATC)
    transceiver_data = {
        "entity_type": transceiver_dict.get("entity_type", "flight"),
        "entity_id": transceiver_dict.get("entity_id"),
        "frequency": transceiver_dict.get("frequency", 0),
        "position_lat": transceiver_dict.get("position_lat"),
        "position_lon": transceiver_dict.get("position_lon")
    }
```

**Current Transceiver Processing:**
1. **Geographic Filtering**: Same boundary filtering as flights
2. **Entity Classification**: Links transceivers to flights or ATC
3. **Frequency Storage**: Stores radio frequency data
4. **Position Tracking**: Records geographic coordinates

### **3. Current Flight-Transceiver Interaction Logic**

#### **A. Flight Detection Service (Controller → Flight)**
**Location**: `app/services/flight_detection_service.py` lines 190-290
```python
async def _find_frequency_matches(self, controller_transceivers, flight_transceivers, ...):
    query = """
        WITH controller_transceivers AS (...),
        flight_transceivers AS (...),
        frequency_matches AS (
            SELECT ... FROM controller_transceivers ct 
            JOIN flight_transceivers ft ON ct.frequency_mhz = ft.frequency_mhz 
            AND ABS(EXTRACT(EPOCH FROM (ct.timestamp - ft.timestamp))) <= :time_window
        )
        SELECT ... WHERE (
            -- Haversine formula for distance in nautical miles
            (3440.065 * ACOS(...)) <= :proximity_threshold_nm
        )
    """
```

**Current Fixed Variables:**
- **Time Window**: 180 seconds (3 minutes) - `FLIGHT_DETECTION_TIME_WINDOW_SECONDS`
- **Proximity Threshold**: Dynamic based on controller type (15nm-1000nm)
- **Frequency Matching**: Exact frequency match required

#### **B. ATC Detection Service (Flight → ATC)**
**Location**: `app/services/atc_detection_service.py` lines 180-260
```python
async def _find_frequency_matches(self, flight_transceivers, atc_transceivers, ...):
    query = """
        WITH flight_transceivers AS (...),
        atc_transceivers AS (...),
        frequency_matches AS (
            SELECT ... FROM flight_transceivers ft 
            JOIN atc_transceivers at ON ft.frequency_mhz = at.frequency_mhz 
            AND ABS(EXTRACT(EPOCH FROM (ft.timestamp - at.timestamp))) <= :time_window
        )
        SELECT ... WHERE (
            -- Haversine formula for distance in nautical miles
            (3440.065 * ACOS(...)) <= :proximity_threshold_nm
        )
    """
```

**Current Fixed Variables:**
- **Time Window**: 180 seconds (3 minutes) - hardcoded in constructor
- **Proximity Threshold**: 300nm - hardcoded in constructor
- **Frequency Matching**: Exact frequency match required

## 🔧 **Implementation Points for Flight-Specific Variables**

### **1. Primary Implementation Location: FlightDetectionService**

**File**: `app/services/flight_detection_service.py`
**Current State**: Uses fixed `self.time_window_seconds` (180s)
**Target State**: Dynamic time window based on flight type

**Required Changes:**
```python
# CURRENT (line 43):
self.time_window_seconds = time_window_seconds or int(os.getenv("FLIGHT_DETECTION_TIME_WINDOW_SECONDS", "180"))

# TARGET:
self.flight_type_detector = FlightTypeDetector()
# Time window will be determined per flight during detection
```

### **2. Secondary Implementation Location: ATCDetectionService**

**File**: `app/services/atc_detection_service.py`
**Current State**: Uses fixed `self.time_window_seconds` (180s) and `self.proximity_threshold_nm` (300nm)
**Target State**: Dynamic variables based on flight type

**Required Changes:**
```python
# CURRENT (line 22):
def __init__(self, time_window_seconds: int = 180, proximity_threshold_nm: float = 300.0):

# TARGET:
def __init__(self):
    self.flight_type_detector = FlightTypeDetector()
    # Variables determined per flight during detection
```

### **3. Data Service Integration Point**

**File**: `app/services/data_service.py`
**Current State**: Processes flights and transceivers separately
**Target State**: Pass flight type information to interaction detection services

**Required Changes:**
```python
# CURRENT (line 270):
await self._track_sector_occupancy(flight_dict, session)

# TARGET:
# Add flight type detection and pass to interaction services
flight_info = self.flight_type_detector.get_flight_info(flight_dict)
flight_dict["flight_type"] = flight_info["flight_type"]
flight_dict["interaction_variables"] = flight_info["interaction_variables"]
await self._track_sector_occupancy(flight_dict, session)
```

### **4. Environment Variable Configuration**

**File**: `docker-compose.yml`
**Current State**: Only `FLIGHT_DETECTION_TIME_WINDOW_SECONDS: "180"`
**Target State**: Flight-specific interaction variables

**Required Additions:**
```yaml
# Flight-specific interaction configuration
FLIGHT_INTERACTION_COMMERCIAL_TIME_WINDOW: "300"      # 5 minutes
FLIGHT_INTERACTION_COMMERCIAL_PROXIMITY_NM: "50"      # 50nm proximity
FLIGHT_INTERACTION_PRIVATE_TIME_WINDOW: "120"         # 2 minutes
FLIGHT_INTERACTION_PRIVATE_PROXIMITY_NM: "25"         # 25nm proximity
FLIGHT_INTERACTION_MILITARY_TIME_WINDOW: "240"        # 4 minutes
FLIGHT_INTERACTION_MILITARY_PROXIMITY_NM: "75"        # 75nm proximity
FLIGHT_INTERACTION_CARGO_TIME_WINDOW: "360"           # 6 minutes
FLIGHT_INTERACTION_CARGO_PROXIMITY_NM: "60"           # 60nm proximity
FLIGHT_INTERACTION_TRAINING_TIME_WINDOW: "90"         # 1.5 minutes
FLIGHT_INTERACTION_TRAINING_PROXIMITY_NM: "15"        # 15nm proximity

# Enable/disable flight-specific interaction variables
ENABLE_FLIGHT_SPECIFIC_INTERACTIONS: "true"

# Fallback values for unknown flight types
FLIGHT_INTERACTION_DEFAULT_TIME_WINDOW: "180"         # 3 minutes (current default)
FLIGHT_INTERACTION_DEFAULT_PROXIMITY_NM: "30"         # 30nm (current default)
```

## 📊 **Database Schema Impact**

### **1. Flight Model Enhancements**

**File**: `app/models.py` lines 81-150
**Current State**: Basic flight data fields
**Target State**: Add flight type and interaction variables

**Required New Fields:**
```python
class Flight(Base, TimestampMixin):
    # ... existing fields ...
    
    # NEW: Flight type classification
    flight_type = Column(String(50), nullable=True, index=True)  # Commercial, Private, Military, etc.
    
    # NEW: Dynamic interaction variables (stored for analytics)
    interaction_time_window = Column(Integer, nullable=True)  # Dynamic time window in seconds
    interaction_proximity_threshold = Column(Float, nullable=True)  # Dynamic proximity in nm
    interaction_frequency_sensitivity = Column(String(20), nullable=True)  # High, Medium, Low
    
    # NEW: Flight type confidence
    flight_type_confidence = Column(Float, nullable=True)  # 0.0-1.0 confidence score
```

### **2. Transceiver Model Enhancements**

**File**: `app/models.py` lines 158-200
**Current State**: Basic transceiver data
**Target State**: Add flight-specific interaction tracking

**Required New Fields:**
```python
class Transceiver(Base):
    # ... existing fields ...
    
    # NEW: Flight-specific interaction data
    flight_interaction_time_window = Column(Integer, nullable=True)  # Time window used for this interaction
    flight_interaction_proximity = Column(Float, nullable=True)  # Proximity threshold used
    flight_interaction_quality = Column(Float, nullable=True)  # Interaction quality score (0.0-1.0)
```

## 🎮 **Flight Type Detection Logic**

### **1. Aircraft Type Classification**

**Implementation Location**: New service `app/services/flight_type_detector.py`

**Classification Criteria:**
```python
def _classify_flight_type(self, aircraft_type: str, aircraft_faa: str, flight_rules: str, altitude: int) -> str:
    # Commercial Aircraft Detection
    if aircraft_type in ["B738", "A320", "B777", "A350"] or aircraft_faa in ["B738", "A320"]:
        return "Commercial"
    
    # Military Aircraft Detection
    if aircraft_type in ["F16", "F18", "C130"] or "MIL" in aircraft_type.upper():
        return "Military"
    
    # Cargo Aircraft Detection
    if aircraft_type in ["B744", "B748", "B77F", "A332F"] or "FREIGHT" in aircraft_type.upper():
        return "Cargo"
    
    # Training Aircraft Detection
    if aircraft_type in ["C152", "C172", "PA28"] or altitude < 15000:
        return "Training"
    
    # Private Aircraft (default)
    return "Private"
```

### **2. Interaction Variable Assignment**

**Variable Mapping:**
```python
def _get_interaction_variables(self, flight_type: str) -> Dict[str, Any]:
    base_vars = self.interaction_variables.get(flight_type, {})
    
    return {
        "time_window_seconds": base_vars.get("time_window_seconds", self.default_time_window),
        "proximity_threshold_nm": base_vars.get("proximity_threshold_nm", self.default_proximity),
        "frequency_sensitivity": base_vars.get("frequency_sensitivity", "medium"),
        "altitude_range_min": base_vars.get("altitude_range_min", 1000),
        "altitude_range_max": base_vars.get("altitude_range_max", 45000)
    }
```

## 🧪 **Testing Strategy**

### **1. Unit Tests**

**File**: `tests/test_flight_type_detector.py` (new)
**Test Cases:**
- Aircraft type classification accuracy
- Interaction variable assignment
- Edge cases and error handling
- Confidence scoring

### **2. Integration Tests**

**File**: `tests/test_flight_detection_service.py` (enhance existing)
**Test Cases:**
- FlightDetectionService with dynamic variables
- ATCDetectionService with dynamic variables
- DataService integration
- End-to-end interaction detection

### **3. Performance Tests**

**Test Cases:**
- Dynamic variable performance impact
- Memory usage with flight type detection
- Database query optimization
- Real-world data processing

## 📈 **Expected Benefits**

1. **Realistic Flight Operations**: Different aircraft types behave differently in real-world operations
2. **Improved Accuracy**: Flight-specific variables lead to more accurate interaction detection
3. **Performance Optimization**: Smaller aircraft get faster queries due to smaller search radius
4. **Flexible Configuration**: Easy adjustment of interaction parameters via environment variables
5. **Better Analytics**: Flight type-specific interaction metrics and performance analysis

## 🔄 **Migration Strategy**

### **Phase 1: Core Service Implementation**
- Create `FlightTypeDetector` service
- Implement aircraft type classification
- Configure interaction variables per flight type

### **Phase 2: Service Integration**
- Update `FlightDetectionService` to use dynamic variables
- Update `ATCDetectionService` to use dynamic variables
- Integrate with `DataService`

### **Phase 3: Configuration & Testing**
- Add environment variable configuration
- Create comprehensive test suite
- Performance testing and optimization

### **Phase 4: Production Deployment**
- Gradual rollout with monitoring
- Performance impact assessment
- User feedback collection

## 📋 **Implementation Priority**

1. **HIGH**: `FlightTypeDetector` service creation
2. **HIGH**: `FlightDetectionService` integration
3. **MEDIUM**: `ATCDetectionService` integration
4. **MEDIUM**: `DataService` integration
5. **LOW**: Database schema enhancements
6. **LOW**: Advanced analytics and reporting

This investigation provides a complete roadmap for implementing flight-specific transceiver interaction variables while maintaining the existing system's performance and reliability.
