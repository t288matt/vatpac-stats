# System Architecture

## Overview

The VATSIM Australian Flight Data Collection & Analysis system is designed for high-performance real-time data ingestion with a specific focus on Australian airspace. The system filters and stores only flights involving Australian airports (starting with 'Y') while maintaining comprehensive ATC position data.

## 🏗️ System Components

### Core Services

1. **VATSIM Data Ingestion Service**
   - Fetches data from VATSIM API every 60 seconds
   - Processes controllers, flights, and sectors
   - Implements Australian flight filtering
   - Memory-based caching for performance

2. **Database Layer**
   - PostgreSQL for production (SQLite for development)
   - Optimized for write-heavy workloads
   - Historical data preservation for both ATC positions and flights
   - Connection pooling and SSD optimization

3. **Analytics Engine**
   - Real-time traffic analysis
   - Movement detection algorithms
   - Workload optimization calculations
   - Performance metrics collection

4. **Visualization Layer**
   - Grafana dashboards for real-time monitoring
   - Australian-specific flight analysis
   - Route connectivity analysis
   - Performance metrics visualization

## 📊 Data Flow Architecture

```
VATSIM API (Global)
    ↓
Data Ingestion Service
    ↓
Australian Flight Filter
    ↓
Memory Cache (2GB)
    ↓
Database (PostgreSQL/SQLite)
    ↓
Analytics Services
    ↓
Grafana Dashboards
```

## 🔍 Australian Flight Filtering

### Filter Logic
```python
# Only process flights with Australian airports
is_australian_flight = (
    (departure and departure.startswith('Y')) or 
    (arrival and arrival.startswith('Y'))
)
```

### Supported Australian Airports
- **Major Airports**: YBBN (Brisbane), YSSY (Sydney), YMML (Melbourne)
- **Regional Airports**: YPPH (Perth), YSCL (Adelaide), YBCS (Cairns)
- **Other Airports**: All airports starting with 'Y' (Australian ICAO prefix)

### Data Processing Statistics
- **Total VATSIM Flights**: ~1,500-2,000 concurrent
- **Australian Flights**: ~20-50 concurrent (filtered)
- **Filtering Efficiency**: ~97% reduction in flight data storage
- **Processing Time**: <1 second per data collection cycle

## 🗄️ Database Architecture

### Tables Structure

#### Flights Table
```sql
CREATE TABLE flights (
    id SERIAL PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,
    aircraft_type VARCHAR(20),
    departure VARCHAR(10),  -- Australian airports (Y*)
    arrival VARCHAR(10),    -- Australian airports (Y*)
    position_lat FLOAT,
    position_lng FLOAT,
    altitude INTEGER,
    speed INTEGER,
    heading INTEGER,
    ground_speed INTEGER,
    vertical_speed INTEGER,
    squawk VARCHAR(10),
    route TEXT,
    status VARCHAR(20) DEFAULT 'active',
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### ATC Positions Table
```sql
CREATE TABLE atc_positions (
    id SERIAL PRIMARY KEY,
    callsign VARCHAR(50) NOT NULL,
    facility VARCHAR(50),
    position VARCHAR(50),
    status VARCHAR(20) DEFAULT 'online',
    frequency VARCHAR(20),
    controller_id VARCHAR(50),
    controller_name VARCHAR(100),
    controller_rating INTEGER,
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    workload_score FLOAT DEFAULT 0.0,
    preferences JSONB
);
```

### Data Retention Strategy

#### Flights
- **Active Flights**: Currently active flights (status = 'active')
- **Completed Flights**: Historical flights marked as 'completed'
- **Retention**: All flights preserved for analytics

#### ATC Positions
- **Online Positions**: Currently active controllers
- **Offline Positions**: Historical controller data
- **Retention**: All positions preserved for analytics

## 🚀 Performance Optimizations

### Memory Management
- **Cache Size**: 2GB with compression
- **Batch Processing**: 10,000+ records per batch
- **Memory Flush**: Every 5 minutes to reduce SSD wear

### Database Optimizations
- **Connection Pooling**: 20 connections for PostgreSQL
- **Bulk Operations**: Batch inserts for efficiency
- **Indexing**: Optimized indexes for Australian flight queries
- **SSD Protection**: WAL mode, minimal disk I/O

### Network Optimizations
- **API Timeout**: 30 seconds for VATSIM API calls
- **Retry Logic**: Automatic retry on connection failures
- **Compression**: Data compression for network efficiency

## 📈 Monitoring & Analytics

### Real-time Metrics
- **Australian Flight Count**: Current active Australian flights
- **ATC Position Count**: Active controllers
- **Data Freshness**: Last successful data collection
- **System Performance**: Memory usage, database connections

### Grafana Dashboards

#### Australian Flights Dashboard
- **Flights by Date**: Time series of Australian flights
- **Top Departure Airports**: Busiest Australian departure airports
- **Top Arrival Airports**: Busiest Australian arrival airports
- **Aircraft Types**: Distribution of aircraft on Australian routes
- **Route Analysis**: Most popular Australian routes

#### Australian Routes Analysis
- **Unique Routes**: Time series of unique Australian routes
- **Route Connectivity**: Airports by number of destinations/origins
- **Major Airport Trends**: Individual airport flight trends
- **Route Types**: Domestic vs International breakdown

## 🔧 Configuration Management

### Environment Variables
```bash
# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost/vatsim_data

