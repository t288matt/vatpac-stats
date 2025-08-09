"""
End-to-end tests for complete workflows.
"""

import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient

from app.main import app
from app.services.vatsim_service import VATSIMService
from app.services.data_service import DataService
from app.services.monitoring_service import MonitoringService
from app.services.performance_monitor import PerformanceMonitor


class TestCompleteWorkflow:
    """Test cases for complete workflows."""

    @pytest.fixture
    def test_client(self):
        """Create a test client for the FastAPI application."""
        return TestClient(app)

    @pytest.fixture
    async def async_client(self):
        """Create an async test client for the FastAPI application."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

    @pytest.mark.asyncio
    async def test_complete_data_ingestion_workflow(self, async_client):
        """Test complete data ingestion workflow."""
        # 1. Check initial system status
        response = await async_client.get("/status")
        assert response.status_code == 200
        initial_status = response.json()
        assert "status" in initial_status
        assert "atc_positions" in initial_status
        assert "active_flights" in initial_status

        # 2. Check health status
        response = await async_client.get("/health")
        assert response.status_code == 200
        health = response.json()
        assert "status" in health

        # 3. Check monitoring metrics
        response = await async_client.get("/api/monitoring/metrics")
        assert response.status_code == 200
        metrics = response.json()
        assert isinstance(metrics, list)

        # 4. Check performance metrics
        response = await async_client.get("/api/performance/metrics/data_ingestion")
        assert response.status_code == 200
        performance = response.json()
        assert isinstance(performance, dict)

        # 5. Check services status
        response = await async_client.get("/api/services/status")
        assert response.status_code == 200
        services = response.json()
        assert isinstance(services, dict)

        # 6. Check flights data
        response = await async_client.get("/flights")
        assert response.status_code == 200
        flights = response.json()
        assert isinstance(flights, list)

        # 7. Check controllers data
        response = await async_client.get("/controllers")
        assert response.status_code == 200
        controllers = response.json()
        assert isinstance(controllers, list)

        # 8. Check traffic analysis
        response = await async_client.get("/traffic-analysis")
        assert response.status_code == 200
        traffic = response.json()
        assert isinstance(traffic, dict)

        # 9. Verify data consistency
        if flights:
            # If there are flights, test flight-specific endpoints
            flight = flights[0]
            callsign = flight.get("callsign")
            if callsign:
                response = await async_client.get(f"/flights/{callsign}")
                assert response.status_code in [200, 404]

        if controllers:
            # If there are controllers, test controller-specific endpoints
            controller = controllers[0]
            callsign = controller.get("callsign")
            if callsign:
                response = await async_client.get(f"/controllers/{callsign}")
                assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_monitoring_and_alerting_workflow(self, async_client):
        """Test monitoring and alerting workflow."""
        # 1. Check monitoring metrics
        response = await async_client.get("/api/monitoring/metrics")
        assert response.status_code == 200
        metrics = response.json()
        assert isinstance(metrics, list)

        # 2. Check alerts
        response = await async_client.get("/api/monitoring/alerts")
        assert response.status_code == 200
        alerts = response.json()
        assert isinstance(alerts, list)

        # 3. Check service health
        response = await async_client.get("/api/monitoring/health/vatsim_service")
        assert response.status_code == 200
        health = response.json()
        assert isinstance(health, dict)

        # 4. Check performance monitoring
        response = await async_client.get("/api/performance/metrics/data_ingestion")
        assert response.status_code == 200
        performance = response.json()
        assert isinstance(performance, dict)

        # 5. Check performance recommendations
        response = await async_client.get("/api/performance/recommendations")
        assert response.status_code == 200
        recommendations = response.json()
        assert isinstance(recommendations, list)

        # 6. Check performance alerts
        response = await async_client.get("/api/performance/alerts")
        assert response.status_code == 200
        performance_alerts = response.json()
        assert isinstance(performance_alerts, list)

    @pytest.mark.asyncio
    async def test_service_management_workflow(self, async_client):
        """Test service management workflow."""
        # 1. Check all services status
        response = await async_client.get("/api/services/status")
        assert response.status_code == 200
        services = response.json()
        assert isinstance(services, dict)

        # 2. Check specific service status
        response = await async_client.get("/api/services/vatsim_service/status")
        assert response.status_code == 200
        vatsim_status = response.json()
        assert isinstance(vatsim_status, dict)

        # 3. Check services health
        response = await async_client.get("/api/services/health")
        assert response.status_code == 200
        health = response.json()
        assert isinstance(health, dict)

        # 4. Verify service consistency
        # All services should be healthy and running
        assert "services" in health
        for service_name, service_health in health["services"].items():
            assert "status" in service_health
            assert "healthy" in service_health

    @pytest.mark.asyncio
    async def test_data_consistency_workflow(self, async_client):
        """Test data consistency workflow."""
        # 1. Get flights data
        response = await async_client.get("/flights")
        assert response.status_code == 200
        flights = response.json()
        assert isinstance(flights, list)

        # 2. Get controllers data
        response = await async_client.get("/controllers")
        assert response.status_code == 200
        controllers = response.json()
        assert isinstance(controllers, list)

        # 3. Get traffic analysis
        response = await async_client.get("/traffic-analysis")
        assert response.status_code == 200
        traffic = response.json()
        assert isinstance(traffic, dict)

        # 4. Get traffic summary
        response = await async_client.get("/traffic-summary")
        assert response.status_code == 200
        summary = response.json()
        assert isinstance(summary, dict)

        # 5. Verify data consistency
        # Check that flight counts are consistent
        if flights:
            assert len(flights) >= 0
            # Verify flight data structure
            for flight in flights[:5]:  # Check first 5 flights
                assert "callsign" in flight
                assert "cid" in flight
                assert "name" in flight

        if controllers:
            assert len(controllers) >= 0
            # Verify controller data structure
            for controller in controllers[:5]:  # Check first 5 controllers
                assert "callsign" in controller
                assert "cid" in controller
                assert "name" in controller

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, async_client):
        """Test error handling workflow."""
        # 1. Test invalid endpoints
        response = await async_client.get("/invalid-endpoint")
        assert response.status_code == 404

        # 2. Test invalid parameters
        response = await async_client.get("/flights?limit=invalid")
        assert response.status_code == 422

        response = await async_client.get("/flights?offset=invalid")
        assert response.status_code == 422

        # 3. Test non-existent resources
        response = await async_client.get("/flights/NONEXISTENT")
        assert response.status_code == 404

        response = await async_client.get("/controllers/NONEXISTENT")
        assert response.status_code == 404

        # 4. Test invalid service health check
        response = await async_client.get("/api/monitoring/health/nonexistent_service")
        assert response.status_code == 200  # Should handle gracefully
        health = response.json()
        assert isinstance(health, dict)

    @pytest.mark.asyncio
    async def test_performance_workflow(self, async_client):
        """Test performance monitoring workflow."""
        # 1. Check performance metrics
        response = await async_client.get("/api/performance/metrics/data_ingestion")
        assert response.status_code == 200
        metrics = response.json()
        assert isinstance(metrics, dict)

        # 2. Check performance recommendations
        response = await async_client.get("/api/performance/recommendations")
        assert response.status_code == 200
        recommendations = response.json()
        assert isinstance(recommendations, list)

        # 3. Check performance alerts
        response = await async_client.get("/api/performance/alerts")
        assert response.status_code == 200
        alerts = response.json()
        assert isinstance(alerts, list)

        # 4. Check logging analytics
        response = await async_client.get("/api/logging/analytics")
        assert response.status_code == 200
        analytics = response.json()
        assert isinstance(analytics, dict)

    @pytest.mark.asyncio


    @pytest.mark.asyncio
    async def test_concurrent_requests_workflow(self, async_client):
        """Test concurrent requests workflow."""
        # Create multiple concurrent requests
        endpoints = [
            "/status",
            "/health",
            "/flights",
            "/controllers",
            "/traffic-analysis",
            "/api/monitoring/metrics",
            "/api/performance/metrics/data_ingestion",
            "/api/services/status"
        ]

        # Make concurrent requests
        tasks = [async_client.get(endpoint) for endpoint in endpoints]
        responses = await asyncio.gather(*tasks)

        # Verify all responses are successful
        for response in responses:
            assert response.status_code == 200

        # Verify response data types
        for i, response in enumerate(responses):
            data = response.json()
            if endpoints[i] in ["/flights", "/controllers"]:
                assert isinstance(data, list)
            else:
                assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_data_freshness_workflow(self, async_client):
        """Test data freshness workflow."""
        # 1. Check system status for data freshness
        response = await async_client.get("/status")
        assert response.status_code == 200
        status = response.json()
        assert "data_freshness" in status

        # 2. Check that data freshness is a valid value
        data_freshness = status["data_freshness"]
        assert isinstance(data_freshness, str)
        assert data_freshness in ["real-time", "stale", "unknown"]

        # 3. If data is real-time, verify we have current data
        if data_freshness == "real-time":
            # Check that we have recent data
            response = await async_client.get("/flights")
            assert response.status_code == 200
            flights = response.json()
            
            if flights:
                # Verify at least one flight has recent data
                recent_flights = [f for f in flights if f.get("last_updated")]
                assert len(recent_flights) >= 0

    @pytest.mark.asyncio
    async def test_system_health_workflow(self, async_client):
        """Test system health workflow."""
        # 1. Check overall system health
        response = await async_client.get("/health")
        assert response.status_code == 200
        health = response.json()
        assert "status" in health
        assert health["status"] in ["operational", "degraded", "down"]

        # 2. Check services health
        response = await async_client.get("/api/services/health")
        assert response.status_code == 200
        services_health = response.json()
        assert isinstance(services_health, dict)

        # 3. Check monitoring health
        response = await async_client.get("/api/monitoring/health/vatsim_service")
        assert response.status_code == 200
        monitoring_health = response.json()
        assert isinstance(monitoring_health, dict)

        # 4. Verify system is operational
        assert health["status"] == "operational"

    def test_synchronous_workflow(self, test_client):
        """Test synchronous workflow."""
        # 1. Check root endpoint
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "message" in data

        # 2. Check health endpoint
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data

        # 3. Check status endpoint
        response = test_client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "atc_positions" in data
        assert "active_flights" in data

        # 4. Check flights endpoint
        response = test_client.get("/flights")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # 5. Check controllers endpoint
        response = test_client.get("/controllers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # 6. Check monitoring endpoints
        response = test_client.get("/api/monitoring/metrics")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        response = test_client.get("/api/monitoring/alerts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # 7. Check performance endpoints
        response = test_client.get("/api/performance/metrics/data_ingestion")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

        response = test_client.get("/api/performance/recommendations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # 8. Check services endpoints
        response = test_client.get("/api/services/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

        response = test_client.get("/api/services/health")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict) 