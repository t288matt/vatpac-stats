# 🛩️ Flight-Specific Transceiver Interaction Variables Implementation

This document outlines the implementation strategy for implementing dynamic, variable-based measurement for flight-transceiver interactions in the VATSIM data system. This enhancement will make the flight interaction detection system much more realistic by matching real-world flight operations and aircraft capabilities.

## 🎯 **Objective**

Currently, the system uses fixed values for flight-transceiver interactions:
- Fixed time window: 180 seconds (3 minutes)
- Fixed geographic proximity thresholds
- Fixed frequency matching criteria

**Goal**: Implement dynamic, flight-specific variables that adjust interaction detection based on:
- **Aircraft type** (commercial vs. private vs. military)
- **Flight rules** (IFR vs. VFR)
- **Altitude** (low altitude vs. high altitude operations)
- **Flight phase** (departure, enroute, arrival)
- **Aircraft performance** (speed, range, communication capabilities)

## 🚀 **Implementation Strategy**

### **Phase 1: Flight Type Detection Service** ✅ **PLANNED**
- Create `FlightTypeDetector` service
- Implement aircraft type classification
- Configure interaction variables per flight type
- Create comprehensive unit tests

### **Phase 2: Dynamic Interaction Variables** ✅ **PLANNED**
- Enhance `FlightDetectionService` to integrate `FlightTypeDetector`
- Remove fixed interaction thresholds
- Implement dynamic variables per flight type
- Update method signatures and SQL queries

### **Phase 3: DataService Integration** ✅ **PLANNED**
- Update `DataService` to pass flight information to interaction detection
- Integrate flight-specific variables in data processing pipeline
- Add enhanced logging for flight type detection and interaction variables

### **Phase 4: Environment Configuration** ✅ **PLANNED**
- Add flight-specific interaction environment variables to `docker-compose.yml`
- Configure interaction variables via Docker environment
- Update `FlightTypeDetector` to use environment variables

### **Phase 5: Testing and Validation** ✅ **PLANNED**
- Update integration tests for flight-specific interaction behavior
- Test end-to-end flight interaction detection
- Validate complete workflow with dynamic variables

## 🎮 **Flight Types and Interaction Variables**

### **Commercial Aircraft (Commercial Airlines)**
- **Time Window**: 300 seconds (5 minutes) - longer range communications
- **Geographic Proximity**: 50nm - commercial aircraft have longer range
- **Frequency Sensitivity**: High - precise frequency matching
- **Altitude Range**: 20,000-45,000 feet

### **Private Aircraft (General Aviation)**
- **Time Window**: 120 seconds (2 minutes) - shorter range communications
- **Geographic Proximity**: 25nm - private aircraft have shorter range
- **Frequency Sensitivity**: Medium - flexible frequency matching
- **Altitude Range**: 3,000-25,000 feet

### **Military Aircraft**
- **Time Window**: 240 seconds (4 minutes) - military communication protocols
- **Geographic Proximity**: 75nm - military aircraft have extended range
- **Frequency Sensitivity**: Very High - secure frequency matching
- **Altitude Range**: 1,000-60,000 feet

### **Cargo Aircraft**
- **Time Window**: 360 seconds (6 minutes) - extended range operations
- **Geographic Proximity**: 60nm - cargo aircraft have long range
- **Frequency Sensitivity**: High - precise frequency matching
- **Altitude Range**: 25,000-45,000 feet

### **Training Aircraft**
- **Time Window**: 90 seconds (1.5 minutes) - local training operations
- **Geographic Proximity**: 15nm - local training area
- **Frequency Sensitivity**: Low - flexible frequency matching
- **Altitude Range**: 1,000-15,000 feet

## 🔧 **Technical Implementation**

### **Flight Type Detection Logic**
```python
class FlightTypeDetector:
    def get_flight_info(self, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze flight data and determine flight type and interaction variables.
        
        Args:
            flight_data: Flight data from VATSIM API
            
        Returns:
            Dict containing flight type and interaction variables
        """
        # Aircraft type analysis
        aircraft_type = flight_data.get("aircraft_short", "")
        aircraft_faa = flight_data.get("aircraft_faa", "")
        
        # Flight rules analysis
        flight_rules = flight_data.get("flight_rules", "")
        
        # Altitude analysis
        altitude = flight_data.get("altitude", 0)
        
        # Determine flight type
        flight_type = self._classify_flight_type(aircraft_type, aircraft_faa, flight_rules, altitude)
        
        # Get interaction variables for flight type
        interaction_vars = self._get_interaction_variables(flight_type)
        
        return {
            "flight_type": flight_type,
            "interaction_variables": interaction_vars,
            "detection_confidence": self._calculate_confidence(flight_data)
        }
```

