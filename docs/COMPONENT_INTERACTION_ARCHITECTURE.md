# VATSIM Data Collection System - Component Interaction Architecture

## 🎯 Overview

This document provides detailed mapping of how all system components interact, communicate, and depend on each other within the VATSIM Data Collection System.

## 🔗 **Component Interaction Overview**

### **High-Level Component Map**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           External Interfaces                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  VATSIM API v3  │  HTTP Clients  │  Grafana  │  PostgreSQL  │  Logs      │
└─────────────────┼─────────────────┼───────────┼──────────────┼────────────┘
                   │                 │           │              │
                   ▼                 ▼           ▼              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Core Application Layer                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  FastAPI App (main.py)  │  Background Tasks  │  Error Handling  │  Logging  │
└─────────────────────────┼─────────────────────┼──────────────────┼──────────┘
                          │                     │                  │
                          ▼                     ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Service Layer                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ VATSIM │ Data │ Database │ Geographic │ Callsign │ ATC Detection │ Monitoring │
│ Service│Service│ Service  │  Filter    │  Filter  │   Service     │  Service   │
└────────┼──────┼──────────┼────────────┼──────────┼───────────────┼───────────┘
         │      │          │            │          │               │
         ▼      ▼          ▼            ▼          ▼               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Data Layer                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  Models  │  Database  │  Utils  │  Filters  │  Config  │  Error Handling │
└──────────┼────────────┼─────────┼───────────┼──────────┼─────────────────┘
           │            │         │           │          │
           ▼            ▼         ▼           ▼          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Infrastructure Layer                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Docker  │  PostgreSQL  │  Grafana  │  Logs  │  Config Files  │  Volumes   │
└──────────┼──────────────┼───────────┼────────┼────────────────┼────────────┘
```

## 🔄 **Detailed Service Interactions**

### **1. Main Application (main.py) Interactions**

#### **Startup Sequence**
```
main.py → lifespan() → Background Tasks → Service Initialization
   │           │              │                    │
   ▼           ▼              ▼                    ▼
FastAPI    Data Task    VATSIM Service    Database Service
Startup    Creation     Initialize()      Initialize()
```

#### **API Endpoint Interactions**
```
HTTP Request → main.py → Service Layer → Database → Response
     │           │           │            │          │
     ▼           ▼           ▼            ▼          ▼
Client     Route Handler  Data Service  PostgreSQL  JSON Response
```

### **2. Service-to-Service Interactions**

#### **Data Service Dependencies**
```
DataService.initialize()
    │
    ├── VATSIMService.initialize()
    │   └── HTTP client creation
    │   └── Connection pool setup
    │
    ├── GeographicBoundaryFilter.__init__()
    │   └── Load polygon data
    │   └── Initialize Shapely objects
    │
    ├── CallsignPatternFilter.__init__()
    │   └── Load exclusion patterns
    │
    └── ATCDetectionService.__init__()
        └── Initialize detection logic
```

#### **Data Processing Flow**
```
DataService.process_vatsim_data()
    │
    ├── VATSIMService.get_current_data()
    │   └── HTTP GET to VATSIM API
    │   └── JSON parsing and validation
    │
    ├── _process_flights()
    │   ├── GeographicBoundaryFilter.filter_flights()
    │   ├── CallsignPatternFilter.filter_flights()
    │
    ├── _process_controllers()
    │   ├── GeographicBoundaryFilter.filter_controllers()
    │   ├── CallsignPatternFilter.filter_controllers()
    │   └── ControllerTypeDetector.get_controller_info()
    │       └── Automatic controller type detection
    │       └── Dynamic proximity range assignment
    │
    ├── _create_controller_summaries()
    │   ├── FlightDetectionService.detect_controller_flight_interactions()
    │   │   └── ControllerTypeDetector.get_controller_info()
    │   │   └── Dynamic proximity threshold retrieval
    │   │   └── Geographic proximity filtering with controller-specific ranges
    │   └── Aircraft interaction detection using appropriate proximity ranges
    │   └── DatabaseService.store_flights()
    │
    ├── _process_controllers()
    │   ├── GeographicBoundaryFilter.filter_controllers()
    │   ├── CallsignPatternFilter.filter_controllers()
    │   └── DatabaseService.store_controllers()
    │
    └── _process_transceivers()
        ├── GeographicBoundaryFilter.filter_transceivers()
        ├── CallsignPatternFilter.filter_transceivers()
        └── DatabaseService.store_transceivers()
