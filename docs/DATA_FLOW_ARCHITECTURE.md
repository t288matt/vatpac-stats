# VATSIM Data Collection System - Data Flow Architecture

## 🎯 Overview

This document provides visual and textual representations of how data flows through the VATSIM Data Collection System, from external APIs to database storage and user consumption.

## 🔄 **Primary Data Flow**

### **Real-Time Data Ingestion Flow**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ VATSIM API  │───▶│ VATSIM      │───▶│ Data        │───▶│ Database    │
│   (v3)      │    │ Service     │    │ Service     │    │ Service     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                           │                   │                   │
                           ▼                   ▼                   ▼
                    ┌─────────────┐    ┌─────────────┐    ┌─────────────┘
                    │ Geographic  │    │ Flight Plan │    │ PostgreSQL  │
                    │ Boundary    │    │ Validation  │    │ Database    │
                    │ Filter      │    │ Filter      │    └─────────────┘
                    └─────────────┘    └─────────────┘
```

### **Data Processing Pipeline**

```
VATSIM API → VATSIM Service → Data Service → Filters → Controller Type Detection → Database Service → PostgreSQL
     │              │              │           │              │              │              │
     ▼              ▼              ▼           ▼              ▼              ▼              ▼
Raw JSON    Parsed Data    Business    Filtered    Proximity    Stored      Persistent
Response    Objects        Logic       Data        Ranges       Records     Storage
```

## 📊 **Detailed Data Flow Breakdown**

### **1. External Data Ingestion**

#### **VATSIM API → VATSIM Service**
- **Input**: HTTP GET requests to VATSIM API v3 endpoints
- **Processing**: JSON parsing, data validation, type conversion
- **Output**: Structured Python objects (Flight, Controller, Transceiver)
- **Frequency**: Every 60 seconds (configurable)
- **Data Volume**: ~1000-2000 records per update

#### **Data Types Ingested**:
- **Flights**: Active flight positions, flight plans, pilot info
- **Controllers**: ATC positions, frequencies, facility info
- **Transceivers**: Radio frequencies, positions, entity linking

### **2. Data Processing & Filtering**

#### **VATSIM Service → Data Service**
- **Input**: Parsed VATSIM data objects
- **Processing**: Business logic, data validation, entity linking
- **Output**: Processed data ready for storage
- **Filters Applied**:
  - Geographic boundary filtering (Australian airspace)
  - Callsign pattern filtering (exclude ATIS, etc.)
  - Flight plan validation (required fields)

#### **Filtering Logic**:
```
Raw Data → Geographic Filter → Callsign Filter → Flight Plan Filter → Controller Type Detection → Storage
   │              │                │                │                │                │
   ▼              ▼                ▼                ▼                ▼                ▼
All Data    Within AU      Valid Callsigns    Complete Flight    Proximity Ranges    Database
            Airspace       (exclude ATIS)     Plans Only        (15nm-1000nm)      Storage
                                    │                │
                                    ▼                ▼
                            Valid Callsigns    Departure + Arrival
                            (exclude ATIS)     Must Be Populated
```

#### **Controller Proximity System**:
- **Ground/Tower Controllers**: 15nm proximity range (local airport operations)
- **Approach Controllers**: 60nm proximity range (terminal area operations)
- **Center Controllers**: 400nm proximity range (enroute operations)
- **FSS Controllers**: 1000nm proximity range (flight service operations)
- **Automatic Detection**: Controller type identified from callsign patterns
- **Dynamic Configuration**: Proximity ranges configurable via environment variables
- **Service Symmetry**: ATCDetectionService and FlightDetectionService use identical logic
- **Comprehensive Testing**: 8 ATCDetectionService tests + enhanced E2E tests with real outcome verification
- **Real Outcomes Verified**: Tests verify actual controller detection, proximity assignment, and live API behavior

### **3. Data Storage & Persistence**

#### **Data Service → Database Service**
- **Input**: Filtered and validated data
- **Processing**: Database session management, transaction handling
- **Output**: Persistent database records
- **Storage Strategy**:
  - **Real-time tables**: flights, controllers, transceivers
  - **Summary tables**: flight_summaries, sector_occupancy
  - **Archive tables**: flights_archive (historical data)

### **4. Data Retrieval & API Response**

#### **Database → API Endpoints**
- **Input**: Database queries and filters
- **Processing**: Data aggregation, formatting, pagination
- **Output**: REST API responses (JSON)
- **Response Types**:
  - Current data (real-time)
  - Historical data (archived)
  - Aggregated data (summaries, analytics)

## 🔄 **Secondary Data Flows**

### **Flight Summary Processing Flow**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Completed   │───▶│ Flight      │───▶│ Summary     │───▶│ Summary     │
│ Flights     │    │ Summary     │    │ Processing  │    │ Tables      │
│ (14h old)   │    │ Service     │    │ Engine      │    │ (Database)  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### **Background Processing Flow**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Scheduled   │───▶│ Background  │───▶│ Database    │
│ Timer       │    │ Tasks       │    │ Updates     │
│ (60 min)    │    │ (Async)     │    │ (Batch)     │
└─────────────┘    └─────────────┘    └─────────────┘
```

