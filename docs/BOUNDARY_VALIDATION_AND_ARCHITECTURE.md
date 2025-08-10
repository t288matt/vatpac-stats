# Boundary Validation and Service Architecture

## ⚠️ **DEPRECATION NOTICE - December 2024**

**This document contains outdated architecture information that no longer reflects the current system.**

**What Changed:**
- ❌ **Service Interfaces**: The `app/services/interfaces/` directory has been removed
- ❌ **Abstract Base Classes**: No more ABC imports or abstract methods
- ❌ **Interface Implementations**: Services now use direct imports instead of interfaces

**Current Architecture:**
- ✅ **Direct Service Imports**: Services are imported and used directly
- ✅ **Simplified Architecture**: No interface layer overhead
- ✅ **Cleaner Code Paths**: Direct service instantiation and usage

**Status**: This document is kept for historical reference but should not be used for current development.

---

## 🎯 Polygon Boundary Validation Strategy

### Overview
Ensuring the polygon correctly defines the user's required airspace is critical for system accuracy. This document outlines comprehensive validation strategies and service architecture principles.

---

## 🧪 Polygon Validation Testing

### 1. Known Point Testing
Test with well-known geographic locations to verify boundary accuracy.

```python
# tests/validation/test_boundary_accuracy.py
import pytest
from app.utils.geographic_utils import is_point_in_polygon

class TestBoundaryAccuracy:
    """Test boundary polygon with known geographic points"""
    
    def load_boundary_coordinates(self):
        """Load the actual boundary coordinates to be validated"""
        # This would load the user's specific boundary data
        pass
    
    def test_major_airports_inside_boundary(self):
        """Test that major airports that should be inside are correctly identified"""
        boundary_coords = self.load_boundary_coordinates()
        
        # Define known airports that SHOULD be inside the boundary
        airports_inside = [
            {"name": "Sydney Airport", "code": "YSSY", "lat": -33.9399, "lon": 151.1753},
            {"name": "Melbourne Airport", "code": "YMML", "lat": -37.6690, "lon": 144.8410},
            {"name": "Brisbane Airport", "code": "YBBN", "lat": -27.3842, "lon": 153.1175},
            # Add more based on user requirements
        ]
        
        for airport in airports_inside:
            result = is_point_in_polygon(airport["lat"], airport["lon"], boundary_coords)
            assert result == True, f"{airport['name']} ({airport['code']}) should be inside boundary but was outside"
    
    def test_major_airports_outside_boundary(self):
        """Test that major airports that should be outside are correctly identified"""
        boundary_coords = self.load_boundary_coordinates()
        
        # Define known airports that SHOULD be outside the boundary
        airports_outside = [
            {"name": "Los Angeles Airport", "code": "KLAX", "lat": 34.0522, "lon": -118.2437},
            {"name": "London Heathrow", "code": "EGLL", "lat": 51.4700, "lon": -0.4543},
            {"name": "Singapore Changi", "code": "WSSS", "lat": 1.3644, "lon": 103.9915},
            # Add more based on user requirements
        ]
        
        for airport in airports_outside:
            result = is_point_in_polygon(airport["lat"], airport["lon"], boundary_coords)
            assert result == False, f"{airport['name']} ({airport['code']}) should be outside boundary but was inside"
    
    def test_boundary_edge_points(self):
        """Test points very close to boundary edges"""
        boundary_coords = self.load_boundary_coordinates()
        
        # Test points just inside and just outside boundary edges
        edge_test_points = [
            {"name": "Just inside northern edge", "lat": -10.001, "lon": 141.0, "expected": True},
            {"name": "Just outside northern edge", "lat": -9.999, "lon": 141.0, "expected": False},
            # Add more edge cases based on actual boundary
        ]
        
        for point in edge_test_points:
            result = is_point_in_polygon(point["lat"], point["lon"], boundary_coords)
            assert result == point["expected"], f"{point['name']} failed boundary test"
```

