#!/usr/bin/env python3
"""
Service Interfaces for VATSIM Data Collection System

This module defines interfaces for all services to ensure consistent
contracts and enable proper service decomposition.
"""

from .data_service_interface import DataServiceInterface
from .vatsim_service_interface import VATSIMServiceInterface
from .flight_processing_interface import FlightProcessingInterface
from .database_service_interface import DatabaseServiceInterface
from .cache_service_interface import CacheServiceInterface
from .event_bus_interface import EventBusInterface

__all__ = [
    'DataServiceInterface',
    'VATSIMServiceInterface', 
    'FlightProcessingInterface',
    'DatabaseServiceInterface',
    'CacheServiceInterface',
    'EventBusInterface'
] 