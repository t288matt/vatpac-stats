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
- System status information
"""

import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from ..utils.logging import get_logger_for_module
from ..utils.error_handling import handle_service_errors, log_operation
from ..services.vatsim_service import VATSIMService
from ..filters.geographic_boundary_filter import GeographicBoundaryFilter
from ..filters.callsign_pattern_filter import CallsignPatternFilter
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
        self.callsign_pattern_filter = CallsignPatternFilter()
        
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
            self.logger.info(f"Callsign pattern filter initialized: {self.callsign_pattern_filter.config.enabled}")
            self._initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize data service: {e}")
            return False
    
    def is_initialized(self) -> bool:
        """Check if service is properly initialized."""
        return self._initialized
    
    async def cleanup(self):
        """Cleanup data service resources."""
        try:
            if self.vatsim_service:
                await self.vatsim_service.cleanup()
            self.logger.info("Data service cleanup completed")
        except Exception as e:
            self.logger.error(f"Data service cleanup failed: {e}")

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
        
        # Apply geographic boundary filtering first (if enabled)
        if self.geographic_boundary_filter.config.enabled:
            filtered_flights = self.geographic_boundary_filter.filter_flights_list(flights_data)
            self.logger.info(f"Geographic filtering: {len(flights_data)} flights -> {len(filtered_flights)} flights")
        else:
            filtered_flights = flights_data
        
        # Get database session
        async with get_database_session() as session:
            if filtered_flights:
                try:
                    # Prepare bulk data
                    bulk_flights = []
                    
                    for flight_dict in filtered_flights:
                        try:
                            # Create data dictionary for bulk insert
                            flight_data = {
                                "callsign": flight_dict.get("callsign", ""),
                                "name": flight_dict.get("name", ""),
                                "aircraft_type": flight_dict.get("aircraft_type", ""),
                                "departure": flight_dict.get("departure", ""),
                                "arrival": flight_dict.get("arrival", ""),
                                "route": flight_dict.get("route", ""),
                                "altitude": flight_dict.get("altitude", 0),
                                "latitude": flight_dict.get("latitude"),
                                "longitude": flight_dict.get("longitude"),
                                "groundspeed": flight_dict.get("groundspeed"),
                                "heading": flight_dict.get("heading"),
                                "cid": flight_dict.get("cid"),
                                "server": flight_dict.get("server", ""),
                                "pilot_rating": flight_dict.get("pilot_rating"),
                                "military_rating": flight_dict.get("military_rating"),
                                "transponder": flight_dict.get("transponder", ""),
                                "logon_time": flight_dict.get("logon_time"),
                                "last_updated_api": flight_dict.get("last_updated"),
                                "flight_rules": flight_dict.get("flight_rules", ""),
                                "aircraft_faa": flight_dict.get("aircraft_faa", ""),
                                "alternate": flight_dict.get("alternate", ""),
                                "cruise_tas": flight_dict.get("cruise_tas", ""),
                                "planned_altitude": flight_dict.get("planned_altitude", ""),
                                "deptime": flight_dict.get("deptime", ""),
                                "enroute_time": flight_dict.get("enroute_time", ""),
                                "fuel_time": flight_dict.get("fuel_time", ""),
                                "remarks": flight_dict.get("remarks", "")
                            }
                            bulk_flights.append(flight_data)
                            
                        except Exception as e:
                            self.logger.warning(f"Failed to prepare flight data for {flight_dict.get('callsign', 'unknown')}: {e}")
                            continue
                    
                    # Bulk insert all flights
                    if bulk_flights:
                        session.bulk_insert_mappings(Flight, bulk_flights)
                        await session.commit()
                        processed_count = len(bulk_flights)
                        self.logger.info(f"Bulk inserted {processed_count} flights")
                    
                except Exception as e:
                    self.logger.error(f"Failed to bulk insert flights: {e}")
                    await session.rollback()
                    raise
        
        return processed_count
    
    async def _process_controllers(self, controllers_data: List[Dict[str, Any]]) -> int:
        """
        Process and store controller data with geographic boundary filtering.
        
        Args:
            controllers_data: Raw controller data from VATSIM API
            
        Returns:
            int: Number of controllers processed and stored
        """
        if not controllers_data:
            return 0
        
        processed_count = 0
        
        # Apply geographic boundary filtering
        if self.geographic_boundary_filter.config.enabled:
            filtered_controllers = self.geographic_boundary_filter.filter_controllers_list(controllers_data)
            self.logger.info(f"Geographic filtering: {len(controllers_data)} controllers -> {len(filtered_controllers)} controllers")
        else:
            filtered_controllers = controllers_data
        
        # Get database session
        async with get_database_session() as session:
            if filtered_controllers:
                try:
                    # Prepare bulk data
                    bulk_controllers = []
                    
                    for controller_dict in filtered_controllers:
                        try:
                            # Create data dictionary for bulk insert
                            controller_data = {
                                "callsign": controller_dict.get("callsign", ""),
                                "frequency": controller_dict.get("frequency", ""),
                                "cid": controller_dict.get("cid"),
                                "name": controller_dict.get("name", ""),
                                "rating": controller_dict.get("rating"),
                                "facility": controller_dict.get("facility"),
                                "visual_range": controller_dict.get("visual_range"),
                                "text_atis": self._convert_text_atis(controller_dict.get("text_atis")),
                                "server": controller_dict.get("server", ""),
                                "last_updated": self._parse_timestamp(controller_dict.get("last_updated")),
                                "logon_time": self._parse_timestamp(controller_dict.get("logon_time"))
                            }
                            bulk_controllers.append(controller_data)
                            
                        except Exception as e:
                            self.logger.warning(f"Failed to prepare controller data for {controller_dict.get('callsign', 'unknown')}: {e}")
                            continue
                    
                    # Bulk insert all controllers
                    if bulk_controllers:
                        session.bulk_insert_mappings(Controller, bulk_controllers)
                        await session.commit()
                        processed_count = len(bulk_controllers)
                        self.logger.info(f"Bulk inserted {processed_count} controllers")
                    
                except Exception as e:
                    self.logger.error(f"Failed to bulk insert controllers: {e}")
                    await session.rollback()
                    raise
        
        return processed_count
    
    def _convert_text_atis(self, text_atis_data: Any) -> Optional[str]:
        """Convert text_atis data to string format - simplified"""
        if text_atis_data is None:
            return None
        return str(text_atis_data) if not isinstance(text_atis_data, str) else text_atis_data
    
    def _parse_timestamp(self, timestamp_str: Optional[Any]) -> Optional[datetime]:
        """Parse timestamp string to datetime object - optimized for bulk operations"""
        if not timestamp_str:
            return None
        
        if isinstance(timestamp_str, datetime):
            return timestamp_str
        
        if isinstance(timestamp_str, str):
            try:
                # Remove 'Z' suffix and parse as UTC
                clean_timestamp = timestamp_str[:-1] if timestamp_str.endswith('Z') else timestamp_str
                parsed_time = datetime.fromisoformat(clean_timestamp)
                return parsed_time.replace(tzinfo=timezone.utc) if parsed_time.tzinfo is None else parsed_time
            except (ValueError, TypeError):
                return None
        
        return None
    
    async def _process_transceivers(self, transceivers_data: List[Dict[str, Any]]) -> int:
        """
        Process and store transceiver data with geographic boundary filtering.
        
        Args:
            transceivers_data: Raw transceiver data from VATSIM API
            
        Returns:
            int: Number of transceivers processed and stored
        """
        if not transceivers_data:
            return 0
        
        processed_count = 0
        
        # Apply callsign pattern filtering first (always enabled)
        filtered_transceivers = self.callsign_pattern_filter.filter_transceivers_list(transceivers_data)
        self.logger.info(f"Callsign pattern filtering: {len(transceivers_data)} transceivers -> {len(filtered_transceivers)} transceivers")
        
        # Apply geographic boundary filtering
        if self.geographic_boundary_filter.config.enabled:
            filtered_transceivers = self.geographic_boundary_filter.filter_transceivers_list(filtered_transceivers)
            self.logger.info(f"Geographic filtering: {len(filtered_transceivers)} transceivers -> {len(filtered_transceivers)} transceivers")
        
        # Get database session
        async with get_database_session() as session:
            if filtered_transceivers:
                try:
                    # Prepare bulk data with current timestamp
                    current_time = datetime.now(timezone.utc)
                    bulk_transceivers = []
                    
                    for transceiver_dict in filtered_transceivers:
                        try:
                            # Create data dictionary for bulk insert
                            transceiver_data = {
                                "callsign": transceiver_dict.get("callsign", ""),
                                "transceiver_id": transceiver_dict.get("transceiver_id", 0),
                                "frequency": transceiver_dict.get("frequency", 0),
                                "position_lat": transceiver_dict.get("position_lat"),
                                "position_lon": transceiver_dict.get("position_lon"),
                                "height_msl": transceiver_dict.get("height_msl"),
                                "height_agl": transceiver_dict.get("height_agl"),
                                "entity_type": transceiver_dict.get("entity_type", ""),
                                "entity_id": transceiver_dict.get("entity_id"),
                                "timestamp": current_time,
                                "updated_at": current_time
                            }
                            bulk_transceivers.append(transceiver_data)
                            
                        except Exception as e:
                            self.logger.warning(f"Failed to prepare transceiver data for {transceiver_dict.get('callsign', 'unknown')}: {e}")
                            continue
                    
                    # Bulk insert all transceivers
                    if bulk_transceivers:
                        session.bulk_insert_mappings(Transceiver, bulk_transceivers)
                        await session.commit()
                        processed_count = len(bulk_transceivers)
                        self.logger.info(f"Bulk inserted {processed_count} transceivers")
                    
                except Exception as e:
                    self.logger.error(f"Failed to bulk insert transceivers: {e}")
                    await session.rollback()
                    raise
        
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
        """Get data processing statistics - simplified"""
        return {
            "flights_processed": self.processing_stats.get("total_flights_processed", 0),
            "controllers_processed": self.processing_stats.get("total_controllers_processed", 0),
            "transceivers_processed": self.processing_stats.get("total_transceivers_processed", 0),
            "last_processing_time": self.processing_stats.get("last_processing_time", 0)
        }
    
    def get_filter_status(self) -> Dict[str, Any]:
        """Get filter status information."""
        return {
            "geographic_boundary_filter": {
                "enabled": self.geographic_boundary_filter.config.enabled,
                "initialized": self.geographic_boundary_filter.is_initialized
            },
            "callsign_pattern_filter": {
                "enabled": self.callsign_pattern_filter.config.enabled,
                "patterns": self.callsign_pattern_filter.config.excluded_patterns
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