### 2. Visual Validation Tools
Create tools to visualize the boundary for manual verification.

```python
# tools/visualize_boundary.py
import folium
import json
from typing import List, Tuple

class BoundaryVisualizer:
    """Tool to visualize geographic boundary on a map"""
    
    def __init__(self, boundary_file_path: str):
        self.boundary_file_path = boundary_file_path
        self.boundary_coords = self._load_boundary()
    
    def _load_boundary(self) -> List[Tuple[float, float]]:
        """Load boundary coordinates from file"""
        with open(self.boundary_file_path, 'r') as f:
            data = json.load(f)
        return [(coord[0], coord[1]) for coord in data["coordinates"]]
    
    def create_validation_map(self, output_file: str = "boundary_validation.html"):
        """Create an interactive map for boundary validation"""
        # Calculate map center
        lats = [coord[0] for coord in self.boundary_coords]
        lons = [coord[1] for coord in self.boundary_coords]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        # Create map
        m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
        
        # Add boundary polygon
        folium.Polygon(
            locations=self.boundary_coords,
            color='red',
            weight=3,
            fillColor='red',
            fillOpacity=0.1,
            popup='Geographic Boundary'
        ).add_to(m)
        
        # Add test airports for validation
        test_airports = [
            {"name": "Sydney (YSSY)", "lat": -33.9399, "lon": 151.1753, "should_be": "inside"},
            {"name": "Melbourne (YMML)", "lat": -37.6690, "lon": 144.8410, "should_be": "inside"},
            {"name": "Los Angeles (KLAX)", "lat": 34.0522, "lon": -118.2437, "should_be": "outside"},
            {"name": "London (EGLL)", "lat": 51.4700, "lon": -0.4543, "should_be": "outside"},
        ]
        
        for airport in test_airports:
            color = 'green' if airport["should_be"] == "inside" else 'blue'
            folium.Marker(
                [airport["lat"], airport["lon"]],
                popup=f"{airport['name']} - Should be {airport['should_be']}",
                icon=folium.Icon(color=color)
            ).add_to(m)
        
        # Save map
        m.save(output_file)
        print(f"Validation map saved to {output_file}")
        print("Green markers should be inside the red boundary")
        print("Blue markers should be outside the red boundary")
        
        return m
    
    def validate_specific_points(self, test_points: List[dict]):
        """Validate specific points and generate report"""
        from app.utils.geographic_utils import is_point_in_polygon
        
        results = []
        for point in test_points:
            actual = is_point_in_polygon(point["lat"], point["lon"], self.boundary_coords)
            expected = point.get("expected", None)
            
            result = {
                "name": point["name"],
                "lat": point["lat"],
                "lon": point["lon"],
                "actual": actual,
                "expected": expected,
                "correct": actual == expected if expected is not None else None
            }
            results.append(result)
        
        return results
    
    def generate_validation_report(self, test_points: List[dict], output_file: str = "validation_report.txt"):
        """Generate a text report of validation results"""
        results = self.validate_specific_points(test_points)
        
        with open(output_file, 'w') as f:
            f.write("BOUNDARY VALIDATION REPORT\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Boundary file: {self.boundary_file_path}\n")
            f.write(f"Boundary points: {len(self.boundary_coords)}\n\n")
            
            f.write("VALIDATION RESULTS:\n")
            f.write("-" * 30 + "\n")
            
            for result in results:
                status = "✅ PASS" if result["correct"] else "❌ FAIL" if result["correct"] is False else "❓ UNKNOWN"
                f.write(f"{status} {result['name']}\n")
                f.write(f"    Location: ({result['lat']:.4f}, {result['lon']:.4f})\n")
                f.write(f"    Expected: {result['expected']}\n")
                f.write(f"    Actual: {result['actual']}\n\n")
        
        print(f"Validation report saved to {output_file}")

# Usage example
if __name__ == "__main__":
    visualizer = BoundaryVisualizer("app/utils/geographic_boundary_coordinates.json")
    
    # Create visual map
    visualizer.create_validation_map()
    
    # Test specific points
    test_points = [
        {"name": "Sydney Airport", "lat": -33.9399, "lon": 151.1753, "expected": True},
        {"name": "Melbourne Airport", "lat": -37.6690, "lon": 144.8410, "expected": True},
        {"name": "Los Angeles Airport", "lat": 34.0522, "lon": -118.2437, "expected": False},
    ]
    
    # Generate validation report
    visualizer.generate_validation_report(test_points)
```

