#!/usr/bin/env python3
"""
Comprehensive Tests for Controller Callsign Filter

Tests the ControllerCallsignFilter class with various configurations
and edge cases to ensure robust operation for filtering VATSIM controller data.
"""

import pytest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

# Import the filter class
from app.filters.controller_callsign_filter import ControllerCallsignFilter, ControllerCallsignFilterConfig


@pytest.mark.unit
@pytest.mark.controller_callsign
class TestControllerCallsignFilterConfig:
    """Test the ControllerCallsignFilterConfig class"""
    
    def test_default_configuration(self):
        """Test default configuration values"""
        config = ControllerCallsignFilterConfig()
        
        assert config.enabled == True
        assert config.callsign_list_path == "config/controller_callsigns_list.txt"
        assert config.case_sensitive == True
    
    def test_from_env_enabled_true(self):
        """Test loading configuration from environment with filter enabled"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
            'CONTROLLER_CALLSIGN_LIST_PATH': '/custom/path/callsigns.txt'
        }):
            config = ControllerCallsignFilterConfig.from_env()
            
            assert config.enabled == True
            assert config.callsign_list_path == '/custom/path/callsigns.txt'
            assert config.case_sensitive == True
    
    def test_from_env_enabled_false(self):
        """Test loading configuration from environment with filter disabled"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'false',
            'CONTROLLER_CALLSIGN_LIST_PATH': '/custom/path/callsigns.txt'
        }):
            config = ControllerCallsignFilterConfig.from_env()
            
            assert config.enabled == False
            assert config.callsign_list_path == '/custom/path/callsigns.txt'
            assert config.case_sensitive == True
    
    def test_from_env_case_insensitive_enabled(self):
        """Test loading configuration with case-insensitive enabled values"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'TRUE',
            'CONTROLLER_CALLSIGN_LIST_PATH': '/custom/path/callsigns.txt'
        }):
            config = ControllerCallsignFilterConfig.from_env()
            
            assert config.enabled == True
    
    def test_from_env_defaults_when_missing(self):
        """Test loading configuration with missing environment variables"""
        with patch.dict(os.environ, {}, clear=True):
            config = ControllerCallsignFilterConfig.from_env()
            
            assert config.enabled == True
            assert config.callsign_list_path == "config/controller_callsigns_list.txt"
            assert config.case_sensitive == True


@pytest.mark.unit
@pytest.mark.controller_callsign
class TestControllerCallsignFilter:
    """Test the ControllerCallsignFilter class"""
    
    def setup_method(self):
        """Setup test environment"""
        # Sample valid callsigns for testing
        self.sample_callsigns = [
            'SY_TWR', 'SY_GND', 'SY_APP', 'ML_TWR', 'ML_GND',
            'BN_TWR', 'BN_GND', 'BN_APP', 'AD_TWR', 'AD_GND', 'SY_DEL'
        ]
        
        # Sample controller data for testing
        self.test_controllers = [
            {'callsign': 'SY_TWR', 'frequency': '118.1', 'facility': 1},
            {'callsign': 'ML_GND', 'frequency': '121.8', 'facility': 2},
            {'callsign': 'BN_APP', 'frequency': '125.5', 'facility': 3},
            {'callsign': 'LHR_TWR', 'frequency': '118.1', 'facility': 4},  # Non-Australian
            {'callsign': 'JFK_GND', 'frequency': '121.8', 'facility': 5},  # Non-Australian
            {'callsign': 'SY_DEL', 'frequency': '127.1', 'facility': 6},
            {'callsign': '', 'frequency': '118.1', 'facility': 7},  # Empty callsign
            {'callsign': None, 'frequency': '118.1', 'facility': 8},  # None callsign
        ]
        
        # Create a temporary callsign file for testing
        self.temp_callsign_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        self.temp_callsign_file.write('\n'.join(self.sample_callsigns))
        self.temp_callsign_file.close()
        self.temp_callsign_path = self.temp_callsign_file.name
    
    def teardown_method(self):
        """Cleanup test environment"""
        if os.path.exists(self.temp_callsign_path):
            os.unlink(self.temp_callsign_path)
    
    def test_initialization_disabled(self):
        """Test filter initialization when disabled"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'false'
        }):
            filter_instance = ControllerCallsignFilter()
            
            assert filter_instance.config.enabled == False
            assert filter_instance._valid_callsigns == set()
            assert filter_instance.stats['valid_callsigns_loaded'] == 0
    
    def test_initialization_enabled_success(self):
        """Test filter initialization when enabled and callsigns load successfully"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
            'CONTROLLER_CALLSIGN_LIST_PATH': self.temp_callsign_path
        }):
            filter_instance = ControllerCallsignFilter()
            
            assert filter_instance.config.enabled == True
            assert len(filter_instance._valid_callsigns) == 11
            assert filter_instance.stats['valid_callsigns_loaded'] == 11
            assert 'SY_TWR' in filter_instance._valid_callsigns
            assert 'ML_GND' in filter_instance._valid_callsigns
    
    def test_initialization_enabled_file_not_found(self):
        """Test filter initialization when enabled but file doesn't exist"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
            'CONTROLLER_CALLSIGN_LIST_PATH': '/nonexistent/file.txt'
        }):
            filter_instance = ControllerCallsignFilter()
            
            assert filter_instance.config.enabled == True
            assert filter_instance._valid_callsigns == set()
            assert filter_instance.stats['valid_callsigns_loaded'] == 0
    
    def test_initialization_enabled_empty_file(self):
        """Test filter initialization with empty callsign file"""
        # Create empty file
        empty_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        empty_file.close()
        
        try:
            with patch.dict(os.environ, {
                'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
                'CONTROLLER_CALLSIGN_LIST_PATH': empty_file.name
            }):
                filter_instance = ControllerCallsignFilter()
                
                assert filter_instance.config.enabled == True
                assert filter_instance._valid_callsigns == set()
                assert filter_instance.stats['valid_callsigns_loaded'] == 0
        finally:
            os.unlink(empty_file.name)
    
    def test_initialization_enabled_file_with_comments(self):
        """Test filter initialization with file containing comments and empty lines"""
        # Create file with comments and empty lines
        comment_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        comment_file.write('# This is a comment\n\nSY_TWR\n  \nML_GND\n# Another comment\nBN_APP\n')
        comment_file.close()
        
        try:
            with patch.dict(os.environ, {
                'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
                'CONTROLLER_CALLSIGN_LIST_PATH': comment_file.name
            }):
                filter_instance = ControllerCallsignFilter()
                
                assert filter_instance.config.enabled == True
                assert len(filter_instance._valid_callsigns) == 3
                assert 'SY_TWR' in filter_instance._valid_callsigns
                assert 'ML_GND' in filter_instance._valid_callsigns
                assert 'BN_APP' in filter_instance._valid_callsigns
        finally:
            os.unlink(comment_file.name)
    
    def test_filter_controllers_list_disabled(self):
        """Test filtering when filter is disabled"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'false'
        }):
            filter_instance = ControllerCallsignFilter()
            result = filter_instance.filter_controllers_list(self.test_controllers)
            
            # Should return all controllers unfiltered
            assert len(result) == len(self.test_controllers)
            assert result == self.test_controllers
    
    def test_filter_controllers_list_enabled_success(self):
        """Test filtering when filter is enabled and working correctly"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
            'CONTROLLER_CALLSIGN_LIST_PATH': self.temp_callsign_path
        }):
            filter_instance = ControllerCallsignFilter()
            result = filter_instance.filter_controllers_list(self.test_controllers)
            
            # Should return only Australian controllers
            assert len(result) == 4  # SY_TWR, ML_GND, BN_APP, SY_DEL
            assert any(c['callsign'] == 'SY_TWR' for c in result)
            assert any(c['callsign'] == 'ML_GND' for c in result)
            assert any(c['callsign'] == 'BN_APP' for c in result)
            assert any(c['callsign'] == 'SY_DEL' for c in result)
            
            # Should not include non-Australian controllers
            assert not any(c['callsign'] == 'LHR_TWR' for c in result)
            assert not any(c['callsign'] == 'JFK_GND' for c in result)
            
            # Should not include controllers with empty/None callsigns
            assert not any(c['callsign'] == '' for c in result)
            assert not any(c['callsign'] is None for c in result)
    
    def test_filter_controllers_list_empty_input(self):
        """Test filtering with empty controller list"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
            'CONTROLLER_CALLSIGN_LIST_PATH': self.temp_callsign_path
        }):
            filter_instance = ControllerCallsignFilter()
            result = filter_instance.filter_controllers_list([])
            
            assert result == []
            assert filter_instance.stats['total_processed'] == 0
            assert filter_instance.stats['controllers_included'] == 0
            assert filter_instance.stats['controllers_excluded'] == 0
    
    def test_filter_controllers_list_none_input(self):
        """Test filtering with None input"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
            'CONTROLLER_CALLSIGN_LIST_PATH': self.temp_callsign_path
        }):
            filter_instance = ControllerCallsignFilter()
            result = filter_instance.filter_controllers_list(None)
            
            assert result is None
    
    def test_filter_controllers_list_no_valid_callsigns_loaded(self):
        """Test filtering when no valid callsigns are loaded"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
            'CONTROLLER_CALLSIGN_LIST_PATH': '/nonexistent/file.txt'
        }):
            filter_instance = ControllerCallsignFilter()
            result = filter_instance.filter_controllers_list(self.test_controllers)
            
            # Should return all controllers unfiltered when no valid callsigns loaded
            assert len(result) == len(self.test_controllers)
            assert result == self.test_controllers
    
    def test_filter_controllers_list_statistics_tracking(self):
        """Test that filtering properly tracks statistics"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
            'CONTROLLER_CALLSIGN_LIST_PATH': self.temp_callsign_path
        }):
            filter_instance = ControllerCallsignFilter()
            
            # Initial stats
            assert filter_instance.stats['total_processed'] == 0
            assert filter_instance.stats['controllers_included'] == 0
            assert filter_instance.stats['controllers_excluded'] == 0
            
            # Filter first batch
            result1 = filter_instance.filter_controllers_list(self.test_controllers)
            assert filter_instance.stats['total_processed'] == 8
            assert filter_instance.stats['controllers_included'] == 4
            assert filter_instance.stats['controllers_excluded'] == 4
            
            # Filter second batch (should accumulate)
            result2 = filter_instance.filter_controllers_list(self.test_controllers)
            assert filter_instance.stats['total_processed'] == 16
            assert filter_instance.stats['controllers_included'] == 8
            assert filter_instance.stats['controllers_excluded'] == 8
    
    def test_is_valid_controller_callsign(self):
        """Test individual callsign validation"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
            'CONTROLLER_CALLSIGN_LIST_PATH': self.temp_callsign_path
        }):
            filter_instance = ControllerCallsignFilter()
            
            # Valid callsigns
            assert filter_instance._is_valid_controller_callsign('SY_TWR') == True
            assert filter_instance._is_valid_controller_callsign('ML_GND') == True
            assert filter_instance._is_valid_controller_callsign('BN_APP') == True
            
            # Invalid callsigns
            assert filter_instance._is_valid_controller_callsign('LHR_TWR') == False
            assert filter_instance._is_valid_controller_callsign('JFK_GND') == False
            assert filter_instance._is_valid_controller_callsign('') == False
            assert filter_instance._is_valid_controller_callsign(None) == False
    
    def test_is_valid_controller_callsign_case_sensitivity(self):
        """Test callsign validation case sensitivity"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
            'CONTROLLER_CALLSIGN_LIST_PATH': self.temp_callsign_path
        }):
            filter_instance = ControllerCallsignFilter()
            
            # Case sensitive matching
            assert filter_instance._is_valid_controller_callsign('SY_TWR') == True
            assert filter_instance._is_valid_controller_callsign('sy_twr') == False
            assert filter_instance._is_valid_controller_callsign('Sy_Twr') == False
    
    def test_reload_callsigns_success(self):
        """Test successful reloading of callsigns"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
            'CONTROLLER_CALLSIGN_LIST_PATH': self.temp_callsign_path
        }):
            filter_instance = ControllerCallsignFilter()
            
            # Initial load
            initial_count = len(filter_instance._valid_callsigns)
            assert initial_count == 11
            
            # Create new callsign file with different content
            new_callsigns = ['NEW_TWR', 'NEW_GND', 'NEW_APP']
            new_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
            new_file.write('\n'.join(new_callsigns))
            new_file.close()
            
            try:
                # Temporarily change the path and reload
                original_path = filter_instance.config.callsign_list_path
                filter_instance.config.callsign_list_path = new_file.name
                
                # Reload
                success = filter_instance.reload_callsigns()
                
                assert success == True
                assert len(filter_instance._valid_callsigns) == 3
                assert 'NEW_TWR' in filter_instance._valid_callsigns
                assert 'NEW_GND' in filter_instance._valid_callsigns
                assert 'NEW_APP' in filter_instance._valid_callsigns
                assert filter_instance.stats['valid_callsigns_loaded'] == 3
                
                # Restore original path
                filter_instance.config.callsign_list_path = original_path
                
            finally:
                os.unlink(new_file.name)
    
    def test_reload_callsigns_failure(self):
        """Test reloading when file doesn't exist"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
            'CONTROLLER_CALLSIGN_LIST_PATH': self.temp_callsign_path
        }):
            filter_instance = ControllerCallsignFilter()
            
            # Initial load
            initial_count = len(filter_instance._valid_callsigns)
            assert initial_count == 11
            
            # Try to reload from non-existent file
            filter_instance.config.callsign_list_path = '/nonexistent/file.txt'
            success = filter_instance.reload_callsigns()
            
            assert success == False
            # Should keep original callsigns
            assert len(filter_instance._valid_callsigns) == 11
            assert filter_instance.stats['valid_callsigns_loaded'] == 11
    
    def test_get_filter_stats(self):
        """Test getting filter statistics"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
            'CONTROLLER_CALLSIGN_LIST_PATH': self.temp_callsign_path
        }):
            filter_instance = ControllerCallsignFilter()
            
            # Filter some controllers to generate stats
            filter_instance.filter_controllers_list(self.test_controllers)
            
            stats = filter_instance.get_filter_stats()
            
            assert stats['enabled'] == True
            assert stats['valid_callsigns_loaded'] == 11
            assert stats['total_processed'] == 8
            assert stats['controllers_included'] == 4
            assert stats['controllers_excluded'] == 4
            assert stats['callsign_list_path'] == self.temp_callsign_path
            assert stats['case_sensitive'] == True
    
    def test_get_filter_status(self):
        """Test getting filter status information"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
            'CONTROLLER_CALLSIGN_LIST_PATH': self.temp_callsign_path
        }):
            filter_instance = ControllerCallsignFilter()
            
            status = filter_instance.get_filter_status()
            
            assert status['enabled'] == True
            assert status['valid_callsigns_loaded'] == 11
            assert status['callsign_list_path'] == self.temp_callsign_path
            assert status['case_sensitive'] == True
            assert status['filtering_active'] == True
    
    def test_get_filter_status_disabled(self):
        """Test getting filter status when disabled"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'false'
        }):
            filter_instance = ControllerCallsignFilter()
            
            status = filter_instance.get_filter_status()
            
            assert status['enabled'] == False
            assert status['valid_callsigns_loaded'] == 0
            assert status['filtering_active'] == False
    
    def test_get_valid_callsigns_sample(self):
        """Test getting a sample of valid callsigns"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
            'CONTROLLER_CALLSIGN_LIST_PATH': self.temp_callsign_path
        }):
            filter_instance = ControllerCallsignFilter()
            
            # Get sample with default limit
            sample = filter_instance.get_valid_callsigns_sample()
            assert len(sample) == 10  # Default limit
            assert all(callsign in self.sample_callsigns for callsign in sample)
            
            # Get sample with custom limit
            sample = filter_instance.get_valid_callsigns_sample(limit=3)
            assert len(sample) == 3
            assert all(callsign in self.sample_callsigns for callsign in sample)
            
            # Get sample when no callsigns loaded
            with patch.dict(os.environ, {
                'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'false'
            }):
                filter_instance = ControllerCallsignFilter()
                sample = filter_instance.get_valid_callsigns_sample()
                assert sample == []
    
    def test_get_valid_callsigns_sample_sorted(self):
        """Test that sample callsigns are returned in sorted order"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
            'CONTROLLER_CALLSIGN_LIST_PATH': self.temp_callsign_path
        }):
            filter_instance = ControllerCallsignFilter()
            
            sample = filter_instance.get_valid_callsigns_sample()
            
            # Should be sorted alphabetically
            assert sample == sorted(sample)
    
    def test_performance_large_controller_list(self):
        """Test performance with large controller lists"""
        with patch.dict(os.environ, {
            'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
            'CONTROLLER_CALLSIGN_LIST_PATH': self.temp_callsign_path
        }):
            filter_instance = ControllerCallsignFilter()
            
            # Create large list of controllers (mix of valid and invalid)
            large_controllers = []
            for i in range(1000):
                if i % 10 == 0:  # Every 10th controller has valid callsign
                    callsign = self.sample_callsigns[i % len(self.sample_callsigns)]
                else:
                    callsign = f'INVALID_{i}'
                
                large_controllers.append({
                    'callsign': callsign,
                    'frequency': f'118.{i % 10}',
                    'facility': i
                })
            
            # Time the filtering operation
            import time
            start_time = time.time()
            result = filter_instance.filter_controllers_list(large_controllers)
            end_time = time.time()
            
            # Should complete in reasonable time (< 100ms for 1000 controllers)
            processing_time = (end_time - start_time) * 1000
            assert processing_time < 100, f"Filtering took {processing_time:.2f}ms, expected < 100ms"
            
            # Should have filtered correctly
            expected_valid = 1000 // 10  # Every 10th controller
            assert len(result) == expected_valid
            
            # All returned controllers should have valid callsigns
            assert all(c['callsign'] in self.sample_callsigns for c in result)


@pytest.mark.unit
@pytest.mark.controller_callsign
class TestControllerCallsignFilterIntegration:
    """Test integration aspects of the controller callsign filter"""
    
    def test_filter_with_real_vatsim_data_structure(self):
        """Test filter with realistic VATSIM API data structure"""
        # Realistic VATSIM controller data structure
        vatsim_controllers = [
            {
                'callsign': 'SY_TWR',
                'cid': '123456',
                'name': 'John Doe',
                'callsign': 'SY_TWR',
                'frequency': '118.1',
                'facility': 1,
                'rating': 3,
                'server': 'vatsim1',
                'visual_range': 50,
                'logon_time': '2024-01-01T10:00:00Z',
                'last_updated': '2024-01-01T10:05:00Z'
            },
            {
                'callsign': 'LHR_TWR',
                'cid': '789012',
                'name': 'Jane Smith',
                'callsign': 'LHR_TWR',
                'frequency': '118.1',
                'facility': 1,
                'rating': 3,
                'server': 'vatsim2',
                'visual_range': 50,
                'logon_time': '2024-01-01T10:00:00Z',
                'last_updated': '2024-01-01T10:05:00Z'
            }
        ]
        
        # Create temporary callsign file with just SY_TWR
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        temp_file.write('SY_TWR\n')
        temp_file.close()
        
        try:
            with patch.dict(os.environ, {
                'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
                'CONTROLLER_CALLSIGN_LIST_PATH': temp_file.name
            }):
                filter_instance = ControllerCallsignFilter()
                result = filter_instance.filter_controllers_list(vatsim_controllers)
                
                # Should only return SY_TWR
                assert len(result) == 1
                assert result[0]['callsign'] == 'SY_TWR'
                assert result[0]['cid'] == '123456'
                assert result[0]['name'] == 'John Doe'
                
                # Should not include LHR_TWR
                assert not any(c['callsign'] == 'LHR_TWR' for c in result)
                
        finally:
            os.unlink(temp_file.name)
    
    def test_filter_preserves_controller_data_integrity(self):
        """Test that filtering preserves all original controller data fields"""
        controller_data = {
            'callsign': 'SY_TWR',
            'cid': '123456',
            'name': 'John Doe',
            'frequency': '118.1',
            'facility': 1,
            'rating': 3,
            'server': 'vatsim1',
            'visual_range': 50,
            'logon_time': '2024-01-01T10:00:00Z',
            'last_updated': '2024-01-01T10:05:00Z',
            'custom_field': 'custom_value'  # Custom field
        }
        
        # Create temporary callsign file
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        temp_file.write('SY_TWR\n')
        temp_file.close()
        
        try:
            with patch.dict(os.environ, {
                'CONTROLLER_CALLSIGN_FILTER_ENABLED': 'true',
                'CONTROLLER_CALLSIGN_LIST_PATH': temp_file.name
            }):
                filter_instance = ControllerCallsignFilter()
                result = filter_instance.filter_controllers_list([controller_data])
                
                # Should return the controller
                assert len(result) == 1
                filtered_controller = result[0]
                
                # All original fields should be preserved
                for key, value in controller_data.items():
                    assert filtered_controller[key] == value
                
                # Should have the same number of fields
                assert len(filtered_controller) == len(controller_data)
                
        finally:
            os.unlink(temp_file.name)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
