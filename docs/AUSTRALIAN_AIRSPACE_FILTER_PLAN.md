# Geographic Boundary Filter - Implementation Plan

## Overview

This document outlines the implementation plan for adding a geographic boundary filter to the VATSIM data collection system. The filter will use geographic coordinates to determine if flights are within specified geographic boundaries, complementing the existing airport-based filtering.

## Requirements Summary

### User Requirements
- **Sequence**: Airport filter first, then boundary filter (both must pass)
- **Position handling**: Require lat/lon data (filter out flights without position)
- **Control**: Independent enable/disable switches for each filter
- **Performance**: Pre-compute polygon at startup for fastest processing
- **Monitoring**: System status integration
- **Config**: Docker Compose environment variables for runtime changes
- **Testing**: Integration tests with real flight data
- **Deployment**: Manual control when ready
- **Data**: Convert geographic data to optimized format
- **Implementation**: Separate `GeographicBoundaryFilter` class

## Architecture Design

### Filter Pipeline
```
VATSIM API → VATSIM Service → Data Service → Airport Filter → Boundary Filter → Database
```

### Component Architecture
```
app/
├── filters/
│   ├── flight_filter.py (existing)
│   └── geographic_boundary_filter.py (new)
├── utils/
│   └── geographic_utils.py (new)
└── services/
    └── data_service.py (modified)
```

## Phase 1: Core Infrastructure

### 1.1 Dependencies
**Add to `requirements.txt`:**
```txt
shapely==2.0.2
```

### 1.2 Geographic Utilities (`app/utils/geographic_utils.py`)
```python
from shapely.geometry import Point, Polygon
from typing import List, Tuple

def is_point_in_polygon(lat: float, lon: float, polygon_coords: List[Tuple[float, float]]) -> bool:
    """
    Check if a point (lat, lon) is inside a polygon.
    
    Args:
        lat (float): Latitude of the point
        lon (float): Longitude of the point
        polygon_coords (list): List of (lat, lon) tuples defining the polygon
        
    Returns:
        bool: True if point is inside the polygon, False otherwise
    """
    # Shapely expects (x, y) => (lon, lat) order
    point = Point(lon, lat)
    polygon = Polygon(polygon_coords)
    return polygon.contains(point)
```

### 1.3 Geographic Boundary Filter (`app/filters/geographic_boundary_filter.py`)
```python
from typing import List, Dict, Any, Optional
from app.utils.geographic_utils import is_point_in_polygon
import logging

class GeographicBoundaryFilter:
    """Filter flights based on geographic boundary polygon"""
    
    def __init__(self, polygon_coordinates: List[Tuple[float, float]]):
        self.polygon_coordinates = polygon_coordinates
        self.logger = logging.getLogger(__name__)
        
    def filter_flights(self, flights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter flights to only include those within geographic boundary"""
        # Implementation details
```

## Phase 2: Integration

### 2.1 Data Service Integration
**Modify `app/services/data_service.py`:**
- Add boundary filter after airport filter
- Add configuration loading from environment variables
- Add system status integration

### 2.2 Configuration Management
**Docker Compose Configuration:**
```yaml
# Add to docker-compose.yml
services:
  app:
    environment:
      # Airport filter control
      - ENABLE_AIRPORT_FILTER=true
      # Boundary filter control  
      - ENABLE_BOUNDARY_FILTER=false
      # Boundary data path
      - BOUNDARY_DATA_PATH=app/utils/geographic_boundary_coordinates.json
```

**Environment Variables:**
```bash
# Airport filter control
ENABLE_AIRPORT_FILTER=true

# Boundary filter control  
ENABLE_BOUNDARY_FILTER=false

# Boundary data path
BOUNDARY_DATA_PATH=app/utils/geographic_boundary_coordinates.json
```

### 2.3 System Monitoring
**Add to system status:**
- Boundary filter status
- Polygon loading status
- Filter performance metrics