### 3. Automated Boundary Validation
Create automated tests that run during CI/CD to ensure boundary integrity.

```python
# tests/validation/test_boundary_integrity.py
import pytest
import json
from app.utils.geographic_utils import validate_polygon_coordinates, is_point_in_polygon

class TestBoundaryIntegrity:
    """Automated tests to ensure boundary data integrity"""
    
    def test_boundary_file_exists(self):
        """Ensure boundary data file exists and is readable"""
        import os
        boundary_path = os.getenv("BOUNDARY_DATA_PATH", "app/utils/sample_boundary_coordinates.json")
        assert os.path.exists(boundary_path), f"Boundary file not found: {boundary_path}"
    
    def test_boundary_file_format(self):
        """Ensure boundary file has correct JSON format"""
        import os
        boundary_path = os.getenv("BOUNDARY_DATA_PATH", "app/utils/sample_boundary_coordinates.json")
        
        with open(boundary_path, 'r') as f:
            data = json.load(f)
        
        assert "coordinates" in data, "Boundary file missing 'coordinates' key"
        assert isinstance(data["coordinates"], list), "Coordinates must be a list"
        assert len(data["coordinates"]) >= 3, "Polygon must have at least 3 points"
    
    def test_coordinate_validity(self):
        """Ensure all coordinates are valid lat/lon values"""
        import os
        boundary_path = os.getenv("BOUNDARY_DATA_PATH", "app/utils/sample_boundary_coordinates.json")
        
        with open(boundary_path, 'r') as f:
            data = json.load(f)
        
        coordinates = [(coord[0], coord[1]) for coord in data["coordinates"]]
        assert validate_polygon_coordinates(coordinates), "Invalid coordinates in boundary file"
    
    def test_polygon_closure(self):
        """Ensure polygon is properly closed (first and last points are same or close)"""
        import os
        boundary_path = os.getenv("BOUNDARY_DATA_PATH", "app/utils/sample_boundary_coordinates.json")
        
        with open(boundary_path, 'r') as f:
            data = json.load(f)
        
        coords = data["coordinates"]
        first_point = coords[0]
        last_point = coords[-1]
        
        # Check if polygon is closed (within 0.001 degrees)
        lat_diff = abs(first_point[0] - last_point[0])
        lon_diff = abs(first_point[1] - last_point[1])
        
        is_closed = lat_diff < 0.001 and lon_diff < 0.001
        
        if not is_closed:
            print(f"Warning: Polygon may not be properly closed")
            print(f"First point: {first_point}")
            print(f"Last point: {last_point}")
    
    def test_polygon_area(self):
        """Ensure polygon has reasonable area (not too small or too large)"""
        from shapely.geometry import Polygon
        import os
        
        boundary_path = os.getenv("BOUNDARY_DATA_PATH", "app/utils/sample_boundary_coordinates.json")
        
        with open(boundary_path, 'r') as f:
            data = json.load(f)
        
        # Convert to Shapely polygon
        coords = [(coord[1], coord[0]) for coord in data["coordinates"]]  # lon, lat for Shapely
        polygon = Polygon(coords)
        
        area = polygon.area  # Area in square degrees
        
        # Reasonable bounds for airspace (adjust based on requirements)
        min_area = 0.1  # Minimum area in square degrees
        max_area = 10000  # Maximum area in square degrees
        
        assert min_area <= area <= max_area, f"Polygon area {area} is outside reasonable bounds [{min_area}, {max_area}]"
    
    def test_known_reference_points(self):
        """Test against known reference points that should be inside/outside"""
        import os
        boundary_path = os.getenv("BOUNDARY_DATA_PATH", "app/utils/sample_boundary_coordinates.json")
        
        with open(boundary_path, 'r') as f:
            data = json.load(f)
        
        coordinates = [(coord[0], coord[1]) for coord in data["coordinates"]]
        
        # Define reference points based on user requirements
        # These should be updated based on the specific airspace being defined
        reference_points = [
            # Add known points that should be inside/outside
            # Example for Australian airspace:
            # {"name": "Sydney CBD", "lat": -33.8688, "lon": 151.2093, "expected": True},
            # {"name": "Auckland NZ", "lat": -36.8485, "lon": 174.7633, "expected": False},
        ]
        
        for point in reference_points:
            actual = is_point_in_polygon(point["lat"], point["lon"], coordinates)
            assert actual == point["expected"], f"{point['name']} boundary test failed: expected {point['expected']}, got {actual}"
```

