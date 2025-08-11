# 🔌 VATSIM Data Collection API Reference

## 📋 Overview

The VATSIM Data Collection System provides a comprehensive RESTful API for accessing real-time flight data, ATC positions, network statistics, and system monitoring information. All endpoints return JSON responses and support standard HTTP status codes.

**Base URL**: `http://localhost:8001` (development) or `https://api.yourdomain.com` (production)

> 📚 **Field Mapping Reference**: For detailed field mappings from VATSIM API to database to API responses, see [API_FIELD_MAPPING.md](./API_FIELD_MAPPING.md)

## 🔐 Authentication

### **Development Mode:**
No authentication required for local development.

### **Production Mode:**
```bash
# API Key Authentication (when API_KEY_REQUIRED=true)
curl -H "Authorization: Bearer YOUR_API_KEY" https://api.yourdomain.com/api/status

# JWT Authentication (advanced)
curl -H "Authorization: JWT YOUR_JWT_TOKEN" https://api.yourdomain.com/api/flights
```

## 🛩️ Flight Data Endpoints

### **GET /api/flights**
Get all active flights with current position and flight plan data.

**Response Example:**
```json
{
  "flights": [
    {
      "callsign": "QFA005",
      "cid": 123456,
      "name": "John Pilot",
      "server": "AUSTRALIA",
      "pilot_rating": 1,
      "latitude": -33.9461,
      "longitude": 151.1772,
      "altitude": 37000,
      "groundspeed": 485,
      "heading": 90,
      "transponder": "2000",
      "departure": "VTBS",
      "arrival": "YBBN",
      "aircraft_type": "B789",
      "flight_rules": "I",
      "planned_altitude": "FL370",
      "last_updated": "2025-08-09T09:15:30Z"
    }
  ],
  "total_count": 74,
  "timestamp": "2025-08-09T09:15:35Z"
}
```

### **GET /api/flights/{callsign}**
Get specific flight by callsign.

**Parameters:**
- `callsign` (string): Aircraft callsign (e.g., "QFA005")

**Response Example:**
```json
{
  "flight": {
    "callsign": "QFA005",
    "cid": 123456,
    "name": "John Pilot",
    "latitude": -33.9461,
    "longitude": 151.1772,
    "altitude": 37000,
    "departure": "VTBS",
    "arrival": "YBBN",
    "route": "VTBS DCT YBBN",
    "aircraft_type": "B789",
    "last_updated": "2025-08-09T09:15:30Z"
  }
}
```

### **GET /api/flights/{callsign}/track**
Get complete flight track with all position updates.

**Response Example:**
```json
{
  "callsign": "QFA005",
  "track_points": [
    {
      "timestamp": "2025-08-09T08:30:00Z",
      "latitude": 13.6900,
      "longitude": 100.7501,
      "altitude": 2000,
      "groundspeed": 180
    },
    {
      "timestamp": "2025-08-09T09:15:30Z",
      "latitude": -33.9461,
      "longitude": 151.1772,
      "altitude": 37000,
      "groundspeed": 485
    }
  ],
  "total_points": 156,
  "flight_duration_minutes": 645
}
```

### **GET /api/flights/{callsign}/stats**
Get flight statistics and summary information.

**Response Example:**
```json
{
  "callsign": "QFA005",
  "statistics": {
    "total_distance_nm": 4287,
    "average_groundspeed": 445,
    "max_altitude": 37000,
    "flight_time_minutes": 645,
    "position_updates": 156,
    "route_efficiency": 0.98
  }
}
```

### **GET /api/flights/memory**
Get flights from memory cache (debugging endpoint).

**Response Example:**
```json
{
  "memory_flights": 74,
  "cache_status": "healthy",
  "last_refresh": "2025-08-09T09:15:30Z",
  "flights": [...]
}
```

## 🎮 ATC Controller Endpoints

### **GET /api/controllers**
Get all active ATC positions.

**Response Example:**
```json
{
  "controllers": [
    {
      "callsign": "YSSY_APP",
      "cid": 789012,
      "name": "Jane Controller",
      "facility": "APP",
      "frequency": "124.700",
      "controller_rating": 5,
      "visual_range": 50,
      "text_atis": "Sydney Approach, contact 124.700",
      "logon_time": "2025-08-09T06:30:00Z",
      "last_updated": "2025-08-09T09:15:30Z"
    }
  ],
  "total_count": 237,
  "timestamp": "2025-08-09T09:15:35Z"
}
```

### **GET /api/atc-positions**
Alternative endpoint for ATC positions (legacy compatibility).

### **GET /api/atc-positions/by-controller-id**
Get ATC positions grouped by controller ID.

**Response Example:**
```json
{
  "controllers_by_id": {
    "789012": [
      {
        "callsign": "YSSY_APP",
        "facility": "APP",
        "frequency": "124.700",
        "logon_time": "2025-08-09T06:30:00Z"
      }
    ]
  }
}
```