### **Interaction Variables Configuration**
```python
class FlightTypeDetector:
    def __init__(self):
        # Load from environment variables
        self.interaction_variables = {
            "Commercial": {
                "time_window_seconds": int(os.getenv("FLIGHT_INTERACTION_COMMERCIAL_TIME_WINDOW", "300")),
                "proximity_threshold_nm": float(os.getenv("FLIGHT_INTERACTION_COMMERCIAL_PROXIMITY_NM", "50")),
                "frequency_sensitivity": "high",
                "altitude_range_min": 20000,
                "altitude_range_max": 45000
            },
            "Private": {
                "time_window_seconds": int(os.getenv("FLIGHT_INTERACTION_PRIVATE_TIME_WINDOW", "120")),
                "proximity_threshold_nm": float(os.getenv("FLIGHT_INTERACTION_PRIVATE_PROXIMITY_NM", "25")),
                "frequency_sensitivity": "medium",
                "altitude_range_min": 3000,
                "altitude_range_max": 25000
            },
            "Military": {
                "time_window_seconds": int(os.getenv("FLIGHT_INTERACTION_MILITARY_TIME_WINDOW", "240")),
                "proximity_threshold_nm": float(os.getenv("FLIGHT_INTERACTION_MILITARY_PROXIMITY_NM", "75")),
                "frequency_sensitivity": "very_high",
                "altitude_range_min": 1000,
                "altitude_range_max": 60000
            },
            "Cargo": {
                "time_window_seconds": int(os.getenv("FLIGHT_INTERACTION_CARGO_TIME_WINDOW", "360")),
                "proximity_threshold_nm": float(os.getenv("FLIGHT_INTERACTION_CARGO_PROXIMITY_NM", "60")),
                "frequency_sensitivity": "high",
                "altitude_range_min": 25000,
                "altitude_range_max": 45000
            },
            "Training": {
                "time_window_seconds": int(os.getenv("FLIGHT_INTERACTION_TRAINING_TIME_WINDOW", "90")),
                "proximity_threshold_nm": float(os.getenv("FLIGHT_INTERACTION_TRAINING_PROXIMITY_NM", "15")),
                "frequency_sensitivity": "low",
                "altitude_range_min": 1000,
                "altitude_range_max": 15000
            }
        }
```

### **Environment Variables Configuration**
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

## 📊 **Database Impact**

### **New Fields in Flight Model**
- `flight_type`: Classification of flight type (Commercial, Private, Military, etc.)
- `interaction_time_window`: Dynamic time window for transceiver interactions
- `interaction_proximity_threshold`: Dynamic proximity threshold for interactions
- `interaction_frequency_sensitivity`: Frequency matching sensitivity level

### **Enhanced Transceiver Interaction Tracking**
- Flight-specific interaction variables stored with each interaction
- Performance metrics per flight type
- Interaction quality scoring based on flight type requirements

## 🧪 **Testing Strategy**

### **Unit Tests**
- Flight type detection accuracy
- Interaction variable assignment
- Edge cases and error handling

### **Integration Tests**
- FlightDetectionService with dynamic variables
- DataService integration
- End-to-end interaction detection

### **Performance Tests**
- Dynamic variable performance impact
- Memory usage with flight type detection
- Database query optimization

## 📈 **Expected Benefits**

1. **Realistic Flight Operations**: Different aircraft types behave differently in real-world operations
2. **Improved Accuracy**: Flight-specific variables lead to more accurate interaction detection
3. **Performance Optimization**: Smaller aircraft get faster queries due to smaller search radius
4. **Flexible Configuration**: Easy adjustment of interaction parameters via environment variables
5. **Better Analytics**: Flight type-specific interaction metrics and performance analysis

## 🔄 **Migration Strategy**

1. **Backward Compatibility**: Maintain existing fixed values as fallbacks
2. **Gradual Rollout**: Enable flight-specific variables per flight type
3. **Performance Monitoring**: Track impact on system performance
4. **User Feedback**: Collect feedback on interaction accuracy improvements

## 📋 **Implementation Checklist**

- [ ] Create `FlightTypeDetector` service
- [ ] Implement aircraft type classification logic
- [ ] Configure interaction variables for each flight type
- [ ] Update `FlightDetectionService` to use dynamic variables
- [ ] Integrate with `DataService`
- [ ] Add environment variable configuration
- [ ] Create comprehensive test suite
- [ ] Update documentation
- [ ] Performance testing and optimization
- [ ] Production deployment

## 🎯 **Next Steps**

1. **Phase 1**: Implement `FlightTypeDetector` service with basic classification
2. **Phase 2**: Integrate with existing flight detection system
3. **Phase 3**: Add environment variable configuration
4. **Phase 4**: Comprehensive testing and validation
5. **Phase 5**: Production deployment and monitoring

This implementation will significantly enhance the realism and accuracy of flight-transceiver interaction detection in the VATSIM data system.