---

## 🏗️ Service Separation, Maintainability & Supportability

### 1. Service Separation Architecture

#### Clear Separation of Concerns
```
┌─────────────────────────────────────────────────────────────┐
│                    VATSIM Data Collection System            │
├─────────────────────────────────────────────────────────────┤
│  API Layer (main.py)                                       │
│  ├── Health endpoints                                      │
│  ├── Data endpoints                                        │
│  └── Filter status endpoints                               │
├─────────────────────────────────────────────────────────────┤
│  Service Layer                                              │
│  ├── DataService (orchestration)                           │
│  ├── VATSIMService (data fetching)                         │
│  ├── MonitoringService (health checks)                     │
│  └── DatabaseService (persistence)                         │
├─────────────────────────────────────────────────────────────┤
│  Filter Layer (independent components)                     │
│  ├── FlightFilter (airport-based filtering)                │
│  └── GeographicBoundaryFilter (polygon-based filtering)    │
├─────────────────────────────────────────────────────────────┤
│  Utility Layer                                             │
│  ├── geographic_utils.py (polygon calculations)            │
│  ├── config_validator.py (configuration validation)        │
│  └── error_handling.py (error management)                  │
├─────────────────────────────────────────────────────────────┤
│  Configuration Layer                                       │
│  ├── Environment variables                                 │
│  ├── JSON configuration files                              │
│  └── Runtime configuration validation                      │
└─────────────────────────────────────────────────────────────┘
```

#### Filter Implementation (Current Architecture)
```python
# app/filters/geographic_boundary_filter.py
from typing import List, Dict, Any

class GeographicBoundaryFilter:
    """Geographic boundary filter for flight data"""
    
    def filter_flights_list(self, flights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter a list of flights based on geographic boundary"""
        # Implementation...
        pass
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """Get filter statistics"""
        # Implementation...
        pass
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        # Implementation...
        pass

# app/filters/flight_filter.py
class FlightFilter:
    """Airport-based flight filter"""
    
    def filter_flights_list(self, flights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter flights based on airport criteria"""
        # Implementation...
        pass
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """Get filter statistics"""
        # Implementation...
        pass
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        # Implementation...
        pass
```

### 2. Maintainability Features

#### Configuration Management
```python
# app/config/filter_config.py
from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class FilterConfig:
    """Centralized filter configuration"""
    
    # Airport filter config
    airport_filter_enabled: bool
    
    # Boundary filter config
    boundary_filter_enabled: bool
    boundary_data_path: str
    boundary_performance_threshold: float
    
    # Logging config
    log_level: str
    
    @classmethod
    def from_environment(cls) -> 'FilterConfig':
        """Create configuration from environment variables"""
        return cls(
            airport_filter_enabled=os.getenv("FLIGHT_FILTER_ENABLED", "false").lower() == "true",
            boundary_filter_enabled=os.getenv("ENABLE_BOUNDARY_FILTER", "false").lower() == "true",
            boundary_data_path=os.getenv("BOUNDARY_DATA_PATH", ""),
            boundary_performance_threshold=float(os.getenv("BOUNDARY_FILTER_PERFORMANCE_THRESHOLD", "10.0")),
            log_level=os.getenv("FILTER_LOG_LEVEL", "INFO")
        )
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        if self.boundary_filter_enabled and not self.boundary_data_path:
            issues.append("Boundary filter enabled but no data path specified")
        
        if self.boundary_performance_threshold <= 0:
            issues.append("Performance threshold must be positive")
        
        return issues
```