```

### **3. Filter System Interactions**

#### **Geographic Boundary Filter**
```
GeographicBoundaryFilter.filter_entity()
    │
    ├── Load polygon data (if not cached)
    │   └── Read australian_airspace_polygon.json
    │   └── Create Shapely Polygon object
    │
    ├── Extract coordinates from entity
    │   ├── Flight: latitude/longitude
    │   ├── Transceiver: position_lat/position_lon
    │   └── Controller: conservative approach
    │
    └── Point-in-polygon test
        └── Shapely.contains() operation
        └── Return True/False + performance metrics
```

#### **Callsign Pattern Filter**
```
CallsignPatternFilter.filter_entity()
    │
    ├── Load exclusion patterns
    │   └── Read from configuration
    │   └── Compile regex patterns
    │
    ├── Extract callsign from entity
    │   ├── Flight: callsign field
    │   ├── Controller: callsign field
    │   └── Transceiver: callsign field
    │
    └── Pattern matching
        └── Regex test against exclusion patterns
        └── Return True/False (True = keep, False = exclude)
```

### **4. Controller Proximity System Interactions**

#### **Controller Type Detection Flow**
```
ControllerTypeDetector.get_controller_info()
    │
    ├── Callsign pattern analysis
    │   ├── Extract last 3 characters
    │   ├── Pattern matching (_TWR, _APP, _CTR, _FSS, _GND, _DEL)
    │   └── Controller type identification
    │
    ├── Proximity range assignment
    │   ├── Ground/Tower: 15nm (local airport operations)
    │   ├── Approach: 60nm (terminal area operations)
    │   ├── Center: 400nm (enroute operations)
    │   └── FSS: 1000nm (flight service operations)
    │
    └── Return controller info
        ├── Controller type
        ├── Proximity threshold
        └── Detection confidence
```

#### **Service Symmetry & Testing Integration**
```
ATCDetectionService ←→ FlightDetectionService
    │                           │
    ├── ControllerTypeDetector  ├── ControllerTypeDetector
    │   ├── Identical logic     │   ├── Identical logic
    │   ├── Same proximity      │   ├── Same proximity
    │   └── Same results        │   └── Same results
    │                           │
    └── Comprehensive Testing   └── Comprehensive Testing
        ├── 8 proximity tests       ├── Enhanced E2E tests
        ├── Real outcome verification├── Live API testing
        ├── Service symmetry        └── Proximity behavior
        └── Controller accuracy     └── Real data validation
```

#### **Flight Detection Service Integration**
```
FlightDetectionService.detect_controller_flight_interactions()
    │
    ├── Controller type detection
    │   └── ControllerTypeDetector.get_controller_info()
    │   └── Dynamic proximity threshold retrieval
    │
    ├── Geographic proximity filtering
    │   ├── Use controller-specific proximity range
    │   ├── Haversine distance calculation
    │   └── Aircraft within proximity threshold
    │
    ├── Frequency matching
    │   ├── Controller frequency identification
    │   ├── Aircraft frequency matching
    │   └── Time window validation
    │
    └── Aircraft interaction detection
        ├── Proximity + frequency + time validation
        ├── Aircraft count calculation
        └── Interaction summary generation
```

### **5. Comprehensive Testing Architecture Interactions**

#### **Real Outcome Testing Flow**
```
Test Suite → Service Layer → Live System → Real Data → Outcome Verification
    │            │              │            │            │
    ▼            ▼              ▼            ▼            ▼