## 📡 Network & System Status

### **GET /api/status**
Get comprehensive system health and statistics.

**Response Example:**
```json
{
  "status": "operational",
  "timestamp": "2025-08-09T09:15:35Z",
  "data_freshness": "real-time",
  "cache_status": "enabled",
  "statistics": {
    "flights_count": 74,
    "controllers_count": 237,
    "transceivers_count": 18797,
    "airports_count": 2720
  },
  "performance": {
    "api_response_time_ms": 45,
    "database_query_time_ms": 12,
    "memory_usage_mb": 1247,
    "uptime_seconds": 86400
  },
  "data_ingestion": {
    "last_vatsim_update": "2025-08-09T09:15:30Z",
    "update_interval_seconds": 10,
    "successful_updates": 8640,
    "failed_updates": 0
  }
}
```

### **GET /api/network/status**
Get VATSIM network status and metrics.

**Response Example:**
```json
{
  "network_status": {
    "api_version": "v3",
    "connected_clients": 1847,
    "unique_users": 1623,
    "update_timestamp": "2025-08-09T09:15:30Z",
    "reload": 1,
    "servers": [
      {
        "name": "AUSTRALIA",
        "location": "Australia",
        "clients": 156
      }
    ]
  }
}
```

### **GET /api/database/status**
Get database status and migration information.

**Response Example:**
```json
{
  "database_status": {
    "connection": "healthy",
    "tables": 6,
    "total_records": 156789,
    "last_migration": "010_remove_flight_status_fields.sql",
    "schema_version": "1.0.10",
    "performance": {
      "avg_query_time_ms": 12,
      "active_connections": 5,
      "pool_size": 10
    }
  }
}
```

## 🔍 Flight Filtering Endpoints

### **GET /api/filter/flight/status**
Get airport filter status and statistics.

**Response Example:**
```json
{
  "filter_status": {
    "enabled": true,
    "type": "airport_based",
    "log_level": "INFO",
    "statistics": {
      "total_flights_processed": 1173,
      "flights_passed": 74,
      "flights_filtered": 1099,
      "filter_efficiency": 93.7,
      "last_filter_run": "2025-08-09T09:15:30Z"
    },
    "configuration": {
      "filter_enabled": true,
      "airport_validation_method": "starts_with_Y"
    }
  }
}
```

### **GET /api/filter/boundary/status**
Get geographic boundary filter status and performance.

**Response Example:**
```json
{
  "boundary_filter": {
    "enabled": false,
    "status": "ready",
    "performance": {
      "average_processing_time_ms": 8.5,
      "performance_threshold_ms": 10.0,
      "total_calculations": 0,
      "cache_hits": 0,
      "cache_misses": 0
    },
    "configuration": {
      "boundary_data_path": "australian_airspace_polygon.json",
      "log_level": "INFO",
      "polygon_loaded": true,
      "polygon_points": 156
    }
  }
}
```

### **GET /api/filter/boundary/info**
Get boundary polygon information and configuration.

**Response Example:**
```json
{
  "boundary_info": {
    "polygon_type": "GeoJSON",
    "coordinate_system": "WGS84",
    "points_count": 156,
    "bounding_box": {
      "min_lat": -43.6345,
      "max_lat": -9.1423,
      "min_lng": 112.9211,
      "max_lng": 159.1056
    },
    "area_sq_km": 7692024,
    "loaded_at": "2025-08-09T08:00:00Z",
    "file_path": "australian_airspace_polygon.json"
  }
}
```

## 📊 Analytics Endpoints

### **REMOVED: Traffic Analysis Endpoints**
Traffic analysis endpoints have been removed in Phase 4:
- `GET /api/analytics/traffic` - REMOVED
- `GET /api/traffic/movements/{airport_icao}` - REMOVED  
- `GET /api/traffic/summary/{region}` - REMOVED

