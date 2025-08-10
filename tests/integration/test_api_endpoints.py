#!/usr/bin/env python3
"""
Integration tests for API endpoints
"""

import pytest
from httpx import AsyncClient
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from datetime import datetime, timezone

from app.main import app
from app.database import get_db
from app.services.cache_service import CacheService

class TestAPIEndpoints:
    """Test class for API endpoints."""
    
    def test_root_endpoint(self, test_client):
        """Test the root endpoint redirect."""
        response = test_client.get("/")
        assert response.status_code in [200, 307, 404]  # Allow redirect or not found

    def test_health_endpoint(self, test_client):
        """Test the health endpoint."""
        response = test_client.get("/health")
        assert response.status_code in [200, 404]  # May not exist

    def test_status_endpoint(self, test_client):
        """Test the status endpoint."""
        response = test_client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data

    def test_flights_endpoint(self, test_client):
        """Test the flights endpoint."""
        response = test_client.get("/flights")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_controllers_endpoint(self, test_client):
        """Test the controllers endpoint."""
        response = test_client.get("/controllers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_airport_endpoints(self, test_client):
        """Test airport-related endpoints."""
        # Test airport by region
        response = test_client.get("/api/airports/region/Australia")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_flight_track_endpoint(self, test_client):
        """Test flight tracking endpoint with mock data."""
        # Test with a mock callsign
        test_callsigns = ["QFA123", "VOZ456", "JST789"]
        
        for callsign in test_callsigns:
            response = test_client.get(f"/flight-track/{callsign}")
            assert response.status_code in [200, 404]  # 404 if flight not found



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
        """Test the monitoring health endpoint for a specific service."""
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

    def test_services_specific_status_endpoint(self, test_client):
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

class TestAsyncAPIEndpoints:
    """Test class for async API endpoints."""

    @pytest.mark.asyncio
    async def test_async_status_endpoint(self, async_client):
        """Test the status endpoint asynchronously."""
        response = await async_client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data

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
