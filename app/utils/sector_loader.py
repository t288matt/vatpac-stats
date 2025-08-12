#!/usr/bin/env python3
"""
Simple Sector Manager Module

Creates basic Australian domestic sectors using the existing australian_airspace_polygon.json
and existing geographic utilities. This is a lightweight approach that doesn't require
complex XML parsing.
"""

import json
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from shapely.geometry import Polygon, Point
from .geographic_utils import get_cached_polygon

logger = logging.getLogger(__name__)

class SimpleSectorManager:
    """Simple sector manager for Australian domestic airspace tracking."""
    
    def __init__(self):
        self.sectors: Dict[str, Polygon] = {}
        self.sector_metadata: Dict[str, Dict] = {}
        self.loaded = False
        
    def load_australian_sectors(self, base_polygon_path: str = "australian_airspace_polygon.json") -> bool:
        """Load basic Australian domestic sectors using the existing airspace polygon."""
        try:
            logger.info("Loading Australian domestic sectors...")
            
            # Load the base Australian airspace polygon
            base_polygon = get_cached_polygon(base_polygon_path)
            if not base_polygon:
                logger.error(f"Failed to load base polygon from {base_polygon_path}")
                return False
            
            # Create simple sectors by dividing the Australian airspace into regions
            self._create_basic_sectors(base_polygon)
            
            self.loaded = True
            logger.info(f"Successfully loaded {len(self.sectors)} basic Australian sectors")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load Australian sectors: {e}")
            return False
    
    def _create_basic_sectors(self, base_polygon: Polygon) -> None:
        """Create basic sectors by dividing Australian airspace into regions."""
        
        # Get the bounding box of Australian airspace
        minx, miny, maxx, maxy = base_polygon.bounds
        
        # Create simple rectangular sectors (this is a simplified approach)
        # In a real system, these would be based on actual ATC sector definitions
        
        # Major city regions (simplified rectangles)
        sectors = {
            'SYDNEY': {
                'bounds': (150.0, -35.0, 152.0, -33.0),
                'description': 'Sydney metropolitan area'
            },
            'MELBOURNE': {
                'bounds': (144.0, -38.5, 146.0, -37.0),
                'description': 'Melbourne metropolitan area'
            },
            'BRISBANE': {
                'bounds': (152.5, -28.0, 154.0, -26.5),
                'description': 'Brisbane metropolitan area'
            },
            'ADELAIDE': {
                'bounds': (138.0, -35.5, 139.0, -34.0),
                'description': 'Adelaide metropolitan area'
            },
            'PERTH': {
                'bounds': (115.0, -32.5, 116.5, -31.0),
                'description': 'Perth metropolitan area'
            },
            'CANBERRA': {
                'bounds': (148.5, -36.0, 149.5, -35.0),
                'description': 'Canberra region'
            },
            'CAIRNS': {
                'bounds': (145.0, -17.5, 146.5, -16.0),
                'description': 'Cairns region'
            },
            'DARWIN': {
                'bounds': (130.5, -13.0, 132.0, -11.5),
                'description': 'Darwin region'
            },
            'HOBART': {
                'bounds': (147.0, -43.0, 148.0, -42.0),
                'description': 'Hobart region'
            },
            'TOWNSVILLE': {
                'bounds': (146.0, -20.0, 147.5, -18.5),
                'description': 'Townsville region'
            },
            'ROCKHAMPTON': {
                'bounds': (150.0, -24.0, 151.5, -22.5),
                'description': 'Rockhampton region'
            },
            'MACKAY': {
                'bounds': (148.5, -22.0, 150.0, -20.5),
                'description': 'Mackay region'
            },
            'GOLD_COAST': {
                'bounds': (153.0, -28.5, 154.0, -27.5),
                'description': 'Gold Coast region'
            },
            'NEWCASTLE': {
                'bounds': (151.5, -33.5, 152.5, -32.5),
                'description': 'Newcastle region'
            },
            'WOLLONGONG': {
                'bounds': (150.5, -35.0, 151.5, -34.0),
                'description': 'Wollongong region'
            },
            'ARMIDALE': {
                'bounds': (151.5, -31.0, 152.5, -30.0),
                'description': 'Armidale region'
            },
            'TAMWORTH': {
                'bounds': (150.5, -32.0, 151.5, -31.0),
                'description': 'Tamworth region'
            },
            'COFFS_HARBOUR': {
                'bounds': (152.5, -31.0, 153.5, -30.0),
                'description': 'Coffs Harbour region'
            },
            'GRAFTON': {
                'bounds': (152.5, -30.0, 153.5, -29.0),
                'description': 'Grafton region'
            },
            'INVERELL': {
                'bounds': (150.5, -30.0, 151.5, -29.0),
                'description': 'Inverell region'
            },
            'GRIFFITH': {
                'bounds': (145.5, -35.0, 146.5, -34.0),
                'description': 'Griffith region'
            },
            'WAGGA_WAGGA': {
                'bounds': (147.0, -36.0, 148.0, -35.0),
                'description': 'Wagga Wagga region'
            },
            'ORANGE': {
                'bounds': (148.5, -34.0, 149.5, -33.0),
                'description': 'Orange region'
            },
            'DUBBO': {
                'bounds': (148.0, -33.0, 149.0, -32.0),
                'description': 'Dubbo region'
            },
            'BATHURST': {
                'bounds': (149.0, -34.0, 150.0, -33.0),
                'description': 'Bathurst region'
            },
            'PORT_MACQUARIE': {
                'bounds': (152.5, -32.0, 153.5, -31.0),
                'description': 'Port Macquarie region'
            }
        }
        
        # Create sector polygons
        for sector_name, sector_info in sectors.items():
            min_lon, min_lat, max_lon, max_lat = sector_info['bounds']
            
            # Create rectangle polygon
            coords = [
                (min_lon, min_lat),
                (max_lon, min_lat),
                (max_lon, max_lat),
                (min_lon, max_lat),
                (min_lon, min_lat)  # Close the polygon
            ]
            
            try:
                sector_polygon = Polygon(coords)
                
                # Only include sectors that intersect with Australian airspace
                if sector_polygon.intersects(base_polygon):
                    self.sectors[sector_name] = sector_polygon
                    self.sector_metadata[sector_name] = {
                        'name': sector_name,
                        'description': sector_info['description'],
                        'bounds': sector_info['bounds'],
                        'type': 'australian_domestic',
                        'source': 'simple_division'
                    }
                    logger.debug(f"Created sector {sector_name}")
                    
            except Exception as e:
                logger.warning(f"Failed to create sector {sector_name}: {e}")
    
    def get_sector_for_point(self, lat: float, lon: float) -> Optional[str]:
        """Find which sector contains the given point.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            
        Returns:
            str: Sector code (e.g., "SYDNEY", "MELBOURNE") or None if not in any sector
        """
        if not self.loaded:
            logger.warning("Sector data not loaded")
            return None
        
        try:
            point = Point(lon, lat)  # Shapely uses (lon, lat) format
            
            # Check each sector
            for sector_code, polygon in self.sectors.items():
                if polygon.contains(point):
                    return sector_code
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking sector for point ({lat}, {lon}): {e}")
            return None
    
    def get_sector_polygon(self, sector_code: str) -> Optional[Polygon]:
        """Get the polygon for a specific sector.
        
        Args:
            sector_code: Sector code (e.g., "SYDNEY", "MELBOURNE")
            
        Returns:
            Polygon: Shapely Polygon object or None if not found
        """
        return self.sectors.get(sector_code)
    
    def get_sector_metadata(self, sector_code: str) -> Optional[Dict]:
        """Get metadata for a specific sector.
        
        Args:
            sector_code: Sector code (e.g., "SYDNEY", "MELBOURNE")
            
        Returns:
            Dict: Sector metadata or None if not found
        """
        return self.sector_metadata.get(sector_code)
    
    def list_sectors(self) -> List[str]:
        """Get list of all loaded sector codes."""
        return list(self.sectors.keys())
    
    def get_sector_count(self) -> int:
        """Get total number of loaded sectors."""
        return len(self.sectors)
    
    def clear(self) -> None:
        """Clear all loaded sector data."""
        self.sectors.clear()
        self.sector_metadata.clear()
        self.loaded = False
        logger.info("Cleared all sector data")