#### Dependency Injection (Current Architecture)
```python
# app/services/service_factory.py
from typing import Protocol

class ServiceFactory:
    """Factory for creating services with proper dependency injection"""
    
    def __init__(self, config: FilterConfig):
        self.config = config
        self._filters = {}
    
    def create_airport_filter(self):
        """Create airport filter with configuration"""
        if 'airport' not in self._filters:
            from app.filters.flight_filter import FlightFilter
            self._filters['airport'] = FlightFilter()
        return self._filters['airport']
    
    def create_boundary_filter(self):
        """Create boundary filter with configuration"""
        if 'boundary' not in self._filters:
            from app.filters.geographic_boundary_filter import GeographicBoundaryFilter
            self._filters['boundary'] = GeographicBoundaryFilter()
        return self._filters['boundary']
    
    def create_data_service(self):
        """Create data service with all dependencies"""
        from app.services.data_service import DataService
        return DataService(
            airport_filter=self.create_airport_filter(),
            boundary_filter=self.create_boundary_filter(),
            config=self.config
        )
```

#### Modular Testing
```python
# tests/unit/test_service_factory.py
class TestServiceFactory:
    """Test service factory and dependency injection"""
    
    def test_filter_independence(self):
        """Test that filters can be created and tested independently"""
        config = FilterConfig.from_environment()
        factory = ServiceFactory(config)
        
        # Test each filter independently
        airport_filter = factory.create_airport_filter()
        boundary_filter = factory.create_boundary_filter()
        
        # Filters should work independently
        assert airport_filter.health_check()["status"] in ["healthy", "disabled"]
        assert boundary_filter.health_check()["status"] in ["healthy", "disabled", "unhealthy"]
    
    def test_service_composition(self):
        """Test that services compose correctly"""
        config = FilterConfig.from_environment()
        factory = ServiceFactory(config)
        
        data_service = factory.create_data_service()
        
        # Service should have all dependencies
        assert hasattr(data_service, 'airport_filter')
        assert hasattr(data_service, 'boundary_filter')
```

### 3. Supportability Features

#### Comprehensive Logging
```python
# app/utils/structured_logging.py
import logging
import json
from typing import Dict, Any

class StructuredLogger:
    """Structured logging for better supportability"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log_filter_operation(self, filter_name: str, operation: str, 
                           input_count: int, output_count: int, 
                           processing_time_ms: float, **kwargs):
        """Log filter operations with structured data"""
        log_data = {
            "event_type": "filter_operation",
            "filter_name": filter_name,
            "operation": operation,
            "input_count": input_count,
            "output_count": output_count,
            "processing_time_ms": processing_time_ms,
            "filtered_count": input_count - output_count,
            **kwargs
        }
        
        self.logger.info(json.dumps(log_data))
    
    def log_configuration_change(self, component: str, old_config: Dict, new_config: Dict):
        """Log configuration changes"""
        log_data = {
            "event_type": "configuration_change",
            "component": component,
            "old_config": old_config,
            "new_config": new_config
        }
        
        self.logger.info(json.dumps(log_data))
    
    def log_health_check(self, component: str, status: str, details: Dict[str, Any]):
        """Log health check results"""
        log_data = {
            "event_type": "health_check",
            "component": component,
            "status": status,
            "details": details
        }
        
        self.logger.info(json.dumps(log_data))
```

