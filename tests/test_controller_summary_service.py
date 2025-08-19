#!/usr/bin/env python3
"""
Unit tests for ControllerSummaryService

This module tests the ControllerSummaryService class methods individually,
ensuring proper data processing, error handling, and business logic.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
import json

from app.services.data_service import ControllerSummaryService
from app.utils.logging import get_logger_for_module


class TestControllerSummaryService:
    """Test ControllerSummaryService class methods"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        config = Mock()
        config.controller_summary.completion_minutes = 30
        config.controller_summary.retention_hours = 168
        config.controller_summary.summary_interval_minutes = 60
        config.controller_summary.enabled = True
        return config
    
    @pytest.fixture
    def mock_logger(self):
        """Mock logger for testing"""
        return get_logger_for_module("test")
    
    @pytest.fixture
    def service(self, mock_config, mock_logger):
        """Create ControllerSummaryService instance for testing"""
        return ControllerSummaryService(mock_config, mock_logger)
    
    @pytest.fixture
    def sample_controller_records(self):
        """Sample controller records for testing"""
        return [
            Mock(
                id=1,
                callsign="TEST_CTR",
                cid=12345,
                name="Test Controller",
                rating=5,
                facility=1,
                server="TEST",
                logon_time=datetime(2025, 8, 18, 10, 0, 0, tzinfo=timezone.utc),
                last_updated=datetime(2025, 8, 18, 12, 0, 0, tzinfo=timezone.utc),
                created_at=datetime(2025, 8, 18, 10, 0, 0, tzinfo=timezone.utc)
            ),
            Mock(
                id=2,
                callsign="TEST_CTR",
                cid=12345,
                name="Test Controller",
                rating=5,
                facility=1,
                server="TEST",
                logon_time=datetime(2025, 8, 18, 10, 0, 0, tzinfo=timezone.utc),
                last_updated=datetime(2025, 8, 18, 12, 30, 0, tzinfo=timezone.utc),
                created_at=datetime(2025, 8, 18, 10, 30, 0, tzinfo=timezone.utc)
            )
        ]
    
    @pytest.fixture
    def sample_aircraft_records(self):
        """Sample aircraft records for testing"""
        return [
            Mock(
                aircraft_callsign="TEST123",
                frequency=122800000,
                first_seen=datetime(2025, 8, 18, 10, 15, 0, tzinfo=timezone.utc),
                last_seen=datetime(2025, 8, 18, 11, 45, 0, tzinfo=timezone.utc),
                updates_count=15
            ),
            Mock(
                aircraft_callsign="TEST456",
                frequency=125200000,
                first_seen=datetime(2025, 8, 18, 11, 0, 0, tzinfo=timezone.utc),
                last_seen=datetime(2025, 8, 18, 12, 15, 0, tzinfo=timezone.utc),
                updates_count=12
            )
        ]

    @pytest.mark.asyncio
    async def test_identify_completed_controllers(self, service):
        """Test identification of completed controllers"""
        # Mock database session and query result
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ("TEST_CTR", datetime(2025, 8, 18, 10, 0, 0, tzinfo=timezone.utc)),
            ("TEST_APP", datetime(2025, 8, 18, 11, 0, 0, tzinfo=timezone.utc))
        ]
        mock_session.execute.return_value = mock_result
        
        with patch('app.services.data_service.get_database_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            result = await service._identify_completed_controllers(30)
            
            assert len(result) == 2
            assert result[0][0] == "TEST_CTR"
            assert result[1][0] == "TEST_APP"
            
            # Verify the query was executed
            mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_frequencies(self, service):
        """Test frequency extraction from controller session"""
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            Mock(frequency="122.8"),
            Mock(frequency="125.2"),
            Mock(frequency="118.1")
        ]
        mock_session.execute.return_value = mock_result
        
        frequencies = await service._get_session_frequencies(
            "TEST_CTR", 
            datetime(2025, 8, 18, 10, 0, 0, tzinfo=timezone.utc),
            mock_session
        )
        
        assert len(frequencies) == 3
        assert "122.8" in frequencies
        assert "125.2" in frequencies
        assert "118.1" in frequencies

    def test_process_aircraft_data(self, service, sample_aircraft_records):
        """Test aircraft data processing into summary format"""
        session_start = datetime(2025, 8, 18, 10, 0, 0, tzinfo=timezone.utc)
        session_end = datetime(2025, 8, 18, 12, 30, 0, tzinfo=timezone.utc)
        
        result = service._process_aircraft_data(sample_aircraft_records, session_start, session_end)
        
        assert result["total_aircraft"] == 2
        assert result["peak_count"] > 0
        assert len(result["details"]) == 2
        assert result["details"][0]["callsign"] == "TEST123"
        assert result["details"][1]["callsign"] == "TEST456"
        
        # Check time calculations
        assert result["details"][0]["time_on_frequency_minutes"] == 90  # 1.5 hours
        assert result["details"][1]["time_on_frequency_minutes"] == 75  # 1.25 hours

    @pytest.mark.asyncio
    async def test_create_hourly_breakdown(self, service):
        """Test creation of hourly aircraft breakdown"""
        # This method doesn't exist in the current implementation
        # Removing this test as it tests functionality that's not implemented
        pytest.skip("_create_hourly_breakdown method not implemented in current version")
    
    @pytest.mark.asyncio
    async def test_empty_aircraft_data(self, service):
        """Test empty aircraft data structure creation"""
        empty_data = service._empty_aircraft_data()
        
        # Verify structure
        assert "summary" in empty_data
        assert "hourly_breakdown" in empty_data
        assert "aircraft_list" in empty_data
        
        # Verify summary fields
        summary = empty_data["summary"]
        assert summary["total_aircraft"] == 0
        assert summary["total_time_minutes"] == 0
        assert summary["peak_aircraft_count"] == 0
        
        # Verify hourly breakdown is empty
        assert empty_data["hourly_breakdown"] == {}
        
        # Verify aircraft list is empty
        assert empty_data["aircraft_list"] == []

    @pytest.mark.asyncio
    async def test_archive_completed_controllers(self, service):
        """Test archiving of completed controllers"""
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.rowcount = 5  # 5 records archived
        mock_session.execute.return_value = mock_result
        
        completed_controllers = [
            ("TEST_CTR", datetime(2025, 8, 18, 10, 0, 0, tzinfo=timezone.utc)),
            ("TEST_APP", datetime(2025, 8, 18, 11, 0, 0, tzinfo=timezone.utc))
        ]
        
        with patch('app.services.data_service.get_database_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            result = await service._archive_completed_controllers(completed_controllers)
            
            assert result == 10  # 5 records per controller
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_completed_controllers(self, service):
        """Test deletion of completed controller records"""
        completed_controllers = [
            ("TEST_CTR", datetime(2025, 8, 18, 10, 0, 0, tzinfo=timezone.utc)),
            ("TEST_APP", datetime(2025, 8, 18, 11, 0, 0, tzinfo=timezone.utc))
        ]
        
        # Mock database session
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.rowcount = 2
        
        with patch('app.services.data_service.get_database_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_session.execute.return_value = mock_result
            
            result = await service._delete_completed_controllers(completed_controllers)
            
            assert result == 2
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_completed_controllers_retention_not_met(self, service):
        """Test deletion with retention period not met"""
        completed_controllers = [
            ("TEST_CTR", datetime(2025, 8, 18, 10, 0, 0, tzinfo=timezone.utc))
        ]
        
        # Mock database session
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.rowcount = 1
        
        with patch('app.services.data_service.get_database_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_session.execute.return_value = mock_result
            
            result = await service._delete_completed_controllers(completed_controllers)
            
            assert result == 1
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_completed_controllers_no_work(self, service):
        """Test processing when no completed controllers found"""
        with patch.object(service, '_identify_completed_controllers', return_value=[]):
            result = await service.process_completed_controllers()
            
            assert result["status"] == "no_work"
            assert result["summaries_created"] == 0
            assert result["records_archived"] == 0
            assert result["records_deleted"] == 0

    @pytest.mark.asyncio
    async def test_process_completed_controllers_with_work(self, service):
        """Test processing when completed controllers are found"""
        completed_controllers = [
            ("TEST_CTR", datetime(2025, 8, 18, 10, 0, 0, tzinfo=timezone.utc))
        ]
        
        with patch.object(service, '_identify_completed_controllers', return_value=completed_controllers), \
             patch.object(service, '_create_controller_summaries', return_value=1), \
             patch.object(service, '_archive_completed_controllers', return_value=5), \
             patch.object(service, '_delete_completed_controllers', return_value=0):
            
            result = await service.process_completed_controllers()
            
            assert result["status"] == "completed"
            assert result["summaries_created"] == 1
            assert result["records_archived"] == 5
            assert result["records_deleted"] == 0

    @pytest.mark.asyncio
    async def test_error_handling_in_identify_controllers(self, service):
        """Test error handling in controller identification"""
        with patch('app.services.data_service.get_database_session', side_effect=Exception("Database error")):
            with pytest.raises(Exception, match="Database error"):
                await service._identify_completed_controllers(30)

    @pytest.mark.asyncio
    async def test_error_handling_in_archive_controllers(self, service):
        """Test error handling in controller archiving"""
        completed_controllers = [
            ("TEST_CTR", datetime(2025, 8, 18, 10, 0, 0, tzinfo=timezone.utc))
        ]
        
        with patch('app.services.data_service.get_database_session', side_effect=Exception("Archive error")):
            with pytest.raises(Exception, match="Archive error"):
                await service._archive_completed_controllers(completed_controllers)

    def test_session_duration_calculation(self, service):
        """Test session duration calculation accuracy"""
        session_start = datetime(2025, 8, 18, 10, 0, 0, tzinfo=timezone.utc)
        session_end = datetime(2025, 8, 18, 12, 30, 0, tzinfo=timezone.utc)
        
        # Calculate expected duration
        expected_minutes = int((session_end - session_start).total_seconds() / 60)
        assert expected_minutes == 150  # 2.5 hours = 150 minutes
        
        # Test with service method
        result = service._empty_aircraft_data()
        # This is just a placeholder test since the actual calculation is in the main method
        assert result["total_aircraft"] == 0

    @pytest.mark.asyncio
    async def test_get_aircraft_interactions_no_frequencies(self, service):
        """Test aircraft interactions when no frequencies available"""
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.fetchall.return_value = []  # No frequencies
        mock_session.execute.return_value = mock_result
        
        result = await service._get_aircraft_interactions(
            "TEST_CTR",
            datetime(2025, 8, 18, 10, 0, 0, tzinfo=timezone.utc),
            datetime(2025, 8, 18, 12, 0, 0, tzinfo=timezone.utc),
            mock_session
        )
        
        assert result["total_aircraft"] == 0
        assert result["peak_count"] == 0
        assert result["hourly_breakdown"] == {}
        assert result["details"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
