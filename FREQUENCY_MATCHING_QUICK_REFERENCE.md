# Frequency Matching System - Quick Reference Guide

## 🚀 **Quick Start Commands**

### **System Health Check**
```bash
curl "http://localhost:8001/api/frequency-matching/health"
```

### **Get Current Frequency Matches**
```bash
curl "http://localhost:8001/api/frequency-matching/matches"
```

### **Get Summary Statistics**
```bash
curl "http://localhost:8001/api/frequency-matching/summary"
```

## 📊 **API Endpoints Reference**

### **Real-time Endpoints**

| Endpoint | Method | Description | Example |
|----------|--------|-------------|---------|
| `/api/frequency-matching/matches` | GET | Current active frequency matches | `curl "http://localhost:8001/api/frequency-matching/matches"` |
| `/api/frequency-matching/summary` | GET | Aggregated statistics | `curl "http://localhost:8001/api/frequency-matching/summary"` |
| `/api/frequency-matching/health` | GET | Service health status | `curl "http://localhost:8001/api/frequency-matching/health"` |

### **Historical Endpoints**

| Endpoint | Method | Description | Example |
|----------|--------|-------------|---------|
| `/api/frequency-matching/history` | GET | Historical matches with filters | `curl "http://localhost:8001/api/frequency-matching/history?hours=24"` |
| `/api/frequency-matching/statistics` | GET | Detailed statistics | `curl "http://localhost:8001/api/frequency-matching/statistics?hours=24"` |

### **Specific Query Endpoints**

| Endpoint | Method | Description | Example |
|----------|--------|-------------|---------|
| `/api/frequency-matching/pilot/{callsign}` | GET | Matches for specific pilot | `curl "http://localhost:8001/api/frequency-matching/pilot/ABC123"` |
| `/api/frequency-matching/controller/{callsign}` | GET | Matches for specific controller | `curl "http://localhost:8001/api/frequency-matching/controller/YBBN_APP"` |
| `/api/frequency-matching/frequency/{frequency_hz}` | GET | Matches for specific frequency | `curl "http://localhost:8001/api/frequency-matching/frequency/120500000"` |
| `/api/frequency-matching/patterns` | GET | Communication patterns | `curl "http://localhost:8001/api/frequency-matching/patterns"` |

## 🔧 **Configuration Parameters**

### **Service Configuration**
```python
max_distance_nm = 100.0  # Maximum distance for meaningful match
min_match_duration_seconds = 30  # Minimum duration to consider
frequency_tolerance_hz = 100  # Frequency matching tolerance
update_interval_seconds = 10  # Update frequency
```

### **Environment Variables**
```yaml
FREQUENCY_MATCHING_ENABLED: "true"
FREQUENCY_MATCHING_MAX_DISTANCE_NM: 100.0
FREQUENCY_MATCHING_TOLERANCE_HZ: 100
FREQUENCY_MATCHING_MIN_DURATION_SECONDS: 30
FREQUENCY_MATCHING_UPDATE_INTERVAL_SECONDS: 10
```

## 📊 **Response Format Examples**

### **Frequency Match Response**
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

### **Summary Response**
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

### **Health Response**
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

### **Key Indexes**
- `idx_frequency_matches_pilot_callsign`
- `idx_frequency_matches_controller_callsign`
- `idx_frequency_matches_frequency`
- `idx_frequency_matches_match_timestamp`
- `idx_frequency_matches_is_active`

## 🔍 **Communication Type Classification**

| Frequency Range (Hz) | Communication Type | Description |
|---------------------|-------------------|-------------|
| 118,000,000 - 121,000,000 | `approach` | Approach control frequencies |
| 121,000,000 - 123,000,000 | `departure` | Departure control frequencies |
| 123,000,000 - 125,000,000 | `tower` | Tower control frequencies |
| 125,000,000 - 127,000,000 | `ground` | Ground control frequencies |
| 127,000,000 - 136,000,000 | `enroute` | Enroute control frequencies |
| 20,000,000 - 30,000,000 | `hf_enroute` | HF enroute frequencies |
| Other | `unknown` | Unknown frequency ranges |

