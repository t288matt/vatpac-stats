#!/usr/bin/env python3
"""
Event Bus Implementation for VATSIM Data Collection System

This module provides the event bus implementation for inter-service communication
using the interfaces defined in the service interfaces package.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timezone
from collections import defaultdict

from .interfaces.event_bus_interface import EventBusInterface, Event, EventType
from ..utils.logging import get_logger_for_module
from ..utils.error_handling import handle_service_errors, log_operation


class EventBus(EventBusInterface):
    """Event bus implementation for inter-service communication."""
    
    def __init__(self):
        self.logger = get_logger_for_module(__name__)
        self.subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self.event_history: List[Event] = []
        self.max_history_size = 1000
        self.running = False
        self.processing_task: Optional[asyncio.Task] = None
    
    @handle_service_errors
    @log_operation("publish_event")
    async def publish(self, event: Event) -> bool:
        """Publish an event to the event bus."""
        try:
            self.logger.debug(f"Publishing event: {event.event_type.value}")
            
            # Add to history
            self.event_history.append(event)
            if len(self.event_history) > self.max_history_size:
                self.event_history.pop(0)
            
            # Get subscribers for this event type
            handlers = self.subscribers.get(event.event_type, [])
            
            if not handlers:
                self.logger.debug(f"No subscribers for event type: {event.event_type.value}")
                return True
            
            # Execute handlers asynchronously
            tasks = []
            for handler in handlers:
                try:
                    task = asyncio.create_task(self._execute_handler(handler, event))
                    tasks.append(task)
                except Exception as e:
                    self.logger.error(f"Failed to create task for handler: {e}")
            
            # Wait for all handlers to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            self.logger.debug(f"Successfully published event: {event.event_type.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to publish event {event.event_type.value}: {e}")
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
    
    async def _execute_handler(self, handler: Callable, event: Event) -> None:
        """Execute a handler for an event."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            self.logger.error(f"Handler execution failed for event {event.event_type.value}: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        try:
            total_subscribers = sum(len(handlers) for handlers in self.subscribers.values())
            total_events = len(self.event_history)
            
            # Count events by type
            event_counts = {}
            for event in self.event_history:
                event_type = event.event_type.value
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            return {
                "total_subscribers": total_subscribers,
                "total_events": total_events,
                "event_counts": event_counts,
                "subscriber_counts": {
                    event_type.value: len(handlers)
                    for event_type, handlers in self.subscribers.items()
                },
                "running": self.running
            }
            
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