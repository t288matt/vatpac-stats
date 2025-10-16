"""
Unified airborne detection logic using speed criteria.

This module provides a single source of truth for determining if an aircraft
is airborne based on groundspeed thresholds.
"""

from typing import Optional


def is_airborne(groundspeed: Optional[float]) -> bool:
    """
    Determine if aircraft is airborne based on speed criteria.
    
    Args:
        groundspeed: Aircraft groundspeed in knots
        
    Returns:
        True if aircraft is airborne (≥60 knots), False otherwise
    """
    return groundspeed is not None and groundspeed >= 60
