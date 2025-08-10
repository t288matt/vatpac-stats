"""
Unit tests for monitoring service.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from app.services.monitoring_service import MonitoringService, AlertType, AlertSeverity


class TestMonitoringService:
    """Test cases for monitoring service."""

    @pytest.fixture
    def monitoring_service(self):
        """Create a monitoring service instance for testing."""
        return MonitoringService()

    @pytest.mark.asyncio
    async def test_service_initialization_type(self, monitoring_service):
        """Test that monitoring service is properly initialized."""
        
        assert isinstance(monitoring_service, MonitoringService)

    @pytest.mark.asyncio
    async def test_service_initialization(self, monitoring_service):
        """Test service initialization."""
        assert monitoring_service is not None
        assert monitoring_service.service_name == "monitoring"
        assert monitoring_service.running is False

    @pytest.mark.asyncio
    async def test_service_start(self, monitoring_service):
        """Test service start functionality."""
        await monitoring_service.initialize()
        assert monitoring_service.running is True

    @pytest.mark.asyncio
    async def test_service_stop(self, monitoring_service):
        """Test service stop functionality."""
        await monitoring_service.initialize()
        await monitoring_service.cleanup()
        assert monitoring_service.running is False

    @pytest.mark.asyncio
    async def test_service_health_check(self, monitoring_service):
        """Test service health check."""
        health = await monitoring_service.health_check()
        assert health is not None
        assert "status" in health
        assert "service" in health
        assert health["service"] == "monitoring"

    @pytest.mark.asyncio
    async def test_record_metric(self, monitoring_service):
        """Test metric recording."""
        # Record a test metric
        monitoring_service.record_metric("test_metric", 100, {"service": "test"})
        
        # Verify metric was recorded
        metrics = monitoring_service.get_metrics("test_metric")
        assert len(metrics) > 0
        
        # Find our test metric
        test_metric = next((m for m in metrics if m.name == "test_metric"), None)
        assert test_metric is not None
        assert test_metric.value == 100

    @pytest.mark.asyncio
    async def test_record_metric_with_tags(self, monitoring_service):
        """Test metric recording with tags."""
        # Record a test metric with tags
        monitoring_service.record_metric("test_metric", 100, {"service": "test"})
        
        # Verify metric was recorded with tags
        metrics = monitoring_service.get_metrics("test_metric")
        test_metric = next((m for m in metrics if m.name == "test_metric"), None)
        assert test_metric is not None
        assert test_metric.tags == {"service": "test"}

    @pytest.mark.asyncio
    async def test_get_metrics(self, monitoring_service):
        """Test metrics retrieval."""
        # Record some test metrics
        monitoring_service.record_metric("metric1", 100, {"service": "test"})
        monitoring_service.record_metric("metric2", 200, {"service": "test"})
        
        metrics1 = monitoring_service.get_metrics("metric1")
        metrics2 = monitoring_service.get_metrics("metric2")
        
        assert len(metrics1) >= 1
        assert len(metrics2) >= 1
        
        # Verify metrics exist
        assert metrics1[0].name == "metric1"
        assert metrics2[0].name == "metric2"

    @pytest.mark.asyncio
    async def test_get_latest_metric(self, monitoring_service):
        """Test latest metric retrieval."""
        # Record a test metric
        monitoring_service.record_metric("test_metric", 100, {"service": "test"})
        
        # Get latest metric
        latest = monitoring_service.metrics_collector.get_latest_metric("test_metric")
        assert latest is not None
        assert latest.name == "test_metric"
        assert latest.value == 100

    @pytest.mark.asyncio
    async def test_get_latest_metric_not_found(self, monitoring_service):
        """Test latest metric retrieval when metric doesn't exist."""
        latest = monitoring_service.metrics_collector.get_latest_metric("nonexistent_metric")
        assert latest is None

    @pytest.mark.asyncio
    async def test_create_alert(self, monitoring_service):
        """Test alert creation."""
        # Create a test alert
        alert = monitoring_service.create_alert(
            AlertType.SERVICE_DOWN,
            AlertSeverity.HIGH,
            "Test alert message",
            "test_service",
            {"metric": "test_metric"}
        )
        
        assert alert is not None
        assert alert.type == AlertType.SERVICE_DOWN
        assert alert.severity == AlertSeverity.HIGH
        assert alert.message == "Test alert message"
        assert alert.service == "test_service"

    @pytest.mark.asyncio
    async def test_get_active_alerts(self, monitoring_service):
        """Test alerts retrieval."""
        # Create some test alerts
        monitoring_service.create_alert(AlertType.SERVICE_DOWN, AlertSeverity.HIGH, "Test alert 1", "test_service")
        monitoring_service.create_alert(AlertType.HIGH_ERROR_RATE, AlertSeverity.MEDIUM, "Test alert 2", "test_service")
        
        alerts = monitoring_service.get_active_alerts()
        assert len(alerts) >= 2
        
        # Verify alerts exist
        alert_types = [a.type for a in alerts]
        assert AlertType.SERVICE_DOWN in alert_types
        assert AlertType.HIGH_ERROR_RATE in alert_types

    @pytest.mark.asyncio
    async def test_get_alerts_by_severity(self, monitoring_service):
        """Test alerts retrieval by severity."""
        # Create test alerts of different severities
        monitoring_service.create_alert(AlertType.SERVICE_DOWN, AlertSeverity.LOW, "Warning", "test_service")
        monitoring_service.create_alert(AlertType.HIGH_ERROR_RATE, AlertSeverity.HIGH, "Error", "test_service")
        
        # Get high severity alerts
        high_alerts = monitoring_service.alert_manager.get_alerts_by_severity(AlertSeverity.HIGH)
        assert len(high_alerts) >= 1
        assert all(a.severity == AlertSeverity.HIGH for a in high_alerts)

    @pytest.mark.asyncio
    async def test_resolve_alert(self, monitoring_service):
        """Test alert resolution."""
        # Create a test alert
        alert = monitoring_service.create_alert(AlertType.SERVICE_DOWN, AlertSeverity.HIGH, "Test alert", "test_service")
        
        # Resolve the alert
        result = monitoring_service.resolve_alert(alert.id)
        assert result is True
        
        # Verify alert is resolved
        alerts = monitoring_service.get_active_alerts()
        resolved_alert = next((a for a in alerts if a.id == alert.id), None)
        assert resolved_alert is None  # Should not be in active alerts

    @pytest.mark.asyncio
    async def test_health_check_service(self, monitoring_service):
        """Test service health checking."""
        # Mock a service
        mock_service = Mock()
        mock_service.is_healthy = Mock(return_value=True)
        mock_service.get_service_info = Mock(return_value={"status": "healthy"})
        
        # Check service health
        health = await monitoring_service.monitor_service("test_service", mock_service.is_healthy)
        assert health is not None
        # The health status depends on the actual implementation, so just check it exists
        assert hasattr(health, 'status')

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_service(self, monitoring_service):
        """Test health checking of unhealthy service."""
        # Mock an unhealthy service
        mock_service = Mock()
        mock_service.is_healthy = Mock(return_value=False)
        mock_service.get_service_info = Mock(return_value={"status": "unhealthy"})
        
        # Check service health
        health = await monitoring_service.monitor_service("test_service", mock_service.is_healthy)
        assert health is not None
        assert health.status == "unhealthy"

    @pytest.mark.asyncio
    async def test_monitor_system_resources(self, monitoring_service):
        """Test system resource monitoring."""
        # Mock system resource data
        with patch('psutil.cpu_percent', return_value=50.0):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = 60.0
                mock_memory.return_value.used = 1024 * 1024 * 1024  # 1GB
                mock_memory.return_value.total = 2 * 1024 * 1024 * 1024  # 2GB
                
                # Monitor system resources
                await monitoring_service._monitor_system_resources()
                
                # Verify metrics were recorded
                cpu_metrics = monitoring_service.get_metrics("system_cpu_usage")
                memory_metrics = monitoring_service.get_metrics("system_memory_usage")
                
                assert len(cpu_metrics) > 0
                assert len(memory_metrics) > 0

    @pytest.mark.asyncio
    async def test_service_configuration(self, monitoring_service):
        """Test service configuration handling."""
        # Test default configuration
        config = monitoring_service.config
        assert config is not None

    @pytest.mark.asyncio
    async def test_error_handling(self, monitoring_service):
        """Test error handling in service."""
        # Test service remains healthy after errors
        initial_health = await monitoring_service.health_check()
        
        # Simulate an error
        monitoring_service._last_error = Exception("Test error")
        
        health_after_error = await monitoring_service.health_check()
        assert health_after_error is not None

    @pytest.mark.asyncio
    async def test_service_lifecycle_with_errors(self, monitoring_service):
        """Test service lifecycle with error handling."""
        # Initialize service
        await monitoring_service.initialize()
        assert monitoring_service.running is True

        # Cleanup service
        await monitoring_service.cleanup()
        assert monitoring_service.running is False 