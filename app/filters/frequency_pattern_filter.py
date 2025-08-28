#!/usr/bin/env python3
"""
Frequency Pattern Filter Module

This module provides filtering for transceivers based on frequency patterns
that should be excluded from the system. Frequencies are rounded to 3 decimal
places (e.g., 122.800 MHz) for practical filtering.
"""

import os
import logging
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class FrequencyPatternConfig:
    """Frequency pattern filter configuration"""
    enabled: bool = True
    excluded_frequencies_mhz: List[float] = None

class FrequencyPatternFilter:
    """
    Frequency Pattern Filter
    
    Filters out transceivers based on frequencies that should be excluded.
    Frequencies are rounded to 3 decimal places (e.g., 122.800 MHz) for
    practical filtering rather than exact Hz matching.
    """
    
    def __init__(self):
        """Initialize frequency pattern filter with configuration."""
        self.config = self._get_filter_config()
        self._setup_logging()
        
        # Statistics tracking with 7-day rolling window
        self.stats = {
            'daily_processed': {},      # {'2025-08-28': 1500000, '2025-08-29': 1600000}
            'daily_included': {},       # {'2025-08-28': 1200000, '2025-08-29': 1280000}
            'daily_excluded': {},       # {'2025-08-28': 300000, '2025-08-29': 320000}
            'window_days': 7           # Keep last 7 days
        }
        
        logger.info(f"Frequency pattern filter initialized - enabled: {self.config.enabled}")
        if self.config.excluded_frequencies_mhz:
            logger.info(f"Configured excluded frequencies: {', '.join(map(str, self.config.excluded_frequencies_mhz))} MHz")
    
    def _get_filter_config(self) -> FrequencyPatternConfig:
        """Get filter configuration from environment variables"""
        # Get excluded frequencies from environment variable (in MHz) - no hardcoded defaults
        excluded_freqs_str = os.getenv("EXCLUDED_FREQUENCIES_MHZ", "")
        
        # Split by comma and convert to floats with partial failure handling
        excluded_frequencies = []
        if excluded_freqs_str:
            for freq_str in excluded_freqs_str.split(","):
                try:
                    freq_value = float(freq_str.strip())
                    # Validate frequency is in reasonable aviation range (118-137 MHz)
                    if 118.0 <= freq_value <= 137.0:
                        excluded_frequencies.append(freq_value)
                    else:
                        logger.error(f"Frequency {freq_value} MHz outside valid aviation range (118-137 MHz) - skipping")
                except ValueError:
                    logger.error(f"Invalid frequency value: {freq_str} - skipping")
        
        return FrequencyPatternConfig(
            enabled=True,  # Always enabled
            excluded_frequencies_mhz=excluded_frequencies
        )
    
    def _setup_logging(self):
        """Setup logging for the filter"""
        logger.setLevel(logging.INFO)
    
    def _get_current_date_key(self) -> str:
        """Get current date as string key for statistics"""
        return datetime.now().strftime('%Y-%m-%d')
    
    def _cleanup_old_stats(self):
        """Remove statistics older than window_days"""
        current_date = datetime.now()
        cutoff_date = current_date - timedelta(days=self.stats['window_days'])
        cutoff_key = cutoff_date.strftime('%Y-%m-%d')
        
        # Remove old daily statistics
        for date_key in list(self.stats['daily_processed'].keys()):
            if date_key < cutoff_key:
                del self.stats['daily_processed'][date_key]
                del self.stats['daily_included'][date_key]
                del self.stats['daily_excluded'][date_key]
    
    def _update_daily_stats(self, processed: int, included: int, excluded: int):
        """Update daily statistics with rolling window cleanup"""
        current_date_key = self._get_current_date_key()
        
        # Initialize current date if not exists
        if current_date_key not in self.stats['daily_processed']:
            self.stats['daily_processed'][current_date_key] = 0
            self.stats['daily_included'][current_date_key] = 0
            self.stats['daily_excluded'][current_date_key] = 0
        
        # Update current day statistics
        self.stats['daily_processed'][current_date_key] += processed
        self.stats['daily_included'][current_date_key] += included
        self.stats['daily_excluded'][current_date_key] += excluded
        
        # Cleanup old statistics
        self._cleanup_old_stats()
    
    def _hz_to_mhz_rounded(self, frequency_hz: int) -> float:
        """
        Convert frequency from Hz to MHz rounded to 3 decimal places.
        
        Args:
            frequency_hz: Frequency in Hz
            
        Returns:
            float: Frequency in MHz rounded to 3 decimal places
        """
        if not frequency_hz:
            return 0.0
        
        # Validate frequency is reasonable (positive and not extremely large)
        if frequency_hz < 0 or frequency_hz > 999999999999:
            raise ValueError(f"Frequency {frequency_hz} Hz is outside reasonable range")
        
        # Convert Hz to MHz and round to 3 decimal places
        frequency_mhz = frequency_hz / 1000000.0
        return round(frequency_mhz, 3)
    
    def _should_exclude_frequency(self, frequency_hz: int) -> bool:
        """
        Check if a frequency should be excluded.
        
        Args:
            frequency_hz: The frequency in Hz to check
            
        Returns:
            True if frequency should be excluded, False otherwise
        """
        if not frequency_hz or not self.config.excluded_frequencies_mhz:
            return False
        
        # Convert Hz to MHz rounded to 3 decimal places
        frequency_mhz = self._hz_to_mhz_rounded(frequency_hz)
        
        # Check if the rounded MHz frequency is in the excluded list
        return frequency_mhz in self.config.excluded_frequencies_mhz
    
    def filter_transceivers_list(self, transceivers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter transceivers list to exclude those with excluded frequencies.
        
        Args:
            transceivers: List of transceiver data dictionaries
            
        Returns:
            Filtered list of transceivers
        """
        if not self.config.enabled or not transceivers:
            return transceivers
        
        original_count = len(transceivers)
        
        # Use list comprehension for better performance
        filtered_transceivers = []
        for transceiver in transceivers:
            try:
                # Validate transceiver has required structure
                if not isinstance(transceiver, dict):
                    logger.error(f"Invalid transceiver data type: {type(transceiver)}")
                    continue
                
                frequency = transceiver.get('frequency')
                if not self._should_exclude_frequency(frequency):
                    filtered_transceivers.append(transceiver)
                    
            except Exception as e:
                logger.error(f"Error processing transceiver {transceiver.get('callsign', 'unknown')}: {e}")
                continue
        
        excluded_count = original_count - len(filtered_transceivers)
        
        # Update daily statistics with rolling window
        self._update_daily_stats(original_count, len(filtered_transceivers), excluded_count)
        
        if excluded_count > 0:
            logger.info(f"Frequency filter: {original_count} transceivers -> {len(filtered_transceivers)} transceivers (excluded {excluded_count})")
        
        return filtered_transceivers
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """Get filter statistics with rolling window data."""
        # Calculate totals for current window
        total_processed = sum(self.stats['daily_processed'].values())
        total_included = sum(self.stats['daily_included'].values())
        total_excluded = sum(self.stats['daily_excluded'].values())
        
        return {
            'enabled': self.config.enabled,
            'window_days': self.stats['window_days'],
            'total_processed': total_processed,
            'transceivers_included': total_included,
            'transceivers_excluded': total_excluded,
            'excluded_frequencies_mhz': self.config.excluded_frequencies_mhz,
            'daily_breakdown': {
                'processed': self.stats['daily_processed'],
                'included': self.stats['daily_included'],
                'excluded': self.stats['daily_excluded']
            }
        }
    
    def get_filter_status(self) -> Dict[str, Any]:
        """Get filter status information."""
        return {
            'enabled': self.config.enabled,
            'excluded_frequencies_mhz': self.config.excluded_frequencies_mhz,
            'window_days': self.stats['window_days'],
            'active_days': len(self.stats['daily_processed'])
        }
    
    def reset_stats(self):
        """Reset all statistics to zero."""
        self.stats['daily_processed'] = {}
        self.stats['daily_included'] = {}
        self.stats['daily_excluded'] = {}
        logger.info("Frequency filter statistics reset")
