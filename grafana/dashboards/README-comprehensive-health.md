# Comprehensive Health Monitoring Dashboard

This Grafana dashboard provides real-time monitoring of your VATSIM data application's health status by directly consuming the `/api/health/comprehensive` HTTP endpoint.

## Features

The dashboard displays the following key metrics:

### System Health
- **Overall System Health**: Percentage score (95%+ = Green, 80-94% = Orange, <80% = Red)
- **Database Status**: Connection status (Connected/Disconnected)
- **Active Controllers**: Current number of active ATC controllers
- **Active Flights**: Current number of active flights in the system

### System Resources
- **CPU Usage**: Current CPU utilization with color-coded thresholds
- **Memory Usage**: Current memory utilization with color-coded thresholds
- **Database Size**: Current database size in MB

### Service Status
- **Cache Service Status**: Health status of the cache service
- **Cache Hit Rate**: Cache performance metrics
- **Data Freshness (ATC)**: How recent the ATC data is (seconds)
- **Data Freshness (Flights)**: How recent the flight data is (seconds)

### Timestamps
- **Last Updated**: Timestamp of the most recent health check

## Data Source

The dashboard uses the **Simple JSON Data Source** plugin configured to fetch data from:
- **URL**: `http://app:8001/api/health/comprehensive`
- **Method**: GET
- **Refresh Rate**: 30 seconds
- **Timeout**: 30 seconds

## Configuration

The dashboard is automatically provisioned when Grafana starts. The datasource configuration is located in:
- `grafana/provisioning/datasources/simple-json-health.yml`

## Access

- **Grafana URL**: http://localhost:3050
- **Default Credentials**: admin/admin
- **Dashboard**: Automatically loaded as "VATSIM Comprehensive Health Monitoring"

## Troubleshooting

### Dashboard Not Loading Data
1. Verify the health endpoint is accessible: `curl http://localhost:8001/api/health/comprehensive`
2. Check Grafana logs: `docker logs vatsim_grafana`
3. Verify the Simple JSON Data Source plugin is installed
4. Check datasource configuration in Grafana UI

### Data Source Issues
1. Ensure the app container is running and healthy
2. Verify network connectivity between Grafana and app containers
3. Check if the health endpoint returns valid JSON

### Performance Issues
1. The dashboard refreshes every 30 seconds by default
2. Reduce refresh rate if needed in dashboard settings
3. Monitor Grafana container resource usage

## Customization

To modify the dashboard:
1. Edit `grafana/dashboards/comprehensive-health-monitoring.json`
2. Restart Grafana: `docker-compose restart grafana`
3. Changes will be automatically applied

## Health Endpoint Details

The `/api/health/comprehensive` endpoint provides:
- Overall system health score
- API endpoint status and response times
- Database connection and performance metrics
- System resource utilization (CPU, memory, disk)
- Data freshness indicators
- Cache service status
- Service health information
- Error monitoring data
- Timestamp information

All data is real-time and reflects the current state of your VATSIM data application.