ATCDetection   Controller    Live API      Real         Verify Actual
Service Tests  TypeDetector  Endpoints     Controller   Proximity
               Proximity     Real Data     Callsigns    Behavior
               Ranges        Real Outputs  Real Types   Real Results
```

#### **Test Coverage & Validation**
```
ATCDetectionService Proximity Tests (8 tests)
    │
    ├── Service Initialization
    │   ├── ControllerTypeDetector integration
    │   ├── Environment variable loading
    │   └── Real service setup verification
    │
    ├── Controller Type Detection
    │   ├── Real callsign pattern matching
    │   ├── Proximity range assignment
    │   ├── Edge case handling
    │   └── Real-world scenario testing
    │
    ├── Service Symmetry Verification
    │   ├── Identical logic comparison
    │   ├── Same proximity ranges
    │   ├── Identical results validation
    │   └── Service behavior consistency
    │
    └── Real Outcome Verification
        ├── Live API endpoint testing
        ├── Real proximity calculations
        ├── Actual controller detection
        └── Production behavior validation
```

### **6. Database Service Interactions**

#### **Database Operations**
```
DatabaseService.store_entity()
    │
    ├── Get database session
    │   └── SessionLocal() or async session
    │   └── Connection pooling
    │
    ├── Data validation
    │   ├── Model instantiation
    │   ├── Constraint checking
    │   └── Type validation
    │
    ├── Transaction handling
    │   ├── session.add(entity)
    │   ├── session.commit()
    │   └── session.close()
    │
    └── Error handling
        ├── Rollback on failure
        ├── Log errors
        └── Return success/failure count
```

## 🔌 **API Layer Interactions**

### **REST API Endpoint Flow**
```
HTTP Request → FastAPI Router → Service Layer → Database → Response
     │              │              │            │          │
     ▼              ▼              ▼            ▼          ▼
Client      Route Handler    Data Service   PostgreSQL   JSON Response
     │              │              │            │          │
     ├── CORS       ├── Validation  ├── Business   ├── Query     ├── Formatting
     ├── Auth       ├── Rate Limit  ├── Logic      ├── Cache     ├── Pagination
     └── Logging    └── Error Handle├── Filtering  ├── Transaction└── Compression
```

### **Background Task Interactions**
```
Background Task → Data Service → VATSIM Service → Database → Logging
      │              │              │            │          │
      ▼              ▼              ▼            ▼          ▼
Scheduler      Process Data    Fetch Data    Store Data   Log Results
      │              │              │            │          │
      ├── Timer      ├── Filtering  ├── HTTP     ├── Models   ├── Success
      ├── Interval   ├── Validation ├── Parsing  ├── Indexes  ├── Errors
      └── Retry      └── Business   └── Caching  └── Constraints└── Metrics
```

## 📊 **Data Flow Between Components**

### **Real-Time Data Pipeline**
```
VATSIM API → VATSIM Service → Data Service → Filters → Database → API Response
     │              │              │           │          │          │
     ▼              ▼              ▼           ▼          ▼          ▼
JSON Data    Parsed Objects   Business    Filtered    Stored      User
Response     (Flight,         Logic       Data        Records     Response
             Controller,      (Validation, (Geographic, (PostgreSQL) (JSON)
             Transceiver)     Filtering)   Callsign)
```

### **Background Processing Pipeline**
```
Scheduler → Data Service → Flight Summary → Database → Archive → Cleanup
    │           │              │              │          │         │
    ▼           ▼              ▼              ▼          ▼         ▼
Timer      Process Old    Generate      Store       Move Old    Remove
Trigger    Flights        Summaries     Results     Data        Old Files
```

## 🔒 **Error Handling & Recovery Interactions**

### **Error Propagation Chain**
```
Service Error → Error Handler → Logging → Monitoring → Alerting → Recovery
      │              │            │          │           │          │
      ▼              ▼            ▼          ▼           ▼          ▼