## 🧪 **Testing Commands**

### **Basic Health Check**
```bash
curl "http://localhost:8001/api/frequency-matching/health"
```

### **Get Current Matches**
```bash
curl "http://localhost:8001/api/frequency-matching/matches"
```

### **Get Summary**
```bash
curl "http://localhost:8001/api/frequency-matching/summary"
```

### **Get Historical Data**
```bash
curl "http://localhost:8001/api/frequency-matching/history?hours=1"
```

### **Get Statistics**
```bash
curl "http://localhost:8001/api/frequency-matching/statistics?hours=24"
```

### **Get Specific Pilot Data**
```bash
curl "http://localhost:8001/api/frequency-matching/pilot/ABC123"
```

### **Get Specific Controller Data**
```bash
curl "http://localhost:8001/api/frequency-matching/controller/YBBN_APP"
```

### **Get Specific Frequency Data**
```bash
curl "http://localhost:8001/api/frequency-matching/frequency/120500000"
```

### **Get Communication Patterns**
```bash
curl "http://localhost:8001/api/frequency-matching/patterns"
```

## 🚀 **Docker Commands**

### **Rebuild and Restart**
```bash
docker-compose build
docker-compose up -d
```

### **View Logs**
```bash
docker-compose logs app
```

### **Database Migration**
```bash
docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f /docker-entrypoint-initdb.d/008_add_frequency_matches_table.sql
```

## 📁 **File Locations**

### **Core Implementation**
- `app/services/frequency_matching_service.py` - Main service
- `app/models.py` - Database model
- `app/main.py` - API endpoints
- `database/008_add_frequency_matches_table.sql` - Database migration

### **Documentation**
- `docs/FREQUENCY_MATCHING_SYSTEM.md` - System documentation
- `FREQUENCY_MATCHING_IMPLEMENTATION_SUMMARY.md` - Implementation summary
- `FREQUENCY_MATCHING_QUICK_REFERENCE.md` - This quick reference

## 🔧 **Troubleshooting**

### **Common Issues**

1. **Service Not Responding**
   ```bash
   docker-compose logs app
   docker-compose restart app
   ```

2. **Database Connection Issues**
   ```bash
   docker-compose logs postgres
   docker-compose restart postgres
   ```

3. **Migration Issues**
   ```bash
   docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -c "\dt"
   ```

### **Health Check Commands**
```bash
# Check if service is running
curl "http://localhost:8001/api/frequency-matching/health"

# Check if database is accessible
docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -c "SELECT COUNT(*) FROM frequency_matches;"

# Check Docker containers
docker-compose ps
```

## 📊 **Performance Monitoring**

### **Key Metrics to Monitor**
- Active matches count
- Response time for API calls
- Database query performance
- Memory usage
- Error rates

### **Monitoring Commands**
```bash
# Check active matches
curl "http://localhost:8001/api/frequency-matching/summary" | jq '.summary.active_matches'

# Check response time
time curl "http://localhost:8001/api/frequency-matching/matches"

# Check database performance
docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -c "SELECT COUNT(*) FROM frequency_matches WHERE match_timestamp >= NOW() - INTERVAL '1 hour';"
```

## 🎯 **Use Cases**

### **Real-time Monitoring**
```bash
# Monitor current frequency matches
watch -n 10 'curl -s "http://localhost:8001/api/frequency-matching/matches" | jq ".total_matches"'
```

### **Historical Analysis**
```bash
# Get 24-hour statistics
curl "http://localhost:8001/api/frequency-matching/statistics?hours=24"
```

### **Specific Entity Tracking**
```bash
# Track specific pilot
curl "http://localhost:8001/api/frequency-matching/pilot/ABC123"

# Track specific controller
curl "http://localhost:8001/api/frequency-matching/controller/YBBN_APP"
```

### **Frequency Analysis**
```bash
# Analyze specific frequency
curl "http://localhost:8001/api/frequency-matching/frequency/120500000"
```

This quick reference provides all the essential commands, endpoints, and information needed to use and maintain the Frequency Matching System.
