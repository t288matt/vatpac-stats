#!/usr/bin/env python3
"""
Sector Loader Module

This module loads Australian airspace sectors from pre-processed JSON data
and converts them to Shapely Polygons for efficient sector boundary detection.

Author: VATSIM Data System
Created: 2025-01-08
Status: Sprint 1, Task 1.4 - Sector Data Loading
"""

import json
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from shapely.geometry import Polygon, Point

# Import our existing geographic utilities
from app.utils.geographic_utils import is_point_in_polygon

logger = logging.getLogger(__name__)

class SectorLoader:
    """
    Sector Loader for Australian Airspace Sectors
    
    Loads sector definitions from australian_sectors.json and converts
    boundaries to Shapely Polygons for fast point-in-polygon detection.
    """
    
    def __init__(self, sectors_file_path: str = "airspace_sector_data/australian_airspace_sectors.geojson"):
        """Initialize sector loader with configuration."""
        self.sectors_file_path = sectors_file_path
        self.sectors: Dict[str, Polygon] = {}
        self.sector_metadata: Dict[str, Dict] = {}
        self.loaded = False
        
        logger.info(f"Sector loader initialized for file: {sectors_file_path}")
    
    def load_sectors(self) -> bool:
        """Load all sectors from the GeoJSON file and convert to Shapely Polygons."""
        try:
            logger.info("Loading Australian airspace sectors from GeoJSON...")
            
            # Check if file exists
            file_path = Path(self.sectors_file_path)
            if not file_path.exists():
                error_msg = f"CRITICAL: Sectors file not found: {self.sectors_file_path}. Application cannot start without sector data."
                logger.critical(error_msg)
                raise FileNotFoundError(error_msg)
            
            # Load GeoJSON data
            with open(file_path, 'r') as f:
                geojson_data = json.load(f)
            
            # Check if it's a GeoJSON FeatureCollection
            if not isinstance(geojson_data, dict) or geojson_data.get('type') != 'FeatureCollection':
                error_msg = f"CRITICAL: Invalid GeoJSON format - expected FeatureCollection, got {type(geojson_data)}"
                logger.critical(error_msg)
                raise ValueError(error_msg)
            
            features = geojson_data.get('features', [])
            if not isinstance(features, list):
                error_msg = f"CRITICAL: Invalid GeoJSON format - expected features list"
                logger.critical(error_msg)
                raise ValueError(error_msg)
            
            logger.info(f"Found {len(features)} sector features in GeoJSON file")
            
            # Process each feature
            sectors_loaded = 0
            sectors_with_boundaries = 0
            
            for feature in features:
                try:
                    # Extract properties
                    properties = feature.get('properties', {})
                    sector_name = properties.get('name')
                    if not sector_name:
                        logger.warning("Feature missing name in properties, skipping")
                        continue
                    
                    # Extract metadata
                    self.sector_metadata[sector_name] = {
                        'name': sector_name,
                        'sector_type': properties.get('sector_type', 'N/A'),
                        'callsign': properties.get('callsign', 'N/A'),
                        'frequency': properties.get('frequency', 'N/A'),
                        'full_name': properties.get('full_name', 'N/A'),
                        'volumes': properties.get('volumes', 'N/A'),
                        'responsible_sectors': properties.get('responsible_sectors', 'N/A')
                    }
                    
                    # Extract geometry
                    geometry = feature.get('geometry', {})
                    if geometry.get('type') != 'Polygon':
                        logger.warning(f"Sector {sector_name} has non-polygon geometry type: {geometry.get('type')}")
                        continue
                    
                    coordinates = geometry.get('coordinates', [])
                    if not coordinates or len(coordinates) == 0:
                        logger.warning(f"Sector {sector_name} has no coordinates")
                        continue
                    
                    # GeoJSON coordinates are already in [lon, lat] format
                    # Take the first ring (exterior boundary)
                    polygon_coords = coordinates[0]
                    
                    if len(polygon_coords) >= 3:
                        try:
                            sector_polygon = Polygon(polygon_coords)
                            
                            # Validate polygon
                            if sector_polygon.is_valid:
                                self.sectors[sector_name] = sector_polygon
                                sectors_with_boundaries += 1
                                logger.debug(f"✅ Loaded sector {sector_name} with {len(polygon_coords)} boundary points")
                            else:
                                # Try to fix invalid polygon
                                fixed_polygon = sector_polygon.buffer(0)
                                if fixed_polygon.is_valid:
                                    self.sectors[sector_name] = fixed_polygon
                                    sectors_with_boundaries += 1
                                    logger.info(f"✅ Loaded sector {sector_name} (fixed invalid polygon)")
                                else:
                                    logger.warning(f"⚠️  Could not fix invalid polygon for sector {sector_name}")
                        except Exception as e:
                            logger.warning(f"⚠️  Failed to create polygon for sector {sector_name}: {e}")
                    else:
                        logger.warning(f"⚠️  Sector {sector_name} has insufficient boundary points")
                    
                    sectors_loaded += 1
                    
                except Exception as e:
                    logger.warning(f"⚠️  Error processing feature {feature.get('properties', {}).get('name', 'UNKNOWN')}: {e}")
                    continue
            
            self.loaded = True
            
            logger.info(f"✅ Successfully loaded {sectors_loaded} sectors from GeoJSON")
            logger.info(f"📊 Sectors with boundaries: {sectors_with_boundaries}")
            logger.info(f"📊 Sectors without boundaries: {sectors_loaded - sectors_with_boundaries}")
            
            if sectors_with_boundaries == 0:
                error_msg = "CRITICAL: No sectors with valid boundaries loaded - application cannot function without sector data"
                logger.critical(error_msg)
                raise RuntimeError(error_msg)
            
            return True
            
        except Exception as e:
            logger.critical(f"CRITICAL: Failed to load sectors: {e}")
            raise  # Re-raise the exception to fail the app
    
    def get_sector_for_point(self, lat: float, lon: float) -> Optional[str]:
        """Find which sector contains the given point.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            
        Returns:
            str: Sector name (e.g., "ARL", "WOL") or None if not in any sector
        """
        if not self.loaded:
            logger.warning("Sector data not loaded")
            return None
        
        try:
            point = Point(lon, lat)  # Shapely uses (lon, lat) format
            
            # Check each sector
            for sector_name, polygon in self.sectors.items():
                if polygon.contains(point):
                    return sector_name
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking sector for point ({lat}, {lon}): {e}")
            return None
    
    def get_sector_polygon(self, sector_name: str) -> Optional[Polygon]:
        """Get the polygon for a specific sector.
        
        Args:
            sector_name: Sector name (e.g., "ARL", "WOL")
            
        Returns:
            Polygon: Shapely Polygon object or None if not found
        """
        return self.sectors.get(sector_name)
    
    def get_sector_metadata(self, sector_name: str) -> Optional[Dict]:
        """Get metadata for a specific sector.
        
        Args:
            sector_name: Sector name (e.g., "ARL", "WOL")
            
        Returns:
            Dict: Sector metadata or None if not found
        """
        return self.sector_metadata.get(sector_name)
    
    def list_sectors(self) -> List[str]:
        """Get list of all loaded sector names."""
        return list(self.sectors.keys())
    
    def get_sector_count(self) -> int:
        """Get total number of loaded sectors."""
        return len(self.sectors)
    
    def get_sectors_with_boundaries_count(self) -> int:
        """Get count of sectors that have valid boundary polygons."""
        return sum(1 for polygon in self.sectors.values() if polygon and polygon.is_valid)
    
    def is_sector_loaded(self, sector_name: str) -> bool:
        """Check if a specific sector is loaded and has valid boundaries."""
        return sector_name in self.sectors and self.sectors[sector_name] is not None
    
    def get_sector_boundary_points(self, sector_name: str) -> Optional[List[Tuple[float, float]]]:
        """Get the boundary coordinates for a sector.
        
        Args:
            sector_name: Sector name (e.g., "ARL", "WOL")
            
        Returns:
            List[Tuple[float, float]]: List of (lon, lat) coordinates or None if not found
        """
        polygon = self.sectors.get(sector_name)
        if polygon and polygon.exterior:
            # Convert back to (lat, lon) format for consistency with original data
            return [(coord[1], coord[0]) for coord in polygon.exterior.coords]
        return None
    
    def clear(self) -> None:
        """Clear all loaded sector data."""
        self.sectors.clear()
        self.sector_metadata.clear()
        self.loaded = False
        logger.info("Cleared all sector data")
    
    def reload(self) -> bool:
        """Reload sectors from file."""
        logger.info("Reloading sectors...")
        self.clear()
        return self.load_sectors()
    
    def get_status(self) -> Dict[str, any]:
        """Get the current status of the sector loader."""
        return {
            "loaded": self.loaded,
            "sectors_file": self.sectors_file_path,
            "total_sectors": self.get_sector_count(),
            "sectors_with_boundaries": self.get_sectors_with_boundaries_count(),
            "sector_names": self.list_sectors()
        }