## Phase 3: Testing & Deployment

### 3.1 Integration Tests
**Create `tests/integration/test_boundary_filter.py`:**
- Test with real flight data
- Test boundary edge cases
- Test performance with large datasets

### 3.2 Performance Validation
- Measure filter processing time
- Validate memory usage
- Test with maximum flight volumes

### 3.3 Deployment Strategy
1. Deploy with boundary filter disabled
2. Test in staging environment
3. Enable via Docker Compose environment variable when ready
4. Monitor performance and accuracy

## Implementation Details

### Boundary Data Processing
1. **Load polygon coordinates** from pre-processed data file
2. **Pre-compute Shapely polygon** at startup
3. **Cache polygon object** in memory for fastest access

### Filter Logic
```python
def apply_boundary_filter(flight):
    # Check if flight has position data
    if not flight.get('latitude') or not flight.get('longitude'):
        return False  # Filter out flights without position
    
    # Check if position is within geographic boundary
    lat = flight['latitude']
    lon = flight['longitude']
    return is_point_in_polygon(lat, lon, self.polygon_coordinates)
```

### Error Handling
- **Data loading errors**: Log error and disable boundary filter
- **Invalid coordinates**: Log warning and skip flight
- **Performance issues**: Add circuit breaker pattern
- **Rollback strategy**: Git commit rollback if issues arise

## Monitoring & Metrics

### System Status
- Boundary filter operational status
- Polygon loading success/failure
- Filter processing time
- Memory usage for polygon data

### Metrics
- Flights filtered by boundary
- Flights rejected due to missing position
- Filter performance (ms per flight)
- Geographic distribution of filtered flights

## Future Enhancements

### Potential Improvements
1. **Multiple boundary support**: Support different airspace regions
2. **Dynamic boundaries**: Update boundaries without restart
3. **Altitude filtering**: Consider flight altitude in boundary checks
4. **Time-based filtering**: Different boundaries for different times
5. **Caching optimization**: Cache boundary check results

### Performance Optimizations
1. **Spatial indexing**: Use R-tree for faster point-in-polygon checks
2. **Coordinate precision**: Optimize coordinate precision for performance
3. **Parallel processing**: Process multiple flights in parallel
4. **Memory pooling**: Reuse polygon objects to reduce GC pressure

## Dependencies

### Required Libraries
- `shapely==2.0.2` - Geographic calculations

### Optional Libraries
- `numpy` - For coordinate array operations
- `rtree` - For spatial indexing (future enhancement)

## Timeline

### Phase 1 (Core Infrastructure): 2-3 days
- Dependencies and utilities
- KML parser implementation
- Boundary filter class

### Phase 2 (Integration): 2-3 days
- Data service integration
- Configuration management
- System monitoring

### Phase 3 (Testing & Deployment): 2-3 days
- Integration testing
- Performance validation
- Deployment preparation

**Total estimated time**: 6-9 days

## Risk Assessment

### Technical Risks
- **Performance impact**: Boundary checks may slow processing
- **Memory usage**: Large polygon data may increase memory footprint
- **Coordinate precision**: Floating point precision issues

### Mitigation Strategies
- **Performance**: Pre-compute polygon, optimize algorithms
- **Memory**: Use efficient data structures, monitor usage
- **Precision**: Use appropriate coordinate precision, add validation

## Success Criteria

### Functional Requirements
- [ ] Boundary filter correctly identifies flights within geographic boundary
- [ ] Filter can be enabled/disabled independently
- [ ] Performance impact is minimal (<10ms per flight)
- [ ] System monitoring provides accurate status

### Quality Requirements
- [ ] Integration tests pass with real data
- [ ] Performance tests meet requirements
- [ ] Error handling is robust
- [ ] Documentation is complete

## Conclusion

This plan provides a comprehensive approach to implementing the geographic boundary filter while maintaining system performance and reliability. The modular design allows for independent control and future enhancements.
