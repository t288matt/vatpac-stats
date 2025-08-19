#!/usr/bin/env python3
"""
Unit tests for ControllerTypeDetector service

This test suite validates the controller type detection logic,
proximity range assignment, and all service methods.
"""

import pytest
from app.services.controller_type_detector import ControllerTypeDetector


class TestControllerTypeDetector:
    """Test controller type detection logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = ControllerTypeDetector()
    
    def test_callsign_pattern_detection(self):
        """Test controller type detection from callsign patterns."""
        # Ground controllers
        assert self.detector.detect_controller_type("CB_GND") == "Ground"
        assert self.detector.detect_controller_type("SY_DEL") == "Ground"
        assert self.detector.detect_controller_type("ML_GND") == "Ground"
        
        # Tower controllers
        assert self.detector.detect_controller_type("SY_TWR") == "Tower"
        assert self.detector.detect_controller_type("YBBN_TWR") == "Tower"
        assert self.detector.detect_controller_type("ADL_TWR") == "Tower"
        
        # Approach controllers
        assert self.detector.detect_controller_type("YBBN_APP") == "Approach"
        assert self.detector.detect_controller_type("SY_DEP") == "Approach"
        assert self.detector.detect_controller_type("ML_APP") == "Approach"
        
        # Center controllers
        assert self.detector.detect_controller_type("AUSTRALIA_CTR") == "Center"
        assert self.detector.detect_controller_type("BN_CTR") == "Center"
        assert self.detector.detect_controller_type("SY_CTR") == "Center"
        
        # FSS controllers
        assert self.detector.detect_controller_type("AU_FSS") == "FSS"
        assert self.detector.detect_controller_type("SY_FSS") == "FSS"
        assert self.detector.detect_controller_type("ML_FSS") == "FSS"
    
    def test_proximity_ranges(self):
        """Test proximity range assignment."""
        assert self.detector.get_proximity_range("Ground") == (15, 15)
        assert self.detector.get_proximity_range("Tower") == (15, 15)
        assert self.detector.get_proximity_range("Approach") == (60, 60)
        assert self.detector.get_proximity_range("Center") == (400, 400)
        assert self.detector.get_proximity_range("FSS") == (1000, 1000)
    
    def test_proximity_thresholds(self):
        """Test proximity threshold retrieval."""
        assert self.detector.get_proximity_threshold("Ground") == 15
        assert self.detector.get_proximity_threshold("Tower") == 15
        assert self.detector.get_proximity_threshold("Approach") == 60
        assert self.detector.get_proximity_threshold("Center") == 400
        assert self.detector.get_proximity_threshold("FSS") == 1000
    
    def test_fallback_behavior(self):
        """Test fallback to default for unknown types."""
        # Unknown controller type should default to Ground
        assert self.detector.detect_controller_type("UNKNOWN") == "Ground"
        assert self.detector.detect_controller_type("TEST123") == "Ground"
        assert self.detector.detect_controller_type("RANDOM") == "Ground"
        
        # Unknown type should use default proximity range
        assert self.detector.get_proximity_range("UnknownType") == (30, 30)
        assert self.detector.get_proximity_threshold("UnknownType") == 30
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Empty callsign
        assert self.detector.detect_controller_type("") == "Ground"
        assert self.detector.detect_controller_type(None) == "Ground"
        
        # Very short callsigns
        assert self.detector.detect_controller_type("A") == "Ground"
        assert self.detector.detect_controller_type("AB") == "Ground"
        assert self.detector.detect_controller_type("ABC") == "Ground"
        
        # Exact 3-character callsigns
        assert self.detector.detect_controller_type("GND") == "Ground"
        assert self.detector.detect_controller_type("TWR") == "Tower"
        assert self.detector.detect_controller_type("APP") == "Approach"
        assert self.detector.detect_controller_type("CTR") == "Center"
        assert self.detector.detect_controller_type("FSS") == "FSS"
        
        # Long callsigns
        assert self.detector.detect_controller_type("VERY_LONG_CALLSIGN_TWR") == "Tower"
        assert self.detector.detect_controller_type("AUSTRALIA_MELBOURNE_APP") == "Approach"
    
    def test_case_insensitivity(self):
        """Test that detection is case insensitive."""
        # Lowercase
        assert self.detector.detect_controller_type("sy_twr") == "Tower"
        assert self.detector.detect_controller_type("cb_gnd") == "Ground"
        assert self.detector.detect_controller_type("ybbn_app") == "Approach"
        
        # Mixed case
        assert self.detector.detect_controller_type("Sy_TwR") == "Tower"
        assert self.detector.detect_controller_type("Cb_GnD") == "Ground"
        assert self.detector.detect_controller_type("YbBn_ApP") == "Approach"
        
        # Uppercase
        assert self.detector.detect_controller_type("SY_TWR") == "Tower"
        assert self.detector.detect_controller_type("CB_GND") == "Ground"
        assert self.detector.detect_controller_type("YBBN_APP") == "Approach"
    
    def test_controller_info_method(self):
        """Test the comprehensive controller info method."""
        info = self.detector.get_controller_info("SY_TWR")
        
        assert info["callsign"] == "SY_TWR"
        assert info["type"] == "Tower"
        assert info["proximity_range"] == (15, 15)
        assert info["proximity_threshold"] == 15
        assert info["detection_method"] == "callsign_pattern"
        
        # Test FSS controller
        fss_info = self.detector.get_controller_info("AU_FSS")
        assert fss_info["type"] == "FSS"
        assert fss_info["proximity_range"] == (1000, 1000)
        assert fss_info["proximity_threshold"] == 1000
    
    def test_validation_methods(self):
        """Test validation and utility methods."""
        # Valid controller types
        assert self.detector.is_valid_controller_type("Ground") == True
        assert self.detector.is_valid_controller_type("Tower") == True
        assert self.detector.is_valid_controller_type("Approach") == True
        assert self.detector.is_valid_controller_type("Center") == True
        assert self.detector.is_valid_controller_type("FSS") == True
        assert self.detector.is_valid_controller_type("default") == True
        
        # Invalid controller types
        assert self.detector.is_valid_controller_type("Invalid") == False
        assert self.detector.is_valid_controller_type("Unknown") == False
        assert self.detector.is_valid_controller_type("") == False
        assert self.detector.is_valid_controller_type(None) == False
    
    def test_proximity_range_updates(self):
        """Test updating proximity ranges."""
        # Update Tower range
        assert self.detector.update_proximity_range("Tower", (20, 20)) == True
        assert self.detector.get_proximity_range("Tower") == (20, 20)
        assert self.detector.get_proximity_threshold("Tower") == 20
        
        # Update Approach range
        assert self.detector.update_proximity_range("Approach", (40, 50)) == True
        assert self.detector.get_proximity_range("Approach") == (40, 50)
        assert self.detector.get_proximity_threshold("Approach") == 50
        
        # Try to update invalid controller type
        assert self.detector.update_proximity_range("Invalid", (20, 20)) == False
        
        # Try to update with invalid range format
        assert self.detector.update_proximity_range("Tower", (20,)) == False
        assert self.detector.update_proximity_range("Tower", (20, -10)) == False
        assert self.detector.update_proximity_range("Tower", (20, "invalid")) == False
    
    def test_reset_functionality(self):
        """Test reset to default values."""
        # Change some values
        self.detector.update_proximity_range("Tower", (20, 20))
        self.detector.update_proximity_range("Approach", (50, 50))
        
        # Verify changes
        assert self.detector.get_proximity_range("Tower") == (20, 20)
        assert self.detector.get_proximity_range("Approach") == (50, 50)
        
        # Reset to defaults
        self.detector.reset_to_defaults()
        
        # Verify defaults restored
        assert self.detector.get_proximity_range("Tower") == (15, 15)
        assert self.detector.get_proximity_range("Approach") == (60, 60)
        assert self.detector.get_proximity_range("Center") == (400, 400)
        assert self.detector.get_proximity_range("FSS") == (1000, 1000)
    
    def test_statistics_method(self):
        """Test the statistics method."""
        stats = self.detector.get_statistics()
        
        assert stats["total_controller_types"] == 5
        assert stats["default_range"] == 30
        assert stats["detection_method"] == "callsign_pattern_analysis"
        
        # Check configured ranges
        configured_ranges = stats["configured_ranges"]
        assert configured_ranges["Ground"] == (15, 15)
        assert configured_ranges["Tower"] == (15, 15)
        assert configured_ranges["Approach"] == (60, 60)
        assert configured_ranges["Center"] == (400, 400)
        assert configured_ranges["FSS"] == (1000, 1000)
        
        # Default should not be in configured ranges
        assert "default" not in configured_ranges
    
    def test_get_all_proximity_ranges(self):
        """Test getting all proximity ranges."""
        ranges = self.detector.get_all_proximity_ranges()
        
        # Should include all ranges including default
        assert len(ranges) == 6  # 5 controller types + default
        assert ranges["Ground"] == (15, 15)
        assert ranges["Tower"] == (15, 15)
        assert ranges["Approach"] == (60, 60)
        assert ranges["Center"] == (400, 400)
        assert ranges["FSS"] == (1000, 1000)
        assert ranges["default"] == (30, 30)
        
        # Should be a copy, not reference
        ranges["Ground"] = (999, 999)
        assert self.detector.get_proximity_range("Ground") == (15, 15)  # Original unchanged
    
    def test_real_world_examples(self):
        """Test with real-world VATSIM callsign examples."""
        # Australian controllers
        assert self.detector.detect_controller_type("SY_TWR") == "Tower"      # Sydney Tower
        assert self.detector.detect_controller_type("ML_APP") == "Approach"   # Melbourne Approach
        assert self.detector.detect_controller_type("BN_CTR") == "Center"     # Brisbane Center
        assert self.detector.detect_controller_type("CB_GND") == "Ground"     # Canberra Ground
        assert self.detector.detect_controller_type("AU_FSS") == "FSS"        # Australia FSS
        
        # International examples
        assert self.detector.detect_controller_type("LAX_TWR") == "Tower"     # Los Angeles Tower
        assert self.detector.detect_controller_type("LHR_APP") == "Approach"  # London Heathrow Approach
        assert self.detector.detect_controller_type("JFK_CTR") == "Center"    # New York Center
        assert self.detector.detect_controller_type("CDG_GND") == "Ground"    # Paris Ground
        assert self.detector.detect_controller_type("DE_FSS") == "FSS"        # Germany FSS
    
    def test_performance_characteristics(self):
        """Test performance characteristics of the service."""
        import time
        
        # Test detection speed
        start_time = time.time()
        for _ in range(1000):
            self.detector.detect_controller_type("SY_TWR")
        detection_time = time.time() - start_time
        
        # Should be very fast (under 1 second for 1000 calls)
        assert detection_time < 1.0
        
        # Test range lookup speed
        start_time = time.time()
        for _ in range(1000):
            self.detector.get_proximity_range("Tower")
        lookup_time = time.time() - start_time
        
        # Should be very fast (under 1 second for 1000 calls)
        assert lookup_time < 1.0


if __name__ == "__main__":
    pytest.main([__file__])