## 📈 **Data Volume & Performance**

### **Data Ingestion Rates**
- **Flights**: 500-1500 records per update
- **Controllers**: 50-200 records per update
- **Transceivers**: 200-500 records per update
- **Total**: ~750-2200 records per minute

### **Processing Performance**
- **Geographic Filtering**: <1ms per entity
- **Database Storage**: <10ms per batch
- **API Response**: <50ms average
- **Overall Pipeline**: <100ms end-to-end

### **Storage Growth**
- **Raw Data**: ~50-100MB per day
- **After Filtering**: ~10-20MB per day (80% reduction)
- **After Summarization**: ~2-5MB per day (90% reduction)

## 🔍 **Data Quality Gates**

### **Input Validation**
- **API Response**: HTTP status, JSON structure
- **Data Types**: Field type validation, range checking
- **Required Fields**: Essential field presence validation

### **Business Logic Validation**
- **Geographic Bounds**: Within Australian airspace
- **Flight Plans**: Complete departure/arrival information (both fields must be populated)
- **Callsigns**: Valid pattern, not excluded types
- **Flight Plan Completeness**: Flights without departure or arrival are filtered out at ingestion

### **Storage Validation**
- **Database Constraints**: Foreign keys, unique constraints
- **Data Integrity**: Referential integrity checks
- **Transaction Safety**: ACID compliance

## 🚨 **Error Handling & Recovery**

### **Data Flow Error Points**
1. **API Failures**: Network timeouts, rate limiting
2. **Parsing Errors**: Malformed JSON, unexpected data
3. **Filter Errors**: Geographic calculation failures
4. **Storage Errors**: Database connection, constraint violations

### **Recovery Strategies**
- **Retry Logic**: Exponential backoff for transient failures
- **Fallback Processing**: Continue with partial data if possible
- **Error Logging**: Comprehensive error tracking and alerting
- **Data Recovery**: Manual reprocessing for failed batches

## 📊 **Monitoring & Observability**

### **Data Flow Metrics**
- **Ingestion Rate**: Records per second/minute
- **Processing Latency**: Time through each pipeline stage
- **Filter Efficiency**: Percentage of data filtered out
- **Storage Performance**: Database operation timing

### **Health Checks**
- **Pipeline Status**: Each stage operational status
- **Data Freshness**: Time since last successful update
- **Error Rates**: Failure percentages by stage
- **Performance Trends**: Latency and throughput trends

## 🔮 **Future Data Flow Enhancements**

### **Planned Improvements**
- **Real-time Streaming**: WebSocket-based live data updates
- **Data Caching**: Redis-based performance optimization
- **Batch Processing**: Apache Kafka for high-volume ingestion
- **Data Lake Integration**: Long-term data archival and analytics

### **Scalability Considerations**
- **Horizontal Scaling**: Multiple data processing instances
- **Load Balancing**: Distributed data ingestion
- **Database Sharding**: Partitioned data storage
- **CDN Integration**: Global data distribution

---

**📅 Last Updated**: 2025-08-13  
**🚀 Status**: Current Implementation  
**🔧 Maintainer**: VATSIM Data System Team
