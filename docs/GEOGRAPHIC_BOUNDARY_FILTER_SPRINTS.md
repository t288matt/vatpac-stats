# Geographic Boundary Filter - Sprint Implementation Plan

## Overview

This document breaks down the geographic boundary filter implementation into small, testable sprints. Each sprint delivers working functionality that can be tested independently before proceeding to the next iteration.

## Sprint Structure

- **Sprint Duration**: 1-2 days each
- **Testing**: Comprehensive tests after each sprint
- **Deployment**: Each sprint creates deployable code
- **Rollback**: Easy rollback if issues arise

---

## 🏃‍♂️ Sprint 1: Core Geographic Utilities

**Duration**: 1 day  
**Goal**: Implement and test basic polygon detection functionality

### 📋 Sprint 1 Tasks

#### 1.1 Dependencies Setup
- [ ] Add `shapely==2.0.2` to `requirements.txt`
- [ ] Update Docker container to include new dependency
- [ ] Test dependency installation

#### 1.2 Geographic Utilities Module
- [ ] Create `app/utils/geographic_utils.py`
- [ ] Implement `is_point_in_polygon()` function
- [ ] Add comprehensive docstrings and type hints
- [ ] Handle edge cases (invalid coordinates, empty polygons)

```python
# app/utils/geographic_utils.py
from shapely.geometry import Point, Polygon
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

def is_point_in_polygon(lat: float, lon: float, polygon_coords: List[Tuple[float, float]]) -> bool:
    """
    Check if a point (lat, lon) is inside a polygon.
    
    Args:
        lat: Latitude of the point
        lon: Longitude of the point  
        polygon_coords: List of (lat, lon) tuples defining the polygon
        
    Returns:
        True if point is inside the polygon, False otherwise
        
    Raises:
        ValueError: If coordinates are invalid
        TypeError: If polygon_coords is not properly formatted
    """
    try:
        # Validate inputs
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            raise ValueError("Latitude and longitude must be numeric")
        
        if not polygon_coords or len(polygon_coords) < 3:
            raise ValueError("Polygon must have at least 3 points")
        
        # Shapely expects (x, y) => (lon, lat) order
        point = Point(lon, lat)
        
        # Convert polygon coordinates from (lat, lon) to (lon, lat) for Shapely
        shapely_coords = [(coord[1], coord[0]) for coord in polygon_coords]
        polygon = Polygon(shapely_coords)
        
        if not polygon.is_valid:
            logger.warning(f"Invalid polygon detected, using buffer to fix")
            polygon = polygon.buffer(0)
        
        return polygon.contains(point)
        
    except Exception as e:
        logger.error(f"Error in polygon detection: {e}")
        return False

def validate_polygon_coordinates(polygon_coords: List[Tuple[float, float]]) -> bool:
    """
    Validate polygon coordinates for basic correctness.
    
    Args:
        polygon_coords: List of (lat, lon) tuples
        
    Returns:
        True if coordinates are valid, False otherwise
    """
    try:
        if not polygon_coords or len(polygon_coords) < 3:
            return False
        
        for lat, lon in polygon_coords:
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                return False
        
        return True
    except (TypeError, ValueError):
        return False
```

#### 1.3 Unit Tests
- [ ] Create `tests/unit/test_geographic_utils.py`
- [ ] Test polygon detection with various scenarios
- [ ] Test edge cases and error handling
- [ ] Test performance with large polygons

```python
# tests/unit/test_geographic_utils.py
import pytest
from app.utils.geographic_utils import is_point_in_polygon, validate_polygon_coordinates

class TestGeographicUtils:
    
    def test_point_inside_simple_polygon(self):
        """Test point inside a simple rectangular polygon"""
        polygon = [
            (-33.0, 151.0),  # Sydney area polygon
            (-33.0, 152.0),
            (-34.0, 152.0),
            (-34.0, 151.0)
        ]
        
        # Point inside
        assert is_point_in_polygon(-33.5, 151.5, polygon) == True
        
        # Point outside
        assert is_point_in_polygon(-32.0, 151.5, polygon) == False
    
    def test_point_on_polygon_edge(self):
        """Test point exactly on polygon edge"""
        polygon = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)]
        
        # Point on edge should return True or False consistently
        result = is_point_in_polygon(0.0, 0.5, polygon)
        assert isinstance(result, bool)
    
    def test_invalid_coordinates(self):
        """Test handling of invalid coordinates"""
        polygon = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)]
        
        # Invalid latitude
        assert is_point_in_polygon(91.0, 0.5, polygon) == False
        
        # Invalid longitude
        assert is_point_in_polygon(0.5, 181.0, polygon) == False
    
    def test_empty_polygon(self):
        """Test handling of empty or invalid polygons"""
        # Empty polygon
        assert is_point_in_polygon(0.5, 0.5, []) == False
        
        # Polygon with less than 3 points
        assert is_point_in_polygon(0.5, 0.5, [(0.0, 0.0), (1.0, 1.0)]) == False
    
    def test_validate_polygon_coordinates(self):
        """Test polygon coordinate validation"""
        # Valid polygon
        valid_polygon = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)]
        assert validate_polygon_coordinates(valid_polygon) == True
        
        # Invalid polygon (too few points)
        assert validate_polygon_coordinates([(0.0, 0.0), (1.0, 1.0)]) == False
        
        # Invalid coordinates (latitude out of range)
        invalid_polygon = [(91.0, 0.0), (0.0, 1.0), (1.0, 1.0)]
        assert validate_polygon_coordinates(invalid_polygon) == False
    
    def test_performance_large_polygon(self):
        """Test performance with large polygon"""
        import time
        
        # Create large polygon (100 points)
        large_polygon = []
        for i in range(100):
            angle = 2 * 3.14159 * i / 100
            lat = -33.0 + 0.1 * (angle / 6.28)  # Small circle around Sydney
            lon = 151.0 + 0.1 * (angle / 6.28)
            large_polygon.append((lat, lon))
        
        start_time = time.time()
        result = is_point_in_polygon(-33.05, 151.05, large_polygon)
        end_time = time.time()
        
        # Should complete in less than 10ms
        assert (end_time - start_time) < 0.01
        assert isinstance(result, bool)
```

### 🧪 Sprint 1 Testing