**Note**: These endpoints are no longer available as the Traffic Analysis Service has been removed.
    "arrivals": 624,
    "busiest_airports": [
      {
        "icao": "YSSY",
        "movements": 156,
        "departures": 78,
        "arrivals": 78
      }
    ],
    "hourly_distribution": [
      {"hour": "00", "movements": 45},
      {"hour": "01", "movements": 52}
    ]
  }
}
```

### **GET /api/analytics/flights**
Get flight summary data and analytics.

### **REMOVED: Traffic Endpoints**
The following traffic endpoints have been removed:
- `GET /api/traffic/movements/{airport_icao}` - REMOVED
- `GET /api/traffic/summary/{region}` - REMOVED

These endpoints are no longer available.

## 🔧 Performance & Monitoring

### **GET /api/performance/metrics**
Get system performance metrics.

**Response Example:**
```json
{
  "performance_metrics": {
    "timestamp": "2025-08-09T09:15:35Z",
    "system": {
      "cpu_usage_percent": 15.6,
      "memory_usage_mb": 1247,
      "memory_total_mb": 4096,
      "disk_usage_percent": 23.4
    },
    "application": {
      "active_connections": 5,
      "requests_per_minute": 120,
      "average_response_time_ms": 45,
      "error_rate_percent": 0.1
    },
    "database": {
      "active_connections": 5,
      "pool_size": 10,
      "avg_query_time_ms": 12,
      "slow_queries": 0
    },
    "cache": {
      "redis_memory_mb": 156,
      "cache_hit_rate": 94.5,
      "operations_per_second": 450
    }
  }
}
```

### **POST /api/performance/optimize**
Trigger performance optimization.

**Response Example:**
```json
{
  "optimization_result": {
    "triggered_at": "2025-08-09T09:15:35Z",
    "actions_taken": [
      "cache_cleanup",
      "connection_pool_optimization",
      "memory_garbage_collection"
    ],
    "performance_improvement": "12% faster response times"
  }
}
```

## 📡 Transceiver Data

### **GET /api/transceivers**
Get radio frequency and position data.

**Response Example:**
```json
{
  "transceivers": [
    {
      "id": 12345,
      "callsign": "YSSY_TWR",
      "frequency": 120.500,
      "position_lat": -33.9461,
      "position_lng": 151.1772,
      "altitude": 21,
      "last_updated": "2025-08-09T09:15:30Z"
    }
  ],
  "total_count": 18797
}
```

## 🗄️ Database Operations

### **GET /api/database/tables**
Get database tables and record counts.

**Response Example:**
```json
{
  "database_tables": {
    "flights": 156789,
    "controllers": 45623,
    "transceivers": 78234,
    // "traffic_movements": 234567,  // REMOVED: Traffic Analysis Service - Phase 4
    "airports": 2720,
    "frequency_matches": 12456
  },
  "total_records": 502573,
  "last_updated": "2025-08-09T09:15:35Z"
}
```

### **POST /api/database/query**
Execute custom SQL queries (admin only).

**Request Body:**
```json
{
  "query": "SELECT COUNT(*) FROM flights WHERE last_updated > NOW() - INTERVAL '1 hour'",
  "limit": 1000
}
```

## 🏢 Airport Data

### **GET /api/airports/region/{region}**
Get airports by region.

**Parameters:**
- `region` (string): Region name (e.g., "Australia")

### **GET /api/airports/{airport_code}/coordinates**
Get airport coordinates and information.

**Parameters:**
- `airport_code` (string): Airport ICAO code (e.g., "YSSY")

## 📈 VATSIM Ratings

### **GET /api/vatsim/ratings**
Get VATSIM controller ratings and descriptions.

**Response Example:**
```json
{
  "ratings": {
    "1": "Observer",
    "2": "Student 1",
    "3": "Student 2", 
    "4": "Student 3",
    "5": "Controller 1",
    "7": "Controller 3",
    "8": "Instructor 1",
    "10": "Instructor 3"
  }
}
```

## ❌ Error Responses

### **Standard Error Format:**
```json
{
  "error": {
    "code": "FLIGHT_NOT_FOUND",
    "message": "Flight with callsign 'ABC123' not found",
    "timestamp": "2025-08-09T09:15:35Z",
    "request_id": "req_12345"
  }
}
```

### **HTTP Status Codes:**
- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized (when authentication required)
- `404` - Resource Not Found
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error
- `503` - Service Unavailable

## 🚀 Rate Limiting

### **Production Rate Limits:**
- **Default**: 100 requests per minute per API key
- **Burst**: Up to 200 requests in 10 seconds
- **Headers**: Rate limit information in response headers

**Response Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1691580935
```

## 📝 Request/Response Examples

### **cURL Examples:**

```bash
# Get system status
curl https://api.yourdomain.com/api/status

# Get flights with authentication
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://api.yourdomain.com/api/flights

# Get specific flight track
curl https://api.yourdomain.com/api/flights/QFA005/track

# Get filter statistics
curl https://api.yourdomain.com/api/filter/flight/status
```

### **Python Example:**
```python
import requests

# Configuration
API_BASE = "https://api.yourdomain.com"
API_KEY = "your_api_key_here"
headers = {"Authorization": f"Bearer {API_KEY}"}

# Get system status
response = requests.get(f"{API_BASE}/api/status", headers=headers)
status = response.json()
print(f"System status: {status['status']}")

# Get all flights
flights_response = requests.get(f"{API_BASE}/api/flights", headers=headers)
flights = flights_response.json()
print(f"Active flights: {flights['total_count']}")
```

---

**📅 Last Updated**: 2025-08-09  
**🔄 API Version**: v1.0  
**📚 Total Endpoints**: 25+  
**🚀 Production Ready**: Yes
