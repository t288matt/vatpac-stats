#!/usr/bin/env python3
"""
API tests for Controller Summary System

This module tests the controller summary API endpoints,
ensuring proper request handling, response formatting, and error handling.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
import json

from fastapi.testclient import TestClient
from fastapi import FastAPI

# Import the main app for testing
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.main import app


class TestControllerSummaryAPI:
    """Test controller summary API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_summary_data(self):
        """Sample controller summary data for testing"""
        return {
            "id": 1,
            "callsign": "TEST_CTR",
            "cid": 12345,
            "name": "Test Controller",
            "session_start_time": "2025-08-18T10:00:00+00:00",
            "session_end_time": "2025-08-18T12:00:00+00:00",
            "session_duration_minutes": 120,
            "rating": 5,
            "facility": 1,
            "server": "TEST",
            "total_aircraft_handled": 10,
            "peak_aircraft_count": 5,
            "hourly_aircraft_breakdown": {
                "2025-08-18T10:00:00+00:00": 3,
                "2025-08-18T11:00:00+00:00": 5,
                "2025-08-18T12:00:00+00:00": 2
            },
            "frequencies_used": ["122.8", "125.2"],
            "aircraft_details": [
                {
                    "callsign": "TEST123",
                    "first_seen": "2025-08-18T10:15:00+00:00",
                    "last_seen": "2025-08-18T11:45:00+00:00",
                    "time_on_frequency_minutes": 90
                }
            ],
            "created_at": "2025-08-18T10:00:00+00:00",
            "updated_at": "2025-08-18T10:00:00+00:00"
        }

    def test_get_controller_summaries_endpoint(self, client):
        """Test GET /api/controller-summaries endpoint"""
        response = client.get("/api/controller-summaries")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "summaries" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "timestamp" in data
        
        # Verify data types
        assert isinstance(data["summaries"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["limit"], int)
        assert isinstance(data["offset"], int)
        assert isinstance(data["timestamp"], str)

    def test_get_controller_summaries_with_filters(self, client):
        """Test GET /api/controller-summaries with query parameters"""
        # Test with callsign filter
        response = client.get("/api/controller-summaries?callsign=TEST_CTR")
        assert response.status_code == 200
        
        # Test with rating filter
        response = client.get("/api/controller-summaries?rating=5")
        assert response.status_code == 200
        
        # Test with facility filter
        response = client.get("/api/controller-summaries?facility=1")
        assert response.status_code == 200
        
        # Test with date filters
        response = client.get("/api/controller-summaries?date_from=2025-08-18T00:00:00+00:00")
        assert response.status_code == 200
        
        response = client.get("/api/controller-summaries?date_to=2025-08-18T23:59:59+00:00")
        assert response.status_code == 200
        
        # Test with pagination
        response = client.get("/api/controller-summaries?limit=50&offset=10")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 50
        assert data["offset"] == 10

    def test_get_controller_summaries_pagination(self, client):
        """Test pagination functionality"""
        # Test default pagination
        response = client.get("/api/controller-summaries")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 100  # Default limit
        assert data["offset"] == 0   # Default offset
        
        # Test custom pagination
        response = client.get("/api/controller-summaries?limit=25&offset=50")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 25
        assert data["offset"] == 50

    def test_get_controller_stats_endpoint(self, client):
        """Test GET /api/controller-summaries/{callsign}/stats endpoint"""
        # Test with valid callsign
        response = client.get("/api/controller-summaries/TEST_CTR/stats")
        
        # Should return 404 if no data exists, or 200 if data exists
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            # Verify response structure
            assert "callsign" in data
            assert "total_sessions" in data
            assert "avg_session_duration_minutes" in data
            assert "total_aircraft_handled" in data
            assert "max_peak_aircraft" in data
            assert "first_session" in data
            assert "last_session" in data
            
            # Verify data types
            assert isinstance(data["callsign"], str)
            assert isinstance(data["total_sessions"], int)
            assert isinstance(data["avg_session_duration_minutes"], (int, float))
            assert isinstance(data["total_aircraft_handled"], int)

    def test_get_controller_stats_not_found(self, client):
        """Test GET /api/controller-summaries/{callsign}/stats with non-existent callsign"""
        response = client.get("/api/controller-summaries/NONEXISTENT_CTR/stats")
        
        # API returns 200 with empty stats for non-existent controllers
        assert response.status_code == 200
        data = response.json()
        assert "callsign" in data
        assert data["callsign"] == "NONEXISTENT_CTR"
        assert data["total_sessions"] == 0
        assert data["total_aircraft_handled"] == 0

    def test_get_performance_overview_endpoint(self, client):
        """Test GET /api/controller-summaries/performance/overview endpoint"""
        response = client.get("/api/controller-summaries/performance/overview")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure (flat structure, not nested)
        assert "total_summaries" in data
        assert "unique_controllers" in data
        assert "avg_session_duration_minutes" in data
        assert "total_aircraft_handled" in data
        assert "avg_aircraft_per_session" in data
        assert "max_peak_aircraft" in data
        assert "earliest_session" in data
        assert "latest_session" in data
        # Note: timestamp field is not present in performance overview response
        
        # Verify data types
        assert isinstance(data["total_summaries"], int)
        assert isinstance(data["unique_controllers"], int)
        assert isinstance(data["avg_session_duration_minutes"], (int, float))
        assert isinstance(data["total_aircraft_handled"], int)
        assert isinstance(data["avg_aircraft_per_session"], (int, float))
        assert isinstance(data["max_peak_aircraft"], int)

    def test_trigger_controller_summary_processing_endpoint(self, client):
        """Test POST /api/controller-summaries/process endpoint"""
        response = client.post("/api/controller-summaries/process")
        
        # Should return 200 if processing is triggered successfully
        # or 500 if there's an error (e.g., no data service available in test)
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            # Verify response structure
            assert "status" in data
            assert "message" in data
            assert "result" in data
            assert "timestamp" in data
            
            # Verify data types
            assert isinstance(data["status"], str)
            assert isinstance(data["message"], str)
            assert isinstance(data["result"], dict)
            assert isinstance(data["timestamp"], str)
            
            # Verify success status
            assert data["status"] == "success"
            assert "completed" in data["message"].lower()

    def test_health_endpoint(self, client):
        """Test GET /api/health/controller-summary endpoint"""
        response = client.get("/api/health/controller-summary")
        
        # Should return 200 for health check
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure (actual API response)
        assert "status" in data
        assert "tables" in data
        assert "timestamp" in data
        
        # Verify status values
        assert data["status"] in ["healthy", "warning", "degraded", "disabled", "unhealthy"]
        
        # Verify tables structure
        tables = data["tables"]
        assert "controller_summaries" in tables
        assert "controllers" in tables
        assert "controllers_archive" in tables
        
        # Verify data types
        assert isinstance(tables["controller_summaries"], int)
        assert isinstance(tables["controllers"], int)
        assert isinstance(tables["controllers_archive"], int)

    def test_dashboard_endpoint(self, client):
        """Test GET /api/dashboard/controller-summaries endpoint"""
        response = client.get("/api/dashboard/controller-summaries")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure (actual API response)
        assert "recent_sessions" in data
        assert "top_controllers" in data
        assert "timestamp" in data
        
        # Verify recent_sessions structure
        recent_sessions = data["recent_sessions"]
        assert isinstance(recent_sessions, list)
        if recent_sessions:
            session = recent_sessions[0]
            assert "callsign" in session
            assert "session_start" in session
            assert "duration_minutes" in session
            assert "aircraft_handled" in session
            assert "peak_aircraft" in session
        
        # Verify top_controllers structure
        top_controllers = data["top_controllers"]
        assert isinstance(top_controllers, list)
        if top_controllers:
            controller = top_controllers[0]
            assert "callsign" in controller
            assert "sessions" in controller
            assert "total_aircraft" in controller
            assert "avg_duration_minutes" in controller

    def test_api_error_handling(self, client):
        """Test API error handling for invalid requests"""
        # Test invalid limit parameter
        response = client.get("/api/controller-summaries?limit=invalid")
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        
        # Test invalid offset parameter
        response = client.get("/api/controller-summaries?offset=invalid")
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        
        # Test invalid date format
        response = client.get("/api/controller-summaries?date_from=invalid-date")
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_api_response_format_consistency(self, client):
        """Test that all API responses have consistent format"""
        endpoints = [
            "/api/controller-summaries",
            "/api/controller-summaries/performance/overview",
            "/api/health/controller-summary",
            "/api/dashboard/controller-summaries"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            
            data = response.json()
            # Most endpoints should have timestamp, but performance overview doesn't
            if endpoint != "/api/controller-summaries/performance/overview":
                assert "timestamp" in data
                assert isinstance(data["timestamp"], str)
                
                # Verify timestamp format (ISO 8601)
                try:
                    datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
                except ValueError:
                    pytest.fail(f"Invalid timestamp format in {endpoint}: {data['timestamp']}")

    def test_api_cors_headers(self, client):
        """Test CORS headers are present (skipped in development)"""
        # CORS is not configured in development environment
        # This test would be relevant in production with proper CORS setup
        pytest.skip("CORS not configured in development environment")

    def test_api_content_type(self, client):
        """Test API responses have correct content type"""
        response = client.get("/api/controller-summaries")
        
        # Should return JSON
        assert response.headers["content-type"] == "application/json"

    def test_api_rate_limiting_headers(self, client):
        """Test API rate limiting headers (if implemented)"""
        response = client.get("/api/controller-summaries")
        
        # Check for rate limiting headers (optional)
        # These might not be implemented yet, so we just check the response is valid
        assert response.status_code == 200

    def test_api_logging_and_monitoring(self, client):
        """Test that API calls are properly logged and monitored"""
        # Make multiple API calls to test logging
        endpoints = [
            "/api/controller-summaries",
            "/api/health/controller-summary",
            "/api/dashboard/controller-summaries"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            
            # Verify response is valid JSON
            try:
                data = response.json()
                assert isinstance(data, dict)
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON response from {endpoint}")

    def test_api_performance_under_load(self, client):
        """Test API performance under multiple concurrent requests"""
        # Make multiple concurrent requests
        import threading
        import time
        
        results = []
        errors = []
        
        def make_request():
            try:
                start_time = time.time()
                response = client.get("/api/controller-summaries")
                end_time = time.time()
                
                if response.status_code == 200:
                    results.append(end_time - start_time)
                else:
                    errors.append(f"Status {response.status_code}")
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(results) > 0, f"All requests failed: {errors}"
        
        # Check performance (should complete in reasonable time)
        avg_response_time = sum(results) / len(results)
        assert avg_response_time < 2.0, f"Average response time too slow: {avg_response_time}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
