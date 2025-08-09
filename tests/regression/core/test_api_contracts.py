"""
API Contract Regression Tests

These tests validate that all API endpoints maintain their expected contracts
and response structures. They ensure that API changes don't break client
expectations and catch regressions in endpoint behavior.

Contract Elements Tested:
- Response status codes
- Response data structure and types
- Required fields presence
- Error response formats
- HTTP headers and content types
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from typing import Dict, Any, List

from app.main import app


@pytest.mark.regression
@pytest.mark.core
class TestAPIEndpointContracts:
    """Test API endpoints maintain expected contracts"""
    
    def test_status_endpoint_contract(self, test_client: TestClient):
        """
        Test GET /api/status endpoint contract
        
        Expected Response:
        {
            "status": str,
            "atc_positions": int,
            "active_flights": int,
            "data_freshness": str,
            "timestamp": str,
            "database": {...},
            "services": {...}
        }
        """
        response = test_client.get("/api/status")
        
        # Basic response validation
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        
        # Required fields
        required_fields = [
            "status", "atc_positions", "active_flights", 
            "data_freshness", "timestamp"
        ]
        
        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from /api/status response"
        
        # Field type validation
        assert isinstance(data["status"], str), "status should be string"
        assert isinstance(data["atc_positions"], int), "atc_positions should be integer"
        assert isinstance(data["active_flights"], int), "active_flights should be integer"
        assert isinstance(data["data_freshness"], str), "data_freshness should be string"
        assert isinstance(data["timestamp"], str), "timestamp should be string"
        
        # Value validation
        assert data["status"] in ["operational", "degraded", "down"], f"Invalid status value: {data['status']}"
        assert data["data_freshness"] in ["real-time", "stale", "unknown"], f"Invalid data_freshness: {data['data_freshness']}"
        assert data["atc_positions"] >= 0, "atc_positions should be non-negative"
        assert data["active_flights"] >= 0, "active_flights should be non-negative"
    
    def test_flights_endpoint_contract(self, test_client: TestClient):
        """
        Test GET /api/flights endpoint contract
        
        Expected Response: List of flight objects with specific structure
        """
        response = test_client.get("/api/flights")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        assert isinstance(data, list), "Flights endpoint should return a list"
        
        # If there are flights, validate structure
        if data:
            flight = data[0]
            
            # Required flight fields
            required_flight_fields = [
                "callsign", "cid", "name", "latitude", "longitude",
                "altitude", "groundspeed", "heading", "last_updated"
            ]
            
            for field in required_flight_fields:
                assert field in flight, f"Required flight field '{field}' missing"
            
            # Type validation for key fields
            assert isinstance(flight["callsign"], str), "callsign should be string"
            assert isinstance(flight["cid"], int), "cid should be integer"
            assert isinstance(flight["name"], str), "name should be string"
            
            # Coordinate validation (can be None)
            if flight["latitude"] is not None:
                assert isinstance(flight["latitude"], (int, float)), "latitude should be number or None"
                assert -90 <= flight["latitude"] <= 90, "latitude should be valid range"
            
            if flight["longitude"] is not None:
                assert isinstance(flight["longitude"], (int, float)), "longitude should be number or None"
                assert -180 <= flight["longitude"] <= 180, "longitude should be valid range"
    
    def test_controllers_endpoint_contract(self, test_client: TestClient):
        """
        Test GET /api/atc-positions endpoint contract
        
        Expected Response: List of controller objects
        """
        response = test_client.get("/api/atc-positions")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        assert isinstance(data, list), "Controllers endpoint should return a list"
        
        # If there are controllers, validate structure
        if data:
            controller = data[0]
            
            required_controller_fields = [
                "callsign", "controller_id", "controller_name", 
                "frequency", "facility", "controller_rating"
            ]
            
            for field in required_controller_fields:
                assert field in controller, f"Required controller field '{field}' missing"
            
            # Type validation
            assert isinstance(controller["callsign"], str), "callsign should be string"
            assert isinstance(controller["controller_id"], int), "controller_id should be integer"
            assert isinstance(controller["controller_name"], str), "controller_name should be string"
            assert isinstance(controller["frequency"], str), "frequency should be string"
            assert isinstance(controller["controller_rating"], int), "controller_rating should be integer"
    
    def test_flight_track_endpoint_contract(self, test_client: TestClient):
        """
        Test GET /api/flights/{callsign}/track endpoint contract
        """
        # First get a valid callsign
        flights_response = test_client.get("/api/flights")
        flights = flights_response.json()
        
        if not flights:
            pytest.skip("No flights available to test track endpoint")
        
        callsign = flights[0]["callsign"]
        response = test_client.get(f"/api/flights/{callsign}/track")
        
        # Should return 200 or 404
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list), "Flight track should return a list"
            
            if data:
                track_point = data[0]
                
                required_track_fields = [
                    "latitude", "longitude", "altitude", 
                    "groundspeed", "heading", "last_updated"
                ]
                
                for field in required_track_fields:
                    assert field in track_point, f"Required track field '{field}' missing"
    
    def test_flight_stats_endpoint_contract(self, test_client: TestClient):
        """
        Test GET /api/flights/{callsign}/stats endpoint contract
        """
        flights_response = test_client.get("/api/flights")
        flights = flights_response.json()
        
        if not flights:
            pytest.skip("No flights available to test stats endpoint")
        
        callsign = flights[0]["callsign"]
        response = test_client.get(f"/api/flights/{callsign}/stats")
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict), "Flight stats should return an object"
            
            expected_stats_fields = [
                "callsign", "total_positions", "flight_duration",
                "max_altitude", "average_speed"
            ]
            
            for field in expected_stats_fields:
                assert field in data, f"Required stats field '{field}' missing"
    
    def test_database_status_endpoint_contract(self, test_client: TestClient):
        """
        Test GET /api/database/status endpoint contract
        """
        response = test_client.get("/api/database/status")
        
        assert response.status_code == 200
        data = response.json()
        
        required_db_fields = [
            "status", "connection_pool", "migration_status"
        ]
        
        for field in required_db_fields:
            assert field in data, f"Required database field '{field}' missing"
        
        assert data["status"] in ["healthy", "degraded", "down"]
    
    def test_network_status_endpoint_contract(self, test_client: TestClient):
        """
        Test GET /api/network/status endpoint contract
        """
        response = test_client.get("/api/network/status")
        
        assert response.status_code == 200
        data = response.json()
        
        required_network_fields = [
            "vatsim_api_status", "last_update", "data_freshness"
        ]
        
        for field in required_network_fields:
            assert field in data, f"Required network field '{field}' missing"


@pytest.mark.regression
@pytest.mark.core
class TestAPIErrorResponseContracts:
    """Test API error responses maintain consistent structure"""
    
    def test_404_error_response_contract(self, test_client: TestClient):
        """
        Test 404 error responses have consistent structure
        """
        response = test_client.get("/api/flights/NONEXISTENT")
        
        assert response.status_code == 404
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        
        # Standard error response structure
        required_error_fields = ["detail"]
        
        for field in required_error_fields:
            assert field in data, f"Required error field '{field}' missing from 404 response"
        
        assert isinstance(data["detail"], str), "Error detail should be string"
    
    def test_422_validation_error_contract(self, test_client: TestClient):
        """
        Test 422 validation error responses have consistent structure
        """
        # Send invalid query parameters
        response = test_client.get("/api/flights?limit=invalid")
        
        assert response.status_code == 422
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        
        # FastAPI validation error structure
        assert "detail" in data, "Validation error should have 'detail' field"
        assert isinstance(data["detail"], list), "Validation error detail should be list"
        
        if data["detail"]:
            error_item = data["detail"][0]
            required_validation_fields = ["loc", "msg", "type"]
            
            for field in required_validation_fields:
                assert field in error_item, f"Validation error item missing '{field}'"
    
    def test_500_error_response_contract(self, test_client: TestClient):
        """
        Test 500 error responses are handled gracefully
        
        Note: This test simulates server errors to ensure
        they return proper error structure
        """
        # This endpoint might not exist or might cause an error
        # The test is to ensure any 500 errors have proper structure
        
        # For now, we'll test that if a 500 occurs, it has proper structure
        # In a real scenario, you might mock an internal service failure
        
        # This is a placeholder - in practice you'd mock a service to fail
        # and then test the error response structure
        pass


@pytest.mark.regression
@pytest.mark.core
class TestAPIParameterContracts:
    """Test API parameters work as expected"""
    
    def test_flights_pagination_contract(self, test_client: TestClient):
        """
        Test flights endpoint pagination parameters
        """
        # Test limit parameter
        response = test_client.get("/api/flights?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5, "Limit parameter should restrict results"
        
        # Test offset parameter
        response = test_client.get("/api/flights?offset=0&limit=10")
        assert response.status_code == 200
        
        # Test invalid parameters
        response = test_client.get("/api/flights?limit=-1")
        assert response.status_code == 422, "Negative limit should return validation error"
        
        response = test_client.get("/api/flights?offset=-1")
        assert response.status_code == 422, "Negative offset should return validation error"
    
    def test_filter_parameter_contracts(self, test_client: TestClient):
        """
        Test filter parameters work correctly
        """
        # Test region filter if it exists
        response = test_client.get("/api/flights?region=australia")
        assert response.status_code in [200, 422], "Region filter should work or return validation error"
        
        # Test aircraft type filter if it exists
        response = test_client.get("/api/flights?aircraft_type=B738")
        assert response.status_code in [200, 422], "Aircraft type filter should work or return validation error"


@pytest.mark.regression
@pytest.mark.core
@pytest.mark.asyncio
class TestAsyncAPIContracts:
    """Test async API endpoints maintain contracts"""
    
    async def test_async_status_endpoint(self, async_client: AsyncClient):
        """
        Test status endpoint via async client
        """
        response = await async_client.get("/api/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Same contract as sync version
        required_fields = ["status", "atc_positions", "active_flights", "data_freshness"]
        
        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from async /api/status"
    
    async def test_concurrent_api_requests(self, async_client: AsyncClient):
        """
        Test API handles concurrent requests correctly
        """
        import asyncio
        
        # Make multiple concurrent requests
        endpoints = [
            "/api/status",
            "/api/flights", 
            "/api/atc-positions",
            "/api/database/status",
            "/api/network/status"
        ]
        
        # Execute all requests concurrently
        tasks = [async_client.get(endpoint) for endpoint in endpoints]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All requests should succeed (or at least not crash)
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                pytest.fail(f"Concurrent request to {endpoints[i]} failed: {response}")
            
            assert response.status_code == 200, f"Endpoint {endpoints[i]} returned {response.status_code}"
            
            # Basic response validation
            data = response.json()
            assert data is not None, f"Endpoint {endpoints[i]} returned null data"


@pytest.mark.regression
@pytest.mark.core
class TestAPIPerformanceContracts:
    """Test API performance requirements"""
    
    def test_api_response_times(self, test_client: TestClient, performance_thresholds):
        """
        Test API endpoints meet response time requirements
        """
        import time
        
        endpoints_with_limits = {
            "/api/status": performance_thresholds["api_endpoint_max_response_time"],
            "/api/flights": performance_thresholds["api_endpoint_max_response_time"],
            "/api/atc-positions": performance_thresholds["api_endpoint_max_response_time"],
            "/api/database/status": performance_thresholds["api_endpoint_max_response_time"],
        }
        
        for endpoint, max_time in endpoints_with_limits.items():
            start_time = time.time()
            
            response = test_client.get(endpoint)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            assert response.status_code == 200, f"Endpoint {endpoint} failed"
            assert response_time < max_time, f"Endpoint {endpoint} took {response_time:.3f}s, should be < {max_time}s"
    
    def test_large_response_handling(self, test_client: TestClient):
        """
        Test API handles large responses correctly
        """
        # Request large number of flights
        response = test_client.get("/api/flights?limit=1000")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle large responses without issues
        assert isinstance(data, list)
        
        # Response should not be truncated unexpectedly
        # (Actual limit depends on implementation)
        assert len(data) <= 1000, "Response should respect limit parameter"
