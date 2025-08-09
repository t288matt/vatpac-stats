#!/usr/bin/env python3
"""
Geographic Boundary Filter Configuration Validator

This module provides validation functionality for the geographic boundary filter
configuration. It checks environment variables, boundary data files, and other
configuration settings to ensure the filter can operate correctly.

Author: VATSIM Data System
Created: 2025-01-08
Status: Sprint 3, Task 3.3 - Configuration Validation
"""

import os
import json
import logging
from typing import Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_boundary_filter_config() -> Dict[str, Any]:
    """
    Validate geographic boundary filter configuration
    
    Checks all environment variables, boundary data files, and configuration
    settings to ensure the filter can operate correctly.
    
    Returns:
        Dictionary with validation results including:
        - enabled: Whether the filter is enabled
        - valid: Whether the configuration is valid
        - issues: List of critical issues that prevent operation
        - warnings: List of non-critical warnings
        - config: Current configuration values
    """
    issues = []
    warnings = []
    config = {}
    
    # Check if filter is enabled
    enabled = os.getenv("ENABLE_BOUNDARY_FILTER", "false").lower() == "true"
    config["enabled"] = enabled
    
    if enabled:
        # Check boundary data path
        data_path = os.getenv("BOUNDARY_DATA_PATH", "")
        config["boundary_data_path"] = data_path
        
        if not data_path:
            issues.append("BOUNDARY_DATA_PATH not set but filter is enabled")
        else:
            # Check if file exists
            if not os.path.exists(data_path):
                issues.append(f"Boundary data file not found: {data_path}")
            else:
                # Validate boundary data file
                try:
                    with open(data_path, 'r') as f:
                        data = json.load(f)
                    
                    # Check for coordinates
                    if "coordinates" not in data:
                        issues.append("Boundary data file missing 'coordinates' key")
                    else:
                        coords = data["coordinates"]
                        
                        # Handle different coordinate formats
                        if "type" in data and data["type"] == "Polygon":
                            # GeoJSON format: coordinates are [[[lon, lat], ...]]
                            if not coords or not coords[0]:
                                issues.append("Invalid GeoJSON polygon coordinates structure")
                            else:
                                polygon_coords = coords[0]  # First ring
                                if len(polygon_coords) < 3:
                                    issues.append("Boundary polygon must have at least 3 points")
                                else:
                                    # Validate GeoJSON coordinates [lon, lat]
                                    for i, coord in enumerate(polygon_coords):
                                        if len(coord) != 2:
                                            issues.append(f"Invalid coordinate format at index {i}")
                                            break
                                        lon, lat = coord
                                        if not (-180 <= lon <= 180):
                                            issues.append(f"Invalid longitude {lon} at index {i}")
                                            break
                                        if not (-90 <= lat <= 90):
                                            issues.append(f"Invalid latitude {lat} at index {i}")
                                            break
                                
                                config["polygon_points"] = len(polygon_coords)
                                config["format"] = "GeoJSON"
                        else:
                            # Simple format: coordinates are [[lat, lon], ...]
                            if len(coords) < 3:
                                issues.append("Boundary polygon must have at least 3 points")
                            else:
                                # Validate simple coordinates [lat, lon]
                                for i, coord in enumerate(coords):
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
                                
                                config["polygon_points"] = len(coords)
                                config["format"] = "Simple"
                
                except json.JSONDecodeError as e:
                    issues.append(f"Invalid JSON in boundary data file: {e}")
                except Exception as e:
                    issues.append(f"Error reading boundary data file: {e}")
        
        # Check log level
        log_level = os.getenv("BOUNDARY_FILTER_LOG_LEVEL", "INFO")
        config["log_level"] = log_level
        
        if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            warnings.append(f"Invalid log level '{log_level}', using INFO")
        
        # Check performance threshold
        try:
            threshold = float(os.getenv("BOUNDARY_FILTER_PERFORMANCE_THRESHOLD", "10.0"))
            config["performance_threshold_ms"] = threshold
            
            if threshold <= 0:
                warnings.append("Performance threshold should be positive")
            elif threshold > 100:
                warnings.append("Performance threshold is very high (>100ms), consider optimization")
        except ValueError:
            warnings.append("Invalid performance threshold, using default 10.0ms")
            config["performance_threshold_ms"] = 10.0
    else:
        # Filter is disabled
        config.update({
            "boundary_data_path": os.getenv("BOUNDARY_DATA_PATH", ""),
            "log_level": os.getenv("BOUNDARY_FILTER_LOG_LEVEL", "INFO"),
            "performance_threshold_ms": float(os.getenv("BOUNDARY_FILTER_PERFORMANCE_THRESHOLD", "10.0"))
        })
    
    return {
        "enabled": enabled,
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "config": config
    }


