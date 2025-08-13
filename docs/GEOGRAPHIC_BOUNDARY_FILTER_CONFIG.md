# Geographic Boundary Filter Configuration

## Overview

The Geographic Boundary Filter provides polygon-based filtering of VATSIM data to only include flights, transceivers, and controllers within specified geographic boundaries. This document describes all configuration options and usage examples.

## Environment Variables

### ENABLE_BOUNDARY_FILTER

- **Type**: Boolean (true/false)
- **Default**: false
- **Description**: Enable or disable the geographic boundary filter
- **Example**: `ENABLE_BOUNDARY_FILTER=true`

When enabled, the filter will process all incoming VATSIM data and only include entities that are physically located within the defined geographic boundary polygon.

### BOUNDARY_DATA_PATH

- **Type**: String (file path)
- **Default**: app/utils/sample_boundary_coordinates.json
- **Description**: Path to the JSON file containing boundary polygon coordinates
- **Example**: `BOUNDARY_DATA_PATH=airspace_sector_data/australian_airspace_polygon.json`

The file must be in GeoJSON format with polygon coordinates. Supports both standard GeoJSON format and simple coordinate arrays.

### BOUNDARY_FILTER_LOG_LEVEL

- **Type**: String (DEBUG/INFO/WARNING/ERROR)
- **Default**: INFO
- **Description**: Log level for boundary filter operations
- **Example**: `BOUNDARY_FILTER_LOG_LEVEL=DEBUG`

Controls the verbosity of logging output:
- **DEBUG**: Detailed per-entity filtering decisions
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
export BOUNDARY_DATA_PATH=airspace_sector_data/australian_airspace_polygon.json
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
      BOUNDARY_DATA_PATH: "airspace_sector_data/australian_airspace_polygon.json"
      BOUNDARY_FILTER_LOG_LEVEL: "INFO"
      BOUNDARY_FILTER_PERFORMANCE_THRESHOLD: "10.0"
```

## Filter Behavior

### Data Processing Pipeline

The filter processes VATSIM data in the following sequence:

1. **Airport Filter** (if enabled) - filters by airport codes
2. **Geographic Boundary Filter** (if enabled) - filters by geographic location
3. Both filters must pass for an entity to be included

### Entity Types Supported

#### Flights
- **Position Data**: Uses `latitude` and `longitude` fields
- **Missing Position**: Flights without coordinates are allowed through (conservative approach)
- **Invalid Coordinates**: Flights with invalid coordinates are filtered out

#### Transceivers
- **Position Data**: Uses `position_lat` and `position_lon` fields
- **Missing Position**: Transceivers without coordinates are allowed through (conservative approach)
- **Invalid Coordinates**: Transceivers with invalid coordinates are filtered out

#### Controllers
- **Position Data**: Currently uses conservative approach (all controllers allowed through)
- **Future Enhancement**: Will support position-based filtering when position data becomes available
- **Current Behavior**: All controllers pass through the filter regardless of location

### Position Data Handling

- **Missing Position**: Entities without latitude/longitude are allowed through (conservative approach)
- **Invalid Coordinates**: Entities with invalid coordinates are filtered out
- **Boundary Detection**: Uses Shapely point-in-polygon calculations for accuracy

### Performance Characteristics

- **Processing Time**: Typically <1ms for 50-100 entities
- **Memory Usage**: Polygon cached in memory for performance
- **Accuracy**: Sub-meter precision using Shapely geometric calculations

## Monitoring and System Status

### Filter Statistics

The filter provides real-time statistics for all entity types:

```json
{
  "enabled": true,
  "initialized": true,
  "polygon_points": 24,
  "boundary_data_path": "australian_airspace_polygon.json",
  "filter_type": "Geographic boundary (point-in-polygon)",
  "processing_time_ms": 1.2,
  "flights_included": 52,
  "flights_excluded": 24,
  "total_transceivers_processed": 15,
  "transceivers_included": 8,
  "transceivers_excluded": 7,
  "total_controllers_processed": 12,
  "controllers_included": 12,
  "controllers_excluded": 0
}
```

### System Status Check

Filter health can be monitored via:

```json
{
  "status": "operational",
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
"Geographic filtering: 76 flights -> 52 flights (24 filtered out)"
"Geographic filtering: 15 transceivers -> 8 transceivers (7 filtered out)"
"Geographic filtering: 12 controllers -> 12 controllers (conservative approach)"

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
- High entity volume
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
print('Status:', filter_obj.get_filter_stats())
"

# Monitor filter logs
docker-compose logs app | grep -i "geographic"
```

## Integration with Other Systems

### Filter Pipeline

The geographic boundary filter integrates with the existing VATSIM data processing pipeline:

1. **VATSIM API** → Raw flight, transceiver, and controller data
2. **Airport Filter** → Filters by airport codes (if enabled)
3. **Geographic Filter** → Filters by location (if enabled)
4. **Database** → Stores filtered results

### API Endpoints

Filter status can be monitored via API endpoints:

- `/api/filter/boundary/status` - Overall filter status
- `/api/filter/boundary/info` - Specific boundary filter information

### Grafana Dashboards

Filter metrics are available for Grafana visualization:

- Entity filtering statistics (flights, transceivers, controllers)
- Processing performance metrics
- Filter status information

## Testing

### Test Scripts

Use the provided test scripts to validate filter functionality:

```bash
# Test filter on/off functionality
python test_filter_on_off.py

# Test geographic filtering with live data
python test_geographic_filtering.py
```

### Test Results

The filter has been tested and validated with:
- ✅ Configuration changes (enable/disable)
- ✅ Filtering behavior (enabled vs disabled)
- ✅ Performance impact measurement
- ✅ Live VATSIM data processing
- ✅ Multi-entity type support

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

1. **Regular status checks** of filter status
2. **Monitor log files** for warnings or errors
3. **Update boundary data** as needed
4. **Performance tuning** based on metrics

## Support

For issues or questions:

1. Check this documentation first
2. Review log files for error messages
3. Validate configuration using provided commands
4. Test with minimal configuration to isolate issues

---

**📅 Last Updated**: 2025-01-27  
**🚀 Status**: Production Ready  
**🗺️ Supported Entities**: Flights, Transceivers, Controllers  
**⚡ Performance**: <1ms for 100 entities  
**🔧 Configuration**: Environment variable based

