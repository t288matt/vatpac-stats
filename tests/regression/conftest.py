"""
Regression Test Configuration and Fixtures

This module provides pytest configuration and fixtures specifically for
regression testing. It includes mock services, test data, and database
setup for comprehensive regression validation.
"""

import asyncio
import pytest
from typing import Dict, Any, Generator, AsyncGenerator
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import application components
from app.main import app
from app.database import SessionLocal, get_db
from app.models import Flight, Controller, Sector, Transceiver, VatsimStatus
from app.services.vatsim_service import VATSIMService
from app.services.data_service import DataService
from app.services.cache_service import CacheService


# ===== EVENT LOOP CONFIGURATION =====

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ===== TEST CLIENT FIXTURES =====

@pytest.fixture
def test_client() -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI application."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# ===== MOCK VATSIM API =====

class VATSIMAPIMock:
    """Mock VATSIM API for controlled testing"""
    
    def __init__(self):
        self.responses = {}
        self.error_conditions = {}
        self.call_count = 0
    
    def set_response(self, endpoint: str, response_data: Dict[str, Any]):
        """Set mock response for specific endpoint"""
        self.responses[endpoint] = response_data
    
    def set_error_condition(self, endpoint: str, error_type: str):
        """Set error condition for endpoint (timeout, http_500, malformed_json, etc.)"""
        self.error_conditions[endpoint] = error_type
    
    def get_response(self, endpoint: str) -> Dict[str, Any]:
        """Get mock response for endpoint"""
        self.call_count += 1
        
        if endpoint in self.error_conditions:
            error_type = self.error_conditions[endpoint]
            if error_type == "timeout":
                raise asyncio.TimeoutError("Mock API timeout")
            elif error_type == "http_500":
                raise Exception("Mock HTTP 500 error")
            elif error_type == "malformed_json":
                raise ValueError("Mock malformed JSON")
        
        return self.responses.get(endpoint, {})
    
    def reset(self):
        """Reset mock state"""
        self.responses.clear()
        self.error_conditions.clear()
        self.call_count = 0


@pytest.fixture
def vatsim_api_mock() -> VATSIMAPIMock:
    """VATSIM API mock for controlled testing"""
    return VATSIMAPIMock()


# ===== GOLDEN TEST DATA =====

@pytest.fixture
def golden_vatsim_data() -> Dict[str, Any]:
    """Golden dataset with known expected outcomes for regression testing"""
    return {
        "general": {
            "version": 8,
            "reload": 1,
            "update": "2024-01-01T12:00:00Z",
            "update_timestamp": "2024-01-01T12:00:00Z",
            "connected_clients": 150,
            "unique_users": 120
        },
        "pilots": [
            # Test Case 1: Australian flight (should pass all filters)
            {
                "cid": 123456,
                "name": "Test Pilot 1",
                "callsign": "QFA123",
                "server": "TEST",
                "pilot_rating": 1,
                "military_rating": 0,
                "latitude": -33.8688,     # Sydney coordinates - INSIDE Australian airspace
                "longitude": 151.2093,
                "altitude": 35000,
                "groundspeed": 450,
                "transponder": "1200",
                "heading": 90,
                "qnh_i_hg": 29.92,
                "qnh_mb": 1013,
                "flight_plan": {
                    "flight_rules": "I",
                    "aircraft_faa": "B738",
                    "aircraft_short": "B738",
                    "departure": "YSSY",     # Australian airport (Y-code)
                    "arrival": "YBBN",      # Australian airport (Y-code)
                    "alternate": "YSCB",
                    "cruise_tas": "450",
                    "planned_altitude": "35000",
                    "deptime": "1200",
                    "enroute_time": "01:30",
                    "fuel_time": "02:30",
                    "remarks": "Test flight for regression testing",
                    "route": "DCT YBBN",
                    "revision_id": 1,
                    "assigned_transponder": "1200"
                },
                "logon_time": "2024-01-01T11:00:00Z",
                "last_updated": "2024-01-01T12:00:00Z"
            },
            # Test Case 2: Non-Australian flight (should be filtered out)
            {
                "cid": 789012,
                "name": "Test Pilot 2",
                "callsign": "UAL456",
                "server": "TEST",
                "pilot_rating": 2,
                "military_rating": 0,
                "latitude": 51.5074,      # London coordinates - OUTSIDE Australian airspace
                "longitude": -0.1278,
                "altitude": 37000,
                "groundspeed": 480,
                "transponder": "2000",
                "heading": 270,
                "qnh_i_hg": 30.12,
                "qnh_mb": 1020,
                "flight_plan": {
                    "flight_rules": "I",
                    "aircraft_faa": "B777",
                    "aircraft_short": "B77W",
                    "departure": "EGLL",     # Non-Australian airport
                    "arrival": "KLAX",      # Non-Australian airport
                    "alternate": "KORD",
                    "cruise_tas": "480",
                    "planned_altitude": "37000",
                    "deptime": "1400",
                    "enroute_time": "11:30",
                    "fuel_time": "13:00",
                    "remarks": "Non-Australian flight for testing",
                    "route": "DCT KLAX"
                },
                "logon_time": "2024-01-01T10:30:00Z",
                "last_updated": "2024-01-01T12:00:00Z"
            },
            # Test Case 3: Edge case - missing coordinates but Australian airports
            {
                "cid": 345678,
                "name": "Test Pilot 3",
                "callsign": "QFA789",
                "server": "TEST",
                "pilot_rating": 1,
                "military_rating": 0,
                "latitude": None,          # Missing coordinates - should use conservative approach
                "longitude": None,
                "altitude": 0,
                "groundspeed": 0,
                "transponder": "1000",
                "heading": 0,
                "flight_plan": {
                    "flight_rules": "I",
                    "aircraft_short": "A320",
                    "departure": "YSSY",     # Australian airport
                    "arrival": "YMML",      # Australian airport
                    "cruise_tas": "420",
                    "planned_altitude": "33000"
                },
                "logon_time": "2024-01-01T11:30:00Z",
                "last_updated": "2024-01-01T12:00:00Z"
            }
        ],
        "controllers": [
            # Test Case: String ID conversion and data mapping
            {
                "cid": "345678",          # String from API (should convert to int)
                "name": "Test Controller",
                "callsign": "SY_APP",
                "frequency": "124.400",
                "facility": 4,
                "rating": "3",            # String from API (should convert to int)
                "server": "TEST",
                "visual_range": 100,
                "text_atis": "Test ATIS for regression testing",
                "logon_time": "2024-01-01T10:00:00Z",
                "last_updated": "2024-01-01T12:00:00Z"
            }
        ],
        "atis": [],
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
            {"id": 1, "short": "FSS", "long": "Flight Service Station"},
            {"id": 4, "short": "APP", "long": "Approach Control"}
        ],
        "ratings": [
            {"id": 1, "short": "OBS", "long": "Observer"},
            {"id": 3, "short": "S1", "long": "Student 1"}
        ],
        "pilot_ratings": [
            {"id": 1, "short": "PPL", "long": "Private Pilot License"},
            {"id": 2, "short": "ATPL", "long": "Airline Transport Pilot License"}
        ],
        "military_ratings": [
            {"id": 0, "short": "NONE", "long": "No Military Rating"}
        ]
    }


