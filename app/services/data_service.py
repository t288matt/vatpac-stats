#!/usr/bin/env python3
"""
Data Service for VATSIM Data Collection System

This module provides the core data processing and storage functionality
for the VATSIM data collection system.

INPUTS:
- VATSIM API data from VATSIM service
- Configuration settings
- Database connection

OUTPUTS:
- Processed and stored flight data
- Processed and stored ATC position data
- Processed and stored transceiver data
- System health and status information
"""

import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from ..utils.logging import get_logger_for_module
from ..utils.error_handling import handle_service_errors, log_operation
from ..services.vatsim_service import VATSIMService
from ..filters.geographic_boundary_filter import GeographicBoundaryFilter
from ..database import get_database_session
from ..models import Flight, Controller, Transceiver
from ..config import get_config
from sqlalchemy import text

logger = get_logger_for_module("services.data_service")


class DataService:
    """
    Core data processing service for VATSIM data collection.
    
    This service handles:
    - Flight data processing and filtering
    - ATC position data processing
    - Transceiver data processing
    - Database storage operations
    - Data validation and error handling
    """
    
    def __init__(self):
        """Initialize data service with configuration."""
        self.service_name = "data_service"
        self.config = get_config()
        self.logger = get_logger_for_module(f"services.{self.service_name}")
        self._initialized = False
        
        # Initialize filters
        self.geographic_boundary_filter = GeographicBoundaryFilter()
        
        # Initialize services
        self.vatsim_service = None
        self.db_session = None
        
        # Performance tracking
        self.processing_stats = {
            "total_flights_processed": 0,
            "total_controllers_processed": 0,
            "total_transceivers_processed": 0,
            "last_processing_time": 0.0,
            "last_processing_timestamp": None
        }
    
    async def initialize(self) -> bool:
        """Initialize data service with dependencies."""
        try:
            # Initialize VATSIM service
            self.vatsim_service = VATSIMService()
            await self.vatsim_service.initialize()
            
            # Geographic boundary filter is already initialized in its constructor
            # No need to call initialize() on it
            
            # Don't get database session here - we'll get it when needed
            self.db_session = None
            
            self.logger.info(f"Geographic filter initialized: {self.geographic_boundary_filter.config.enabled}")
            self._initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize data service: {e}")
            return False
    
    def is_initialized(self) -> bool:
        """Check if service is properly initialized."""
        return self._initialized
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform data service health check."""
        try:
            if not self._initialized:
                return {"status": "uninitialized", "error": "Service not initialized"}
            
            # Check VATSIM service
            vatsim_health = await self.vatsim_service.health_check()
            
            # Check geographic boundary filter
            boundary_filter_health = {
                "enabled": self.geographic_boundary_filter.config.enabled,
                "initialized": self.geographic_boundary_filter.is_initialized
            }
            
            # Check database connectivity
            try:
                async with get_database_session() as session:
                    session.execute(text("SELECT 1"))
                    database_status = "connected"
            except Exception:
                database_status = "disconnected"
            
            return {
                "status": "healthy" if vatsim_health["status"] == "healthy" else "unhealthy",
                "vatsim_service": vatsim_health,
                "geographic_boundary_filter": boundary_filter_health,
                "database": database_status
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def cleanup(self):
        """Cleanup data service resources."""
        try:
            if self.vatsim_service:
                await self.vatsim_service.cleanup()
            
            if self.db_session:
                await self.db_session.close()
                
            self.logger.info("Data service cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    @handle_service_errors
    @log_operation("process_vatsim_data")
    async def process_vatsim_data(self) -> Dict[str, Any]:
        """
        Process VATSIM data and store to database.
        
        Returns:
            Dict[str, Any]: Processing results and statistics
        """
        if not self._initialized:
            raise RuntimeError("Data service not initialized")
        
        start_time = time.time()
        
        try:
            # Fetch current VATSIM data
            self.logger.info("Fetching current VATSIM data")
            vatsim_data = await self.vatsim_service.get_current_data()
            
            # Process flights with geographic boundary filtering
            flights_processed = await self._process_flights(vatsim_data.get("flights", []))
            
            # Process controllers
            controllers_processed = await self._process_controllers(vatsim_data.get("controllers", []))
            
            # Process transceivers
            transceivers_processed = await self._process_transceivers(vatsim_data.get("transceivers", []))
            
            # Update VATSIM status
            # await self._update_vatsim_status(vatsim_data) # This line is removed
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Update statistics
            self.processing_stats.update({
                "total_flights_processed": self.processing_stats["total_flights_processed"] + flights_processed,
                "total_controllers_processed": self.processing_stats["total_controllers_processed"] + controllers_processed,
                "total_transceivers_processed": self.processing_stats["total_transceivers_processed"] + transceivers_processed,
                "last_processing_time": processing_time,
                "last_processing_timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            self.logger.info("VATSIM data processing completed", extra={
                "flights_processed": flights_processed,
                "controllers_processed": controllers_processed,
                "transceivers_processed": transceivers_processed,
                "processing_time": processing_time
            })
            
            return {
                "status": "success",
                "flights_processed": flights_processed,
                "controllers_processed": controllers_processed,
                "transceivers_processed": transceivers_processed,
                "processing_time": processing_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing VATSIM data: {e}")
            raise
    
    async def _process_flights(self, flights_data: List[Dict[str, Any]]) -> int:
        """
        Process and store flight data with geographic boundary filtering.
        
        Args:
            flights_data: Raw flight data from VATSIM API
            
        Returns:
            int: Number of flights processed and stored
        """
        if not flights_data:
            return 0
        
        processed_count = 0
        
        # Get database session
        async with get_database_session() as session:
            for flight_dict in flights_data:
                try:
                    # Apply geographic boundary filtering
                    if self.geographic_boundary_filter.config.enabled:
                        if not self.geographic_boundary_filter.filter_flights_list([flight_dict]):
                            # Flight filtered out by geographic boundary
                            continue
                    
                    # Create flight model
                    flight = Flight(
                        callsign=flight_dict.get("callsign", ""),
                        name=flight_dict.get("name", ""),  # Changed from pilot_name to name
                        aircraft_type=flight_dict.get("aircraft_type", ""),  # Use aircraft_type, not aircraft_short
                        departure=flight_dict.get("departure", ""),
                        arrival=flight_dict.get("arrival", ""),
                        route=flight_dict.get("route", ""),
                        altitude=flight_dict.get("altitude", 0),
                        latitude=flight_dict.get("latitude"),
                        longitude=flight_dict.get("longitude"),
                        groundspeed=flight_dict.get("groundspeed"),  # Changed from groundspeed to groundspeed
                        heading=flight_dict.get("heading"),
                        cid=flight_dict.get("cid"),
                        server=flight_dict.get("server", ""),
                        pilot_rating=flight_dict.get("pilot_rating"),
                        military_rating=flight_dict.get("military_rating"),
                        transponder=flight_dict.get("transponder", ""),
                        logon_time=flight_dict.get("logon_time"),
                        last_updated_api=flight_dict.get("last_updated"),
                        flight_rules=flight_dict.get("flight_rules", ""),
                        aircraft_faa=flight_dict.get("aircraft_faa", ""),
                        alternate=flight_dict.get("alternate", ""),
                        cruise_tas=flight_dict.get("cruise_tas", ""),
                        planned_altitude=flight_dict.get("planned_altitude", ""),
                        deptime=flight_dict.get("deptime", ""),
                        enroute_time=flight_dict.get("enroute_time", ""),
                        fuel_time=flight_dict.get("fuel_time", ""),
                        remarks=flight_dict.get("remarks", "")
                    )
                    
                    # Store to database
                    session.add(flight)
                    processed_count += 1
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process flight {flight_dict.get('callsign', 'unknown')}: {e}")
                    continue
            
            # Commit all flights
            if processed_count > 0:
                session.commit()
        
        return processed_count
    
    async def _process_controllers(self, controllers_data: List[Dict[str, Any]]) -> int:
        """
        Process and store controller data.
        
        Args:
            controllers_data: Raw controller data from VATSIM API
            
        Returns:
            int: Number of controllers processed and stored
        """
        if not controllers_data:
            return 0
        
        processed_count = 0
        
        # Get database session
        async with get_database_session() as session:
            for controller_dict in controllers_data:
                try:
                    # Insert new controller (allow duplicates)
                    session.execute(
                        text("""
                            INSERT INTO controllers (
                                callsign, frequency, cid, name, rating, facility, 
                                visual_range, text_atis, server, last_updated, logon_time
                            ) VALUES (
                                :callsign, :frequency, :cid, :name, :rating, :facility,
                                :visual_range, :text_atis, :server, :last_updated, :logon_time
                            )
                        """),
                        {
                            "callsign": controller_dict.get("callsign", ""),
                            "frequency": controller_dict.get("frequency", ""),
                            "cid": controller_dict.get("cid"),
                            "name": controller_dict.get("name", ""),
                            "rating": controller_dict.get("rating"),
                            "facility": controller_dict.get("facility"),
                            "visual_range": controller_dict.get("visual_range"),
                            "text_atis": controller_dict.get("text_atis"),
                            "server": controller_dict.get("server", ""),
                            "last_updated": controller_dict.get("last_updated"),
                            "logon_time": controller_dict.get("logon_time")
                        }
                    )
                    
                    processed_count += 1
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process controller {controller_dict.get('callsign', 'unknown')}: {e}")
                    continue
            
            # Commit all controllers
            if processed_count > 0:
                session.commit()
        
        return processed_count
    
    async def _process_transceivers(self, transceivers_data: List[Dict[str, Any]]) -> int:
        """
        Process and store transceiver data.
        
        Args:
            transceivers_data: Raw transceiver data from VATSIM API
            
        Returns:
            int: Number of transceivers processed and stored
        """
        if not transceivers_data:
            return 0
        
        processed_count = 0
        
        # Get database session
        async with get_database_session() as session:
            for transceiver_dict in transceivers_data:
                try:
                    # Create transceiver model
                    transceiver = Transceiver(
                        callsign=transceiver_dict.get("callsign", ""),
                        transceiver_id=transceiver_dict.get("transceiver_id", 0),
                        frequency=transceiver_dict.get("frequency", 0),
                        position_lat=transceiver_dict.get("position_lat"),
                        position_lon=transceiver_dict.get("position_lon"),
                        height_msl=transceiver_dict.get("height_msl"),
                        height_agl=transceiver_dict.get("height_agl"),
                        entity_type=transceiver_dict.get("entity_type", ""),
                        entity_id=transceiver_dict.get("entity_id"),
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    # Store to database
                    session.add(transceiver)
                    processed_count += 1
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process transceiver for {transceiver_dict.get('callsign', 'unknown')}: {e}")
                    continue
            
            # Commit all transceivers
            if processed_count > 0:
                session.commit()
        
        return processed_count
    
    # async def _update_vatsim_status(self, vatsim_data: Dict[str, Any]): # This method is removed
    #     """ # This method is removed
    #     Update VATSIM network status information. # This method is removed
    #     # This method is removed
    #     Args: # This method is removed
    #         vatsim_data: Current VATSIM data # This method is removed
    #     """ # This method is removed
    #     try: # This method is removed
    #         # Create or update status record # This method is removed
    #         status = VatsimStatus( # This method is removed
    #             timestamp=datetime.now(timezone.utc), # This method is removed
    #             total_controllers=vatsim_data.get("total_controllers", 0), # This method is removed
    #             total_flights=vatsim_data.get("total_flights", 0), # This method is removed
    #             total_sectors=vatsim_data.get("total_sectors", 0), # This method is removed
    #             total_transceivers=vatsim_data.get("total_transceivers", 0), # This method is removed
    #             api_status="healthy" # This method is removed
    #         ) # This method is removed
    #         # This method is removed
    #         self.db_session.add(status) # This method is removed
    #         await self.db_session.commit() # This method is removed
    #         # This method is removed
    #     except Exception as e: # This method is removed
    #         self.logger.error(f"Failed to update VATSIM status: {e}") # This method is removed
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics."""
        return self.processing_stats.copy()
    
    def get_filter_status(self) -> Dict[str, Any]:
        """Get current filter status and configuration."""
        return {
            "geographic_boundary_filter": {
                "enabled": self.geographic_boundary_filter.config.enabled,
                "initialized": self.geographic_boundary_filter.is_initialized,
                "performance": self.geographic_boundary_filter.get_filter_stats()
            }
        }


# Global service instance
_data_service: Optional[DataService] = None


async def get_data_service() -> DataService:
    """
    Get the global data service instance.
    
    Returns:
        DataService: The global data service instance
    """
    global _data_service
    if _data_service is None:
        _data_service = DataService()
        await _data_service.initialize()
    return _data_service 
