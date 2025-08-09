# ATC Service Coverage Analysis Dashboard

## Overview
This Grafana dashboard provides comprehensive analysis of ATC (Air Traffic Control) service coverage across the VATSIM network. It measures what percentage of flight data records occurred while aircraft were in radio contact with air traffic controllers.

## Dashboard Panels

### 1. ATC Service Coverage by Position Type (Pie Chart)
- **Visualization**: Pie chart showing ATC coverage percentage by position type
- **Position Types**: FSS, CTR, APP, TWR, GND, DEL, OTHER
- **Purpose**: Visual breakdown of which ATC positions provide the most coverage

### 2. ATC Service Coverage Statistics by Position (Table)
- **Columns**: Position Type, Total Flights, Total Flight Records, Records with ATC, ATC Coverage %
- **Sort**: Ordered by ATC Coverage % (highest first)
- **Color Coding**: Red (<30%), Yellow (30-60%), Green (>60%)

### 3. Individual Aircraft ATC Service Coverage (Table)
- **Shows**: Top 50 aircraft with their individual ATC coverage statistics
- **Columns**: Flight Callsign, Total Flight Records, Records with ATC, ATC Coverage %
- **Purpose**: Identify which specific flights had the best/worst ATC coverage

### 4. ATC Service Coverage Over Time (Time Series)
- **Time Range**: Last 24 hours, hourly aggregation
- **Metrics**: Total Flights, Flights with ATC, ATC Coverage %
- **Purpose**: Track ATC coverage trends over time

### 5. Overall ATC Service Statistics (Stat Panel)
- **Metrics**: Total Flights, Total Flight Records, Records with ATC, Overall ATC Coverage %
- **Purpose**: High-level summary statistics

## SQL Query Logic

The dashboard uses sophisticated SQL queries with Common Table Expressions (CTEs):

### Key Matching Criteria:
1. **Frequency Match**: Flight and ATC on same radio frequency
2. **Time Window**: Within 180 seconds (3 minutes)
3. **Distance Constraint**: Within 300 coordinate units
4. **ATC Filter**: Excludes observers (`facility != 'OBS'`)

### Data Sources:
- **`transceivers`**: Radio frequency data for flights and ATC
- **`controllers`**: ATC position information
- **`flights`**: Flight position/status records

### Position Type Classification:
- **FSS**: Flight Service Station
- **CTR**: Center Control
- **APP**: Approach Control
- **TWR**: Tower Control
- **GND**: Ground Control
- **DEL**: Clearance Delivery
- **OTHER**: Unclassified positions

## Dashboard Settings

- **Refresh Rate**: 30 seconds
- **Time Range**: Last 6 hours (default)
- **Theme**: Dark mode
- **Tags**: VATSIM, ATC, Service Coverage, Analytics

## Access Information

- **Dashboard UID**: `atc-service-coverage`
- **Location**: Grafana → VATSIM folder → "ATC Service Coverage Analysis"
- **URL**: `http://localhost:3050/d/atc-service-coverage/atc-service-coverage-analysis`

## Usage Notes

1. **Performance**: Queries may take several seconds to execute on large datasets
2. **Data Freshness**: Dashboard updates every 30 seconds with latest data
3. **Time Filtering**: Use Grafana's time picker to analyze different time periods
4. **Interactive**: Click on pie chart segments to filter other panels

## Interpretation

- **High Coverage (>70%)**: Excellent ATC service provision
- **Medium Coverage (30-70%)**: Adequate ATC service with room for improvement  
- **Low Coverage (<30%)**: Limited ATC service coverage

This dashboard helps VATSIM administrators and researchers understand:
- Which ATC positions are most active
- How well the network serves pilots with ATC coverage
- Trends in ATC service provision over time
- Individual flight experiences with ATC services
