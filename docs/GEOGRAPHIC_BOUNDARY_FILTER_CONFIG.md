# Geographic Boundary Filter Configuration

## Overview

The Geographic Boundary Filter provides polygon-based filtering of VATSIM flight data to only include flights within specified geographic boundaries. This document describes all configuration options and usage examples.

## Environment Variables

### ENABLE_BOUNDARY_FILTER

- **Type**: Boolean (true/false)
- **Default**: false
- **Description**: Enable or disable the geographic boundary filter
- **Example**: `ENABLE_BOUNDARY_FILTER=true`

When enabled, the filter will process all incoming flight data and only include flights that are physically located within the defined geographic boundary polygon.

### BOUNDARY_DATA_PATH

- **Type**: String (file path)
- **Default**: app/utils/sample_boundary_coordinates.json
- **Description**: Path to the JSON file containing boundary polygon coordinates
- **Example**: `BOUNDARY_DATA_PATH=australian_airspace_polygon.json`

The file must be in GeoJSON format with polygon coordinates. Supports both standard GeoJSON format and simple coordinate arrays.

### BOUNDARY_FILTER_LOG_LEVEL

- **Type**: String (DEBUG/INFO/WARNING/ERROR)
- **Default**: INFO
- **Description**: Log level for boundary filter operations
- **Example**: `BOUNDARY_FILTER_LOG_LEVEL=DEBUG`

Controls the verbosity of logging output:
- **DEBUG**: Detailed per-flight filtering decisions
- **INFO**: Filter statistics and performance metrics
- **WARNING**: Performance threshold violations and issues
- **ERROR**: Critical errors only

### BOUNDARY_FILTER_PERFORMANCE_THRESHOLD

- **Type**: Float (milliseconds)
- **Default**: 10.0
- **Description**: Performance threshold in ms, warnings logged if exceeded
- **Example**: `BOUNDARY_FILTER_PERFORMANCE_THRESHOLD=5.0`

If filter processing takes longer than this threshold, a warning will be logged.

## Boundary Data File Format

The boundary data file must be in JSON format with coordinate arrays. Two formats are supported:

### Standard GeoJSON Format

```json
{
  "type": "Polygon",
  "coordinates": [[
    [151.0, -33.0],
    [152.0, -33.0],
    [152.0, -34.0],
    [151.0, -34.0],
    [151.0, -33.0]
  ]]
}
```

### Simple Coordinate Format

```json
{
  "coordinates": [
    [-33.0, 151.0],
    [-33.0, 152.0],
    [-34.0, 152.0],
    [-34.0, 151.0],
    [-33.0, 151.0]
  ]
}
```

**Note**: 
- GeoJSON format uses [longitude, latitude] order
- Simple format uses [latitude, longitude] order
- Coordinates must form a closed polygon
- Minimum 3 coordinate pairs required

## Usage Examples

### Development Configuration

```bash
# Enable filter with debug logging
export ENABLE_BOUNDARY_FILTER=true
export BOUNDARY_DATA_PATH=australian_airspace_polygon.json
export BOUNDARY_FILTER_LOG_LEVEL=DEBUG
export BOUNDARY_FILTER_PERFORMANCE_THRESHOLD=10.0
```

### Production Configuration

```bash
# Production settings with performance optimization
export ENABLE_BOUNDARY_FILTER=true
export BOUNDARY_DATA_PATH=/app/data/production_boundary.json
export BOUNDARY_FILTER_LOG_LEVEL=INFO
export BOUNDARY_FILTER_PERFORMANCE_THRESHOLD=5.0
```

### Docker Compose Configuration

```yaml
services:
  app:
    environment:
      # Geographic Boundary Filter Configuration
      ENABLE_BOUNDARY_FILTER: "true"
      BOUNDARY_DATA_PATH: "australian_airspace_polygon.json"
      BOUNDARY_FILTER_LOG_LEVEL: "INFO"
      BOUNDARY_FILTER_PERFORMANCE_THRESHOLD: "10.0"
```

## Filter Behavior

### Flight Processing

The filter processes flights in the following sequence:

1. **Airport Filter** (if enabled) - filters by airport codes
2. **Geographic Boundary Filter** (if enabled) - filters by geographic location
3. Both filters must pass for a flight to be included

### Position Data Handling

