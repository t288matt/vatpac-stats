# VATSIM API Endpoints Status Dashboard

## Overview

This dashboard provides real-time monitoring of all VATSIM API endpoints status. It focuses specifically on endpoint availability, response times, and error tracking.

## Access

- **URL**: http://localhost:3050
- **Username**: admin
- **Password**: admin

## Dashboard Features

### 1. API Endpoints Status
- **Location**: Main table panel
- **Data Source**: `/api/status`
- **Refresh Rate**: 10 seconds
- **Shows**:
  - Endpoint URL
  - HTTP Status Code (color-coded)
  - Response Time (in seconds)
  - Health Status (true/false)
  - Timestamp

### 2. Visual Indicators
- **Green**: Operational endpoints (status 200, response time < 1s)
- **Yellow**: Warning endpoints (status 300-399)
- **Red**: Error endpoints (status 400+, response time > 1s, or connection errors)

### 3. Monitored Endpoints
- `/api/status` - System status
- `/api/network/status` - Network status
- `/api/atc-positions` - ATC positions data
- `/api/flights` - Flight data
- `/api/database/status` - Database status
- `/api/performance/metrics` - Performance metrics

### 4. Data Freshness Monitoring
- **ATC Positions**: Last update time and age in seconds
- **Flight Data**: Last update time and age in seconds
- **Data Stale Status**: Overall data freshness indicator
- **Visual Indicators**:
  - **Green**: Data updated within last 5 minutes
  - **Yellow**: Data updated within last 10 minutes
  - **Red**: Data older than 10 minutes or no data

## Dashboard Files

1. **endpoint-health-dashboard.json** - Comprehensive dashboard with multiple panels including data freshness
2. **endpoint-health-simple.json** - Simple, focused dashboard with endpoint health and data freshness tables

## Configuration

The dashboard uses the `vatsim-api` datasource which connects to:
- **URL**: http://vatsim-app:8001
- **Method**: GET
- **Timeout**: 30 seconds

## Troubleshooting

### If endpoints show as non-operational:
1. Check if the VATSIM API container is running: `docker ps`
2. Verify API is responding: `curl http://localhost:8001/api/status`
3. Check container logs: `docker logs vatsim_app`

### If Grafana dashboard is not loading:
1. Restart Grafana: `docker compose restart grafana`
2. Clear browser cache
3. Check Grafana logs: `docker logs vatsim_grafana`

## API Status Endpoints

The dashboard pulls data from multiple health endpoints:

### `/api/health/endpoints` - Endpoint Health
Returns:

```json
{
  "/api/status": {
    "status": 200,
    "response_time": 0.011773,
    "healthy": true,
    "timestamp": "2025-08-05T20:01:45.750776"
  },
  "/api/network/status": {
    "status": 500,
    "response_time": 0.028678,
    "healthy": false,
    "timestamp": "2025-08-05T20:01:45.779482"
  }
}
```

### `/api/health/data-freshness` - Data Freshness
Returns:

```json
{
  "last_atc_update": "2025-08-05T20:01:45.750776",
  "last_flight_update": "2025-08-05T20:01:45.750776",
  "atc_freshness_seconds": 120.5,
  "flight_freshness_seconds": 120.5,
  "data_stale": false,
  "timestamp": "2025-08-05T20:03:44.279830"
}
```

## Customization

To add more endpoints to monitor:
1. Update the `check_api_endpoints()` method in `app/utils/health_monitor.py`
2. Add the endpoint URL to the `endpoints` list
3. Restart the application container

To modify dashboard refresh rate:
1. Edit the dashboard JSON file
2. Change the `"refresh"` value (e.g., `"5s"` for 5 seconds)
3. Save and reload the dashboard in Grafana 