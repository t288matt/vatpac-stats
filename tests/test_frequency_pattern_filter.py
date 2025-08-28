#!/usr/bin/env python3
"""
Comprehensive Tests for Frequency Pattern Filter

Tests the FrequencyPatternFilter class with various configurations
and edge cases to ensure robust operation for filtering transceivers
based on frequency patterns.
"""

import pytest
import os
from unittest.mock import patch, MagicMock

# Import the filter class
from app.filters.frequency_pattern_filter import FrequencyPatternFilter, FrequencyPatternConfig


@pytest.mark.unit
@pytest.mark.frequency_pattern
class TestFrequencyPatternConfig:
    """Test the FrequencyPatternConfig class"""
    
    def test_default_configuration(self):
        """Test default configuration values"""
        config = FrequencyPatternConfig()
        
        assert config.enabled == True
        assert config.excluded_frequencies_mhz == None
    
    def test_custom_configuration(self):
        """Test custom configuration values"""
        excluded_freqs = [122.800, 121.500, 123.450]
        config = FrequencyPatternConfig(
            enabled=False,
            excluded_frequencies_mhz=excluded_freqs
        )
        
        assert config.enabled == False
        assert config.excluded_frequencies_mhz == excluded_freqs


@pytest.mark.unit
@pytest.mark.frequency_pattern
class TestFrequencyPatternFilter:
    """Test the FrequencyPatternFilter class"""
    
    def setup_method(self):
        """Setup test environment"""
        # Sample transceiver data for testing - using realistic VATSIM structure
        self.test_transceivers = [
            # UNICOM frequency (should be excluded)
            {'transceiver_id': 1001, 'frequency': 122800000, 'callsign': 'PILOT001'},  # 122.800 MHz
            {'transceiver_id': 1002, 'frequency': 122800020, 'callsign': 'PILOT002'},  # 122.800020 MHz -> 122.800
            {'transceiver_id': 1003, 'frequency': 122800019, 'callsign': 'PILOT003'},  # 122.800019 MHz -> 122.800
            
            # Valid frequencies (should be included)
            {'transceiver_id': 1004, 'frequency': 118100000, 'callsign': 'PILOT004'},  # 118.100 MHz
            {'transceiver_id': 1005, 'frequency': 121800000, 'callsign': 'PILOT005'},  # 121.800 MHz
            {'transceiver_id': 1006, 'frequency': 125500000, 'callsign': 'PILOT006'},  # 125.500 MHz
            {'transceiver_id': 1007, 'frequency': 127100000, 'callsign': 'PILOT007'},  # 127.100 MHz
            
            # Edge cases
            {'transceiver_id': 1008, 'frequency': None, 'callsign': 'PILOT008'},      # No frequency
            {'transceiver_id': 1009, 'frequency': 0, 'callsign': 'PILOT009'},         # Zero frequency
            {'transceiver_id': 1010, 'frequency': 122799999, 'callsign': 'PILOT010'}, # 122.799999 MHz -> 122.800 (excluded)
            {'transceiver_id': 1011, 'frequency': 122800001, 'callsign': 'PILOT011'}, # 122.800001 MHz -> 122.800 (excluded)
        ]
    
    def test_default_initialization(self):
        """Test filter initialization with default configuration"""
        with patch.dict(os.environ, {}, clear=True):
            filter_instance = FrequencyPatternFilter()
            
            assert filter_instance.config.enabled == True
            assert filter_instance.config.excluded_frequencies_mhz == []  # No default when env var is empty
            assert filter_instance.stats['window_days'] == 7
            assert len(filter_instance.stats['daily_processed']) == 0
            assert len(filter_instance.stats['daily_included']) == 0
            assert len(filter_instance.stats['daily_excluded']) == 0
    
    def test_custom_environment_configuration(self):
        """Test filter initialization with custom environment variables"""
        with patch.dict(os.environ, {
            'EXCLUDED_FREQUENCIES_MHZ': '122.800,121.500,123.450'
        }):
            filter_instance = FrequencyPatternFilter()
            
            assert filter_instance.config.enabled == True
            assert filter_instance.config.excluded_frequencies_mhz == [122.800, 121.500, 123.450]
            assert filter_instance.stats['window_days'] == 7
    
    def test_invalid_environment_configuration(self):
        """Test filter initialization with invalid environment variables"""
        with patch.dict(os.environ, {
            'EXCLUDED_FREQUENCIES_MHZ': '122.800,invalid,123.450'
        }):
            filter_instance = FrequencyPatternFilter()
            
            # Should handle invalid values gracefully (partial failure)
            assert filter_instance.config.enabled == True
            assert 122.800 in filter_instance.config.excluded_frequencies_mhz
            assert 123.450 in filter_instance.config.excluded_frequencies_mhz
            # Invalid value should be skipped
            assert 'invalid' not in filter_instance.config.excluded_frequencies_mhz
    
    def test_hz_to_mhz_rounded_conversion(self):
        """Test Hz to MHz conversion with rounding"""
        filter_instance = FrequencyPatternFilter()
        
        # Test exact conversions
        assert filter_instance._hz_to_mhz_rounded(122800000) == 122.800
        assert filter_instance._hz_to_mhz_rounded(118100000) == 118.100
        assert filter_instance._hz_to_mhz_rounded(121800000) == 121.800
        
        # Test conversions with precision
        assert filter_instance._hz_to_mhz_rounded(122800020) == 122.800
        assert filter_instance._hz_to_mhz_rounded(122800019) == 122.800
        assert filter_instance._hz_to_mhz_rounded(122800500) == 122.800
        assert filter_instance._hz_to_mhz_rounded(122800999) == 122.801  # 122.800999 rounds to 122.801
        
        # Test edge cases
        assert filter_instance._hz_to_mhz_rounded(0) == 0.0
        assert filter_instance._hz_to_mhz_rounded(None) == 0.0
    
    def test_should_exclude_frequency_logic(self):
        """Test frequency exclusion logic"""
        with patch.dict(os.environ, {
            'EXCLUDED_FREQUENCIES_MHZ': '122.800,121.500'
        }):
            filter_instance = FrequencyPatternFilter()
            
            # Test UNICOM frequency (122.800 MHz)
            assert filter_instance._should_exclude_frequency(122800000) == True
            assert filter_instance._should_exclude_frequency(122800020) == True
            assert filter_instance._should_exclude_frequency(122800019) == True
            
            # Test other excluded frequency (121.500 MHz)
            assert filter_instance._should_exclude_frequency(121500000) == True
            assert filter_instance._should_exclude_frequency(121500020) == True
            
            # Test non-excluded frequencies
            assert filter_instance._should_exclude_frequency(118100000) == False  # 118.100 MHz
            assert filter_instance._should_exclude_frequency(125500000) == False  # 125.500 MHz
            assert filter_instance._should_exclude_frequency(127100000) == False  # 127.100 MHz
            
            # Test edge cases
            assert filter_instance._should_exclude_frequency(None) == False
            assert filter_instance._should_exclude_frequency(0) == False
    
    def test_filter_transceivers_list_basic_functionality(self):
        """Test basic transceiver filtering functionality"""
        with patch.dict(os.environ, {
            'EXCLUDED_FREQUENCIES_MHZ': '122.800'
        }):
            filter_instance = FrequencyPatternFilter()
            
            # Filter the test transceivers
            filtered_result = filter_instance.filter_transceivers_list(self.test_transceivers)
            
            # Should exclude UNICOM frequencies (transceiver_id 1001, 1002, 1003, 1010, 1011)
            expected_included = [1004, 1005, 1006, 1007, 1008, 1009]  # transceiver_ids
            expected_excluded = [1001, 1002, 1003, 1010, 1011]        # transceiver_ids
            
            # Verify included transceivers
            for transceiver in filtered_result:
                assert transceiver['transceiver_id'] in expected_included
                assert transceiver['transceiver_id'] not in expected_excluded
            
            # Verify excluded transceivers
            for transceiver_id in expected_excluded:
                assert not any(t['transceiver_id'] == transceiver_id for t in filtered_result)
            
            # Verify counts
            assert len(filtered_result) == 6  # 11 total - 5 excluded
    
    def test_filter_transceivers_list_multiple_excluded_frequencies(self):
        """Test filtering with multiple excluded frequencies"""
        with patch.dict(os.environ, {
            'EXCLUDED_FREQUENCIES_MHZ': '122.800,121.500'
        }):
            filter_instance = FrequencyPatternFilter()
            
            # Filter the test transceivers
            filtered_result = filter_instance.filter_transceivers_list(self.test_transceivers)
            
            # Should exclude UNICOM (122.800) frequencies
            # Note: 121.800 MHz is NOT 121.500 MHz, so it should be included
            expected_excluded = [1001, 1002, 1003, 1010, 1011]  # All round to 122.800 MHz
            expected_included = [1004, 1005, 1006, 1007, 1008, 1009]
            
            # Verify included transceivers
            for transceiver in filtered_result:
                assert transceiver['transceiver_id'] in expected_included
                assert transceiver['transceiver_id'] not in expected_excluded
            
            # Verify counts
            assert len(filtered_result) == 6  # 11 total - 5 excluded
    
    def test_filter_transceivers_list_empty_input(self):
        """Test filtering with empty input"""
        filter_instance = FrequencyPatternFilter()
        
        # Test empty list
        result = filter_instance.filter_transceivers_list([])
        assert result == []
        
        # Test None input
        result = filter_instance.filter_transceivers_list(None)
        assert result is None  # Filter returns None when None is passed
    
    def test_filter_transceivers_list_no_excluded_frequencies(self):
        """Test filtering when no frequencies are configured for exclusion"""
        with patch.dict(os.environ, {
            'EXCLUDED_FREQUENCIES_MHZ': ''
        }):
            filter_instance = FrequencyPatternFilter()
            
            # All transceivers should pass through
            filtered_result = filter_instance.filter_transceivers_list(self.test_transceivers)
            
            assert len(filtered_result) == len(self.test_transceivers)
    
    def test_filter_transceivers_list_edge_cases(self):
        """Test filtering with edge case frequency values"""
        edge_case_transceivers = [
            {'transceiver_id': 2001, 'frequency': 122799999, 'callsign': 'EDGE001'},  # Just below 122.800
            {'transceiver_id': 2002, 'frequency': 122800001, 'callsign': 'EDGE002'},  # Just above 122.800
            {'transceiver_id': 2003, 'frequency': 122800500, 'callsign': 'EDGE003'},  # 122.800500 -> 122.800
            {'transceiver_id': 2004, 'frequency': 122800999, 'callsign': 'EDGE004'},  # 122.800999 -> 122.801
        ]
        
        with patch.dict(os.environ, {
            'EXCLUDED_FREQUENCIES_MHZ': '122.800'
        }):
            filter_instance = FrequencyPatternFilter()
            
            filtered_result = filter_instance.filter_transceivers_list(edge_case_transceivers)
            
            # E1 should be excluded (122.799999 -> 122.800)
            # E2, E3 should be excluded (round to 122.800)
            # E4 should be included (122.800999 -> 122.801, not 122.800)
            assert len(filtered_result) == 1  # Only E4 should pass through
            assert filtered_result[0]['transceiver_id'] == 2004
    
    def test_rolling_window_statistics(self):
        """Test rolling window statistics functionality"""
        filter_instance = FrequencyPatternFilter()
        
        # Process some data
        filter_instance.filter_transceivers_list(self.test_transceivers)
        
        # Check that daily statistics are created
        stats = filter_instance.get_filter_stats()
        assert 'daily_breakdown' in stats
        assert 'window_days' in stats
        assert stats['window_days'] == 7
        
        # Check that we have current day data
        current_date = filter_instance._get_current_date_key()
        assert current_date in stats['daily_breakdown']['processed']
    
    def test_get_filter_stats(self):
        """Test filter statistics retrieval with rolling window"""
        with patch.dict(os.environ, {
            'EXCLUDED_FREQUENCIES_MHZ': '122.800,121.500'
        }):
            filter_instance = FrequencyPatternFilter()
            
            # Process some data
            filter_instance.filter_transceivers_list(self.test_transceivers)
            
            stats = filter_instance.get_filter_stats()
            
            assert stats['enabled'] == True
            assert stats['window_days'] == 7
            assert 'daily_breakdown' in stats
            assert stats['excluded_frequencies_mhz'] == [122.800, 121.500]
    
    def test_get_filter_status(self):
        """Test filter status information retrieval"""
        with patch.dict(os.environ, {
            'EXCLUDED_FREQUENCIES_MHZ': '122.800,121.500'
        }):
            filter_instance = FrequencyPatternFilter()
            
            status = filter_instance.get_filter_status()
            
            assert status['enabled'] == True
            assert status['excluded_frequencies_mhz'] == [122.800, 121.500]
            assert status['window_days'] == 7
            assert 'active_days' in status
    
    def test_filter_with_real_vatsim_frequency_data(self):
        """Test filtering with realistic VATSIM frequency data"""
        # Real VATSIM frequencies from the database
        real_transceivers = [
            {'transceiver_id': 3001, 'frequency': 122800019, 'callsign': 'REAL001'},  # 122.800019 MHz -> 122.800
            {'transceiver_id': 3002, 'frequency': 122800020, 'callsign': 'REAL002'},  # 122.800020 MHz -> 122.800
            {'transceiver_id': 3003, 'frequency': 118100000, 'callsign': 'REAL003'},  # 118.100 MHz
            {'transceiver_id': 3004, 'frequency': 121800000, 'callsign': 'REAL004'},  # 121.800 MHz
            {'transceiver_id': 3005, 'frequency': 125500000, 'callsign': 'REAL005'},  # 125.500 MHz
        ]
        
        with patch.dict(os.environ, {
            'EXCLUDED_FREQUENCIES_MHZ': '122.800'
        }):
            filter_instance = FrequencyPatternFilter()
            
            filtered_result = filter_instance.filter_transceivers_list(real_transceivers)
            
            # R1 and R2 should be excluded (both round to 122.800 MHz)
            # R3, R4, R5 should be included
            assert len(filtered_result) == 3
            assert len(filtered_result) == 3
            
            # Verify specific exclusions
            excluded_ids = [3001, 3002]
            for transceiver in filtered_result:
                assert transceiver['transceiver_id'] not in excluded_ids


