# Frequency Matching System Documentation

## Overview

The Frequency Matching System detects when pilots and ATC controllers are on the same frequency, enabling real-time analysis of communication patterns and frequency utilization across the VATSIM network.

## 🎯 **Purpose**

This system answers the question: **"When are pilots and ATC on the same frequency?"** by:

1. **Real-time Detection**: Continuously monitors transceiver data to find frequency matches
2. **Communication Analysis**: Analyzes patterns in pilot-controller communications
3. **Frequency Utilization**: Tracks which frequencies are most active
4. **Geographic Analysis**: Maps communication patterns by location
5. **Historical Tracking**: Stores frequency matches for trend analysis

## 🏗️ **System Architecture**

### **Core Components**

1. **FrequencyMatchingService** (`app/services/frequency_matching_service.py`)
   - Real-time frequency matching detection
   - Communication pattern analysis
   - Geographic distance calculations
   - Confidence scoring for matches

2. **Database Model** (`app/models.py` - `FrequencyMatch`)
   - Stores frequency matching events
   - Historical data persistence
   - Optimized indexes for queries

3. **API Endpoints** (`app/main.py`)
   - Real-time frequency match queries
   - Historical data retrieval
   - Statistical analysis endpoints

### **Data Flow**

```
VATSIM API → Transceiver Data → Frequency Matching Service → Database Storage → API Endpoints
```

## 🔍 **How It Works**

### **1. Frequency Detection Process**

The system analyzes transceiver data from VATSIM API to find frequency matches:

```python
# Get transceiver data
pilot_transceivers = [t for t in transceivers if t.entity_type == 'flight']
controller_transceivers = [t for t in transceivers if t.entity_type == 'atc']

# Find frequency matches
for pilot_tx in pilot_transceivers:
    for controller_tx in controller_transceivers:
        if abs(pilot_tx.frequency - controller_tx.frequency) <= 100:  # 100Hz tolerance
            # Create frequency match
```

### **2. Match Validation**

Each potential match is validated using multiple criteria:

- **Frequency Tolerance**: ±100Hz tolerance for frequency matching
- **Distance Calculation**: Haversine formula for geographic distance
- **Communication Type**: Determined by frequency range
- **Confidence Scoring**: Based on data quality and distance

### **3. Communication Type Classification**

Frequencies are classified by communication type:

| Frequency Range (Hz) | Communication Type | Description |
|---------------------|-------------------|-------------|
| 118,000,000 - 121,000,000 | `approach` | Approach control frequencies |
| 121,000,000 - 123,000,000 | `departure` | Departure control frequencies |
| 123,000,000 - 125,000,000 | `tower` | Tower control frequencies |
| 125,000,000 - 127,000,000 | `ground` | Ground control frequencies |
| 127,000,000 - 136,000,000 | `enroute` | Enroute control frequencies |
| 20,000,000 - 30,000,000 | `hf_enroute` | HF enroute frequencies |
| Other | `unknown` | Unknown frequency ranges |

## 📊 **API Endpoints**

### **Real-time Frequency Matching**

#### **Get Current Frequency Matches**
```http
GET /api/frequency-matching/matches
```

**Response:**
```json
{
  "status": "success",
  "matches": [
    {
      "pilot_callsign": "ABC123",
      "controller_callsign": "YBBN_APP",
      "frequency": 120500000,
      "pilot_lat": -27.3842,
      "pilot_lon": 153.1234,
      "controller_lat": -27.3842,
      "controller_lon": 153.1234,
      "distance_nm": 5.2,
      "match_timestamp": "2025-01-27T10:30:00Z",
      "duration_seconds": 180,
      "is_active": true,
      "match_confidence": 0.95,
      "communication_type": "approach"
    }
  ],
  "total_matches": 1,
  "timestamp": "2025-01-27T10:30:00Z"
}
```

#### **Get Frequency Match Summary**
```http
GET /api/frequency-matching/summary
```

**Response:**
```json
{
  "status": "success",
  "summary": {
    "total_matches": 25,
    "active_matches": 8,
    "unique_pilots": 15,
    "unique_controllers": 5,
    "unique_frequencies": 3,
    "avg_match_duration": 245.6,
    "most_common_frequency": 120500000,
    "busiest_controller": "YBBN_APP",
    "busiest_pilot": "ABC123",
    "communication_patterns": {
      "approach": 12,
      "tower": 8,
      "ground": 5
    },
    "geographic_distribution": {
      "local": 15,
      "regional": 8,
      "long_range": 2
    }
  },
  "timestamp": "2025-01-27T10:30:00Z"
}
```