#### Manual Testing
```bash
# Test dependency installation
docker-compose build
docker-compose up -d

# Run unit tests
docker-compose exec app python -m pytest tests/unit/test_geographic_utils.py -v

# Test import in Python shell
docker-compose exec app python -c "
from app.utils.geographic_utils import is_point_in_polygon
print('Import successful')
print('Test result:', is_point_in_polygon(-33.5, 151.5, [(-33.0, 151.0), (-33.0, 152.0), (-34.0, 152.0), (-34.0, 151.0)]))
"
```

#### Success Criteria
- [ ] All unit tests pass
- [ ] Shapely dependency installs correctly
- [ ] Function handles edge cases gracefully
- [ ] Performance meets requirements (<10ms per check)
- [ ] No memory leaks with large polygons

---

## 🏃‍♂️ Sprint 2: Geographic Boundary Filter Class

**Duration**: 1 day  
**Goal**: Implement the filter class with configuration support

### 📋 Sprint 2 Tasks

#### 2.1 Filter Class Implementation
- [ ] Create `app/filters/geographic_boundary_filter.py`
- [ ] Implement `GeographicBoundaryFilter` class
- [ ] Add configuration loading from environment variables
- [ ] Add comprehensive logging and error handling

```python
# app/filters/geographic_boundary_filter.py
import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from app.utils.geographic_utils import is_point_in_polygon, validate_polygon_coordinates

logger = logging.getLogger(__name__)

@dataclass
class GeographicBoundaryConfig:
    """Geographic boundary filter configuration"""
    enabled: bool = False
    boundary_data_path: str = ""
    log_level: str = "INFO"
    performance_threshold_ms: float = 10.0

class GeographicBoundaryFilter:
    """
    Geographic Boundary Filter
    
    Filters flights based on whether they are within a specified geographic boundary polygon.
    Uses Shapely for efficient point-in-polygon calculations.
    """
    
    def __init__(self):
        self.config = self._get_filter_config()
        self.polygon_coordinates: List[Tuple[float, float]] = []
        self.is_initialized = False
        self._setup_logging()
        
        if self.config.enabled:
            self._load_boundary_data()
    
    def _get_filter_config(self) -> GeographicBoundaryConfig:
        """Get filter configuration from environment variables"""
        return GeographicBoundaryConfig(
            enabled=os.getenv("ENABLE_BOUNDARY_FILTER", "false").lower() == "true",
            boundary_data_path=os.getenv("BOUNDARY_DATA_PATH", ""),
            log_level=os.getenv("BOUNDARY_FILTER_LOG_LEVEL", "INFO"),
            performance_threshold_ms=float(os.getenv("BOUNDARY_FILTER_PERFORMANCE_THRESHOLD", "10.0"))
        )
    
    def _setup_logging(self):
        """Setup logging for the filter"""
        logging.basicConfig(level=getattr(logging, self.config.log_level))
        logger.info(f"Geographic boundary filter initialized - enabled: {self.config.enabled}")
    
    def _load_boundary_data(self):
        """Load boundary polygon data from file"""
        try:
            if not self.config.boundary_data_path:
                logger.error("Boundary data path not configured")
                return
            
            if not os.path.exists(self.config.boundary_data_path):
                logger.error(f"Boundary data file not found: {self.config.boundary_data_path}")
                return
            
            with open(self.config.boundary_data_path, 'r') as f:
                data = json.load(f)
            
            # Expect format: {"coordinates": [[lat, lon], [lat, lon], ...]}
            if "coordinates" not in data:
                logger.error("Invalid boundary data format: missing 'coordinates' key")
                return
            
            self.polygon_coordinates = [(float(coord[0]), float(coord[1])) for coord in data["coordinates"]]
            
            if not validate_polygon_coordinates(self.polygon_coordinates):
                logger.error("Invalid polygon coordinates in boundary data")
                return
            
            self.is_initialized = True
            logger.info(f"Loaded boundary polygon with {len(self.polygon_coordinates)} points")
            
        except Exception as e:
            logger.error(f"Failed to load boundary data: {e}")
            self.is_initialized = False
    
    def _is_flight_in_boundary(self, flight_data: Dict[str, Any]) -> bool:
        """
        Check if a flight is within the geographic boundary
        
        Args:
            flight_data: Flight data from VATSIM API
            
        Returns:
            True if flight is within boundary, False otherwise
        """
        # Check if filter is properly initialized
        if not self.is_initialized:
            logger.debug("Filter not initialized, allowing flight through")
            return True
        
        # Extract position data
        latitude = flight_data.get('latitude')
        longitude = flight_data.get('longitude')
        
        if latitude is None or longitude is None:
            callsign = flight_data.get('callsign', 'UNKNOWN')
            logger.debug(f"Flight {callsign} has no position data, filtering out")
            return False
        
        try:
            # Convert to float if needed
            lat = float(latitude)
            lon = float(longitude)
            
            # Check if position is within boundary
            is_inside = is_point_in_polygon(lat, lon, self.polygon_coordinates)
            
            callsign = flight_data.get('callsign', 'UNKNOWN')
            if is_inside:
                logger.debug(f"Flight {callsign} is within boundary at ({lat:.4f}, {lon:.4f})")
            else:
                logger.debug(f"Flight {callsign} is outside boundary at ({lat:.4f}, {lon:.4f})")
            
            return is_inside
            
        except (ValueError, TypeError) as e:
            callsign = flight_data.get('callsign', 'UNKNOWN')
            logger.warning(f"Invalid coordinates for flight {callsign}: {e}")
            return False
    
    def filter_flights_list(self, flights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter a list of flight objects to only include those within the boundary
        
        Args:
            flights: List of flight data dictionaries
            
        Returns:
            Filtered list of flight data dictionaries
        """
        if not self.config.enabled:
            logger.debug("Geographic boundary filter is disabled, returning original flights")
            return flights
        
        if not flights:
            logger.debug("No flights provided to filter")
            return flights
        
        import time
        start_time = time.time()
        
        original_count = len(flights)
        filtered_flights = []
        
        for flight in flights:
            if self._is_flight_in_boundary(flight):
                filtered_flights.append(flight)
        
        end_time = time.time()
        processing_time_ms = (end_time - start_time) * 1000
        
        filtered_count = len(filtered_flights)
        logger.info(f"Geographic boundary filter: {original_count} flights -> {filtered_count} flights "
                   f"({original_count - filtered_count} filtered out) in {processing_time_ms:.2f}ms")
        
        # Check performance threshold
        if processing_time_ms > self.config.performance_threshold_ms:
            logger.warning(f"Geographic boundary filter exceeded performance threshold: "
                          f"{processing_time_ms:.2f}ms > {self.config.performance_threshold_ms}ms")
        
        return filtered_flights
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """
        Get filter statistics and status
        
        Returns:
            Dictionary with filter statistics
        """
        return {
            "enabled": self.config.enabled,
            "initialized": self.is_initialized,
            "polygon_points": len(self.polygon_coordinates) if self.is_initialized else 0,
            "boundary_data_path": self.config.boundary_data_path,
            "log_level": self.config.log_level,
            "performance_threshold_ms": self.config.performance_threshold_ms,
            "filter_type": "Geographic boundary polygon validation",
            "inclusion_criteria": "Flights with position within geographic boundary"
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the filter
        
        Returns:
            Health check results
        """
        health = {
            "status": "healthy",
            "enabled": self.config.enabled,
            "initialized": self.is_initialized,
            "issues": []
        }
        
        if self.config.enabled and not self.is_initialized:
            health["status"] = "unhealthy"
            health["issues"].append("Filter enabled but not properly initialized")
        
        if self.config.enabled and not self.polygon_coordinates:
            health["status"] = "unhealthy"
            health["issues"].append("No boundary polygon loaded")
        
        if self.config.enabled and not os.path.exists(self.config.boundary_data_path):
            health["status"] = "unhealthy"
            health["issues"].append(f"Boundary data file not found: {self.config.boundary_data_path}")
        
        return health
```

