"""
Integration tests for API endpoints.
"""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from app.main import app


class TestAPIEndpoints:
    """Test cases for API endpoints."""

    @pytest.fixture
    def test_client(self):
        """Create a test client for the FastAPI application."""
        return TestClient(app)

    @pytest.fixture
    async def async_client(self):
        """Create an async test client for the FastAPI application."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

    def test_root_endpoint(self, test_client):
        """Test the root endpoint."""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "message" in data

    def test_health_endpoint(self, test_client):
        """Test the health endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data

    def test_status_endpoint(self, test_client):
        """Test the status endpoint."""
        response = test_client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "atc_positions" in data
        assert "active_flights" in data
        assert "data_freshness" in data

    def test_flights_endpoint(self, test_client):
        """Test the flights endpoint."""
        response = test_client.get("/flights")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_flights_with_limit(self, test_client):
        """Test the flights endpoint with limit parameter."""
        response = test_client.get("/flights?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5

    def test_flights_with_offset(self, test_client):
        """Test the flights endpoint with offset parameter."""
        response = test_client.get("/flights?offset=10&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_flight_by_callsign(self, test_client):
        """Test getting a specific flight by callsign."""
        # First get all flights to find a valid callsign
        flights_response = test_client.get("/flights?limit=1")
        if flights_response.status_code == 200:
            flights = flights_response.json()
            if flights:
                callsign = flights[0].get("callsign")
                if callsign:
                    response = test_client.get(f"/flights/{callsign}")
                    assert response.status_code in [200, 404]  # 404 if flight not found

    def test_controllers_endpoint(self, test_client):
        """Test the controllers endpoint."""
        response = test_client.get("/controllers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_controllers_with_limit(self, test_client):
        """Test the controllers endpoint with limit parameter."""
        response = test_client.get("/controllers?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5

    def test_controller_by_callsign(self, test_client):
        """Test getting a specific controller by callsign."""
        # First get all controllers to find a valid callsign
        controllers_response = test_client.get("/controllers?limit=1")
        if controllers_response.status_code == 200:
            controllers = controllers_response.json()
            if controllers:
                callsign = controllers[0].get("callsign")
                if callsign:
                    response = test_client.get(f"/controllers/{callsign}")
                    assert response.status_code in [200, 404]  # 404 if controller not found

    def test_flight_track_endpoint(self, test_client):
        """Test the flight track endpoint."""
        # First get all flights to find a valid callsign
        flights_response = test_client.get("/flights?limit=1")
        if flights_response.status_code == 200:
            flights = flights_response.json()
            if flights:
                callsign = flights[0].get("callsign")
                if callsign:
                    response = test_client.get(f"/flight-track/{callsign}")
                    assert response.status_code in [200, 404]  # 404 if flight not found

    def test_traffic_analysis_endpoint(self, test_client):
        """Test the traffic analysis endpoint."""
        response = test_client.get("/traffic-analysis")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_traffic_summary_endpoint(self, test_client):
        """Test the traffic summary endpoint."""
        response = test_client.get("/traffic-summary")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_monitoring_metrics_endpoint(self, test_client):
        """Test the monitoring metrics endpoint."""
        response = test_client.get("/api/monitoring/metrics")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_monitoring_alerts_endpoint(self, test_client):
        """Test the monitoring alerts endpoint."""
        response = test_client.get("/api/monitoring/alerts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_monitoring_health_endpoint(self, test_client):
        """Test the monitoring health endpoint."""
        response = test_client.get("/api/monitoring/health/vatsim_service")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_performance_metrics_endpoint(self, test_client):
        """Test the performance metrics endpoint."""
        response = test_client.get("/api/performance/metrics/data_ingestion")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_performance_recommendations_endpoint(self, test_client):
        """Test the performance recommendations endpoint."""
        response = test_client.get("/api/performance/recommendations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_performance_alerts_endpoint(self, test_client):
        """Test the performance alerts endpoint."""
        response = test_client.get("/api/performance/alerts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_services_status_endpoint(self, test_client):
        """Test the services status endpoint."""
        response = test_client.get("/api/services/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_service_status_endpoint(self, test_client):
        """Test the specific service status endpoint."""
        response = test_client.get("/api/services/vatsim_service/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_services_health_endpoint(self, test_client):
        """Test the services health endpoint."""
        response = test_client.get("/api/services/health")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_logging_analytics_endpoint(self, test_client):
        """Test the logging analytics endpoint."""
        response = test_client.get("/api/logging/analytics")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_ml_predictions_endpoint(self, test_client):
        """Test the ML predictions endpoint (disabled)."""
        response = test_client.get("/api/ml/predictions")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "disabled"

    def test_ml_anomalies_endpoint(self, test_client):
        """Test the ML anomalies endpoint (disabled)."""
        response = test_client.get("/api/ml/anomalies")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "disabled"

    def test_ml_patterns_endpoint(self, test_client):
        """Test the ML patterns endpoint (disabled)."""
        response = test_client.get("/api/ml/patterns")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "disabled"

    def test_invalid_endpoint(self, test_client):
        """Test invalid endpoint returns 404."""
        response = test_client.get("/invalid-endpoint")
        assert response.status_code == 404

    def test_flights_invalid_limit(self, test_client):
        """Test flights endpoint with invalid limit parameter."""
        response = test_client.get("/flights?limit=invalid")
        assert response.status_code == 422  # Validation error

    def test_flights_invalid_offset(self, test_client):
        """Test flights endpoint with invalid offset parameter."""
        response = test_client.get("/flights?offset=invalid")
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_async_root_endpoint(self, async_client):
        """Test the root endpoint asynchronously."""
        response = await async_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "message" in data

    @pytest.mark.asyncio
    async def test_async_health_endpoint(self, async_client):
        """Test the health endpoint asynchronously."""
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_async_status_endpoint(self, async_client):
        """Test the status endpoint asynchronously."""
        response = await async_client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "atc_positions" in data
        assert "active_flights" in data
        assert "data_freshness" in data

    @pytest.mark.asyncio
    async def test_async_flights_endpoint(self, async_client):
        """Test the flights endpoint asynchronously."""
        response = await async_client.get("/flights")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_async_controllers_endpoint(self, async_client):
        """Test the controllers endpoint asynchronously."""
        response = await async_client.get("/controllers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_async_traffic_analysis_endpoint(self, async_client):
        """Test the traffic analysis endpoint asynchronously."""
        response = await async_client.get("/traffic-analysis")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_async_monitoring_endpoints(self, async_client):
        """Test monitoring endpoints asynchronously."""
        # Test metrics endpoint
        response = await async_client.get("/api/monitoring/metrics")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Test alerts endpoint
        response = await async_client.get("/api/monitoring/alerts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Test health endpoint
        response = await async_client.get("/api/monitoring/health/vatsim_service")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_async_performance_endpoints(self, async_client):
        """Test performance endpoints asynchronously."""
        # Test metrics endpoint
        response = await async_client.get("/api/performance/metrics/data_ingestion")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

        # Test recommendations endpoint
        response = await async_client.get("/api/performance/recommendations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Test alerts endpoint
        response = await async_client.get("/api/performance/alerts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_async_services_endpoints(self, async_client):
        """Test services endpoints asynchronously."""
        # Test services status endpoint
        response = await async_client.get("/api/services/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

        # Test specific service status endpoint
        response = await async_client.get("/api/services/vatsim_service/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

        # Test services health endpoint
        response = await async_client.get("/api/services/health")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_async_ml_endpoints(self, async_client):
        """Test ML endpoints asynchronously (disabled)."""
        # Test predictions endpoint
        response = await async_client.get("/api/ml/predictions")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "disabled"

        # Test anomalies endpoint
        response = await async_client.get("/api/ml/anomalies")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "disabled"

        # Test patterns endpoint
        response = await async_client.get("/api/ml/patterns")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "disabled" 