### **Historical Data**

#### **Get Historical Frequency Matches**
```http
GET /api/frequency-matching/history?pilot_callsign=ABC123&hours=24
```

**Parameters:**
- `pilot_callsign` (optional): Filter by pilot callsign
- `controller_callsign` (optional): Filter by controller callsign
- `frequency` (optional): Filter by frequency in Hz
- `hours` (default: 24): Number of hours to look back

#### **Get Frequency Matching Statistics**
```http
GET /api/frequency-matching/statistics?hours=24
```

**Response:**
```json
{
  "status": "success",
  "statistics": {
    "total_matches": 150,
    "active_matches": 8,
    "unique_pilots": 45,
    "unique_controllers": 12,
    "unique_frequencies": 8,
    "avg_duration": 320.5,
    "most_common_frequency": 120500000,
    "busiest_controller": "YBBN_APP",
    "busiest_pilot": "ABC123",
    "communication_patterns": {
      "approach": 60,
      "tower": 40,
      "ground": 30,
      "enroute": 20
    },
    "geographic_distribution": {
      "local": 90,
      "regional": 45,
      "long_range": 15
    },
    "frequency_distribution": {
      "120MHz": 60,
      "121MHz": 40,
      "122MHz": 30,
      "123MHz": 20
    },
    "hourly_distribution": {
      "10": 15,
      "11": 20,
      "12": 25,
      "13": 30
    }
  },
  "hours_analyzed": 24,
  "timestamp": "2025-01-27T10:30:00Z"
}
```

### **Specific Queries**

#### **Get Matches for Specific Pilot**
```http
GET /api/frequency-matching/pilot/{callsign}
```

#### **Get Matches for Specific Controller**
```http
GET /api/frequency-matching/controller/{callsign}
```

#### **Get Matches for Specific Frequency**
```http
GET /api/frequency-matching/frequency/{frequency_hz}
```

#### **Get Communication Patterns**
```http
GET /api/frequency-matching/patterns?frequency=120500000
```

#### **Get Service Health**
```http
GET /api/frequency-matching/health
```

## 🗄️ **Database Schema**

### **FrequencyMatch Table**