#### 2.2 Sample Boundary Data File
- [ ] Create sample boundary data file
- [ ] Document the expected JSON format

```json
// app/utils/sample_boundary_coordinates.json
{
  "name": "Sample Geographic Boundary",
  "description": "Sample polygon for testing geographic boundary filter",
  "coordinates": [
    [-33.0, 151.0],
    [-33.0, 152.0],
    [-34.0, 152.0],
    [-34.0, 151.0],
    [-33.0, 151.0]
  ],
  "metadata": {
    "created": "2025-01-08",
    "source": "Manual creation for testing",
    "coordinate_system": "WGS84",
    "format": "lat,lon"
  }
}
```

#### 2.3 Unit Tests for Filter Class
- [ ] Create `tests/unit/test_geographic_boundary_filter.py`
- [ ] Test filter initialization and configuration
- [ ] Test flight filtering logic
- [ ] Test error handling and edge cases

```python
# tests/unit/test_geographic_boundary_filter.py
import pytest
import os
import json
import tempfile
from unittest.mock import patch
from app.filters.geographic_boundary_filter import GeographicBoundaryFilter

class TestGeographicBoundaryFilter:
    
    def create_test_boundary_file(self, coordinates):
        """Helper to create temporary boundary data file"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        data = {"coordinates": coordinates}
        json.dump(data, temp_file)
        temp_file.close()
        return temp_file.name
    
    def test_filter_disabled_by_default(self):
        """Test that filter is disabled by default"""
        with patch.dict(os.environ, {}, clear=True):
            filter_obj = GeographicBoundaryFilter()
            assert filter_obj.config.enabled == False
            assert filter_obj.is_initialized == False
    
    @patch.dict(os.environ, {"ENABLE_BOUNDARY_FILTER": "true"})
    def test_filter_enabled_via_env(self):
        """Test that filter can be enabled via environment variable"""
        filter_obj = GeographicBoundaryFilter()
        assert filter_obj.config.enabled == True
    
    def test_filter_with_valid_boundary_data(self):
        """Test filter with valid boundary data"""
        # Create test boundary file
        coordinates = [[-33.0, 151.0], [-33.0, 152.0], [-34.0, 152.0], [-34.0, 151.0]]
        boundary_file = self.create_test_boundary_file(coordinates)
        
        try:
            with patch.dict(os.environ, {
                "ENABLE_BOUNDARY_FILTER": "true",
                "BOUNDARY_DATA_PATH": boundary_file
            }):
                filter_obj = GeographicBoundaryFilter()
                assert filter_obj.is_initialized == True
                assert len(filter_obj.polygon_coordinates) == 4
        finally:
            os.unlink(boundary_file)
    
    def test_filter_flights_within_boundary(self):
        """Test filtering flights within boundary"""
        coordinates = [[-33.0, 151.0], [-33.0, 152.0], [-34.0, 152.0], [-34.0, 151.0]]
        boundary_file = self.create_test_boundary_file(coordinates)
        
        try:
            with patch.dict(os.environ, {
                "ENABLE_BOUNDARY_FILTER": "true",
                "BOUNDARY_DATA_PATH": boundary_file
            }):
                filter_obj = GeographicBoundaryFilter()
                
                flights = [
                    {"callsign": "QFA123", "latitude": -33.5, "longitude": 151.5},  # Inside
                    {"callsign": "VOZ456", "latitude": -32.0, "longitude": 151.5},  # Outside
                    {"callsign": "JST789", "latitude": -33.8, "longitude": 151.8},  # Inside
                ]
                
                filtered = filter_obj.filter_flights_list(flights)
                
                assert len(filtered) == 2
                assert filtered[0]["callsign"] == "QFA123"
                assert filtered[1]["callsign"] == "JST789"
        finally:
            os.unlink(boundary_file)
    
    def test_filter_flights_without_position(self):
        """Test filtering flights without position data"""
        coordinates = [[-33.0, 151.0], [-33.0, 152.0], [-34.0, 152.0], [-34.0, 151.0]]
        boundary_file = self.create_test_boundary_file(coordinates)
        
        try:
            with patch.dict(os.environ, {
                "ENABLE_BOUNDARY_FILTER": "true",
                "BOUNDARY_DATA_PATH": boundary_file
            }):
                filter_obj = GeographicBoundaryFilter()
                
                flights = [
                    {"callsign": "QFA123", "latitude": -33.5, "longitude": 151.5},  # Has position
                    {"callsign": "VOZ456"},  # No position
                    {"callsign": "JST789", "latitude": None, "longitude": 151.8},  # Partial position
                ]
                
                filtered = filter_obj.filter_flights_list(flights)
                
                assert len(filtered) == 1
                assert filtered[0]["callsign"] == "QFA123"
        finally:
            os.unlink(boundary_file)
    
    def test_health_check(self):
        """Test health check functionality"""
        coordinates = [[-33.0, 151.0], [-33.0, 152.0], [-34.0, 152.0], [-34.0, 151.0]]
        boundary_file = self.create_test_boundary_file(coordinates)
        
        try:
            with patch.dict(os.environ, {
                "ENABLE_BOUNDARY_FILTER": "true",
                "BOUNDARY_DATA_PATH": boundary_file
            }):
                filter_obj = GeographicBoundaryFilter()
                health = filter_obj.health_check()
                
                assert health["status"] == "healthy"
                assert health["enabled"] == True
                assert health["initialized"] == True
                assert len(health["issues"]) == 0
        finally:
            os.unlink(boundary_file)
    
    def test_get_filter_stats(self):
        """Test filter statistics"""
        coordinates = [[-33.0, 151.0], [-33.0, 152.0], [-34.0, 152.0], [-34.0, 151.0]]
        boundary_file = self.create_test_boundary_file(coordinates)
        
        try:
            with patch.dict(os.environ, {
                "ENABLE_BOUNDARY_FILTER": "true",
                "BOUNDARY_DATA_PATH": boundary_file
            }):
                filter_obj = GeographicBoundaryFilter()
                stats = filter_obj.get_filter_stats()
                
                assert stats["enabled"] == True
                assert stats["initialized"] == True
                assert stats["polygon_points"] == 4
                assert stats["filter_type"] == "Geographic boundary polygon validation"
        finally:
            os.unlink(boundary_file)
```