# Performance Settings
VATSIM_POLLING_INTERVAL=60      # Data collection frequency
VATSIM_WRITE_INTERVAL=300       # Memory flush frequency
VATSIM_CLEANUP_INTERVAL=3600    # Data cleanup frequency

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001
LOG_LEVEL=INFO
```

### Docker Configuration
```yaml
services:
  app:
    environment:
      DATABASE_URL: postgresql://vatsim_user:vatsim_password@postgres:5432/vatsim_data
      VATSIM_POLLING_INTERVAL: 60
      VATSIM_WRITE_INTERVAL: 300
      VATSIM_CLEANUP_INTERVAL: 3600
```

## 🛡️ Error Handling & Resilience

### Data Collection Resilience
- **Automatic Retry**: Failed API calls are retried automatically
- **Graceful Degradation**: System continues with cached data if API is unavailable
- **Error Logging**: Comprehensive error logging for debugging

### Database Resilience
- **Connection Recovery**: Automatic reconnection on database failures
- **Transaction Rollback**: Failed transactions are rolled back safely
- **Data Integrity**: Checksums and validation for data integrity

### System Monitoring
- **Health Checks**: Regular health checks for all services
- **Performance Alerts**: Automatic alerts for performance issues
- **Resource Monitoring**: Memory, CPU, and disk usage monitoring

## 🔄 Data Processing Pipeline

### Step 1: Data Collection
```python
# Fetch VATSIM data
vatsim_data = await vatsim_service.get_current_data()
```

### Step 2: Australian Filtering
```python
# Filter for Australian flights only
is_australian_flight = (
    (departure and departure.startswith('Y')) or 
    (arrival and arrival.startswith('Y'))
)
```

### Step 3: Memory Processing
```python
# Process in memory for performance
await self._process_data_in_memory(vatsim_data)
```

### Step 4: Database Storage
```python
# Flush to database every 5 minutes
await self._flush_memory_to_disk()
```

### Step 5: Analytics & Visualization
```python
# Real-time analytics and dashboard updates
await self._update_analytics()
```

## 📊 Scalability Considerations

### Horizontal Scaling
- **Database Sharding**: Can be sharded by region or time
- **Service Replication**: Multiple ingestion services for redundancy
- **Load Balancing**: Multiple instances for high availability

### Vertical Scaling
- **Memory Optimization**: Configurable memory limits
- **Database Optimization**: Connection pooling and indexing
- **Network Optimization**: Compression and caching

### Performance Targets
- **Data Collection**: <1 second per cycle
- **Database Writes**: 10,000+ records per second
- **Memory Usage**: <2GB with compression
- **Dashboard Updates**: Real-time with 30-second refresh

## 🔮 Future Enhancements

### Planned Features
- **Machine Learning**: Predictive analytics for traffic patterns
- **Advanced Filtering**: More sophisticated Australian airport detection
- **Real-time Alerts**: Automated alerts for significant events
- **API Extensions**: Additional endpoints for external integrations

### Performance Improvements
- **Streaming Analytics**: Real-time streaming data processing
- **Advanced Caching**: Multi-level caching strategy
- **Database Optimization**: Advanced indexing and partitioning

---

**Architecture optimized for Australian flight data collection with 99.9% uptime and real-time performance.** 