#### Metrics Collection
```python
# app/services/metrics_service.py
from typing import Dict, Any
import time
from collections import defaultdict, deque

class MetricsService:
    """Service for collecting and exposing system metrics"""
    
    def __init__(self):
        self.counters = defaultdict(int)
        self.timers = defaultdict(list)
        self.gauges = defaultdict(float)
        self.recent_operations = deque(maxlen=1000)
    
    def increment_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """Increment a counter metric"""
        key = self._make_key(name, tags)
        self.counters[key] += value
    
    def record_timer(self, name: str, duration_ms: float, tags: Dict[str, str] = None):
        """Record a timer metric"""
        key = self._make_key(name, tags)
        self.timers[key].append(duration_ms)
        
        # Keep only recent measurements
        if len(self.timers[key]) > 100:
            self.timers[key] = self.timers[key][-100:]
    
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric"""
        key = self._make_key(name, tags)
        self.gauges[key] = value
    
    def record_filter_operation(self, filter_name: str, input_count: int, 
                              output_count: int, duration_ms: float):
        """Record filter operation metrics"""
        tags = {"filter": filter_name}
        
        self.increment_counter("filter.operations", 1, tags)
        self.increment_counter("filter.flights.input", input_count, tags)
        self.increment_counter("filter.flights.output", output_count, tags)
        self.increment_counter("filter.flights.filtered", input_count - output_count, tags)
        self.record_timer("filter.duration_ms", duration_ms, tags)
        
        # Record recent operation
        self.recent_operations.append({
            "timestamp": time.time(),
            "filter": filter_name,
            "input_count": input_count,
            "output_count": output_count,
            "duration_ms": duration_ms
        })
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        return {
            "counters": dict(self.counters),
            "timers": {
                key: {
                    "count": len(values),
                    "avg": sum(values) / len(values) if values else 0,
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0
                }
                for key, values in self.timers.items()
            },
            "gauges": dict(self.gauges),
            "recent_operations": list(self.recent_operations)[-10:]  # Last 10 operations
        }
    
    def _make_key(self, name: str, tags: Dict[str, str] = None) -> str:
        """Create metric key with tags"""
        if not tags:
            return name
        
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"
```

#### Diagnostic Tools
```python
# tools/diagnostic_tool.py
import json
import sys
from typing import Dict, Any

class DiagnosticTool:
    """Tool for diagnosing system issues"""
    
    def __init__(self):
        self.checks = []
    
    def run_full_diagnostic(self) -> Dict[str, Any]:
        """Run complete system diagnostic"""
        results = {
            "timestamp": time.time(),
            "system_info": self._get_system_info(),
            "configuration": self._check_configuration(),
            "dependencies": self._check_dependencies(),
            "filters": self._check_filters(),
            "data_files": self._check_data_files(),
            "performance": self._check_performance()
        }
        
        return results
    
    def _check_configuration(self) -> Dict[str, Any]:
        """Check system configuration"""
        from app.utils.config_validator import validate_boundary_filter_config
        
        return {
            "boundary_filter": validate_boundary_filter_config(),
            "environment_variables": {
                key: value for key, value in os.environ.items() 
                if key.startswith(('ENABLE_', 'BOUNDARY_', 'FLIGHT_FILTER_'))
            }
        }
    
    def _check_filters(self) -> Dict[str, Any]:
        """Check filter health and functionality"""
        results = {}
        
        try:
            from app.filters.geographic_boundary_filter import GeographicBoundaryFilter
            boundary_filter = GeographicBoundaryFilter()
            results["boundary_filter"] = boundary_filter.health_check()
        except Exception as e:
            results["boundary_filter"] = {"status": "error", "error": str(e)}
        
        try:
            from app.filters.flight_filter import FlightFilter
            flight_filter = FlightFilter()
            results["flight_filter"] = flight_filter.get_filter_stats()
        except Exception as e:
            results["flight_filter"] = {"status": "error", "error": str(e)}
        
        return results
    
    def _check_performance(self) -> Dict[str, Any]:
        """Check system performance with sample data"""
        try:
            from app.services.data_service import DataService
            
            # Create sample data
            sample_data = {
                "pilots": [
                    {"callsign": f"TEST{i:03d}", "latitude": -33.5 + i*0.01, "longitude": 151.5 + i*0.01, 
                     "departure": "YSSY", "arrival": "YMML"}
                    for i in range(100)
                ]
            }
            
            data_service = DataService()
            
            start_time = time.time()
            result = await data_service.process_vatsim_data(sample_data)
            end_time = time.time()
            
            processing_time = (end_time - start_time) * 1000
            
            return {
                "sample_size": len(sample_data["pilots"]),
                "filtered_size": len(result["pilots"]),
                "processing_time_ms": processing_time,
                "performance_ok": processing_time < 100
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    tool = DiagnosticTool()
    results = tool.run_full_diagnostic()
    
    print("SYSTEM DIAGNOSTIC REPORT")
    print("=" * 50)
    print(json.dumps(results, indent=2))
    
    # Check for critical issues
    critical_issues = []
    
    if results["configuration"]["boundary_filter"]["valid"] == False:
        critical_issues.extend(results["configuration"]["boundary_filter"]["issues"])
    
    if results["filters"]["boundary_filter"]["status"] == "error":
        critical_issues.append(f"Boundary filter error: {results['filters']['boundary_filter'].get('error', 'Unknown')}")
    
    if critical_issues:
        print("\nCRITICAL ISSUES FOUND:")
        for issue in critical_issues:
            print(f"❌ {issue}")
        sys.exit(1)
    else:
        print("\n✅ No critical issues found")
```