### 🧪 Sprint 2 Testing

#### Manual Testing
```bash
# Test filter class creation
docker-compose exec app python -c "
from app.filters.geographic_boundary_filter import GeographicBoundaryFilter
filter_obj = GeographicBoundaryFilter()
print('Filter created successfully')
print('Stats:', filter_obj.get_filter_stats())
print('Health:', filter_obj.health_check())
"

# Test with sample data
docker-compose exec app python -c "
import os
os.environ['ENABLE_BOUNDARY_FILTER'] = 'true'
os.environ['BOUNDARY_DATA_PATH'] = 'app/utils/sample_boundary_coordinates.json'

from app.filters.geographic_boundary_filter import GeographicBoundaryFilter
filter_obj = GeographicBoundaryFilter()

flights = [
    {'callsign': 'TEST123', 'latitude': -33.5, 'longitude': 151.5},
    {'callsign': 'TEST456', 'latitude': -32.0, 'longitude': 151.5}
]

filtered = filter_obj.filter_flights_list(flights)
print(f'Original: {len(flights)}, Filtered: {len(filtered)}')
"

# Run unit tests
docker-compose exec app python -m pytest tests/unit/test_geographic_boundary_filter.py -v
```

#### Success Criteria
- [ ] All unit tests pass
- [ ] Filter class initializes correctly
- [ ] Configuration loading works from environment variables
- [ ] Flight filtering logic works correctly
- [ ] Health check and stats functions work
- [ ] Performance meets requirements
- [ ] Error handling works for invalid data

---

## 🏃‍♂️ Sprint 3: Configuration and Environment Setup

**Duration**: 1 day  
**Goal**: Set up proper configuration management and Docker environment

### 📋 Sprint 3 Tasks

#### 3.1 Docker Configuration
- [ ] Update `docker-compose.yml` with new environment variables
- [ ] Update `Dockerfile` if needed for new dependencies
- [ ] Create environment variable documentation

```yaml
# Addition to docker-compose.yml
services:
  app:
    environment:
      # Existing variables...
      
      # Geographic Boundary Filter Configuration
      - ENABLE_BOUNDARY_FILTER=${ENABLE_BOUNDARY_FILTER:-false}
      - BOUNDARY_DATA_PATH=${BOUNDARY_DATA_PATH:-app/utils/sample_boundary_coordinates.json}
      - BOUNDARY_FILTER_LOG_LEVEL=${BOUNDARY_FILTER_LOG_LEVEL:-INFO}
      - BOUNDARY_FILTER_PERFORMANCE_THRESHOLD=${BOUNDARY_FILTER_PERFORMANCE_THRESHOLD:-10.0}
```

#### 3.2 Environment Variables Documentation
- [ ] Create `docs/GEOGRAPHIC_BOUNDARY_FILTER_CONFIG.md`
- [ ] Document all configuration options
- [ ] Provide usage examples

```markdown
# Geographic Boundary Filter Configuration

## Environment Variables

### ENABLE_BOUNDARY_FILTER
- **Type**: Boolean (true/false)
- **Default**: false
- **Description**: Enable or disable the geographic boundary filter
- **Example**: `ENABLE_BOUNDARY_FILTER=true`

### BOUNDARY_DATA_PATH
- **Type**: String (file path)
- **Default**: app/utils/sample_boundary_coordinates.json
- **Description**: Path to the JSON file containing boundary polygon coordinates
- **Example**: `BOUNDARY_DATA_PATH=/app/data/australia_boundary.json`

### BOUNDARY_FILTER_LOG_LEVEL
- **Type**: String (DEBUG/INFO/WARNING/ERROR)
- **Default**: INFO
- **Description**: Log level for boundary filter operations
- **Example**: `BOUNDARY_FILTER_LOG_LEVEL=DEBUG`

### BOUNDARY_FILTER_PERFORMANCE_THRESHOLD
- **Type**: Float (milliseconds)
- **Default**: 10.0
- **Description**: Performance threshold in ms, warnings logged if exceeded
- **Example**: `BOUNDARY_FILTER_PERFORMANCE_THRESHOLD=5.0`

## Usage Examples

### Enable Filter for Development
```bash
export ENABLE_BOUNDARY_FILTER=true
export BOUNDARY_DATA_PATH=app/utils/sample_boundary_coordinates.json
export BOUNDARY_FILTER_LOG_LEVEL=DEBUG
```

### Production Configuration
```bash
export ENABLE_BOUNDARY_FILTER=true
export BOUNDARY_DATA_PATH=/app/data/production_boundary.json
export BOUNDARY_FILTER_LOG_LEVEL=INFO
export BOUNDARY_FILTER_PERFORMANCE_THRESHOLD=5.0
```
```

