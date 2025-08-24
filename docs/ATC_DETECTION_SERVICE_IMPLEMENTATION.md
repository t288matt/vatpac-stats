# 🎯 ATC Detection Service Implementation

## 📋 Overview

The ATC Detection Service provides comprehensive analysis of air traffic control interactions with flights, calculating both total and airborne ATC coverage percentages. This service implements intelligent proximity detection and time-based calculations using the actual VATSIM API polling intervals.

**Service**: `app/services/atc_detection_service.py`  
**Status**: ✅ Production Ready  
**Last Updated**: January 2025

---

## 🔧 **Core Functionality**

### **Dual ATC Coverage Metrics**

The service now provides two distinct ATC coverage measurements:

#### **1. Total ATC Coverage (`controller_time_percentage`)**
- **Scope**: All ATC contacts (ground + airborne)
- **Denominator**: Total flight time
- **Use Case**: Overall ATC service utilization
- **Calculation**: `(total_controller_time / total_flight_time) * 100`

#### **2. Airborne ATC Coverage (`airborne_controller_time_percentage`)**
- **Scope**: Only ATC contacts when aircraft > 1500ft
- **Denominator**: Total enroute time (above 1500ft)
- **Use Case**: Enroute ATC coverage analysis
- **Calculation**: `(airborne_controller_time / total_enroute_time) * 100`

---

## ⚙️ **Configuration**

### **Environment Variables**

```yaml
# docker-compose.yml
VATSIM_POLLING_INTERVAL: 60    # How often to fetch VATSIM data (60 seconds)
FLIGHT_DETECTION_TIME_WINDOW_SECONDS: 180  # Time window for frequency matching
```

### **Key Parameters**

- **`VATSIM_POLLING_INTERVAL`**: API update frequency (default: 60 seconds)
- **`time_window_seconds`**: Maximum time difference for frequency matching (default: 180 seconds)
- **`proximity_threshold`**: Dynamic per controller type (CTR: 300nm, APP: 150nm, TWR: 50nm)

---

## 🧮 **Calculation Logic**

### **Time Calculation**

```python
# Convert contact count to actual minutes using VATSIM polling interval
controller["time_minutes"] = controller["contact_count"] * (self.vatsim_polling_interval_seconds / 60.0)
```

#### **Examples:**

| VATSIM Polling Interval | Contact Count | Time Calculation | Result |
|-------------------------|---------------|------------------|---------|
| 60 seconds (1 min)     | 10 contacts   | 10 × (60/60)     | 10 minutes |
| 120 seconds (2 min)    | 10 contacts   | 10 × (120/60)    | 20 minutes |
| 30 seconds (0.5 min)   | 10 contacts   | 10 × (30/60)     | 5 minutes |

### **Percentage Calculations**

#### **Total ATC Coverage**
```python
total_controller_time = sum(ctrl["time_minutes"] for ctrl in controller_data.values())
controller_time_percentage = min(100.0, (total_controller_time / total_records) * 100)
```

#### **Airborne ATC Coverage**
```python
total_airborne_controller_time = sum(ctrl["time_minutes"] for ctrl in airborne_controller_data.values())
total_enroute_time = count_records_above_1500ft * (vatsim_polling_interval / 60.0)
airborne_controller_time_percentage = min(100.0, (total_airborne_controller_time / total_enroute_time) * 100)
```

---

## 🚁 **Airborne Detection Logic**

### **Altitude Threshold**
- **Airborne**: Aircraft altitude > 1500ft
- **Ground**: Aircraft altitude ≤ 1500ft

### **Contact Classification**
```python
def _is_airborne_contact(self, match: Dict, flight_altitude_data: List[Dict]) -> bool:
    # Find closest altitude record to contact time
    # Return True if altitude > 1500ft
    return closest_altitude > 1500
```

### **Enroute Time Calculation**
```python
async def _get_total_enroute_time(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime) -> float:
    # Count records where altitude > 1500ft
    # Convert to minutes using VATSIM polling interval
    return enroute_records * (self.vatsim_polling_interval_seconds / 60.0)
```

---

## 📊 **Data Flow**

### **1. Data Collection**
```
Flight Transceivers → ATC Transceivers → Frequency Matching → Proximity Filtering
```

### **2. Contact Processing**
```
Frequency Matches → Altitude Filtering → Time Calculation → Percentage Computation
```

