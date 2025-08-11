"""
Pytest configuration and fixtures for VATSIM Data Collection System tests.
"""

import asyncio
import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import Mock, AsyncMock

from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app

from app.services.vatsim_service import VATSIMService
from app.services.data_service import DataService
from app.services.database_service import DatabaseService
from app.services.resource_manager import ResourceManager
from app.filters.geographic_boundary_filter import GeographicBoundaryFilter
from app.utils.geographic_utils import load_polygon_from_geojson
from app.database import get_database_session
from app.models import Flight, Controller, Transceiver


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_client() -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI application."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_vatsim_data() -> Dict[str, Any]:
    """Mock VATSIM data for testing."""
    return {
        "general": {
            "version": 8,
            "reload": 1,
            "update": "2024-01-01T12:00:00Z",
            "update_timestamp": "2024-01-01T12:00:00Z",
            "connected_clients": 1000,
            "unique_users": 500
        },
        "pilots": [
            {
                "cid": 123456,
                "name": "Test Pilot",
                "callsign": "TEST123",
                "server": "TEST",
                "pilot_rating": 1,
                "military_rating": 0,
                "latitude": -33.8688,
                "longitude": 151.2093,
                "altitude": 3000,
                "groundspeed": 250,
                "transponder": "1200",
                "heading": 90,
                "qnh_i_hg": 29.92,
                "qnh_mb": 1013,
                "flight_plan": {
                    "flight_rules": "I",
                    "type": "B738",
                    "departure": "YSBK",
                    "arrival": "YSSY",
                    "alternate": "YSCB",
                    "cruise_tas": "450",
                    "altitude": "FL350",
                    "deptime": "1200",
                    "enroute_time": "01:30",
                    "fuel_time": "02:30",
                    "remarks": "Test flight",
                    "route": "DCT YSSY"
                },
                "logon_time": "2024-01-01T11:00:00Z",
                "last_updated": "2024-01-01T12:00:00Z"
            }
        ],
        "controllers": [
            {
                "cid": 789012,
                "name": "Test Controller",
                "callsign": "TEST_CTR",
                "frequency": "118.100",
                "facility": 4,
                "rating": 3,
                "server": "TEST",
                "visual_range": 300,
                "text_atis": "Test ATIS",
                "last_updated": "2024-01-01T12:00:00Z",
                "logon_time": "2024-01-01T11:00:00Z"
            }
        ],
        "atc": [
            {
                "cid": 789012,
                "name": "Test Controller",
                "callsign": "TEST_CTR",
                "frequency": "118.100",
                "facility": 4,
                "rating": 3,
                "server": "TEST",
                "visual_range": 300,
                "text_atis": "Test ATIS",
                "last_updated": "2024-01-01T12:00:00Z",
                "logon_time": "2024-01-01T11:00:00Z"
            }
        ],
        "servers": [
            {
                "ident": "TEST",
                "hostname_or_ip": "test.vatsim.net",
                "location": "Test Location",
                "name": "Test Server",
                "clients_connection_allowed": True,
                "client_connections_allowed": True,
                "is_sweatbox": False
            }
        ],
        "prefiles": [],
        "facilities": [
            {
                "id": 1,
                "short": "FSS",
                "long": "Flight Service Station"
            }
        ],
        "ratings": [
            {
                "id": 1,
                "short": "OBS",
                "long": "Observer"
            }
        ],
        "pilot_ratings": [
            {
                "id": 1,
                "short": "PPL",
                "long": "Private Pilot License"
            }
        ],
        "military_ratings": [
            {
                "id": 0,
                "short": "NONE",
                "long": "No Military Rating"
            }
        ]
    }


@pytest.fixture
def mock_flight_data() -> Dict[str, Any]:
    """Mock flight data for testing."""
    return {
        "callsign": "TEST123",
        "cid": 123456,
        "name": "Test Pilot",
        "latitude": -33.8688,
        "longitude": 151.2093,
        "altitude": 3000,
        "groundspeed": 250,
        "heading": 90,
        "transponder": "1200",
        "flight_plan": {
            "departure": "YSBK",
            "arrival": "YSSY",
            "type": "B738",
            "route": "DCT YSSY"
        },
        "last_updated": "2024-01-01T12:00:00Z"
    }


@pytest.fixture
def mock_controller_data() -> Dict[str, Any]:
    """Mock controller data for testing."""
    return {
        "callsign": "TEST_CTR",
        "cid": 789012,
        "name": "Test Controller",
        "frequency": "118.100",
        "facility": 4,
        "rating": 3,
        "visual_range": 300,
        "text_atis": "Test ATIS",
        "last_updated": "2024-01-01T12:00:00Z"
    }


@pytest.fixture
def mock_vatsim_service() -> Mock:
    """Mock VATSIM service for testing."""
    mock_service = Mock(spec=VATSIMService)
    mock_service.get_current_data = AsyncMock()
    mock_service.is_healthy = Mock(return_value=True)
    mock_service.get_service_info = Mock(return_value={"status": "healthy"})
    return mock_service


@pytest.fixture
def mock_data_service() -> Mock:
    """Mock data service for testing."""
    mock_service = Mock(spec=DataService)
    mock_service.start_data_ingestion = AsyncMock()
    mock_service.stop_data_ingestion = AsyncMock()
    mock_service.is_healthy = Mock(return_value=True)
    mock_service.get_service_info = Mock(return_value={"status": "healthy"})
    return mock_service


@pytest.fixture
def mock_database_service() -> Mock:
    """Mock database service for testing."""
    mock_service = Mock(spec=DatabaseService)
    mock_service.store_flights = AsyncMock()
    mock_service.store_controllers = AsyncMock()
    mock_service.get_flight_track = AsyncMock(return_value=[])
    mock_service.is_healthy = Mock(return_value=True)
    mock_service.get_service_info = Mock(return_value={"status": "healthy"})
    return mock_service


@pytest.fixture
def mock_resource_manager() -> Mock:
    """Mock resource manager for testing."""
    mock_service = Mock(spec=ResourceManager)
    mock_service.get_resource_usage = Mock(return_value={})
    mock_service.allocate_resources = Mock()
    mock_service.release_resources = Mock()
    mock_service.is_healthy = Mock(return_value=True)
    mock_service.get_service_info = Mock(return_value={"status": "healthy"})
    return mock_service


 