- **Missing Position**: Flights without latitude/longitude are allowed through (conservative approach)
- **Invalid Coordinates**: Flights with invalid coordinates are filtered out
- **Boundary Detection**: Uses Shapely point-in-polygon calculations for accuracy

### Performance Characteristics

- **Processing Time**: Typically <1ms for 50-100 flights
- **Memory Usage**: Polygon cached in memory for performance
- **Accuracy**: Sub-meter precision using Shapely geometric calculations

## Monitoring and Health Checks

### Filter Statistics

The filter provides real-time statistics:

```json
{
  "enabled": true,
  "initialized": true,
  "polygon_points": 24,
  "boundary_data_path": "australian_airspace_polygon.json",
  "filter_type": "Geographic boundary (point-in-polygon)",
  "processing_time_ms": 1.2,
  "flights_included": 52,
  "flights_excluded": 24
}
```

### Health Check

Filter health can be monitored via:

```json
{
  "status": "healthy",
  "enabled": true,
  "initialized": true,
  "issues": []
}
```

### Log Messages

Key log messages to monitor:

```
# Filter initialization
"Geographic boundary filter initialized - enabled: true"

# Processing statistics
"Geographic boundary filter: 76 flights -> 52 flights (24 filtered out) in 1.21ms"

# Performance warnings
"Geographic boundary filter exceeded performance threshold: 15.2ms > 10.0ms"
```

## Troubleshooting

### Common Issues

#### Filter Not Initializing

**Symptoms**: Filter shows as disabled in logs
**Causes**: 
- `ENABLE_BOUNDARY_FILTER` not set to "true"
- Container not restarted after configuration change

**Solution**: 
```bash
docker-compose down
docker-compose up -d
```

#### Boundary Data File Not Found

**Symptoms**: "Boundary data file not found" error
**Causes**:
- Incorrect `BOUNDARY_DATA_PATH`
- File not mounted in container

**Solution**: Verify file exists and path is correct relative to container

#### Invalid Polygon Data

**Symptoms**: "Invalid polygon coordinates" error
**Causes**:
- Malformed JSON file
- Incorrect coordinate format
- Insufficient coordinate points (<3)

**Solution**: Validate JSON format and coordinate structure

#### Poor Performance

**Symptoms**: Performance threshold warnings
**Causes**:
- Very complex polygon (thousands of points)
- High flight volume
- Resource constraints

**Solutions**:
- Simplify polygon geometry
- Increase performance threshold
- Monitor system resources

### Validation Commands

```bash
# Check environment variables
docker-compose exec app env | grep BOUNDARY

# Test filter initialization
docker-compose exec app python -c "
from app.filters.geographic_boundary_filter import GeographicBoundaryFilter
filter_obj = GeographicBoundaryFilter()
print('Enabled:', filter_obj.config.enabled)
print('Initialized:', filter_obj.is_initialized)
print('Health:', filter_obj.health_check())
"

# Monitor filter logs
docker-compose logs app | grep -i "geographic"
```

## Integration with Other Systems

### Filter Pipeline

The geographic boundary filter integrates with the existing flight filter pipeline:

1. **VATSIM API** → Raw flight data
2. **Airport Filter** → Filters by airport codes (if enabled)
3. **Geographic Filter** → Filters by location (if enabled)
4. **Database** → Stores filtered results

### API Endpoints

Filter status can be monitored via API endpoints:

- `/api/health/filters` - Overall filter health
- `/api/health/boundary-filter` - Specific boundary filter status

### Grafana Dashboards

Filter metrics are available for Grafana visualization:

- Flight filtering statistics
- Processing performance metrics
- Filter health status

## Best Practices

### Configuration

1. **Test in development first** with debug logging enabled
2. **Use appropriate performance thresholds** based on your system
3. **Monitor filter statistics** regularly
4. **Keep boundary polygons simple** for best performance

### Deployment

1. **Validate configuration** before production deployment
2. **Test with sample data** to verify filtering behavior
3. **Monitor performance** after enabling
4. **Have rollback plan** ready (disable filter if needed)

### Maintenance

1. **Regular health checks** of filter status
2. **Monitor log files** for warnings or errors
3. **Update boundary data** as needed
4. **Performance tuning** based on metrics

## Support

For issues or questions:

1. Check this documentation first
2. Review log files for error messages
3. Validate configuration using provided commands
4. Test with minimal configuration to isolate issues