@pytest.mark.integration
@pytest.mark.frequency_pattern
class TestFrequencyPatternFilterIntegration:
    """Integration tests for FrequencyPatternFilter"""
    
    def test_filter_integration_with_data_service(self):
        """Test that the filter integrates properly with DataService"""
        from app.services.data_service import DataService
        
        # Mock the VATSIM service to return test data
        with patch('app.services.data_service.VATSIMService') as mock_vatsim_service:
            mock_service = MagicMock()
            mock_vatsim_service.return_value = mock_service
            
            # Mock transceivers data
            mock_transceivers = [
                {'transceiver_id': 4001, 'frequency': 122800000, 'callsign': 'INT001'},  # Excluded
                {'transceiver_id': 4002, 'frequency': 118100000, 'callsign': 'INT002'},  # Included
                {'transceiver_id': 4003, 'frequency': 121800000, 'callsign': 'INT003'},  # Included
            ]
            
            mock_service.get_transceivers.return_value = mock_transceivers
            
            # Create DataService instance
            data_service = DataService()
            
            # Verify filter is initialized
            assert hasattr(data_service, 'frequency_pattern_filter')
            assert data_service.frequency_pattern_filter is not None
            assert data_service.frequency_pattern_filter.config.enabled == True
    
    def test_filter_configuration_environment_integration(self):
        """Test that filter configuration properly reads from environment"""
        # Test with default environment
        with patch.dict(os.environ, {}, clear=True):
            filter_instance = FrequencyPatternFilter()
            assert filter_instance.config.excluded_frequencies_mhz == []
        
        # Test with custom environment
        with patch.dict(os.environ, {
            'EXCLUDED_FREQUENCIES_MHZ': '122.800,121.500,123.450'
        }):
            filter_instance = FrequencyPatternFilter()
            assert filter_instance.config.excluded_frequencies_mhz == [122.800, 121.500, 123.450]
        
        # Test with empty environment
        with patch.dict(os.environ, {
            'EXCLUDED_FREQUENCIES_MHZ': ''
        }):
            filter_instance = FrequencyPatternFilter()
            assert filter_instance.config.excluded_frequencies_mhz == []