Exception      Decorator      Logger     Metrics     Grafana    Retry Logic
      │              │            │          │           │          │
      ├── HTTP       ├── Log      ├── Error  ├── Count    ├── Dashboard ├── Exponential
      ├── Database   ├── Context  ├── Level  ├── Latency  ├── Alerts    ├── Backoff
      └── Network    └── Stack    ├── Format ├── Success  └── Notifications└── Circuit Breaker
```

### **Circuit Breaker Pattern**
```
Service Call → Circuit Breaker → Service → Success/Failure → State Update
      │              │              │            │              │
      ▼              ▼              ▼            ▼              ▼
Request      Check State     Execute     Record      Update
             (Open/Closed/   Operation   Result      Circuit State
              Half-Open)     (Timeout)   (Success/   (Open/Closed)
                              (Retry)     Failure)    (Reset Timer)
```

## 📈 **Performance & Monitoring Interactions**

### **Performance Tracking**
```
Service Operation → Performance Monitor → Metrics Collection → Grafana → Alerts
       │                   │                    │              │         │
       ▼                   ▼                    ▼              ▼         ▼
API Call/DB     Timing Start/Stop      Aggregate Data    Dashboard   Threshold
Operation       Performance Counters   (Count, Latency,  (Charts,    (CPU, Memory,
              (Response Time)         Success Rate)     Metrics)    Response Time)
```

### **Health Check Interactions**
```
Health Check → Service Status → Database Check → VATSIM API Check → Response
      │              │              │              │              │
      ▼              ▼              ▼              ▼              │
/health      Service State    Connection Test   API Response    JSON Status
Endpoint     (Initialized,    (Connected,       (Status Code,   (Healthy,
             Operational)     Tables Count)     Response Time)   Degraded,
                                                                    Unhealthy)
```

## 🔄 **Asynchronous Interaction Patterns**

### **Async Service Communication**
```
Main App → Background Task → Data Service → VATSIM Service → Database → Callback
    │            │              │              │              │          │
    ▼            ▼              ▼              ▼              ▼          │
FastAPI     asyncio.Task    async/await    async/await    async/await  Update
Startup     Creation        (Non-blocking) (Non-blocking) (Non-blocking) Status
```

### **Event-Driven Interactions**
```
Data Update → Event Trigger → Background Processing → Database Update → Notification
      │            │                │                  │              │
      ▼            ▼                ▼                  ▼              │
New Flight    Event Bus        Flight Summary     Archive Data    Log Update
Data          (Async Event)    Processing Task    (Batch Update)  (Success/Failure)
```

## 🚀 **Deployment & Infrastructure Interactions**

### **Docker Container Interactions**
```
Docker Compose → Container Startup → Service Initialization → Health Checks → Ready
       │               │                    │                  │            │
       ▼               ▼                    ▼                  ▼            │
docker-compose   Container    Service.initialize()    Health Check    Service
up -d           (PostgreSQL,  (Database, VATSIM,      (Database      Available
                 App,         Filters, Background     Connection,    (Port 8001)
                 Grafana)     Tasks)                  API Response)  (API Ready)
```

### **Configuration Management**
```
Environment → Config Service → Service Configuration → Runtime Settings → Validation
     │              │                │                  │              │
     ▼              ▼                ▼                  ▼              │
.env File    get_config()      Service Config      Apply Settings   Check Values
     │              │                │                  │              │
     ├── Database   ├── Parse        ├── Database URL   ├── Set        ├── Required
     ├── API Keys   ├── Validate     ├── API Timeouts   ├── Defaults   ├── Ranges
     └── Feature    └── Defaults     ├── Filter Config  ├── Overrides  └── Types
        Flags                       ├── Log Levels     ├── Validation
```

---

**📅 Last Updated**: 2025-08-13  
**🚀 Status**: Current Implementation  
**🔧 Maintainer**: VATSIM Data System Team