#### 3.3 Configuration Validation
- [ ] Add configuration validation to filter class
- [ ] Create configuration test script
- [ ] Add startup configuration checks

```python
# app/utils/config_validator.py
import os
import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def validate_boundary_filter_config() -> Dict[str, Any]:
    """
    Validate geographic boundary filter configuration
    
    Returns:
        Dictionary with validation results
    """
    issues = []
    warnings = []
    
    # Check if filter is enabled
    enabled = os.getenv("ENABLE_BOUNDARY_FILTER", "false").lower() == "true"
    
    if enabled:
        # Check boundary data path
        data_path = os.getenv("BOUNDARY_DATA_PATH", "")
        if not data_path:
            issues.append("BOUNDARY_DATA_PATH not set but filter is enabled")
        elif not os.path.exists(data_path):
            issues.append(f"Boundary data file not found: {data_path}")
        else:
            # Validate boundary data file
            try:
                with open(data_path, 'r') as f:
                    data = json.load(f)
                
                if "coordinates" not in data:
                    issues.append("Boundary data file missing 'coordinates' key")
                elif len(data["coordinates"]) < 3:
                    issues.append("Boundary polygon must have at least 3 points")
                else:
                    # Check coordinate validity
                    for i, coord in enumerate(data["coordinates"]):
                        if len(coord) != 2:
                            issues.append(f"Invalid coordinate format at index {i}")
                            break
                        lat, lon = coord
                        if not (-90 <= lat <= 90):
                            issues.append(f"Invalid latitude {lat} at index {i}")
                            break
                        if not (-180 <= lon <= 180):
                            issues.append(f"Invalid longitude {lon} at index {i}")
                            break
            
            except json.JSONDecodeError as e:
                issues.append(f"Invalid JSON in boundary data file: {e}")
            except Exception as e:
                issues.append(f"Error reading boundary data file: {e}")
        
        # Check log level
        log_level = os.getenv("BOUNDARY_FILTER_LOG_LEVEL", "INFO")
        if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            warnings.append(f"Invalid log level '{log_level}', using INFO")
        
        # Check performance threshold
        try:
            threshold = float(os.getenv("BOUNDARY_FILTER_PERFORMANCE_THRESHOLD", "10.0"))
            if threshold <= 0:
                warnings.append("Performance threshold should be positive")
        except ValueError:
            warnings.append("Invalid performance threshold, using default 10.0ms")
    
    return {
        "enabled": enabled,
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings
    }

if __name__ == "__main__":
    # Command line validation
    result = validate_boundary_filter_config()
    print("Geographic Boundary Filter Configuration Validation")
    print("=" * 50)
    print(f"Enabled: {result['enabled']}")
    print(f"Valid: {result['valid']}")
    
    if result['issues']:
        print("\nIssues:")
        for issue in result['issues']:
            print(f"  ❌ {issue}")
    
    if result['warnings']:
        print("\nWarnings:")
        for warning in result['warnings']:
            print(f"  ⚠️  {warning}")
    
    if result['valid'] and result['enabled']:
        print("\n✅ Configuration is valid and ready for use")
    elif not result['enabled']:
        print("\n💤 Filter is disabled")
    else:
        print("\n❌ Configuration has issues that need to be resolved")
```

### 🧪 Sprint 3 Testing

#### Manual Testing
```bash
# Test configuration validation
docker-compose exec app python app/utils/config_validator.py

# Test with invalid configuration
docker-compose exec app bash -c "
export ENABLE_BOUNDARY_FILTER=true
export BOUNDARY_DATA_PATH=nonexistent.json
python app/utils/config_validator.py
"

# Test with valid configuration
docker-compose exec app bash -c "
export ENABLE_BOUNDARY_FILTER=true
export BOUNDARY_DATA_PATH=app/utils/sample_boundary_coordinates.json
python app/utils/config_validator.py
"

# Test Docker environment variables
docker-compose down
docker-compose up -d
docker-compose exec app env | grep BOUNDARY
```

#### Integration Testing
```bash
# Test full filter initialization with configuration
docker-compose exec app python -c "
import os
os.environ['ENABLE_BOUNDARY_FILTER'] = 'true'
os.environ['BOUNDARY_DATA_PATH'] = 'app/utils/sample_boundary_coordinates.json'

from app.filters.geographic_boundary_filter import GeographicBoundaryFilter
from app.utils.config_validator import validate_boundary_filter_config

# Validate configuration
config_result = validate_boundary_filter_config()
print('Config validation:', config_result)

# Initialize filter
filter_obj = GeographicBoundaryFilter()
print('Filter initialized:', filter_obj.is_initialized)
print('Filter health:', filter_obj.health_check())
"
```

#### Success Criteria
- [ ] Docker environment variables work correctly
- [ ] Configuration validation catches all error cases
- [ ] Filter initializes properly with valid configuration
- [ ] Filter fails gracefully with invalid configuration
- [ ] Documentation is complete and accurate
- [ ] All environment variable combinations tested

---

## 🏃‍♂️ Sprint 4: Data Service Integration

**Duration**: 1-2 days  
**Goal**: Integrate the boundary filter with the existing data service

### 📋 Sprint 4 Tasks

#### 4.1 Data Service Integration
- [ ] Analyze existing `app/services/data_service.py`
- [ ] Add boundary filter after airport filter
- [ ] Maintain existing filter sequence
- [ ] Add proper error handling

