#!/usr/bin/env python3
"""
Data Service Interface for VATSIM Data Collection System

This interface defines the contract for data ingestion and processing services.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime


class DataServiceInterface(ABC):
    """Interface for data ingestion and processing services."""
    
    @abstractmethod
    async def start_data_ingestion(self) -> bool:
        """Start the data ingestion process."""
        pass
    
    @abstractmethod
    async def stop_data_ingestion(self) -> bool:
        """Stop the data ingestion process."""
        pass
    
    @abstractmethod
    async def get_ingestion_status(self) -> Dict[str, Any]:
        """Get current ingestion status and statistics."""
        pass
    
    @abstractmethod
    async def process_data_in_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data in memory before database storage."""
        pass
    
    @abstractmethod
    async def flush_memory_to_disk(self) -> bool:
        """Flush memory cache to database."""
        pass
    
    @abstractmethod
    async def cleanup_old_data(self) -> bool:
        """Clean up old data based on retention policies."""
        pass
    
    @abstractmethod
    async def get_network_status(self) -> Dict[str, Any]:
        """Get current network status and statistics."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the data service."""
        pass 