@pytest.fixture
def expected_database_state() -> Dict[str, Any]:
    """Expected database state after processing golden dataset"""
    return {
        "flights": [
            # Only Australian flights should be present
            {
                "callsign": "QFA123",
                "cid": 123456,
                "name": "Test Pilot 1",
                "departure": "YSSY",
                "arrival": "YBBN",
                "latitude": -33.8688,
                "longitude": 151.2093,
                "aircraft_short": "B738"
            },
            {
                "callsign": "QFA789", 
                "cid": 345678,
                "name": "Test Pilot 3",
                "departure": "YSSY",
                "arrival": "YMML",
                "latitude": None,  # Missing coordinates allowed through (conservative)
                "longitude": None,
                "aircraft_short": "A320"
            }
            # UAL456 should NOT be present (filtered out)
        ],
        "controllers": [
            {
                "callsign": "SY_APP",
                "controller_id": 345678,    # Converted from string to int
                "controller_name": "Test Controller",
                "controller_rating": 3,     # Converted from string to int
                "frequency": "124.400",
                "visual_range": 100,
                "text_atis": "Test ATIS for regression testing"
            }
        ],
        "vatsim_status": [
            {
                "api_version": 8,
                "reload": 1,
                "connected_clients": 150,
                "unique_users": 120
            }
        ]
    }


# ===== DATABASE FIXTURES =====