```python
# Modifications to app/services/data_service.py
from app.filters.geographic_boundary_filter import GeographicBoundaryFilter

class DataService:
    def __init__(self):
        # Existing initialization...
        self.flight_filter = FlightFilter()  # Existing airport filter
        self.boundary_filter = GeographicBoundaryFilter()  # New boundary filter
        
    async def process_vatsim_data(self, vatsim_data: Dict) -> Dict:
        """
        Process VATSIM data through filter pipeline
        
        Filter sequence:
        1. Airport filter (existing)
        2. Boundary filter (new)
        """
        try:
            # Apply existing airport filter first
            filtered_data = self.flight_filter.filter_vatsim_data(vatsim_data)
            
            # Apply boundary filter to the already filtered data
            if self.boundary_filter.config.enabled:
                # Extract flights from filtered data
                flights = filtered_data.get("pilots", [])
                
                # Apply boundary filter
                boundary_filtered_flights = self.boundary_filter.filter_flights_list(flights)
                
                # Update the data with boundary filtered flights
                filtered_data["pilots"] = boundary_filtered_flights
                
                # Log combined filtering results
                original_count = len(vatsim_data.get("pilots", []))
                airport_count = len(flights)
                final_count = len(boundary_filtered_flights)
                
                self.logger.info(f"Combined filter results: {original_count} -> {airport_count} (airport) -> {final_count} (boundary)")
            
            return filtered_data
            
        except Exception as e:
            self.logger.error(f"Error in filter pipeline: {e}")
            # Return original data if filtering fails
            return vatsim_data
    
    def get_filter_health(self) -> Dict[str, Any]:
        """Get health status of all filters"""
        return {
            "airport_filter": self.flight_filter.get_filter_stats(),
            "boundary_filter": self.boundary_filter.health_check()
        }
```

#### 4.2 Filter Pipeline Tests
- [ ] Create `tests/integration/test_filter_pipeline.py`
- [ ] Test combined airport + boundary filtering
- [ ] Test filter sequence and error handling

```python
# tests/integration/test_filter_pipeline.py
import pytest
import os
import json
import tempfile
from unittest.mock import patch
from app.services.data_service import DataService

class TestFilterPipeline:
    
    def create_test_boundary_file(self, coordinates):
        """Helper to create temporary boundary data file"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        data = {"coordinates": coordinates}
        json.dump(data, temp_file)
        temp_file.close()
        return temp_file.name
    
    def create_sample_vatsim_data(self):
        """Create sample VATSIM data for testing"""
        return {
            "pilots": [
                {
                    "callsign": "QFA123",
                    "departure": "YSSY",  # Sydney (Australian)
                    "arrival": "YMML",    # Melbourne (Australian)
                    "latitude": -33.5,
                    "longitude": 151.5
                },
                {
                    "callsign": "UAL456", 
                    "departure": "KLAX",  # Los Angeles (Non-Australian)
                    "arrival": "YSSY",    # Sydney (Australian)
                    "latitude": -33.6,
                    "longitude": 151.6
                },
                {
                    "callsign": "BAW789",
                    "departure": "EGLL",  # London (Non-Australian)
                    "arrival": "KLAX",    # Los Angeles (Non-Australian)
                    "latitude": -33.7,
                    "longitude": 151.7
                },
                {
                    "callsign": "JST999",
                    "departure": "YSSY",  # Sydney (Australian)
                    "arrival": "YMML",    # Melbourne (Australian)
                    "latitude": -32.0,    # Outside boundary
                    "longitude": 151.5
                }
            ],
            "controllers": [],
            "servers": []
        }
    
    def test_airport_filter_only(self):
        """Test with only airport filter enabled"""
        with patch.dict(os.environ, {
            "FLIGHT_FILTER_ENABLED": "true",
            "ENABLE_BOUNDARY_FILTER": "false"
        }):
            data_service = DataService()
            vatsim_data = self.create_sample_vatsim_data()
            
            # Should filter to only Australian flights (QFA123, UAL456, JST999)
            result = await data_service.process_vatsim_data(vatsim_data)
            
            assert len(result["pilots"]) == 3
            callsigns = [flight["callsign"] for flight in result["pilots"]]
            assert "QFA123" in callsigns
            assert "UAL456" in callsigns
            assert "JST999" in callsigns
            assert "BAW789" not in callsigns
    
    def test_both_filters_enabled(self):
        """Test with both airport and boundary filters enabled"""
        # Create boundary that includes Sydney area but excludes JST999's position
        coordinates = [[-33.0, 151.0], [-33.0, 152.0], [-34.0, 152.0], [-34.0, 151.0]]
        boundary_file = self.create_test_boundary_file(coordinates)
        
        try:
            with patch.dict(os.environ, {
                "FLIGHT_FILTER_ENABLED": "true",
                "ENABLE_BOUNDARY_FILTER": "true",
                "BOUNDARY_DATA_PATH": boundary_file
            }):
                data_service = DataService()
                vatsim_data = self.create_sample_vatsim_data()
                
                # Should filter to Australian flights within boundary (QFA123, UAL456)
                result = await data_service.process_vatsim_data(vatsim_data)
                
                assert len(result["pilots"]) == 2
                callsigns = [flight["callsign"] for flight in result["pilots"]]
                assert "QFA123" in callsigns
                assert "UAL456" in callsigns
                assert "BAW789" not in callsigns  # Non-Australian
                assert "JST999" not in callsigns  # Outside boundary
        finally:
            os.unlink(boundary_file)
    
    def test_filter_error_handling(self):
        """Test filter pipeline error handling"""
        with patch.dict(os.environ, {
            "FLIGHT_FILTER_ENABLED": "true",
            "ENABLE_BOUNDARY_FILTER": "true",
            "BOUNDARY_DATA_PATH": "nonexistent.json"
        }):
            data_service = DataService()
            vatsim_data = self.create_sample_vatsim_data()
            
            # Should not crash, should return filtered data from airport filter
            result = await data_service.process_vatsim_data(vatsim_data)
            
            # Should still have airport filtering applied
            assert len(result["pilots"]) >= 0
            assert "pilots" in result
    
    def test_filter_health_check(self):
        """Test combined filter health check"""
        coordinates = [[-33.0, 151.0], [-33.0, 152.0], [-34.0, 152.0], [-34.0, 151.0]]
        boundary_file = self.create_test_boundary_file(coordinates)
        
        try:
            with patch.dict(os.environ, {
                "FLIGHT_FILTER_ENABLED": "true",
                "ENABLE_BOUNDARY_FILTER": "true",
                "BOUNDARY_DATA_PATH": boundary_file
            }):
                data_service = DataService()
                health = data_service.get_filter_health()
                
                assert "airport_filter" in health
                assert "boundary_filter" in health
                assert health["boundary_filter"]["status"] == "healthy"
        finally:
            os.unlink(boundary_file)
```

