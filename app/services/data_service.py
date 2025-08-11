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
from ..filters.flight_filter import FlightFilter
from ..filters.geographic_boundary_filter import GeographicBoundaryFilter
from ..config_package.vatsim import VATSIMConfig
from ..database import get_database_session
from ..models import Flight, Controller, Transceiver

class DataService:
    """Data service for processing and storing VATSIM data"""
    
    def __init__(self):
        self.service_name = "data_service"
        self.logger = get_logger_for_module(f"services.{self.service_name}")
        self._initialized = False
        
        # Initialize configuration
        self.vatsim_config = VATSIMConfig.load_from_env()
        
        # Initialize VATSIM service
        self.vatsim_service = VATSIMService()
        
        # Initialize both filters independently
        self.flight_filter = FlightFilter()
        self.geographic_boundary_filter = GeographicBoundaryFilter()
        
        # Get intervals from configuration system
        self.vatsim_polling_interval = self.vatsim_config.polling_interval
        # Use the configured write interval from docker-compose.yml (30 seconds)
        self.vatsim_write_interval = self.vatsim_config.write_interval
        
        # Log the configured intervals and filter status
        self.logger.info(f"Data service configured with polling interval: {self.vatsim_polling_interval}s, write interval: {self.vatsim_write_interval}s")
        self.logger.info(f"Flight filters initialized - Airport filter: {self.flight_filter.config.enabled}, Geographic filter: {self.geographic_boundary_filter.config.enabled}")
        
        # Simple memory buffer for batching writes
        self.memory_buffer = {
            'flights': [],
            'atc_positions': [],
            'transceivers': [],
            'last_write': 0,
            'write_interval': self.vatsim_write_interval
        }
        self.write_count = 0
    
    async def initialize(self) -> bool:
        """Initialize data service with dependencies."""
        try:
            # Initialize VATSIM service
            await self.vatsim_service.initialize()
            
            self.logger.info("Data service initialized successfully")
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
            # Check VATSIM service
            vatsim_health = await self.vatsim_service.health_check()
            
            # Check memory buffer status
            buffer_status = {
                'flights_count': len(self.memory_buffer['flights']),
                'atc_positions_count': len(self.memory_buffer['atc_positions']),
                'transceivers_count': len(self.memory_buffer['transceivers']),
                'memory_buffer_size': sum([
                    len(self.memory_buffer['flights']),
                    len(self.memory_buffer['atc_positions']),
                    len(self.memory_buffer['transceivers'])
                ]),
                'write_interval': self.memory_buffer['write_interval']
            }
            
            return {
                'vatsim_service': vatsim_health,
                'buffer_status': buffer_status,
                'write_count': self.write_count
            }
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {'error': str(e)}
    
    async def cleanup(self):
        """Cleanup data service resources."""
        # Clear memory buffer
        self.memory_buffer['flights'].clear()
        self.memory_buffer['atc_positions'].clear()
        self.memory_buffer['transceivers'].clear()
        
        self.logger.info("Data service cleanup completed")
    
    async def start_data_ingestion(self):
        """Start the data ingestion process with SSD wear optimization"""
        self.logger.info("Starting data ingestion process with SSD wear optimization")
        
        try:
            # Fetch VATSIM data
            self.logger.info("Fetching VATSIM data...")
            vatsim_data = await self.vatsim_service.get_current_data()
            
            if vatsim_data:
                self.logger.info(f"Received VATSIM data: {len(vatsim_data.flights) if hasattr(vatsim_data, 'flights') else 0} flights, {len(vatsim_data.controllers) if hasattr(vatsim_data, 'controllers') else 0} controllers")
                
                # Process data in memory first
                await self._process_data_in_memory(vatsim_data)
                
                # Only write to disk periodically to reduce SSD wear
                current_time = time.time()
                if current_time - self.memory_buffer['last_write'] >= self.memory_buffer['write_interval']:
                    self.logger.info("Flushing memory buffer to disk...")
                    await self._flush_memory_to_disk()
                    self.memory_buffer['last_write'] = current_time
                    self.logger.info(f"Flushed memory buffer to disk. Write count: {self.write_count}")
                else:
                    self.logger.debug(f"Buffer write interval not reached yet. Next write in {self.memory_buffer['write_interval'] - (current_time - self.memory_buffer['last_write']):.1f}s")
                
                self.logger.info("Data ingestion cycle completed successfully")
                return True
            else:
                self.logger.warning("No VATSIM data received")
                return False
                
        except Exception as e:
            self.logger.error(f"Error in data ingestion: {e}")
            return False
    
    async def _process_data_in_memory(self, vatsim_data):
        """Process VATSIM data in memory buffer"""
        try:
            # Process ATC positions directly from VATSIM dataclass objects
            if hasattr(vatsim_data, 'controllers'):
                atc_positions_count = await self._process_atc_positions_in_memory(vatsim_data.controllers)
            else:
                atc_positions_count = 0
                
            # Process flights directly from VATSIM dataclass objects
            if hasattr(vatsim_data, 'flights'):
                flights_count = await self._process_flights_in_memory(vatsim_data.flights)
            else:
                flights_count = 0
            
            # Sectors removed - VATSIM API v3 doesn't provide sectors data
            
            # Process transceivers directly from VATSIM dataclass objects
            if hasattr(vatsim_data, 'transceivers'):
                transceivers_count = await self._process_transceivers_in_memory(vatsim_data.transceivers)
            else:
                transceivers_count = 0
            
            self.logger.info(f"Processed {flights_count} flights, {atc_positions_count} ATC positions, {transceivers_count} transceivers")
            
        except Exception as e:
            self.logger.error(f"Error processing data in memory: {e}")
    
    async def _process_atc_positions_in_memory(self, atc_positions_data) -> int:
        """Process ATC positions in memory buffer - EXACT API field mapping from VATSIM dataclass"""
        try:
            processed_count = 0
            
            for controller_data in atc_positions_data:
                try:
                    # Convert dataclass to dict for processing
                    controller_dict = {
                        'callsign': controller_data.callsign,
                        'cid': controller_data.cid,
                        'name': controller_data.name,
                        'facility': controller_data.facility,
                        'rating': controller_data.rating,
                        'server': controller_data.server,
                        'visual_range': controller_data.visual_range,
                        'text_atis': controller_data.text_atis,
                        'logon_time': controller_data.logon_time,
                        'last_updated': controller_data.last_updated
                    }
                    
                    # Validate controller data
                    if self._validate_controller_data(controller_dict):
                        # Apply filters if enabled
                        if self.flight_filter.config.enabled:
                            # ATC positions are not filtered by flight filters
                            pass
                        
                        # Add to memory buffer
                        self.memory_buffer['atc_positions'].append(controller_dict)
                        processed_count += 1
                    else:
                        self.logger.warning(f"Invalid controller data for {controller_dict.get('callsign', 'unknown')}")
                        
                except Exception as e:
                    self.logger.error(f"Error processing controller {getattr(controller_data, 'callsign', 'unknown')}: {e}")
                    continue
            
            self.logger.info(f"Processed {processed_count} ATC positions into memory buffer")
            return processed_count
            
        except Exception as e:
            self.logger.error(f"Error processing ATC positions in memory: {e}")
            return 0
    
    def _validate_controller_data(self, controller_data: Dict[str, Any]) -> bool:
        """Validate controller data before processing"""
        try:
            required_fields = ['callsign', 'cid', 'facility']
            
            for field in required_fields:
                if not controller_data.get(field):
                    return False
            
            # Convert controller_id to integer
            if controller_data.get('cid'):
                controller_data['cid'] = int(controller_data['cid'])
            
            # Convert rating to integer
            if controller_data.get('rating'):
                controller_data['rating'] = int(controller_data['rating'])
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating controller data: {e}")
            return False
    
    async def _process_flights_in_memory(self, flights_data) -> int:
        """Process flights in memory buffer - EXACT API field mapping from VATSIM dataclass"""
        try:
            processed_count = 0
            
            for flight_data in flights_data:
                try:
                    # Convert dataclass to dict for processing
                    flight_dict = {
                        'callsign': flight_data.callsign,
                        'cid': flight_data.cid,
                        'name': flight_data.name,
                        'server': flight_data.server,
                        'pilot_rating': flight_data.pilot_rating,
                        'military_rating': flight_data.military_rating,
                        'latitude': flight_data.latitude,
                        'longitude': flight_data.longitude,
                        'altitude': flight_data.altitude,
                        'groundspeed': flight_data.groundspeed,
                        'transponder': flight_data.transponder,
                        'heading': flight_data.heading,
                        'qnh_i_hg': flight_data.qnh_i_hg,
                        'qnh_mb': flight_data.qnh_mb,
                        'logon_time': flight_data.logon_time,
                        'last_updated': flight_data.last_updated,
                        'departure': flight_data.departure,
                        'arrival': flight_data.arrival,
                        'route': flight_data.route,
                        'aircraft_type': flight_data.aircraft_type,
                        'flight_rules': flight_data.flight_rules,
                        'aircraft_faa': flight_data.aircraft_faa,
                        'aircraft_short': flight_data.aircraft_short,
                        'alternate': flight_data.alternate,
                        'cruise_tas': flight_data.cruise_tas,
                        'planned_altitude': flight_data.planned_altitude,
                        'deptime': flight_data.deptime,
                        'enroute_time': flight_data.enroute_time,
                        'fuel_time': flight_data.fuel_time,
                        'remarks': flight_data.remarks,
                        'revision_id': flight_data.revision_id,
                        'assigned_transponder': flight_data.assigned_transponder
                    }
                    
                    # Apply flight filters if enabled
                    if self.flight_filter.config.enabled:
                        if not self.flight_filter.filter_flights_list([flight_dict]):
                            continue  # Skip filtered flights
                    
                    # Apply geographic boundary filter if enabled
                    if self.geographic_boundary_filter.config.enabled:
                        if not self.geographic_boundary_filter.filter_flights_list([flight_dict]):
                            continue  # Skip filtered flights
                    
                    # Add to memory buffer
                    self.memory_buffer['flights'].append(flight_dict)
                    processed_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing flight {getattr(flight_data, 'callsign', 'unknown')}: {e}")
                    continue
            
            self.logger.info(f"Processed {processed_count} flights into memory buffer")
            return processed_count
            
        except Exception as e:
            self.logger.error(f"Error processing flights in memory: {e}")
            return 0
    
    async def _process_transceivers_in_memory(self, transceivers_data) -> int:
        """Process transceivers in memory buffer - EXACT API field mapping from VATSIM dataclass"""
        try:
            processed_count = 0
            
            for transceiver_data in transceivers_data:
                try:
                    # Convert dataclass to dict for processing
                    transceiver_dict = {
                        'callsign': transceiver_data.callsign,
                        'frequency': transceiver_data.frequency,
                        'position_lat': transceiver_data.position_lat,
                        'position_lon': transceiver_data.position_lon,
                        'altitude': transceiver_data.altitude,
                        'last_updated': transceiver_data.last_updated
                    }
                    
                    # Add to memory buffer
                    self.memory_buffer['transceivers'].append(transceiver_dict)
                    processed_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing transceiver {getattr(transceiver_data, 'callsign', 'unknown')}: {e}")
                    continue
            
            self.logger.info(f"Processed {processed_count} transceivers into memory buffer")
            return processed_count
            
        except Exception as e:
            self.logger.error(f"Error processing transceivers in memory: {e}")
            return 0
    
    async def _flush_memory_to_disk(self):
        """Flush memory buffer to database"""
        try:
            async with get_database_session() as session:
                # Process flights
                if self.memory_buffer['flights']:
                    for flight_data in self.memory_buffer['flights']:
                        try:
                            # Create flight object
                            flight = Flight(**flight_data)
                            session.add(flight)
                        except Exception as e:
                            self.logger.error(f"Error adding flight {flight_data.get('callsign', 'unknown')}: {e}")
                            continue
                    
                    self.logger.info(f"Added {len(self.memory_buffer['flights'])} flights to database")
                    self.memory_buffer['flights'].clear()
                
                # Process ATC positions
                if self.memory_buffer['atc_positions']:
                    for atc_data in self.memory_buffer['atc_positions']:
                        try:
                            # Create controller object
                            controller = Controller(**atc_data)
                            session.add(controller)
                        except Exception as e:
                            self.logger.error(f"Error adding controller {atc_data.get('callsign', 'unknown')}: {e}")
                            continue
                    
                    self.logger.info(f"Added {len(self.memory_buffer['atc_positions'])} controllers to database")
                    self.memory_buffer['atc_positions'].clear()
                
                # Process transceivers
                if self.memory_buffer['transceivers']:
                    for transceiver_data in self.memory_buffer['transceivers']:
                        try:
                            # Create transceiver object
                            transceiver = Transceiver(**transceiver_data)
                            session.add(transceiver)
                        except Exception as e:
                            self.logger.error(f"Error adding transceiver {transceiver_data.get('callsign', 'unknown')}: {e}")
                            continue
                    
                    self.logger.info(f"Added {len(self.memory_buffer['transceivers'])} transceivers to database")
                    self.memory_buffer['transceivers'].clear()
                
                # Commit all changes
                await session.commit()
                self.write_count += 1
                
                self.logger.info("Successfully flushed memory buffer to database")
                
        except Exception as e:
            self.logger.error(f"Error flushing memory buffer to database: {e}")
    
    async def get_network_status(self) -> Dict[str, Any]:
        """Get current network status and statistics"""
        try:
            # Get current VATSIM data for status
            vatsim_data = await self.vatsim_service.get_current_data()
            
            if not vatsim_data:
                return {
                    "status": "no_data",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": "No VATSIM data available"
                }
            
            # Extract status information
            status_info = {
                "status": "operational",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data_freshness": "real-time",
                "statistics": {
                    "flights_count": len(vatsim_data.flights) if hasattr(vatsim_data, 'flights') else 0,
                    "controllers_count": len(vatsim_data.controllers) if hasattr(vatsim_data, 'controllers') else 0,
                    "transceivers_count": len(vatsim_data.transceivers) if hasattr(vatsim_data, 'transceivers') else 0
                },
                "data_ingestion": {
                    "last_vatsim_update": vatsim_data.update_timestamp if hasattr(vatsim_data, 'update_timestamp') else "unknown",
                    "update_interval_seconds": self.vatsim_polling_interval,
                    "write_interval_seconds": self.vatsim_write_interval
                }
            }
            
            return status_info
            
        except Exception as e:
            self.logger.error(f"Error getting network status: {e}")
            return {
                "status": "error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }

async def get_data_service() -> DataService:
    """Get or create data service instance"""
    return DataService() 
