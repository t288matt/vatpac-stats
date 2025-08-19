#!/usr/bin/env python3
"""
Controller Type Detection Service

This service analyzes VATSIM controller callsigns to determine their type
and assign appropriate geographic proximity ranges for flight detection.

The detection is based on the last 3 characters of the callsign:
- GND/DEL → Ground (15nm)
- TWR → Tower (15nm)  
- APP/DEP → Approach (60nm)
- CTR → Center (400nm)
- FSS → FSS (1000nm)
"""

import logging
from typing import Tuple, Dict, Any


class ControllerTypeDetector:
    """
    Service for detecting controller types and determining proximity ranges.
    
    This service analyzes controller callsigns to determine the appropriate
    geographic proximity range for flight detection, making the system
    much more realistic by matching real-world ATC operations.
    """
    
    def __init__(self):
        """Initialize the controller type detector with proximity ranges."""
        import os
        
        # Load proximity ranges from environment variables with defaults
        self.proximity_ranges = {
            "Ground": (
                int(os.getenv("CONTROLLER_PROXIMITY_GROUND_NM", "15")),
                int(os.getenv("CONTROLLER_PROXIMITY_GROUND_NM", "15"))
            ),
            "Tower": (
                int(os.getenv("CONTROLLER_PROXIMITY_TOWER_NM", "15")),
                int(os.getenv("CONTROLLER_PROXIMITY_TOWER_NM", "15"))
            ),
            "Approach": (
                int(os.getenv("CONTROLLER_PROXIMITY_APPROACH_NM", "60")),
                int(os.getenv("CONTROLLER_PROXIMITY_APPROACH_NM", "60"))
            ),
            "Center": (
                int(os.getenv("CONTROLLER_PROXIMITY_CENTER_NM", "400")),
                int(os.getenv("CONTROLLER_PROXIMITY_CENTER_NM", "400"))
            ),
            "FSS": (
                int(os.getenv("CONTROLLER_PROXIMITY_FSS_NM", "1000")),
                int(os.getenv("CONTROLLER_PROXIMITY_FSS_NM", "1000"))
            ),
            "default": (
                int(os.getenv("CONTROLLER_PROXIMITY_DEFAULT_NM", "30")),
                int(os.getenv("CONTROLLER_PROXIMITY_DEFAULT_NM", "30"))
            )
        }

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Controller Type Detector initialized with proximity ranges: {self.proximity_ranges}")
    
    def detect_controller_type(self, callsign: str) -> str:
        """
        Determine controller type from last 3 characters of callsign.
        
        Args:
            callsign: Controller callsign (e.g., "SY_TWR", "ML_APP")
            
        Returns:
            Controller type string (Ground, Tower, Approach, Center, FSS)
            
        Examples:
            >>> detector = ControllerTypeDetector()
            >>> detector.detect_controller_type("SY_TWR")
            'Tower'
            >>> detector.detect_controller_type("CB_GND")
            'Ground'
            >>> detector.detect_controller_type("YBBN_APP")
            'Approach'
        """
        if not callsign:
            self.logger.warning("Empty callsign provided, defaulting to Ground")
            return "Ground"
        
        # Get last 3 characters of callsign
        if len(callsign) >= 3:
            last_three = callsign[-3:].upper()
        else:
            last_three = callsign.upper()
        
        # Determine controller type from last 3 characters
        if last_three in ["GND", "DEL"]:
            controller_type = "Ground"
        elif last_three == "TWR":
            controller_type = "Tower"  
        elif last_three in ["APP", "DEP"]:
            controller_type = "Approach"
        elif last_three == "CTR":
            controller_type = "Center"
        elif last_three == "FSS":
            controller_type = "FSS"
        else:
            # Fallback: Default to ground for unknown patterns
            controller_type = "Ground"
        
        self.logger.debug(f"Controller {callsign} detected as {controller_type} from last 3 characters: {last_three}")
        return controller_type
    
    def get_proximity_range(self, controller_type: str) -> Tuple[int, int]:
        """
        Get proximity range for controller type.
        
        Args:
            controller_type: Type of controller (Ground, Tower, Approach, Center, FSS)
            
        Returns:
            Tuple of (min_nm, max_nm) for proximity range
            
                 Examples:
             >>> detector = ControllerTypeDetector()
             >>> detector.get_proximity_range("Tower")
             (15, 15)
             >>> detector.get_proximity_range("Center")
             (400, 400)
        """
        return self.proximity_ranges.get(controller_type, self.proximity_ranges["default"])
    
    def get_proximity_threshold(self, controller_type: str) -> int:
        """
        Get proximity threshold (upper bound) for controller type.
        
        Args:
            controller_type: Type of controller
            
        Returns:
            Maximum proximity range in nautical miles
            
                 Examples:
             >>> detector = ControllerTypeDetector()
             >>> detector.get_proximity_threshold("Approach")
             60
        """
        range_tuple = self.get_proximity_range(controller_type)
        return range_tuple[1]  # Return upper bound
    
    def get_all_proximity_ranges(self) -> Dict[str, Tuple[int, int]]:
        """
        Get all configured proximity ranges.
        
        Returns:
            Dictionary mapping controller types to their proximity ranges
            
        Examples:
            >>> detector = ControllerTypeDetector()
            >>> ranges = detector.get_all_proximity_ranges()
            >>> ranges["Tower"]
            (10, 10)
        """
        return self.proximity_ranges.copy()
    
    def is_valid_controller_type(self, controller_type: str) -> bool:
        """
        Check if a controller type is valid.
        
        Args:
            controller_type: Controller type to validate
            
        Returns:
            True if valid, False otherwise
            
        Examples:
            >>> detector = ControllerTypeDetector()
            >>> detector.is_valid_controller_type("Tower")
            True
            >>> detector.is_valid_controller_type("Invalid")
            False
        """
        return controller_type in self.proximity_ranges
    
    def get_controller_info(self, callsign: str) -> Dict[str, Any]:
        """
        Get comprehensive controller information including type and proximity range.
        
        Args:
            callsign: Controller callsign
            
        Returns:
            Dictionary with controller type, proximity range, and threshold
            
                 Examples:
             >>> detector = ControllerTypeDetector()
             >>> info = detector.get_controller_info("SY_TWR")
             >>> info["type"]
             'Tower'
             >>> info["proximity_range"]
             (15, 15)
             >>> info["proximity_threshold"]
             15
        """
        controller_type = self.detect_controller_type(callsign)
        proximity_range = self.get_proximity_range(controller_type)
        proximity_threshold = self.get_proximity_threshold(controller_type)
        
        return {
            "callsign": callsign,
            "type": controller_type,
            "proximity_range": proximity_range,
            "proximity_threshold": proximity_threshold,
            "detection_method": "callsign_pattern"
        }
    
    def update_proximity_range(self, controller_type: str, new_range: Tuple[int, int]) -> bool:
        """
        Update proximity range for a controller type.
        
        Args:
            controller_type: Type of controller to update
            new_range: New proximity range as (min_nm, max_nm)
            
        Returns:
            True if updated successfully, False otherwise
            
        Examples:
            >>> detector = ControllerTypeDetector()
            >>> detector.update_proximity_range("Tower", (15, 15))
            True
            >>> detector.get_proximity_range("Tower")
            (15, 15)
        """
        if not self.is_valid_controller_type(controller_type):
            self.logger.warning(f"Cannot update invalid controller type: {controller_type}")
            return False
        
        if len(new_range) != 2 or not all(isinstance(x, int) and x > 0 for x in new_range):
            self.logger.warning(f"Invalid range format: {new_range}. Expected (min_nm, max_nm)")
            return False
        
        self.proximity_ranges[controller_type] = new_range
        self.logger.info(f"Updated {controller_type} proximity range to {new_range}")
        return True
    
    def reset_to_defaults(self) -> None:
        """Reset all proximity ranges to default values from environment variables."""
        import os
        
        self.proximity_ranges = {
            "Ground": (
                int(os.getenv("CONTROLLER_PROXIMITY_GROUND_NM", "15")),
                int(os.getenv("CONTROLLER_PROXIMITY_GROUND_NM", "15"))
            ),
            "Tower": (
                int(os.getenv("CONTROLLER_PROXIMITY_TOWER_NM", "15")),
                int(os.getenv("CONTROLLER_PROXIMITY_TOWER_NM", "15"))
            ),
            "Approach": (
                int(os.getenv("CONTROLLER_PROXIMITY_APPROACH_NM", "60")),
                int(os.getenv("CONTROLLER_PROXIMITY_APPROACH_NM", "60"))
            ),
            "Center": (
                int(os.getenv("CONTROLLER_PROXIMITY_CENTER_NM", "400")),
                int(os.getenv("CONTROLLER_PROXIMITY_CENTER_NM", "400"))
            ),
            "FSS": (
                int(os.getenv("CONTROLLER_PROXIMITY_FSS_NM", "1000")),
                int(os.getenv("CONTROLLER_PROXIMITY_FSS_NM", "1000"))
            ),
            "default": (
                int(os.getenv("CONTROLLER_PROXIMITY_DEFAULT_NM", "30")),
                int(os.getenv("CONTROLLER_PROXIMITY_DEFAULT_NM", "30"))
            )
        }
        self.logger.info("Reset all proximity ranges to default values from environment variables")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the controller type detector.
        
        Returns:
            Dictionary with configuration statistics
            
        Examples:
            >>> detector = ControllerTypeDetector()
            >>> stats = detector.get_statistics()
            >>> stats["total_controller_types"]
            5
            >>> stats["default_range"]
            30
        """
        return {
            "total_controller_types": len(self.proximity_ranges) - 1,  # Exclude default
            "default_range": self.proximity_ranges["default"][0],
            "configured_ranges": {
                controller_type: range_tuple 
                for controller_type, range_tuple in self.proximity_ranges.items()
                if controller_type != "default"
            },
            "detection_method": "callsign_pattern_analysis"
        }