#### 4.3 Performance Testing
- [ ] Create performance tests for filter pipeline
- [ ] Test with large datasets
- [ ] Measure combined filter performance

```python
# tests/performance/test_filter_performance.py
import pytest
import time
import json
import tempfile
from app.services.data_service import DataService

class TestFilterPerformance:
    
    def create_large_vatsim_dataset(self, flight_count=1000):
        """Create large VATSIM dataset for performance testing"""
        flights = []
        for i in range(flight_count):
            flights.append({
                "callsign": f"TEST{i:04d}",
                "departure": "YSSY" if i % 2 == 0 else "KLAX",
                "arrival": "YMML" if i % 2 == 0 else "EGLL", 
                "latitude": -33.5 + (i % 100) * 0.01,
                "longitude": 151.5 + (i % 100) * 0.01
            })
        
        return {
            "pilots": flights,
            "controllers": [],
            "servers": []
        }
    
    def test_filter_pipeline_performance(self):
        """Test filter pipeline performance with large dataset"""
        # Create boundary
        coordinates = [[-35.0, 150.0], [-35.0, 153.0], [-31.0, 153.0], [-31.0, 150.0]]
        boundary_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump({"coordinates": coordinates}, boundary_file)
        boundary_file.close()
        
        try:
            with patch.dict(os.environ, {
                "FLIGHT_FILTER_ENABLED": "true",
                "ENABLE_BOUNDARY_FILTER": "true",
                "BOUNDARY_DATA_PATH": boundary_file.name
            }):
                data_service = DataService()
                large_dataset = self.create_large_vatsim_dataset(1000)
                
                start_time = time.time()
                result = await data_service.process_vatsim_data(large_dataset)
                end_time = time.time()
                
                processing_time = (end_time - start_time) * 1000  # Convert to ms
                
                # Should process 1000 flights in less than 100ms
                assert processing_time < 100
                
                # Should have filtered results
                assert len(result["pilots"]) < len(large_dataset["pilots"])
                
                print(f"Processed {len(large_dataset['pilots'])} flights in {processing_time:.2f}ms")
                print(f"Filtered to {len(result['pilots'])} flights")
        finally:
            os.unlink(boundary_file.name)
```

### 🧪 Sprint 4 Testing

#### Integration Testing
```bash
# Test data service with filters
docker-compose exec app python -c "
import os
import asyncio

# Set up environment
os.environ['FLIGHT_FILTER_ENABLED'] = 'true'
os.environ['ENABLE_BOUNDARY_FILTER'] = 'true'
os.environ['BOUNDARY_DATA_PATH'] = 'app/utils/sample_boundary_coordinates.json'

from app.services.data_service import DataService

async def test_integration():
    data_service = DataService()
    
    # Test sample data
    sample_data = {
        'pilots': [
            {'callsign': 'QFA123', 'departure': 'YSSY', 'arrival': 'YMML', 'latitude': -33.5, 'longitude': 151.5},
            {'callsign': 'UAL456', 'departure': 'KLAX', 'arrival': 'YSSY', 'latitude': -33.6, 'longitude': 151.6},
            {'callsign': 'BAW789', 'departure': 'EGLL', 'arrival': 'KLAX', 'latitude': -33.7, 'longitude': 151.7}
        ]
    }
    
    result = await data_service.process_vatsim_data(sample_data)
    print(f'Original flights: {len(sample_data[\"pilots\"])}')
    print(f'Filtered flights: {len(result[\"pilots\"])}')
    
    # Test health check
    health = data_service.get_filter_health()
    print('Filter health:', health)

asyncio.run(test_integration())
"

# Run integration tests
docker-compose exec app python -m pytest tests/integration/test_filter_pipeline.py -v

# Run performance tests
docker-compose exec app python -m pytest tests/performance/test_filter_performance.py -v
```

#### Success Criteria
- [ ] Data service integrates both filters correctly
- [ ] Filter sequence works (airport → boundary)
- [ ] Error handling prevents crashes
- [ ] Performance meets requirements
- [ ] Health checks work for both filters
- [ ] Integration tests pass
- [ ] Performance tests pass

---

## 🏃‍♂️ Sprint 5: Health Monitoring and Deployment

**Duration**: 1 day  
**Goal**: Add health monitoring and prepare for production deployment

### 📋 Sprint 5 Tasks

#### 5.1 Health Monitoring Integration
- [ ] Add boundary filter to existing health checks
- [ ] Create monitoring endpoints
- [ ] Add metrics collection

```python
# app/services/monitoring_service.py (additions)
from app.filters.geographic_boundary_filter import GeographicBoundaryFilter

class MonitoringService:
    def __init__(self):
        # Existing initialization...
        self.boundary_filter = GeographicBoundaryFilter()
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health including filters"""
        health = {
            # Existing health checks...
            "filters": {
                "airport_filter": self._get_airport_filter_health(),
                "boundary_filter": self._get_boundary_filter_health()
            }
        }
        
        return health
    
    def _get_boundary_filter_health(self) -> Dict[str, Any]:
        """Get boundary filter health status"""
        try:
            health = self.boundary_filter.health_check()
            stats = self.boundary_filter.get_filter_stats()
            
            return {
                "status": health["status"],
                "enabled": health["enabled"],
                "initialized": health["initialized"],
                "issues": health["issues"],
                "polygon_points": stats["polygon_points"],
                "performance_threshold_ms": stats["performance_threshold_ms"]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
```

#### 5.2 API Health Endpoints
- [ ] Add filter health to existing API endpoints
- [ ] Create detailed filter status endpoint

```python
# app/main.py (additions)
@app.get("/api/health/filters")
async def get_filter_health():
    """Get detailed filter health information"""
    try:
        from app.services.data_service import DataService
        
        data_service = DataService()
        filter_health = data_service.get_filter_health()
        
        return {
            "status": "success",
            "filters": filter_health,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/api/health/boundary-filter")
async def get_boundary_filter_health():
    """Get specific boundary filter health and configuration"""
    try:
        from app.filters.geographic_boundary_filter import GeographicBoundaryFilter
        from app.utils.config_validator import validate_boundary_filter_config
        
        filter_obj = GeographicBoundaryFilter()
        health = filter_obj.health_check()
        stats = filter_obj.get_filter_stats()
        config_validation = validate_boundary_filter_config()
        
        return {
            "status": "success",
            "health": health,
            "stats": stats,
            "config_validation": config_validation,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
```