```sql
CREATE TABLE frequency_matches (
    id SERIAL PRIMARY KEY,
    pilot_callsign VARCHAR(50) NOT NULL,
    controller_callsign VARCHAR(50) NOT NULL,
    frequency INTEGER NOT NULL,
    pilot_lat FLOAT,
    pilot_lon FLOAT,
    controller_lat FLOAT,
    controller_lon FLOAT,
    distance_nm FLOAT,
    match_timestamp TIMESTAMP NOT NULL,
    duration_seconds INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    match_confidence FLOAT DEFAULT 1.0,
    communication_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### **Indexes for Performance**

- `idx_frequency_matches_pilot_callsign`: Fast pilot lookups
- `idx_frequency_matches_controller_callsign`: Fast controller lookups
- `idx_frequency_matches_frequency`: Fast frequency queries
- `idx_frequency_matches_match_timestamp`: Time-based queries
- `idx_frequency_matches_is_active`: Active match filtering
- `idx_frequency_matches_communication_type`: Communication type filtering
- `idx_frequency_matches_distance`: Distance-based queries

## ⚙️ **Configuration**

### **Service Configuration**

```python
# Frequency matching configuration
self.max_distance_nm = 100.0  # Maximum distance for meaningful match
self.min_match_duration_seconds = 30  # Minimum duration to consider
self.frequency_tolerance_hz = 100  # Frequency matching tolerance
self.update_interval_seconds = 10  # Update frequency
```

### **Environment Variables**

```yaml
# Frequency Matching Configuration
FREQUENCY_MATCHING_ENABLED: "true"
FREQUENCY_MATCHING_MAX_DISTANCE_NM: 100.0
FREQUENCY_MATCHING_TOLERANCE_HZ: 100
FREQUENCY_MATCHING_MIN_DURATION_SECONDS: 30
FREQUENCY_MATCHING_UPDATE_INTERVAL_SECONDS: 10
```

## 📈 **Use Cases**

### **1. Real-time Communication Monitoring**

**Use Case**: Monitor which pilots are currently communicating with which controllers

```bash
curl "http://localhost:8001/api/frequency-matching/matches"
```

**Benefits:**
- Real-time visibility into pilot-controller communications
- Identify busy controllers and frequencies
- Monitor communication patterns

### **2. Historical Analysis**

**Use Case**: Analyze communication patterns over time

```bash
curl "http://localhost:8001/api/frequency-matching/statistics?hours=168"
```

**Benefits:**
- Identify peak communication hours
- Analyze frequency utilization patterns
- Track controller workload trends

### **3. Specific Pilot/Controller Tracking**

**Use Case**: Track communication history for specific pilots or controllers

```bash
curl "http://localhost:8001/api/frequency-matching/pilot/ABC123"
curl "http://localhost:8001/api/frequency-matching/controller/YBBN_APP"
```

**Benefits:**
- Monitor individual pilot communication patterns
- Track controller workload and frequency usage
- Analyze communication efficiency

### **4. Frequency Utilization Analysis**

**Use Case**: Analyze which frequencies are most active

```bash
curl "http://localhost:8001/api/frequency-matching/frequency/120500000"
```

**Benefits:**
- Identify congested frequencies
- Plan frequency allocation
- Optimize controller workload distribution

## 🔧 **Implementation Details**

### **Frequency Matching Algorithm**

1. **Data Collection**: Fetch transceiver data from VATSIM API
2. **Entity Separation**: Separate pilots and controllers
3. **Frequency Comparison**: Compare frequencies with tolerance
4. **Distance Calculation**: Calculate geographic distance
5. **Validation**: Apply distance and confidence filters
6. **Classification**: Determine communication type
7. **Storage**: Store matches in database

### **Confidence Scoring**

Confidence scores (0.0 to 1.0) are calculated based on:

- **Position Data**: Higher confidence with position data
- **Distance**: Lower confidence for distant communications
- **Frequency Tolerance**: Lower confidence for high tolerance matches
- **Data Quality**: Higher confidence for recent data

### **Performance Optimizations**

- **Indexed Queries**: Optimized database indexes
- **Caching**: In-memory cache for active matches
- **Batch Processing**: Efficient database operations
- **Tolerance Filtering**: Early filtering of non-matches

## 🚀 **Getting Started**

### **1. Enable Frequency Matching**

The frequency matching system is enabled by default. To verify:

```bash
curl "http://localhost:8001/api/frequency-matching/health"
```

### **2. Run Database Migration**

Apply the frequency matches table migration:

```bash
docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f /docker-entrypoint-initdb.d/008_add_frequency_matches_table.sql
```

### **3. Test the System**

```bash
# Get current frequency matches
curl "http://localhost:8001/api/frequency-matching/matches"

# Get summary statistics
curl "http://localhost:8001/api/frequency-matching/summary"

# Get historical data
curl "http://localhost:8001/api/frequency-matching/history?hours=1"
```

## 📊 **Monitoring and Analytics**

### **Key Metrics**

- **Active Matches**: Number of current frequency matches
- **Match Duration**: Average duration of frequency matches
- **Communication Types**: Distribution by communication type
- **Geographic Distribution**: Local vs regional vs long-range
- **Frequency Utilization**: Most active frequencies
- **Controller Workload**: Busiest controllers

### **Health Monitoring**

```bash
curl "http://localhost:8001/api/frequency-matching/health"
```

**Response:**
```json
{
  "status": "success",
  "health": {
    "status": "healthy",
    "active_matches": 8,
    "total_matches_detected": 150,
    "last_update_seconds_ago": 5,
    "cache_size": 8,
    "history_size": 142
  },
  "timestamp": "2025-01-27T10:30:00Z"
}
```

## 🔮 **Future Enhancements**

### **Planned Features**

1. **Real-time Alerts**: Notifications for specific frequency events
2. **Advanced Analytics**: Machine learning for pattern prediction
3. **Grafana Integration**: Dashboard for frequency matching visualization
4. **API Rate Limiting**: Protect against excessive API usage
5. **WebSocket Support**: Real-time frequency match streaming

### **Potential Improvements**

- **Audio Analysis**: Integration with voice communication data
- **Predictive Modeling**: Predict frequency congestion
- **Geographic Clustering**: Group communications by region
- **Performance Optimization**: Further query optimization
- **Mobile Support**: Mobile-friendly API responses

## 📝 **Conclusion**

The Frequency Matching System provides comprehensive real-time and historical analysis of pilot-controller communications on VATSIM. It enables:

- **Real-time monitoring** of frequency matches
- **Historical analysis** of communication patterns
- **Statistical insights** into frequency utilization
- **Geographic analysis** of communication distribution
- **Performance tracking** of controllers and frequencies

This system answers the core question "When are pilots and ATC on the same frequency?" with detailed, actionable data that can be used for network analysis, controller training, and operational planning.
