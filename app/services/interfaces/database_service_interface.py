#!/usr/bin/env python3
"""
Database Service Interface for VATSIM Data Collection System

This interface defines the contract for database operations while preserving
existing models and schema.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session


class DatabaseServiceInterface(ABC):
    """Interface for database operations using existing models."""
    
    @abstractmethod
    async def store_flights(self, flights: List[Dict[str, Any]]) -> int:
        """Store flight data using existing Flight model."""
        pass
    
    @abstractmethod
    async def store_controllers(self, controllers: List[Dict[str, Any]]) -> int:
        """Store controller data using existing Controller model."""
        pass
    
    @abstractmethod
    async def store_sectors(self, sectors: List[Dict[str, Any]]) -> int:
        """Store sector data using existing Sector model."""
        pass
    
    @abstractmethod
    async def store_transceivers(self, transceivers: List[Dict[str, Any]]) -> int:
        """Store transceiver data using existing Transceiver model."""
        pass
    
    @abstractmethod
    async def get_flight_track(self, callsign: str, start_time: Optional[datetime] = None, 
                              end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get complete flight track using existing Flight model."""
        pass
    
    @abstractmethod
    async def get_flight_stats(self, callsign: str) -> Dict[str, Any]:
        """Get flight statistics using existing Flight model."""
        pass
    
    @abstractmethod
    async def get_active_flights(self) -> List[Dict[str, Any]]:
        """Get active flights using existing Flight model."""
        pass
    
    @abstractmethod
    async def get_active_controllers(self) -> List[Dict[str, Any]]:
        """Get active controllers using existing Controller model."""
        pass
    

    
    @abstractmethod
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and health information."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the database service."""
        pass
    
    @abstractmethod
    async def get_session(self) -> Session:
        """Get database session for direct model operations."""
        pass 