@pytest.fixture
def db_session() -> Generator[SessionLocal, None, None]:
    """Provide database session for testing (will use test database when implemented)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def clean_database(db_session):
    """Clean database state for testing (placeholder for future test database implementation)"""
    # TODO: Implement when test database approach is ready
    # For now, this is a placeholder that doesn't actually clean
    # When test database is implemented, this will truncate all tables
    pass


# ===== SERVICE MOCKS =====

@pytest.fixture
def mock_vatsim_service(vatsim_api_mock, golden_vatsim_data) -> Mock:
    """Mock VATSIM service with controlled responses"""
    mock_service = Mock(spec=VATSIMService)
    
    # Set up golden data response by default
    vatsim_api_mock.set_response("/v3/vatsim-data.json", golden_vatsim_data)
    
    # Mock service methods
    mock_service.get_current_data = AsyncMock()
    mock_service.initialize = AsyncMock()
    mock_service.is_healthy = Mock(return_value=True)
    mock_service.get_service_info = Mock(return_value={"status": "healthy"})
    
    return mock_service


@pytest.fixture
def mock_data_service() -> Mock:
    """Mock data service for testing"""
    mock_service = Mock(spec=DataService)
    mock_service.initialize = AsyncMock()
    mock_service.start_data_ingestion = AsyncMock()
    mock_service.stop_data_ingestion = AsyncMock()
    mock_service._process_data_in_memory = AsyncMock()
    mock_service._flush_memory_to_disk = AsyncMock()
    mock_service.is_healthy = Mock(return_value=True)
    mock_service.get_service_info = Mock(return_value={"status": "healthy"})
    
    return mock_service


@pytest.fixture
def mock_cache_service() -> Mock:
    """Mock cache service for testing"""
    mock_service = Mock(spec=CacheService)
    mock_service.get = AsyncMock(return_value=None)
    mock_service.set = AsyncMock()
    mock_service.delete = AsyncMock()
    mock_service.clear = AsyncMock()
    mock_service.is_healthy = Mock(return_value=True)
    mock_service.get_service_info = Mock(return_value={"status": "healthy"})
    
    return mock_service


# ===== FILTER TEST DATA =====

@pytest.fixture
def airport_filter_test_cases() -> list:
    """Test cases for airport filter validation"""
    return [
        # Format: (departure, arrival, expected_result, description)
        ("YSSY", "YBBN", True, "Both Australian airports"),
        ("YSSY", "KLAX", True, "Australian origin, non-Australian destination"),
        ("KLAX", "YSSY", True, "Non-Australian origin, Australian destination"),
        ("EGLL", "KLAX", False, "Neither airport is Australian"),
        ("YSSY", None, True, "Australian origin, missing destination"),
        (None, "YSSY", True, "Missing origin, Australian destination"),
        ("YSSY", "", True, "Australian origin, empty destination"),
        ("", "YSSY", True, "Empty origin, Australian destination"),
        (None, None, False, "Both missing"),
        ("", "", False, "Both empty"),
        ("YSSY", "EGLL", True, "Australian origin overrides non-Australian destination")
    ]


@pytest.fixture
def geographic_filter_test_cases() -> list:
    """Test cases for geographic filter validation"""
    return [
        # Format: (latitude, longitude, expected_result, description)
        (-33.8688, 151.2093, True, "Sydney - inside Australian airspace"),
        (-37.8136, 144.9631, True, "Melbourne - inside Australian airspace"),
        (-34.9285, 138.6007, True, "Adelaide - inside Australian airspace"),
        (-31.9505, 115.8605, True, "Perth - inside Australian airspace"),
        (51.5074, -0.1278, False, "London - outside Australian airspace"),
        (40.7128, -74.0060, False, "New York - outside Australian airspace"),
        (35.6762, 139.6503, False, "Tokyo - outside Australian airspace"),
        (None, None, True, "Missing coordinates - conservative approach"),
        (None, 151.2093, True, "Missing latitude - conservative approach"),
        (-33.8688, None, True, "Missing longitude - conservative approach"),
        (999.0, 999.0, False, "Invalid coordinates - outside valid range")
    ]


# ===== PERFORMANCE TEST CONFIGURATION =====

@pytest.fixture
def performance_thresholds() -> Dict[str, float]:
    """Performance thresholds for regression testing"""
    return {
        "api_endpoint_max_response_time": 1.0,      # 1 second max for API endpoints
        "filter_pipeline_max_time": 0.1,            # 100ms max for filter pipeline
        "database_query_max_time": 0.5,             # 500ms max for database queries
        "large_dataset_max_time": 30.0,             # 30 seconds max for 1000 flights
        "memory_usage_max_mb": 512,                 # 512MB max memory usage
    }


# ===== UTILITY FUNCTIONS =====

def assert_flight_data_matches(actual_flight: Flight, expected_data: Dict[str, Any]):
    """Utility function to assert flight data matches expected values"""
    assert actual_flight.callsign == expected_data["callsign"]
    assert actual_flight.cid == expected_data["cid"]
    assert actual_flight.name == expected_data["name"]
    assert actual_flight.departure == expected_data["departure"]
    assert actual_flight.arrival == expected_data["arrival"]
    
    # Handle None values for coordinates
    if expected_data["latitude"] is not None:
        assert abs(actual_flight.latitude - expected_data["latitude"]) < 0.0001
    else:
        assert actual_flight.latitude is None
        
    if expected_data["longitude"] is not None:
        assert abs(actual_flight.longitude - expected_data["longitude"]) < 0.0001
    else:
        assert actual_flight.longitude is None


def assert_controller_data_matches(actual_controller: Controller, expected_data: Dict[str, Any]):
    """Utility function to assert controller data matches expected values"""
    assert actual_controller.callsign == expected_data["callsign"]
    assert actual_controller.controller_id == expected_data["controller_id"]
    assert actual_controller.controller_name == expected_data["controller_name"]
    assert actual_controller.controller_rating == expected_data["controller_rating"]
    assert actual_controller.frequency == expected_data["frequency"]
    assert actual_controller.visual_range == expected_data["visual_range"]
    assert actual_controller.text_atis == expected_data["text_atis"]
