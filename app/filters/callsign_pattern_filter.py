#!/usr/bin/env python3
"""
Callsign Pattern Filter Module

This module provides filtering for transceivers based on callsign patterns
that should be excluded from the system.
"""

import os
import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from functools import lru_cache

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class CallsignPatternConfig:
    """Callsign pattern filter configuration"""
    enabled: bool = True
    excluded_patterns: List[str] = None
    case_sensitive: bool = True

class CallsignPatternFilter:
    """
    Callsign Pattern Filter
    
    Filters out transceivers based on callsign patterns that should be excluded.
    This filter is always enabled and filters based on environment variable configuration.
    """
    
    def __init__(self):
        """Initialize callsign pattern filter with configuration."""
        self.config = self._get_filter_config()
        self._setup_logging()
        
        # Pre-compile regex patterns for performance
        self._compiled_patterns = self._compile_patterns()
        
        # Statistics tracking
        self.stats = {
            'total_processed': 0,
            'transceivers_included': 0,
            'transceivers_excluded': 0,
            'patterns_configured': len(self.config.excluded_patterns) if self.config.excluded_patterns else 0
        }
        
        logger.info(f"Callsign pattern filter initialized - enabled: {self.config.enabled}")
        if self.config.excluded_patterns:
            logger.info(f"Configured patterns: {', '.join(self.config.excluded_patterns)}")
    
    def _get_filter_config(self) -> CallsignPatternConfig:
        """Get filter configuration from environment variables"""
        # Get excluded patterns from environment variable
        excluded_patterns_str = os.getenv("EXCLUDED_CALLSIGN_PATTERNS", "ATIS")
        
        # Split by comma and strip whitespace
        excluded_patterns = [pattern.strip() for pattern in excluded_patterns_str.split(",") if pattern.strip()]
        
        return CallsignPatternConfig(
            enabled=True,  # Always enabled
            excluded_patterns=excluded_patterns,
            case_sensitive=True  # Always case sensitive
        )
    
    def _setup_logging(self):
        """Setup logging for the filter"""
        logger.setLevel(logging.INFO)
    
    @lru_cache(maxsize=1)
    def _compile_patterns(self) -> List[re.Pattern]:
        """Pre-compile regex patterns for performance optimization"""
        if not self.config.excluded_patterns:
            return []
        
        compiled = []
        for pattern in self.config.excluded_patterns:
            try:
                # Use re.escape to handle special regex characters safely
                escaped_pattern = re.escape(pattern)
                # Compile with re.IGNORECASE if case insensitive, otherwise case sensitive
                flags = 0 if self.config.case_sensitive else re.IGNORECASE
                compiled.append(re.compile(escaped_pattern, flags))
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")
                # Fallback to simple string matching for invalid patterns
                compiled.append(pattern)
        
        return compiled
    
    def _should_exclude_callsign(self, callsign: str) -> bool:
        """
        Check if a callsign should be excluded based on configured patterns.
        
        Args:
            callsign: The callsign to check
            
        Returns:
            True if callsign should be excluded, False otherwise
        """
        if not callsign or not self._compiled_patterns:
            return False
        
        # Fast path: if only one pattern, avoid loop overhead
        if len(self._compiled_patterns) == 1:
            pattern = self._compiled_patterns[0]
            if isinstance(pattern, re.Pattern):
                return bool(pattern.search(callsign))
            else:
                # Fallback for non-compiled patterns
                return pattern in callsign
        
        # Multiple patterns: use optimized loop
        for pattern in self._compiled_patterns:
            if isinstance(pattern, re.Pattern):
                if pattern.search(callsign):
                    logger.debug(f"Excluding callsign '{callsign}' due to pattern '{pattern.pattern}'")
                    return True
            else:
                # Fallback for non-compiled patterns
                if pattern in callsign:
                    logger.debug(f"Excluding callsign '{callsign}' due to pattern '{pattern}'")
                    return True
        
        return False
    
    def filter_transceivers_list(self, transceivers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter transceivers list to exclude those matching excluded patterns.
        
        Args:
            transceivers: List of transceiver data dictionaries
            
        Returns:
            Filtered list of transceivers
        """
        if not self.config.enabled or not transceivers:
            return transceivers
        
        original_count = len(transceivers)
        
        # Use list comprehension for better performance than manual loop
        filtered_transceivers = [
            transceiver for transceiver in transceivers
            if not self._should_exclude_callsign(transceiver.get('callsign', ''))
        ]
        
        excluded_count = original_count - len(filtered_transceivers)
        
        # Update statistics
        self.stats['total_processed'] += original_count
        self.stats['transceivers_included'] += len(filtered_transceivers)
        self.stats['transceivers_excluded'] += excluded_count
        
        if excluded_count > 0:
            logger.info(f"Callsign pattern filter: {original_count} transceivers -> {len(filtered_transceivers)} transceivers (excluded {excluded_count})")
        
        return filtered_transceivers
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """Get filter statistics."""
        return {
            'enabled': self.config.enabled,
            'patterns_configured': self.stats['patterns_configured'],
            'total_processed': self.stats['total_processed'],
            'transceivers_included': self.stats['transceivers_included'],
            'transceivers_excluded': self.stats['transceivers_excluded'],
            'excluded_patterns': self.config.excluded_patterns,
            'compiled_patterns_count': len(self._compiled_patterns)
        }
    
    def get_filter_status(self) -> Dict[str, Any]:
        """Get filter status information."""
        return {
            'enabled': self.config.enabled,
            'patterns_configured': self.stats['patterns_configured'],
            'excluded_patterns': self.config.excluded_patterns,
            'case_sensitive': self.config.case_sensitive,
            'compiled_patterns_count': len(self._compiled_patterns)
        }
