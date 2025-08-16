#!/usr/bin/env python3
"""
Unit tests for cleanup functionality in DataService.

This module tests the cleanup methods that handle stale sector entries.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.data_service import DataService


@pytest.fixture
def data_service():
    """Create a DataService instance for testing."""
    service = DataService()
    # Mock the logger to avoid logging during tests
    service.logger = MagicMock()
    # Mock the sector loader
    service.sector_loader = MagicMock()
    service.sector_tracking_enabled = True
    return service

@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session

@pytest.fixture
def sample_stale_sectors():
    """Sample stale sector data for testing."""
    return [
        MagicMock(
            callsign="TEST001",
            sector_name="BRISBANE",
            entry_timestamp=datetime.now(timezone.utc) - timedelta(minutes=10),
            entry_lat=-27.4698,
            entry_lon=153.0251,
            entry_altitude=30000,
            last_lat=-27.4698,
            last_lon=153.0251,
            last_alt=30000
        ),
        MagicMock(
            callsign="TEST002", 
            sector_name="SYDNEY",
            entry_timestamp=datetime.now(timezone.utc) - timedelta(minutes=15),
            entry_lat=-33.8688,
            entry_lon=151.2093,
            entry_altitude=25000,
            last_lat=-33.8688,
            last_lon=151.2093,
            last_alt=25000
        )
    ]


class TestCleanupFunctionality:
    """Test cases for cleanup functionality."""
    
    @pytest.mark.asyncio
    async def test_cleanup_stale_sectors_success(self, data_service, mock_session, sample_stale_sectors):
        """Test successful cleanup of stale sectors."""
        # Mock the helper methods
        data_service._close_stale_sectors = AsyncMock(return_value=2)
        data_service._cleanup_memory_state_for_closed_sectors = AsyncMock(return_value=2)
        
        # Mock get_database_session context manager
        with patch('app.services.data_service.get_database_session', return_value=mock_session):
            result = await data_service.cleanup_stale_sectors()
        
        # Verify the result
        assert result["status"] == "success"
        assert result["sectors_closed"] == 2
        assert result["memory_states_cleaned"] == 2
        assert "cleanup_time_seconds" in result
        assert "timestamp" in result
        
        # Verify method calls
        data_service._close_stale_sectors.assert_called_once()
        data_service._cleanup_memory_state_for_closed_sectors.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_stale_sectors_no_stale_sectors(self, data_service, mock_session):
        """Test cleanup when no stale sectors are found."""
        # Mock no stale sectors found
        data_service._close_stale_sectors = AsyncMock(return_value=0)
        data_service._cleanup_memory_state_for_closed_sectors = AsyncMock(return_value=0)
        
        with patch('app.services.data_service.get_database_session', return_value=mock_session):
            result = await data_service.cleanup_stale_sectors()
        
        # Verify result
        assert result["status"] == "success"
        assert result["sectors_closed"] == 0
        assert result["memory_states_cleaned"] == 0
        
        # Verify helper methods were called
        data_service._close_stale_sectors.assert_called_once()
        data_service._cleanup_memory_state_for_closed_sectors.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_stale_sectors_with_custom_timeout(self, data_service, mock_session, sample_stale_sectors):
        """Test cleanup with custom timeout from environment variable."""
        # Mock environment variable
        with patch.dict('os.environ', {'CLEANUP_FLIGHT_TIMEOUT': '600'}):
            data_service._close_stale_sectors = AsyncMock(return_value=1)
            data_service._cleanup_memory_state_for_closed_sectors = AsyncMock(return_value=1)
            
            with patch('app.services.data_service.get_database_session', return_value=mock_session):
                result = await data_service.cleanup_stale_sectors()
        
        # Verify result
        assert result["status"] == "success"
        data_service._close_stale_sectors.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_stale_sectors_exception_handling(self, data_service, mock_session):
        """Test cleanup handles exceptions gracefully."""
        # Mock an exception in _close_stale_sectors
        data_service._close_stale_sectors = AsyncMock(side_effect=Exception("Database error"))
        
        with patch('app.services.data_service.get_database_session', return_value=mock_session):
            with pytest.raises(Exception, match="Database error"):
                await data_service.cleanup_stale_sectors()
    
    @pytest.mark.asyncio
    async def test_close_stale_sectors(self, data_service, mock_session, sample_stale_sectors):
        """Test closing stale sectors in the database."""
        # Mock database result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = sample_stale_sectors
        mock_session.execute.return_value = mock_result
        
        result = await data_service._close_stale_sectors(mock_session, 300)
        
        # Verify result
        assert result == 2
        
        # Verify database calls
        assert mock_session.execute.call_count == 3  # 1 select + 2 updates
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_stale_sectors_database_error(self, data_service, mock_session):
        """Test handling database errors when closing stale sectors."""
        # Mock database error
        mock_session.execute.side_effect = Exception("Update failed")
        
        with pytest.raises(Exception, match="Update failed"):
            await data_service._close_stale_sectors(mock_session, 300)
    
    @pytest.mark.asyncio
    async def test_close_stale_sectors_empty_list(self, data_service, mock_session):
        """Test closing stale sectors when none are found."""
        # Mock empty result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        
        result = await data_service._close_stale_sectors(mock_session, 300)
        
        # Verify result
        assert result == 0
        
        # Verify no database updates
        mock_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cleanup_memory_state_for_closed_sectors(self, data_service, mock_session):
        """Test cleaning up memory state for closed sectors."""
        # Mock database result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["TEST001", "TEST002"]
        mock_session.execute.return_value = mock_result
        
        # Set up flight sector states
        data_service.flight_sector_states = {
            "TEST001": {"current_sector": "BRISBANE"},
            "TEST002": {"current_sector": "SYDNEY"},
            "TEST003": {"current_sector": "MELBOURNE"}  # This one should remain
        }
        
        result = await data_service._cleanup_memory_state_for_closed_sectors(mock_session)
        
        # Verify result
        assert result == 2
        
        # Verify memory state was cleaned
        assert "TEST001" not in data_service.flight_sector_states
        assert "TEST002" not in data_service.flight_sector_states
        assert "TEST003" in data_service.flight_sector_states  # Should remain
    
    @pytest.mark.asyncio
    async def test_cleanup_memory_state_no_flight_sector_states(self, data_service, mock_session):
        """Test cleaning memory state when no flight sector states exist."""
        # Mock database result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["TEST001"]
        mock_session.execute.return_value = mock_result
        
        # No flight sector states
        data_service.flight_sector_states = {}
        
        result = await data_service._cleanup_memory_state_for_closed_sectors(mock_session)
        
        # Verify result
        assert result == 0
        
        # Verify no changes
        assert data_service.flight_sector_states == {}
    
    @pytest.mark.asyncio
    async def test_cleanup_memory_state_exception_handling(self, data_service, mock_session):
        """Test handling exceptions when cleaning memory state."""
        # Mock database error
        mock_session.execute.side_effect = Exception("Query failed")
        
        result = await data_service._cleanup_memory_state_for_closed_sectors(mock_session)
        
        # Verify error handling
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_integration_workflow(self, data_service, mock_session, sample_stale_sectors):
        """Test the complete cleanup workflow integration."""
        # Mock all helper methods
        data_service._close_stale_sectors = AsyncMock(return_value=2)
        data_service._cleanup_memory_state_for_closed_sectors = AsyncMock(return_value=2)
        
        # Mock get_database_session context manager
        with patch('app.services.data_service.get_database_session', return_value=mock_session):
            result = await data_service.cleanup_stale_sectors()
        
        # Verify complete workflow
        assert result["status"] == "success"
        assert result["sectors_closed"] == 2
        assert result["memory_states_cleaned"] == 2
        assert "cleanup_time_seconds" in result
        assert "timestamp" in result
        
        # Verify all methods were called in sequence
        data_service._close_stale_sectors.assert_called_once()
        data_service._cleanup_memory_state_for_closed_sectors.assert_called_once()
