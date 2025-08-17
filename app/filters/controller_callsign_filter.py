#!/usr/bin/env python3
"""
Controller Callsign Filter Module

This module provides filtering for controllers based on a predefined list of valid
Australian VATSIM controller callsigns. It filters out controllers that don't have
callsigns matching the approved list.

This filter is specifically designed for controllers since they don't have geographic
data and cannot be filtered by geographic boundaries.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class ControllerCallsignFilterConfig:
    """Controller callsign filter configuration"""
    enabled: bool = True
    callsign_list_path: str = "config/controller_callsigns_list.txt"
    case_sensitive: bool = True
    
    @classmethod
    def from_env(cls):
        """Load controller callsign filter configuration from environment variables."""
        return cls(
            enabled=os.getenv("CONTROLLER_CALLSIGN_FILTER_ENABLED", "true").lower() == "true",
            callsign_list_path=os.getenv("CONTROLLER_CALLSIGN_LIST_PATH", "config/controller_callsigns_list.txt")
        )

class ControllerCallsignFilter:
    """
    Controller Callsign Filter
    
    Filters controllers based on a predefined list of valid Australian VATSIM controller callsigns.
    This filter is specifically designed for controllers since they don't have geographic data
    and cannot be filtered by geographic boundaries.
    """
    
    def __init__(self):
        """Initialize controller callsign filter with configuration."""
        self.config = self._get_filter_config()
        self._setup_logging()
        
        # Load valid callsigns into memory for O(1) lookup
        self._valid_callsigns = self._load_valid_callsigns()
        
        # Statistics tracking
        self.stats = {
            'total_processed': 0,
            'controllers_included': 0,
            'controllers_excluded': 0,
            'valid_callsigns_loaded': len(self._valid_callsigns) if self._valid_callsigns else 0,
            'callsign_list_path': self.config.callsign_list_path
        }
        
        logger.info(f"Controller callsign filter initialized - enabled: {self.config.enabled}")
        if self._valid_callsigns:
            logger.info(f"Loaded {len(self._valid_callsigns)} valid controller callsigns from {self.config.callsign_list_path}")
        else:
            logger.warning(f"No valid callsigns loaded from {self.config.callsign_list_path}")
    
    def _get_filter_config(self) -> ControllerCallsignFilterConfig:
        """Get filter configuration from environment variables"""
        enabled = os.getenv("CONTROLLER_CALLSIGN_FILTER_ENABLED", "true").lower() == "true"
        callsign_list_path = os.getenv("CONTROLLER_CALLSIGN_LIST_PATH", "config/controller_callsigns_list.txt")
        
        return ControllerCallsignFilterConfig(
            enabled=enabled,
            callsign_list_path=callsign_list_path,
            case_sensitive=True  # Always case sensitive for callsigns
        )
    
    def _setup_logging(self):
        """Setup logging for the filter"""
        logger.setLevel(logging.INFO)
    
    def _load_valid_callsigns(self) -> Optional[set]:
        """
        Load valid controller callsigns from the text file.
        
        Returns:
            Set of valid callsigns, or None if loading fails
        """
        if not self.config.enabled:
            return set()
        
        try:
            # Try to load from the configured path
            callsign_file = Path(self.config.callsign_list_path)
            
            if not callsign_file.exists():
                logger.error(f"Callsign list file not found: {callsign_file}")
                return set()
            
            # Load callsigns from file
            with open(callsign_file, 'r', encoding='utf-8') as f:
                callsigns = set()
                for line in f:
                    callsign = line.strip()
                    if callsign and not callsign.startswith('#'):  # Skip empty lines and comments
                        callsigns.add(callsign)
                
                logger.info(f"Successfully loaded {len(callsigns)} valid controller callsigns")
                return callsigns
                
        except Exception as e:
            logger.error(f"Failed to load callsign list from {self.config.callsign_list_path}: {e}")
            return set()
    
    def _is_valid_controller_callsign(self, callsign: str) -> bool:
        """
        Check if a controller callsign is valid based on the loaded list.
        
        Args:
            callsign: The callsign to check
            
        Returns:
            True if callsign is valid, False otherwise
        """
        if not callsign or not self._valid_callsigns:
            return False
        
        # Check if callsign exists in the valid set (O(1) lookup)
        return callsign in self._valid_callsigns
    
    def filter_controllers_list(self, controllers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter controllers list to only include those with valid callsigns.
        
        Args:
            controllers: List of controller data dictionaries
            
        Returns:
            Filtered list of controllers with valid callsigns
        """
        if not self.config.enabled or not controllers:
            return controllers
        
        if not self._valid_callsigns:
            logger.warning("No valid callsigns loaded, returning all controllers unfiltered")
            return controllers
        
        original_count = len(controllers)
        
        # Use list comprehension for better performance than manual loop
        filtered_controllers = [
            controller for controller in controllers
            if self._is_valid_controller_callsign(controller.get('callsign', ''))
        ]
        
        excluded_count = original_count - len(filtered_controllers)
        
        # Update statistics
        self.stats['total_processed'] += original_count
        self.stats['controllers_included'] += len(filtered_controllers)
        self.stats['controllers_excluded'] += excluded_count
        
        if excluded_count > 0:
            logger.info(f"Controller callsign filter: {original_count} controllers -> {len(filtered_controllers)} controllers (excluded {excluded_count})")
        else:
            logger.debug(f"Controller callsign filter: {original_count} controllers -> {len(filtered_controllers)} controllers")
        
        return filtered_controllers
    
    def reload_callsigns(self) -> bool:
        """
        Reload the valid callsigns from the file.
        
        Returns:
            True if reload successful, False otherwise
        """
        try:
            new_callsigns = self._load_valid_callsigns()
            if new_callsigns is not None and len(new_callsigns) > 0:
                self._valid_callsigns = new_callsigns
                self.stats['valid_callsigns_loaded'] = len(self._valid_callsigns)
                logger.info(f"Successfully reloaded {len(self._valid_callsigns)} valid controller callsigns")
                return True
            else:
                logger.error("Failed to reload callsigns - no valid callsigns loaded")
                return False
        except Exception as e:
            logger.error(f"Error reloading callsigns: {e}")
            return False
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """Get filter statistics."""
        return {
            'enabled': self.config.enabled,
            'valid_callsigns_loaded': self.stats['valid_callsigns_loaded'],
            'total_processed': self.stats['total_processed'],
            'controllers_included': self.stats['controllers_included'],
            'controllers_excluded': self.stats['controllers_excluded'],
            'callsign_list_path': self.stats['callsign_list_path'],
            'case_sensitive': self.config.case_sensitive
        }
    
    def get_filter_status(self) -> Dict[str, Any]:
        """Get filter status information."""
        return {
            'enabled': self.config.enabled,
            'valid_callsigns_loaded': self.stats['valid_callsigns_loaded'],
            'callsign_list_path': self.stats['callsign_list_path'],
            'case_sensitive': self.config.case_sensitive,
            'filtering_active': self.config.enabled and bool(self._valid_callsigns)
        }
    
    def get_valid_callsigns_sample(self, limit: int = 10) -> List[str]:
        """
        Get a sample of valid callsigns for debugging/monitoring.
        
        Args:
            limit: Maximum number of callsigns to return
            
        Returns:
            List of sample callsigns
        """
        if not self._valid_callsigns:
            return []
        
        # Return a sorted sample for consistent output
        return sorted(list(self._valid_callsigns))[:limit]
