#!/usr/bin/env python3
"""
Test Controller Frequency Compatibility

Tests for the CTR controller frequency association fix that ensures CTR controllers are
only associated with aircraft on CTR frequencies, not APP/TWR/GND/DEL frequencies.
"""

import os
import pytest
from decimal import Decimal
import asyncio
from datetime import datetime, timedelta, timezone

from app.services.atc_detection_service import ATCDetectionService
from app.services.flight_detection_service import FlightDetectionService
from app.services.config_loader import load_frequency_owners, get_frequency_owner

class TestControllerFrequencyCompatibility:
    """Tests for controller frequency compatibility checks"""
    
    def setup_method(self):
        """Set up test environment"""
        # Create service instances
        self.atc_detection_service = ATCDetectionService()
        self.flight_detection_service = FlightDetectionService()
        
        # Load frequency mappings
        self.frequency_owners = load_frequency_owners()
        self.freq_tolerance_mhz = Decimal("0.005")
        
    def test_is_ctr_on_non_ctr_frequency(self):
        """Test the CTR on non-CTR frequency helper function"""
        # Test CTR controller on CTR frequency
        assert not self.atc_detection_service._is_ctr_on_non_ctr_frequency("ML-GUN_CTR", "ML-WOL_CTR")
        
        # Test CTR controller on non-CTR frequency
        assert self.atc_detection_service._is_ctr_on_non_ctr_frequency("ML-GUN_CTR", "ML_APP")
        assert self.atc_detection_service._is_ctr_on_non_ctr_frequency("ML-GUN_CTR", "ML_TWR")
        assert self.atc_detection_service._is_ctr_on_non_ctr_frequency("ML-GUN_CTR", "ML_GND")
        
        # Test non-CTR controller on any frequency (should always be False)
        assert not self.atc_detection_service._is_ctr_on_non_ctr_frequency("ML_APP", "ML-GUN_CTR")
        assert not self.atc_detection_service._is_ctr_on_non_ctr_frequency("ML_APP", "ML_TWR")
        
        # Test edge cases
        assert not self.atc_detection_service._is_ctr_on_non_ctr_frequency("ML-GUN_CTR", None)
        assert not self.atc_detection_service._is_ctr_on_non_ctr_frequency("ML_APP", None)
    
    def test_frequency_ownership_lookups(self):
        """Test frequency ownership lookups for common frequencies"""
        # This test requires the real controller_callsigns_list.txt to be in the config directory
        if not self.frequency_owners:
            pytest.skip("Frequency owners data not available")
        
        # CTR frequencies
        assert get_frequency_owner(Decimal("128.4"), self.frequency_owners, self.freq_tolerance_mhz) == "ML-GUN_CTR"
        assert get_frequency_owner(Decimal("125.0"), self.frequency_owners, self.freq_tolerance_mhz) == "ML-WOL_CTR"
        
        # APP frequencies
        assert get_frequency_owner(Decimal("132.0"), self.frequency_owners, self.freq_tolerance_mhz) == "ML_APP"
        
        # TWR frequencies
        assert get_frequency_owner(Decimal("120.5"), self.frequency_owners, self.freq_tolerance_mhz) == "ML_TWR"
        
        # GND frequencies
        assert get_frequency_owner(Decimal("121.7"), self.frequency_owners, self.freq_tolerance_mhz) == "ML_GND"