### 4. Documentation and Knowledge Management

#### API Documentation
```python
# Comprehensive API documentation with examples
@app.get("/api/health/boundary-filter", 
         summary="Get boundary filter health",
         description="Returns detailed health information for the geographic boundary filter",
         response_model=BoundaryFilterHealthResponse,
         tags=["Health", "Filters"])
async def get_boundary_filter_health():
    """
    Get comprehensive health information for the geographic boundary filter.
    
    Returns:
    - Filter status (healthy/unhealthy/disabled)
    - Configuration details
    - Performance metrics
    - Any issues or warnings
    
    Example response:
    ```json
    {
        "status": "healthy",
        "enabled": true,
        "initialized": true,
        "polygon_points": 156,
        "issues": []
    }
    ```
    """
    pass
```

#### Runbook Documentation
```markdown
# Geographic Boundary Filter Runbook

## Common Issues and Solutions

### Issue: Filter Not Initializing
**Symptoms:** Health check shows "unhealthy", logs show initialization errors
**Diagnosis:** Check boundary data file and configuration
**Solution:**
1. Validate configuration: `python app/utils/config_validator.py`
2. Check file permissions on boundary data file
3. Validate JSON format of boundary file

### Issue: Poor Performance
**Symptoms:** Processing time exceeds threshold, warnings in logs
**Diagnosis:** Check polygon complexity and system load
**Solution:**
1. Check polygon point count (should be < 1000 points)
2. Monitor system resources
3. Consider polygon simplification

### Issue: Incorrect Filtering Results
**Symptoms:** Known points incorrectly classified as inside/outside
**Diagnosis:** Boundary polygon may be incorrect
**Solution:**
1. Run boundary validation tests
2. Use visualization tool to check polygon
3. Verify coordinate format (lat/lon vs lon/lat)
```

This comprehensive approach ensures:

1. **Polygon Accuracy**: Multiple validation methods (automated tests, visual tools, reference points)
2. **Service Separation**: Clear interfaces, dependency injection, modular design
3. **Maintainability**: Structured configuration, comprehensive logging, metrics collection
4. **Supportability**: Diagnostic tools, runbooks, comprehensive documentation

The architecture supports independent development, testing, and deployment of each component while maintaining system integrity and performance.

