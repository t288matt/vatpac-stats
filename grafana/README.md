# Grafana Setup for VATSIM Data Visualization

This directory contains the Grafana configuration for visualizing VATSIM data in real-time.

## 🚀 Quick Start

1. **Start the services:**
   ```bash
   docker-compose up -d
   ```

2. **Access Grafana:**
   - URL: http://localhost:3050
   - No authentication required (anonymous access enabled)
   - Admin credentials: `admin` / `admin` (if needed)

3. **Available Dashboards:**
   - **VATSIM Overview**: Real-time network activity, controller counts, flight data
   - **Australian Flights Dashboard**: Australian flight analysis by airport and date
   - **Australian Routes Analysis**: Detailed route analysis and connectivity
   - **Custom Dashboards**: Create your own using the VATSIM API datasource

## 📊 Data Sources

### VATSIM API Datasource
- **Type**: SimpleJSON
- **URL**: http://app:8001
- **Access**: Proxy
- **Available Endpoints:**
  - `/api/status` - System status and counts
  - `/api/network/status` - Network statistics
  - `/api/atc-positions` - Active ATC positions
  - `/api/flights` - Active flights
  <!-- REMOVED: Traffic Analysis Service - Final Sweep
  - `/api/traffic/summary/{region}` - Traffic summaries
  -->
  - `/api/performance/metrics` - System performance

## 📈 Dashboard Features

### VATSIM Overview Dashboard
- **Real-time Network Activity**: Live graphs of controller and flight counts
- **System Statistics**: Total controllers, flights, data freshness
- **ATC Position Analysis**: Breakdown by facility type
- **Performance Metrics**: System status and response times

### Australian Flights Dashboard
- **Australian Flights by Date**: Time series of Australian flights (last 7 & 30 days)
- **Top Australian Airports**: Busiest departure and arrival airports
- **Aircraft Types**: Distribution of aircraft on Australian routes
- **Route Analysis**: Most popular Australian routes with flight counts

### Australian Routes Analysis Dashboard
- **Unique Australian Routes**: Time series of unique routes over time
- **Route Connectivity**: Airports by number of destinations and origins
- **Major Airport Trends**: Individual airport flight trends (Brisbane, Sydney, Melbourne)
- **Route Types**: Domestic vs International flight breakdown

### Custom Queries
You can create custom panels using the SimpleJSON datasource:

```json
{
  "targets": [
    {
      "expr": "/api/atc-positions",
      "refId": "A"
    }
  ]
}
```

## 🔧 Configuration

### Datasource Configuration
- **File**: `provisioning/datasources/vatsim-api.json`
- **Auto-provisioned**: Yes
- **Editable**: Yes

### Dashboard Configuration
- **File**: `provisioning/dashboards/dashboard.yml`
- **Auto-provisioned**: Yes
- **Update Interval**: 10 seconds

## 🎨 Customization

### Adding New Dashboards
1. Create a new JSON file in `dashboards/`
2. Use the VATSIM API datasource
3. Restart Grafana or wait for auto-provisioning

### Available Metrics
- **Controllers**: Total online, by facility, by rating
- **Flights**: Active flights, aircraft types, routes
- **Australian Flights**: Filtered Australian flight data only
- **Australian Routes**: Route analysis and connectivity
<!-- REMOVED: Traffic Analysis Service - Final Sweep
- **Traffic**: Movements, density, trends
-->
- **Performance**: Response times, cache status, memory usage

## 🔍 Troubleshooting

### Common Issues
1. **Datasource not found**: Check if the VATSIM app is running
2. **No data**: Verify API endpoints are accessible
3. **Authentication**: Use admin/vatsim_admin credentials

### Logs
```bash
docker-compose logs grafana
```

## 📚 Resources
- [Grafana Documentation](https://grafana.com/docs/)
- [SimpleJSON Datasource](https://grafana.com/grafana/plugins/grafana-simple-json-datasource/)
- [VATSIM API Documentation](http://localhost:8001/docs) 