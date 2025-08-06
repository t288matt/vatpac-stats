#!/usr/bin/env python3
"""
Event Bus Interface for VATSIM Data Collection System

This interface defines the contract for inter-service communication.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum


class EventType(Enum):
    """Event types for the event bus."""
    VATSIM_DATA_RECEIVED = "vatsim_data_received"
    FLIGHT_DATA_PROCESSED = "flight_data_processed"
    CONTROLLER_DATA_PROCESSED = "controller_data_processed"
    SECTOR_DATA_PROCESSED = "sector_data_processed"
    TRANSCEIVER_DATA_PROCESSED = "transceiver_data_processed"
    DATA_FLUSHED_TO_DISK = "data_flushed_to_disk"
    ERROR_OCCURRED = "error_occurred"
    HEALTH_CHECK_REQUESTED = "health_check_requested"
    CACHE_INVALIDATED = "cache_invalidated"
    SERVICE_STARTED = "service_started"
    SERVICE_STOPPED = "service_stopped"


class Event:
    """Event object for the event bus."""
    
    def __init__(self, event_type: EventType, data: Dict[str, Any], timestamp: Optional[datetime] = None):
        self.event_type = event_type
        self.data = data
        self.timestamp = timestamp or datetime.now()
        self.id = f"{event_type.value}_{timestamp.timestamp()}"


class EventBusInterface(ABC):
    """Interface for event bus operations."""
    
    @abstractmethod
    async def publish(self, event: Event) -> bool:
        """Publish an event to the event bus."""
        pass
    
    @abstractmethod
    async def subscribe(self, event_type: EventType, handler: Callable) -> bool:
        """Subscribe to an event type with a handler."""
        pass
    
    @abstractmethod
    async def unsubscribe(self, event_type: EventType, handler: Callable) -> bool:
        """Unsubscribe from an event type."""
        pass
    
    @abstractmethod
    async def get_subscribers(self, event_type: EventType) -> List[Callable]:
        """Get all subscribers for an event type."""
        pass
    
    @abstractmethod
    async def get_event_history(self, event_type: Optional[EventType] = None, 
                               limit: int = 100) -> List[Event]:
        """Get event history for monitoring."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the event bus."""
        pass
    
    @abstractmethod
    async def clear_history(self) -> bool:
        """Clear event history."""
        pass 