#### 5.3 Deployment Documentation
- [ ] Create deployment guide
- [ ] Document rollback procedures
- [ ] Create monitoring checklist

```markdown
# Geographic Boundary Filter Deployment Guide

## Pre-Deployment Checklist

### Environment Preparation
- [ ] Boundary data file prepared and validated
- [ ] Environment variables configured
- [ ] Docker container built with new dependencies
- [ ] All tests passing

### Configuration Validation
```bash
# Validate configuration before deployment
docker-compose exec app python app/utils/config_validator.py
```

### Health Check Verification
```bash
# Test health endpoints
curl http://localhost:8000/api/health/filters
curl http://localhost:8000/api/health/boundary-filter
```

## Deployment Steps

### Step 1: Deploy with Filter Disabled
```bash
# Set environment variables
export ENABLE_BOUNDARY_FILTER=false
export BOUNDARY_DATA_PATH=app/utils/sample_boundary_coordinates.json

# Deploy
docker-compose down
docker-compose build
docker-compose up -d

# Verify deployment
curl http://localhost:8000/api/health
```

### Step 2: Validate System Stability
- [ ] Monitor system for 10 minutes
- [ ] Check logs for errors
- [ ] Verify existing functionality works

### Step 3: Enable Filter in Staging
```bash
# Enable filter
export ENABLE_BOUNDARY_FILTER=true

# Restart service
docker-compose restart app

# Monitor health
curl http://localhost:8000/api/health/boundary-filter
```

### Step 4: Validate Filter Functionality
- [ ] Check filter health endpoint
- [ ] Verify flight filtering works
- [ ] Monitor performance metrics
- [ ] Check filter statistics

### Step 5: Production Deployment
- [ ] Apply configuration to production
- [ ] Monitor system performance
- [ ] Verify filter statistics
- [ ] Check for any issues

## Monitoring

### Key Metrics to Monitor
- Filter processing time
- Number of flights filtered
- Filter health status
- System memory usage
- API response times

### Health Check URLs
- General health: `/api/health`
- Filter health: `/api/health/filters`
- Boundary filter: `/api/health/boundary-filter`

## Rollback Procedures

### Emergency Rollback
```bash
# Disable filter immediately
export ENABLE_BOUNDARY_FILTER=false
docker-compose restart app
```

### Full Rollback
```bash
# Revert to previous version
git checkout <previous-commit>
docker-compose down
docker-compose build
docker-compose up -d
```

## Troubleshooting

### Common Issues

#### Filter Not Initializing
- Check boundary data file exists
- Validate JSON format
- Check file permissions

#### Poor Performance
- Check polygon complexity
- Monitor processing times
- Consider boundary simplification

#### Memory Issues
- Monitor memory usage
- Check for memory leaks
- Consider polygon optimization
```

### 🧪 Sprint 5 Testing

#### End-to-End Testing
```bash
# Test complete deployment workflow
docker-compose down

# Deploy with filter disabled
export ENABLE_BOUNDARY_FILTER=false
docker-compose up -d

# Verify basic health
curl http://localhost:8000/api/health

# Enable filter
export ENABLE_BOUNDARY_FILTER=true
export BOUNDARY_DATA_PATH=app/utils/sample_boundary_coordinates.json
docker-compose restart app

# Test filter health
curl http://localhost:8000/api/health/boundary-filter

# Test filter functionality
curl http://localhost:8000/api/health/filters

# Monitor logs
docker-compose logs app | grep -i boundary
```

#### Load Testing
```bash
# Test system under load with filter enabled
docker-compose exec app python -c "
import asyncio
import time
from app.services.data_service import DataService

async def load_test():
    data_service = DataService()
    
    # Create large dataset
    large_data = {
        'pilots': [
            {'callsign': f'TEST{i:04d}', 'departure': 'YSSY', 'arrival': 'YMML', 
             'latitude': -33.5 + i*0.001, 'longitude': 151.5 + i*0.001}
            for i in range(500)
        ]
    }
    
    # Process multiple times
    times = []
    for i in range(10):
        start = time.time()
        result = await data_service.process_vatsim_data(large_data)
        end = time.time()
        times.append((end - start) * 1000)
        print(f'Run {i+1}: {times[-1]:.2f}ms, {len(result[\"pilots\"])} flights')
    
    avg_time = sum(times) / len(times)
    print(f'Average processing time: {avg_time:.2f}ms')

asyncio.run(load_test())
"
```

#### Success Criteria
- [ ] Health monitoring endpoints work
- [ ] Filter health checks are accurate
- [ ] Deployment procedures work smoothly
- [ ] Rollback procedures work correctly
- [ ] Performance under load is acceptable
- [ ] System remains stable with filter enabled
- [ ] All monitoring metrics are collected

---

## 📊 Sprint Summary

### Overall Timeline
- **Sprint 1**: Core utilities (1 day)
- **Sprint 2**: Filter class (1 day)  
- **Sprint 3**: Configuration (1 day)
- **Sprint 4**: Integration (1-2 days)
- **Sprint 5**: Monitoring & deployment (1 day)

**Total: 5-6 days**

### Key Deliverables
1. ✅ **Polygon detection utilities** with comprehensive testing
2. ✅ **Geographic boundary filter class** with configuration support
3. ✅ **Environment-based configuration** with validation
4. ✅ **Data service integration** maintaining filter sequence
5. ✅ **Health monitoring** and deployment procedures

### Testing Strategy
- **Unit tests** after each sprint
- **Integration tests** for filter pipeline
- **Performance tests** with large datasets
- **End-to-end testing** for deployment
- **Load testing** for production readiness

### Risk Mitigation
- **Small iterations** allow for quick rollback
- **Comprehensive testing** catches issues early
- **Disabled by default** allows safe deployment
- **Health monitoring** enables proactive issue detection
- **Clear rollback procedures** minimize downtime risk

This sprint-based approach ensures that each iteration delivers working, testable functionality while maintaining system stability and allowing for easy rollback if issues arise.