def validate_boundary_data_file(file_path: str) -> Dict[str, Any]:
    """
    Validate a specific boundary data file
    
    Args:
        file_path: Path to the boundary data file
        
    Returns:
        Dictionary with validation results
    """
    issues = []
    warnings = []
    info = {}
    
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            issues.append(f"File not found: {file_path}")
            return {
                "valid": False,
                "issues": issues,
                "warnings": warnings,
                "info": info
            }
        
        # Get file info
        file_stat = os.stat(file_path)
        info["file_size_bytes"] = file_stat.st_size
        info["file_path"] = os.path.abspath(file_path)
        
        # Load and validate JSON
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Detect format
        if "type" in data and data["type"] == "Polygon":
            info["format"] = "GeoJSON"
            coords = data["coordinates"][0] if data.get("coordinates") else []
            info["coordinate_order"] = "[longitude, latitude]"
        else:
            info["format"] = "Simple"
            coords = data.get("coordinates", [])
            info["coordinate_order"] = "[latitude, longitude]"
        
        info["coordinate_count"] = len(coords)
        
        # Validate polygon
        if len(coords) < 3:
            issues.append("Polygon must have at least 3 coordinate pairs")
        elif len(coords) > 10000:
            warnings.append(f"Very complex polygon ({len(coords)} points) may impact performance")
        
        # Check if polygon is closed
        if len(coords) >= 3:
            if coords[0] != coords[-1]:
                warnings.append("Polygon is not closed (first and last points differ)")
            
            # Calculate bounding box
            if info["format"] == "GeoJSON":
                lons = [coord[0] for coord in coords]
                lats = [coord[1] for coord in coords]
            else:
                lats = [coord[0] for coord in coords]
                lons = [coord[1] for coord in coords]
            
            info["bounding_box"] = {
                "min_lat": min(lats),
                "max_lat": max(lats),
                "min_lon": min(lons),
                "max_lon": max(lons)
            }
        
        # Additional metadata
        if "name" in data:
            info["name"] = data["name"]
        if "description" in data:
            info["description"] = data["description"]
        
    except json.JSONDecodeError as e:
        issues.append(f"Invalid JSON format: {e}")
    except Exception as e:
        issues.append(f"Error validating file: {e}")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "info": info
    }


def test_filter_initialization() -> Dict[str, Any]:
    """
    Test if the geographic boundary filter can be initialized with current configuration
    
    Returns:
        Dictionary with test results
    """
    try:
        from app.filters.geographic_boundary_filter import GeographicBoundaryFilter
        
        # Try to initialize the filter
        filter_obj = GeographicBoundaryFilter()
        
        # Get filter status
        health = filter_obj.health_check()
        stats = filter_obj.get_filter_stats()
        
        return {
            "success": True,
            "initialized": filter_obj.is_initialized,
            "health": health,
            "stats": stats,
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "initialized": False,
            "health": None,
            "stats": None,
            "error": str(e)
        }


def main():
    """Command line interface for configuration validation"""
    import sys
    
    print("Geographic Boundary Filter Configuration Validation")
    print("=" * 60)
    
    # Validate configuration
    result = validate_boundary_filter_config()
    
    print(f"Filter Enabled: {result['enabled']}")
    print(f"Configuration Valid: {result['valid']}")
    
    if result['config']:
        print("\nConfiguration:")
        for key, value in result['config'].items():
            print(f"  {key}: {value}")
    
    if result['issues']:
        print("\n❌ Critical Issues:")
        for issue in result['issues']:
            print(f"  • {issue}")
    
    if result['warnings']:
        print("\n⚠️  Warnings:")
        for warning in result['warnings']:
            print(f"  • {warning}")
    
    # Test filter initialization if configuration is valid
    if result['valid'] and result['enabled']:
        print("\n" + "=" * 60)
        print("Testing Filter Initialization...")
        
        init_result = test_filter_initialization()
        
        if init_result['success']:
            print("✅ Filter initialization successful")
            print(f"   Initialized: {init_result['initialized']}")
            print(f"   Health Status: {init_result['health']['status']}")
            
            if init_result['stats']:
                stats = init_result['stats']
                print(f"   Polygon Points: {stats.get('polygon_points', 'N/A')}")
                print(f"   Filter Type: {stats.get('filter_type', 'N/A')}")
        else:
            print("❌ Filter initialization failed")
            print(f"   Error: {init_result['error']}")
    
    # Validate boundary data file if specified
    if result['enabled'] and result['config'].get('boundary_data_path'):
        print("\n" + "=" * 60)
        print("Validating Boundary Data File...")
        
        file_result = validate_boundary_data_file(result['config']['boundary_data_path'])
        
        if file_result['valid']:
            print("✅ Boundary data file is valid")
            info = file_result['info']
            print(f"   Format: {info.get('format', 'Unknown')}")
            print(f"   Coordinates: {info.get('coordinate_count', 0)} points")
            print(f"   File Size: {info.get('file_size_bytes', 0)} bytes")
            
            if 'bounding_box' in info:
                bbox = info['bounding_box']
                print(f"   Bounding Box: ({bbox['min_lat']:.2f}, {bbox['min_lon']:.2f}) to ({bbox['max_lat']:.2f}, {bbox['max_lon']:.2f})")
        else:
            print("❌ Boundary data file has issues")
            for issue in file_result['issues']:
                print(f"   • {issue}")
        
        if file_result['warnings']:
            for warning in file_result['warnings']:
                print(f"   ⚠️  {warning}")
    
    # Final status
    print("\n" + "=" * 60)
    if result['valid'] and result['enabled']:
        print("✅ Configuration is valid and ready for use")
        sys.exit(0)
    elif not result['enabled']:
        print("💤 Filter is disabled")
        sys.exit(0)
    else:
        print("❌ Configuration has issues that need to be resolved")
        sys.exit(1)


if __name__ == "__main__":
    main()

