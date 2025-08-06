# Phase 2 Quick Reference Guide

## Overview
Phase 2 implemented comprehensive error handling and event-driven architecture enhancements for the VATSIM Data Collection System.

## Key Files

### Error Management
- **`app/utils/error_manager.py`** - Centralized error management system
- **`app/services/event_bus.py`** - Enhanced event bus with error handling
- **`app/services/database_service.py`** - Database service with error integration

### API Endpoints
- **`app/main.py`** - New Phase 2 API endpoints

## Error Management Quick Reference

### Error Severity Levels
```python
ErrorSeverity.LOW      # Minor issues, no impact
ErrorSeverity.MEDIUM   # Moderate issues, some impact
ErrorSeverity.HIGH     # Significant issues, service impact
ErrorSeverity.CRITICAL # Critical issues, system impact
```

### Error Categories
```python
ErrorCategory.NETWORK      # Connection, timeout issues
ErrorCategory.DATABASE     # Database operation failures
ErrorCategory.API         # API call failures
ErrorCategory.VALIDATION  # Data validation errors
ErrorCategory.CONFIGURATION # Configuration issues
ErrorCategory.RESOURCE    # Memory, disk issues
ErrorCategory.TIMEOUT     # Timeout errors
ErrorCategory.UNKNOWN     # Unclassified errors
```

### Using Error Manager
```python
from app.utils.error_manager import error_manager, ErrorContext

# Create error context
context = ErrorContext(
    service_name="my_service",
    operation="data_processing",
    metadata={"user_id": "123", "data_size": 1000}
)

# Handle error
await error_manager.handle_error(exception, context)

# Get analytics
analytics = error_manager.get_error_analytics(hours=24)

# Get circuit breaker status
status = error_manager.get_circuit_breaker_status()
```

## Event Bus Quick Reference

### Event Metrics
```python
from app.services.event_bus import EventMetrics

metrics = EventMetrics()
# Access: metrics.total_events, metrics.failed_events, etc.
```

### Using Event Bus
```python
from app.services.event_bus import get_event_bus, publish_event
from app.services.interfaces.event_bus_interface import EventType

# Get event bus
event_bus = await get_event_bus()

# Publish event
await publish_event(EventType.FLIGHT_UPDATE, {"callsign": "ABC123"})

# Subscribe to events
async def my_handler(event):
    print(f"Received event: {event.event_type}")

await event_bus.subscribe(EventType.FLIGHT_UPDATE, my_handler)

# Get statistics
stats = event_bus.get_statistics()
```

## Database Service Quick Reference

### Using Database Service
```python
from app.services.database_service import get_database_service

db_service = get_database_service()

# Store data
await db_service.store_flights(flight_data)

# Get data
flights = await db_service.get_active_flights()
track = await db_service.get_flight_track("ABC123")

# Get statistics
stats = await db_service.get_database_stats()
health = await db_service.health_check()
```

## API Endpoints Quick Reference

### Error Management Endpoints
```bash
# Get error analytics
GET /api/errors/analytics

# Get circuit breaker status
GET /api/errors/circuit-breakers
```

### Database Service Endpoints
```bash
# Get database statistics
GET /api/database/service/stats

# Get database health
GET /api/database/service/health
```

### Event Analytics Endpoint
```bash
# Get event bus statistics
GET /api/events/analytics
```

## Circuit Breaker Patterns

### Circuit Breaker States
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Circuit open, requests fail fast
- **HALF_OPEN**: Testing if service recovered

### Circuit Breaker Configuration
```python
# Default settings
failure_threshold = 5    # Failures before opening
timeout = 60            # Seconds before half-open
```

## Error Recovery Strategies

### Retry Handler
```python
# Exponential backoff retry
retry_handler = RetryHandler(
    max_retries=3,
    backoff_factor=2.0
)
```

### Circuit Breaker Handler
```python
# Circuit breaker protection
circuit_breaker = CircuitBreakerHandler(
    failure_threshold=5,
    timeout=60
)
```

## Performance Monitoring

### Error Metrics
- Total errors by category
- Error severity distribution
- Recovery success rate
- Most common errors

### Event Metrics
- Total events processed
- Failed events count
- Average processing time
- Events by type

### Database Metrics
- Query count and timing
- Connection pool status
- Data volume statistics
- Health check results

## Common Patterns

### Error Handling Pattern
```python
try:
    result = await operation()
    return result
except Exception as e:
    context = ErrorContext(
        service_name="my_service",
        operation="operation_name"
    )
    await error_manager.handle_error(e, context)
    raise
```

### Event Publishing Pattern
```python
try:
    await publish_event(EventType.MY_EVENT, data)
except Exception as e:
    # Event bus handles errors automatically
    logger.error(f"Failed to publish event: {e}")
```

### Database Operation Pattern
```python
try:
    result = await db_service.operation(data)
    return result
except Exception as e:
    # Database service handles errors automatically
    logger.error(f"Database operation failed: {e}")
    raise
```

## Configuration

### Environment Variables
All Phase 2 features use existing Phase 1 configuration:
- Database connection settings
- Service configuration
- Logging configuration

### Service Configuration
```python
# Error manager configuration
ERROR_MANAGER_ENABLED = True
ERROR_ANALYTICS_RETENTION_HOURS = 24

# Event bus configuration
EVENT_BUS_MAX_HISTORY_SIZE = 1000
EVENT_BUS_MAX_DEAD_LETTER_SIZE = 100
EVENT_BUS_HANDLER_TIMEOUT = 30.0

# Database service configuration
DATABASE_SERVICE_MAX_POOL_SIZE = 10
DATABASE_SERVICE_CLEANUP_HOURS = 24
```

## Troubleshooting

### Common Issues

1. **Circuit Breaker Open**
   - Check failure count and last failure time
   - Wait for timeout period
   - Reset circuit breaker if needed

2. **Event Processing Failures**
   - Check dead letter queue size
   - Review handler timeout settings
   - Monitor event metrics

3. **Database Connection Issues**
   - Check database health endpoint
   - Review connection pool status
   - Monitor query performance

### Debug Commands
```bash
# Check system health
curl http://localhost:8001/api/status

# Check error analytics
curl http://localhost:8001/api/errors/analytics

# Check database health
curl http://localhost:8001/api/database/service/health

# Check event analytics
curl http://localhost:8001/api/events/analytics
```

## Integration with Existing Code

### Backward Compatibility
- All existing models preserved unchanged
- Existing API endpoints remain functional
- No breaking changes to existing code

### Service Integration
- Error manager integrates with existing services
- Event bus enhances existing event processing
- Database service uses existing models

## Next Steps

Phase 2 is complete and ready for **Phase 3: Advanced Analytics & ML Integration**:
- Machine learning service enhancements
- Advanced traffic pattern analysis
- Predictive modeling capabilities
- Real-time anomaly detection
- Performance optimization algorithms

## Support

For issues or questions about Phase 2 implementation:
1. Check the detailed implementation summary: `PHASE_2_IMPLEMENTATION_SUMMARY.md`
2. Review the architecture diagram: `PHASE_2_ARCHITECTURE_DIAGRAM.md`
3. Test the API endpoints to verify functionality
4. Check application logs for detailed error information 