### **3. Result Generation**
```
{
    "controller_callsigns": {...},
    "controller_time_percentage": 45.2,           # Total coverage
    "airborne_controller_time_percentage": 67.8,  # Airborne coverage
    "total_controller_time_minutes": 120,
    "total_flight_records": 180,
    "atc_contacts_detected": 15
}
```

---

## 🔍 **Proximity Detection**

### **Controller-Specific Ranges**

| Controller Type | Proximity Threshold | Use Case |
|-----------------|-------------------|----------|
| **CTR** (Center) | 300nm | Enroute control |
| **APP** (Approach) | 150nm | Terminal area |
| **TWR** (Tower) | 50nm | Airport vicinity |
| **GND** (Ground) | 25nm | Surface operations |

### **Dynamic Proximity**
```python
# Get controller type and proximity range
controller_info = self.controller_type_detector.get_controller_info(controller_callsign)
proximity_range = controller_info["proximity_threshold"]
```

---

## 📈 **Performance Optimizations**

### **Database Queries**
- **Indexed Fields**: `callsign`, `entity_type`, `timestamp`, `altitude`
- **Time Windows**: Limited to 24 hours for ATC data
- **Record Limits**: Maximum 1000 ATC transceiver records per query
- **Efficient JOINs**: Uses EXISTS clauses for flight validation

### **Caching Strategy**
- **Controller Type Detection**: Cached per session
- **Proximity Ranges**: Pre-calculated per controller type
- **Build Arguments**: Docker layer caching for faster rebuilds

---

## 🧪 **Testing**

### **Unit Tests**
- **File**: `tests/test_atc_detection_service_proximity.py`
- **Coverage**: Proximity detection, time calculations, altitude filtering
- **Mock Data**: Simulated transceiver data with known altitudes

### **Integration Tests**
- **File**: `tests/test_atc_detection_service.py`
- **Coverage**: End-to-end ATC detection workflow
- **Database**: Real database queries with test data

---

## 🚀 **Deployment**

### **Docker Build**
```bash
docker-compose build
```

### **Environment Setup**
```bash
# Required environment variables
VATSIM_POLLING_INTERVAL=60
FLIGHT_DETECTION_TIME_WINDOW_SECONDS=180
```

### **Database Migration**
```sql
-- Add new field to existing tables
ALTER TABLE flight_summaries ADD COLUMN IF NOT EXISTS airborne_controller_time_percentage DECIMAL(5,2);

-- Add constraint
ALTER TABLE flight_summaries ADD CONSTRAINT valid_airborne_controller_time 
CHECK (airborne_controller_time_percentage >= 0 AND airborne_controller_time_percentage <= 100);

-- Add index
CREATE INDEX idx_flight_summaries_airborne_controller_time ON flight_summaries(airborne_controller_time_percentage);
```

---

## 📋 **API Response Schema**

### **ATC Detection Response**
```json
{
    "controller_callsigns": {
        "YSSY_APP": {
            "callsign": "YSSY_APP",
            "type": "APP",
            "time_minutes": 45.0,
            "first_contact": "2025-01-27T10:30:00",
            "last_contact": "2025-01-27T11:15:00",
            "contact_count": 45
        }
    },
    "controller_time_percentage": 45.2,
    "airborne_controller_time_percentage": 67.8,
    "total_controller_time_minutes": 120,
    "total_flight_records": 180,
    "atc_contacts_detected": 15
}
```

---

## 🔮 **Future Enhancements**

### **Planned Features**
- **Weather Integration**: Consider weather conditions in proximity calculations
- **Traffic Density**: Adjust proximity based on airspace congestion
- **Historical Analysis**: Trend analysis of ATC coverage patterns
- **Performance Metrics**: Response time and coverage quality metrics

### **Potential Improvements**
- **Machine Learning**: Predictive ATC coverage modeling
- **Real-time Alerts**: Coverage gap notifications
- **Multi-aircraft**: Batch processing for multiple flights
- **Geographic Filtering**: Region-specific ATC analysis

---

## 📚 **Related Documentation**

- **API Reference**: `docs/API_REFERENCE.md`
- **Field Mapping**: `docs/API_FIELD_MAPPING.md`
- **Flight Summary Requirements**: `docs/FLIGHT_SUMMARY_REPORTING_REQUIREMENTS.md`
- **Decision Log**: `docs/DECISION_LOG.md`

---

**📅 Last Updated**: January 2025  
**🔄 Version**: 2.0 (Added airborne coverage metrics)  
**🚀 Production Ready**: Yes  
**🧪 Test Coverage**: Comprehensive  
**📊 Performance**: Optimized for production workloads
