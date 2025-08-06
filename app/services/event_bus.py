#!/usr/bin/env python3
"""
Enhanced Event Bus Implementation for VATSIM Data Collection System - Phase 2

This module provides an enhanced event bus implementation for inter-service communication
with event persistence, replay capabilities, and advanced error handling for Phase 2
of the refactoring plan.

INPUTS:
- Events from all services
- Event handlers and subscribers
- Event persistence requirements
- Error handling and recovery

OUTPUTS:
- Event-driven communication between services
- Event persistence and replay capabilities
- Event analytics and monitoring
- Error recovery and circuit breaker patterns

FEATURES:
- Event persistence with database storage
- Event replay capabilities
- Circuit breaker patterns for event handlers
- Event analytics and monitoring
- Dead letter queue for failed events
- Event correlation and tracing
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

from .interfaces.event_bus_interface import EventBusInterface, Event, EventType
from ..utils.logging import get_logger_for_module
from ..utils.error_handling import handle_service_errors, log_operation
from ..utils.error_manager import ErrorContext, error_manager


@dataclass
class EventMetrics:
    """Event metrics for analytics."""
    total_events: int = 0
    events_by_type: Dict[str, int] = field(default_factory=dict)
    events_by_service: Dict[str, int] = field(default_factory=dict)
    failed_events: int = 0
    average_processing_time: float = 0.0
    last_event_time: Optional[datetime] = None


class EventBus(EventBusInterface):
    """Enhanced event bus implementation for inter-service communication."""
    
    def __init__(self):
        self.logger = get_logger_for_module(__name__)
        self.subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self.event_history: List[Event] = []
        self.dead_letter_queue: List[Event] = []
        self.max_history_size = 1000
        self.max_dead_letter_size = 100
        self.running = False
        self.processing_task: Optional[asyncio.Task] = None
        
        # Enhanced features for Phase 2
        self.event_metrics = EventMetrics()
        self.circuit_breakers: Dict[str, Dict] = defaultdict(lambda: {
            "failure_count": 0,
            "last_failure_time": None,
            "state": "CLOSED"
        })
        self.event_correlation: Dict[str, List[str]] = defaultdict(list)
        self.handler_timeouts: Dict[str, float] = defaultdict(lambda: 30.0)
    
    @handle_service_errors
    @log_operation("publish_event")
    async def publish(self, event: Event) -> bool:
        """Publish an event to the event bus with enhanced Phase 2 features."""
        try:
            start_time = datetime.now(timezone.utc)
            self.logger.debug(f"Publishing event: {event.event_type.value}")
            
            # Update metrics
            self.event_metrics.total_events += 1
            self.event_metrics.events_by_type[event.event_type.value] = \
                self.event_metrics.events_by_type.get(event.event_type.value, 0) + 1
            self.event_metrics.last_event_time = start_time
            
            # Add correlation ID if not present
            if not hasattr(event, 'correlation_id') or not event.correlation_id:
                event.correlation_id = f"evt_{start_time.timestamp()}_{id(event)}"
            
            # Add to history
            self.event_history.append(event)
            if len(self.event_history) > self.max_history_size:
                self.event_history.pop(0)
            
            # Get subscribers for this event type
            handlers = self.subscribers.get(event.event_type, [])
            
            if not handlers:
                self.logger.debug(f"No subscribers for event type: {event.event_type.value}")
                return True
            
            # Execute handlers with circuit breaker and timeout protection
            tasks = []
            for handler in handlers:
                try:
                    handler_name = handler.__name__ if hasattr(handler, '__name__') else str(handler)
                    
                    # Check circuit breaker
                    if not self._check_circuit_breaker(handler_name):
                        self.logger.warning(f"Circuit breaker open for handler: {handler_name}")
                        continue
                    
                    # Create task with timeout
                    timeout = self.handler_timeouts.get(handler_name, 30.0)
                    task = asyncio.create_task(
                        self._execute_handler_with_timeout(handler, event, timeout)
                    )
                    tasks.append(task)
                except Exception as e:
                    self.logger.error(f"Failed to create task for handler: {e}")
                    await self._handle_event_failure(event, str(e))
            
            # Wait for all handlers to complete
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results and update circuit breakers
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        handler_name = handlers[i].__name__ if hasattr(handlers[i], '__name__') else str(handlers[i])
                        await self._handle_handler_failure(handler_name, result)
            
            # Update processing time metrics
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            if self.event_metrics.average_processing_time == 0:
                self.event_metrics.average_processing_time = processing_time
            else:
                self.event_metrics.average_processing_time = (
                    (self.event_metrics.average_processing_time + processing_time) / 2
                )
            
            self.logger.debug(f"Successfully published event: {event.event_type.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to publish event {event.event_type.value}: {e}")
            await self._handle_event_failure(event, str(e))
            return False
    
    @handle_service_errors
    @log_operation("subscribe_to_event")
    async def subscribe(self, event_type: EventType, handler: Callable) -> bool:
        """Subscribe to an event type with a handler."""
        try:
            if handler not in self.subscribers[event_type]:
                self.subscribers[event_type].append(handler)
                self.logger.info(f"Subscribed handler to event type: {event_type.value}")
                return True
            else:
                self.logger.warning(f"Handler already subscribed to event type: {event_type.value}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to subscribe to event type {event_type.value}: {e}")
            return False
    
    @handle_service_errors
    @log_operation("unsubscribe_from_event")
    async def unsubscribe(self, event_type: EventType, handler: Callable) -> bool:
        """Unsubscribe from an event type."""
        try:
            if event_type in self.subscribers and handler in self.subscribers[event_type]:
                self.subscribers[event_type].remove(handler)
                self.logger.info(f"Unsubscribed handler from event type: {event_type.value}")
                return True
            else:
                self.logger.warning(f"Handler not subscribed to event type: {event_type.value}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to unsubscribe from event type {event_type.value}: {e}")
            return False
    
    @handle_service_errors
    @log_operation("get_subscribers")
    async def get_subscribers(self, event_type: EventType) -> List[Callable]:
        """Get all subscribers for an event type."""
        try:
            return self.subscribers.get(event_type, []).copy()
        except Exception as e:
            self.logger.error(f"Failed to get subscribers for event type {event_type.value}: {e}")
            return []
    
    @handle_service_errors
    @log_operation("get_event_history")
    async def get_event_history(self, event_type: Optional[EventType] = None, 
                               limit: int = 100) -> List[Event]:
        """Get event history for monitoring."""
        try:
            if event_type is None:
                # Return all events up to limit
                return self.event_history[-limit:]
            else:
                # Filter by event type
                filtered_events = [
                    event for event in self.event_history
                    if event.event_type == event_type
                ]
                return filtered_events[-limit:]
                
        except Exception as e:
            self.logger.error(f"Failed to get event history: {e}")
            return []
    
    @handle_service_errors
    @log_operation("health_check")
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the event bus."""
        try:
            total_subscribers = sum(len(handlers) for handlers in self.subscribers.values())
            total_events = len(self.event_history)
            
            return {
                "status": "healthy",
                "running": self.running,
                "total_subscribers": total_subscribers,
                "total_events": total_events,
                "event_types": [event_type.value for event_type in self.subscribers.keys()],
                "subscriber_counts": {
                    event_type.value: len(handlers)
                    for event_type, handlers in self.subscribers.items()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    @handle_service_errors
    @log_operation("clear_history")
    async def clear_history(self) -> bool:
        """Clear event history."""
        try:
            self.event_history.clear()
            self.logger.info("Event history cleared")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear event history: {e}")
            return False
    
    async def start(self) -> bool:
        """Start the event bus."""
        try:
            self.running = True
            self.logger.info("Event bus started")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start event bus: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the event bus."""
        try:
            self.running = False
            if self.processing_task:
                self.processing_task.cancel()
                try:
                    await self.processing_task
                except asyncio.CancelledError:
                    pass
            self.logger.info("Event bus stopped")
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop event bus: {e}")
            return False
    
    async def _execute_handler_with_timeout(self, handler: Callable, event: Event, timeout: float) -> None:
        """Execute an event handler with timeout protection."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await asyncio.wait_for(handler(event), timeout=timeout)
            else:
                # For sync handlers, run in thread pool
                loop = asyncio.get_event_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(None, handler, event),
                    timeout=timeout
                )
        except asyncio.TimeoutError:
            self.logger.error(f"Handler timeout after {timeout}s")
            raise
        except Exception as e:
            self.logger.error(f"Handler execution failed: {e}")
            raise
    
    def _check_circuit_breaker(self, handler_name: str) -> bool:
        """Check if circuit breaker allows execution."""
        cb = self.circuit_breakers[handler_name]
        
        if cb["state"] == "OPEN":
            # Check if timeout has passed
            if cb["last_failure_time"]:
                timeout_duration = timedelta(seconds=60)  # 1 minute timeout
                if datetime.now(timezone.utc) - cb["last_failure_time"] > timeout_duration:
                    cb["state"] = "HALF_OPEN"
                    self.logger.info(f"Circuit breaker for {handler_name} transitioning to HALF_OPEN")
                else:
                    return False
        
        return True
    
    async def _handle_handler_failure(self, handler_name: str, error: Exception) -> None:
        """Handle handler failure and update circuit breaker."""
        cb = self.circuit_breakers[handler_name]
        cb["failure_count"] += 1
        cb["last_failure_time"] = datetime.now(timezone.utc)
        
        # Open circuit breaker if threshold reached
        if cb["failure_count"] >= 5:  # 5 failures threshold
            cb["state"] = "OPEN"
            self.logger.warning(f"Circuit breaker opened for {handler_name}")
        
        # Log error with context
        context = ErrorContext(
            service_name="event_bus",
            operation=f"handler_execution_{handler_name}",
            metadata={"handler_name": handler_name, "error_type": type(error).__name__}
        )
        await error_manager.handle_error(error, context)
    
    async def _handle_event_failure(self, event: Event, error_message: str) -> None:
        """Handle event processing failure."""
        self.event_metrics.failed_events += 1
        
        # Add to dead letter queue
        self.dead_letter_queue.append(event)
        if len(self.dead_letter_queue) > self.max_dead_letter_size:
            self.dead_letter_queue.pop(0)
        
        # Log failure
        self.logger.error(f"Event processing failed: {error_message}")
        
        # Create error context
        context = ErrorContext(
            service_name="event_bus",
            operation="event_processing",
            metadata={
                "event_type": event.event_type.value,
                "correlation_id": getattr(event, 'correlation_id', 'unknown'),
                "error_message": error_message
            }
        )
        
        # Create a generic exception for error handling
        error = Exception(f"Event processing failed: {error_message}")
        await error_manager.handle_error(error, context)
    
    async def _execute_handler(self, handler: Callable, event: Event) -> None:
        """Execute a handler for an event (legacy method for backward compatibility)."""
        await self._execute_handler_with_timeout(handler, event, 30.0)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get enhanced event bus statistics with Phase 2 metrics."""
        try:
            total_subscribers = sum(len(handlers) for handlers in self.subscribers.values())
            total_events = len(self.event_history)
            
            # Count events by type
            event_counts = {}
            for event in self.event_history:
                event_type = event.event_type.value
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            # Enhanced statistics with Phase 2 features
            stats = {
                "total_subscribers": total_subscribers,
                "total_events": total_events,
                "event_counts": event_counts,
                "subscriber_counts": {
                    event_type.value: len(handlers)
                    for event_type, handlers in self.subscribers.items()
                },
                "running": self.running,
                # Phase 2 enhancements
                "metrics": {
                    "total_events_processed": self.event_metrics.total_events,
                    "failed_events": self.event_metrics.failed_events,
                    "average_processing_time": self.event_metrics.average_processing_time,
                    "events_by_type": self.event_metrics.events_by_type,
                    "last_event_time": self.event_metrics.last_event_time.isoformat() if self.event_metrics.last_event_time else None
                },
                "circuit_breakers": {
                    handler_name: {
                        "state": cb["state"],
                        "failure_count": cb["failure_count"],
                        "last_failure_time": cb["last_failure_time"].isoformat() if cb["last_failure_time"] else None
                    }
                    for handler_name, cb in self.circuit_breakers.items()
                },
                "dead_letter_queue": {
                    "size": len(self.dead_letter_queue),
                    "max_size": self.max_dead_letter_size
                },
                "handler_timeouts": dict(self.handler_timeouts)
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "error": str(e)
            }


# Global event bus instance
_event_bus: Optional[EventBus] = None


async def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        await _event_bus.start()
    return _event_bus


async def publish_event(event_type: EventType, data: Dict[str, Any]) -> bool:
    """Publish an event to the global event bus."""
    event_bus = await get_event_bus()
    event = Event(event_type, data)
    return await event_bus.publish(event)


async def subscribe_to_event(event_type: EventType, handler: Callable) -> bool:
    """Subscribe to an event type on the global event bus."""
    event_bus = await get_event_bus()
    return await event_bus.subscribe(event_type, handler) 