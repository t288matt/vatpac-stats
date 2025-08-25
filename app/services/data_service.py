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
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta, date
import json

from app.utils.logging import get_logger_for_module
from app.utils.error_handling import handle_service_errors, log_operation, fail_fast_on_critical_errors
from app.services.vatsim_service import VATSIMService
from app.filters.geographic_boundary_filter import GeographicBoundaryFilter
from app.filters.callsign_pattern_filter import CallsignPatternFilter
from app.filters.controller_callsign_filter import ControllerCallsignFilter
from app.database import get_database_session
from app.models import Flight, Controller, Transceiver
from app.config import get_config, AppConfig
from app.services.atc_detection_service import ATCDetectionService
from app.services.flight_detection_service import FlightDetectionService
from app.utils.sector_loader import SectorLoader
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger_for_module("services.data_service")


class DataService:
    """Main data service for VATSIM data collection and processing."""
    
    def __init__(self):
        """Initialize the data service."""
        self.logger = logger
        self.config = get_config()
        self._initialized = False
        
        # Initialize filters
        self.geographic_boundary_filter = GeographicBoundaryFilter()
        self.callsign_pattern_filter = CallsignPatternFilter()
        self.controller_callsign_filter = ControllerCallsignFilter()
        
        # Initialize services
        self.vatsim_service = None
        self.db_session = None
        
        # Initialize ATC detection service
        self.atc_detection_service = ATCDetectionService()
        
        # Initialize Flight detection service for controller summaries
        self.flight_detection_service = FlightDetectionService()
        
        # NEW: Initialize sector tracking
        self.sector_tracking_enabled = self.config.sector_tracking.enabled
        self.sector_update_interval = self.config.sector_tracking.update_interval
        self.sector_loader = None  # Will be initialized in initialize() method
        self.flight_sector_states = {}  # Track current sector for each flight
        
        # Debug logging for sector tracking configuration
        self.logger.info(f"Sector tracking config: enabled={self.sector_tracking_enabled}, update_interval={self.sector_update_interval}")
        self.logger.info(f"Sector file path: {self.config.sector_tracking.sectors_file_path}")
        
        # Performance tracking - simplified
        self.stats = {
            "flights": 0,
            "controllers": 0,
            "transceivers": 0,
            "last_run": None
        }
        
        # Task tracking for scheduled processing
        self.flight_summary_task: Optional[asyncio.Task] = None
        self.controller_summary_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> bool:
        """Initialize data service with dependencies."""
        try:
            # Initialize VATSIM service
            self.vatsim_service = VATSIMService()
            await self.vatsim_service.initialize()
            
            # Geographic boundary filter is already initialized in its constructor
            # No need to call initialize() on it
            
            # NEW: Initialize sector tracking
            if self.sector_tracking_enabled:
                self.sector_loader = SectorLoader(self.config.sector_tracking.sectors_file_path)
                # Critical: If sectors can't be loaded, the app must fail
                sector_loaded = self.sector_loader.load_sectors()
                if not sector_loaded:
                    # This should never happen now since load_sectors() raises exceptions on failure
                    error_msg = "CRITICAL: Sector loading failed but no exception was raised - this indicates a bug"
                    self.logger.critical(error_msg)
                    raise RuntimeError(error_msg)
                self.logger.info(f"Sector tracking initialized with {self.sector_loader.get_sector_count()} sectors")
            
            # Don't get database session here - we'll get it when needed
            self.db_session = None
            
            self.logger.info(f"Filters: geo={self.geographic_boundary_filter.config.enabled}, callsign={self.callsign_pattern_filter.config.enabled}, controller_callsign={self.controller_callsign_filter.config.enabled}, sector={self.sector_tracking_enabled}")
            self._initialized = True
            
            # Start scheduled flight summary processing
            await self.start_scheduled_flight_processing()
            
            # Start scheduled controller summary processing
            if self.config.controller_summary.enabled:
                await self.start_scheduled_controller_processing()
            
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
    @fail_fast_on_critical_errors
    async def process_vatsim_data(self) -> Dict[str, Any]:
        """
        Process VATSIM data and store to database.
        
        Returns:
            Dict[str, Any]: Processing results and statistics
        """
        if not self._initialized and not getattr(self, '_test_mode', False):
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
            self.stats.update({
                "flights": self.stats["flights"] + flights_processed,
                "controllers": self.stats["controllers"] + controllers_processed,
                "transceivers": self.stats["transceivers"] + transceivers_processed,
                "last_run": datetime.now(timezone.utc)
            })
            
            # NEW: Cleanup sector states periodically
            if hasattr(self, 'sector_tracking_enabled') and self.sector_tracking_enabled:
                await self._cleanup_sector_states()
            
            # Log summary only when there's significant activity or filtering
            total_processed = flights_processed + controllers_processed + transceivers_processed
            if total_processed > 0:
                self.logger.info(f"VATSIM data processed: {flights_processed} flights, {controllers_processed} controllers, {transceivers_processed} transceivers in {processing_time:.2f}s")
            else:
                self.logger.debug(f"VATSIM data processed: {flights_processed} flights, {controllers_processed} controllers, {transceivers_processed} transceivers in {processing_time:.2f}s")
            
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
        Process and store flight data with geographic boundary filtering and incomplete flight filtering.
        
        This method applies two levels of filtering:
        1. Geographic boundary filtering (if enabled)
        2. Flight plan completeness filtering (departure and arrival must be populated)
        
        Args:
            flights_data: Raw flight data from VATSIM API
            
        Returns:
            int: Number of flights processed and stored
        """
        if not flights_data:
            return 0
        
        processed_count = 0
        
        # Apply geographic boundary filtering (if enabled)
        if self.geographic_boundary_filter.config.enabled:
            filtered_flights = self.geographic_boundary_filter.filter_flights_list(flights_data)
        else:
            filtered_flights = flights_data
        
        # Log filtering results
        if len(flights_data) != len(filtered_flights):
            self.logger.info(f"Flights: {len(flights_data)} → {len(filtered_flights)} (geographically filtered)")
        
        # Get database session
        async with get_database_session() as session:
            if filtered_flights:
                try:
                    # Prepare bulk data
                    bulk_flights = []
                    incomplete_flights_count = 0
                    
                    for flight_dict in filtered_flights:
                        try:
                            # NEW: Filter incomplete flights before processing
                            departure = flight_dict.get("departure", "")
                            arrival = flight_dict.get("arrival", "")
                            
                            # Skip flights without complete flight plan data
                            if not departure or not arrival:
                                incomplete_flights_count += 1
                                self.logger.debug(f"Skipping incomplete flight {flight_dict.get('callsign', 'unknown')}: departure='{departure}', arrival='{arrival}'")
                                continue
                            
                            # Create data dictionary for bulk insert
                            flight_data = {
                                "callsign": flight_dict.get("callsign", ""),
                                "name": flight_dict.get("name", ""),
                                "aircraft_type": flight_dict.get("aircraft_type", ""),
                                "departure": departure,  # Already validated above
                                "arrival": arrival,      # Already validated above
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
                            
                            # NEW: Track sector occupancy for this flight
                            await self._track_sector_occupancy(flight_dict, session)
                            
                        except Exception as e:
                            self.logger.warning(f"Failed to prepare flight data for {flight_dict.get('callsign', 'unknown')}: {e}")
                            continue
                    
                    # Log incomplete flight filtering results
                    if incomplete_flights_count > 0:
                        self.logger.info(f"Flights: {len(filtered_flights)} → {len(bulk_flights)} (incomplete flights filtered: {incomplete_flights_count})")
                    
                    # Bulk insert all flights
                    if bulk_flights:
                        session.add_all([Flight(**flight_data) for flight_data in bulk_flights])
                        await session.commit()
                        processed_count = len(bulk_flights)
                        self.logger.debug(f"Bulk inserted {processed_count} flights")
                    
                except Exception as e:
                    self.logger.error(f"Failed to bulk insert flights: {e}")
                    await session.rollback()
                    raise
        
        return processed_count


    
    @fail_fast_on_critical_errors
    async def _process_controllers(self, controllers_data: List[Dict[str, Any]]) -> int:
        """
        Process and store controller data with callsign filtering.
        
        Args:
            controllers_data: Raw controller data from VATSIM API
            
        Returns:
            int: Number of controllers processed and stored
        """
        if not controllers_data:
            return 0
        
        processed_count = 0
        
        # Apply controller callsign filtering (controllers don't have geographic data)
        if self.controller_callsign_filter.config.enabled:
            filtered_controllers = self.controller_callsign_filter.filter_controllers_list(controllers_data)
        else:
            filtered_controllers = controllers_data
        
        # Log only summary, not individual controller details
        if len(controllers_data) != len(filtered_controllers):
            self.logger.info(f"Controllers: {len(controllers_data)} → {len(filtered_controllers)} (callsign filtered)")
        else:
            self.logger.debug(f"Controllers: {len(controllers_data)} → {len(filtered_controllers)}")
        
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
                        session.add_all([Controller(**controller_data) for controller_data in bulk_controllers])
                        await session.commit()
                        processed_count = len(bulk_controllers)
                        self.logger.debug(f"Bulk inserted {processed_count} controllers")
                    
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
        
        # Apply geographic boundary filtering
        if self.geographic_boundary_filter.config.enabled:
            filtered_transceivers = self.geographic_boundary_filter.filter_transceivers_list(transceivers_data)
        else:
            filtered_transceivers = transceivers_data
        
        # Log only summary, not individual transceiver details
        if len(transceivers_data) != len(filtered_transceivers):
            self.logger.info(f"Transceivers: {len(transceivers_data)} → {len(filtered_transceivers)} (filtered)")
        else:
            self.logger.debug(f"Transceivers: {len(transceivers_data)} → {len(filtered_transceivers)}")
        
        # Get database session
        async with get_database_session() as session:
            if filtered_transceivers:
                try:
                    # Prepare bulk data
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
                                "entity_type": transceiver_dict.get("entity_type", "flight"),
                                "entity_id": transceiver_dict.get("entity_id"),
                                "timestamp": datetime.now(timezone.utc)
                            }
                            bulk_transceivers.append(transceiver_data)
                            
                        except Exception as e:
                            self.logger.warning(f"Failed to prepare transceiver data for {transceiver_dict.get('callsign', 'unknown')}: {e}")
                            continue
                    
                    # Bulk insert all transceivers
                    if bulk_transceivers:
                        session.add_all([Transceiver(**transceiver_data) for transceiver_data in bulk_transceivers])
                        await session.commit()
                        processed_count = len(bulk_transceivers)
                        self.logger.debug(f"Bulk inserted {processed_count} transceivers")
                    
                except Exception as e:
                    self.logger.error(f"Failed to bulk insert transceivers: {e}")
                    await session.rollback()
                    raise
        
        return processed_count
    
    # ============================================================================
    # SECTOR TRACKING METHODS
    # ============================================================================
    
    async def _track_sector_occupancy(self, flight_dict: Dict[str, Any], session: AsyncSession) -> None:
        """
        Track sector occupancy for a flight with speed-based entry/exit criteria.
        
        Entry Criteria: Aircraft must be above 60 knots (inclusive) AND within sector geographic boundary
        Exit Criteria: Aircraft must be below 30 knots for 2 consecutive VATSIM polls (60-second intervals)
        
        Args:
            flight_dict: Flight data dictionary from VATSIM API
            session: Database session for recording sector data
        """
        if not hasattr(self, 'sector_loader') or not hasattr(self, 'sector_tracking_enabled'):
            # Sector tracking not initialized, skip
            return
            
        if not self.sector_tracking_enabled:
            return
        
        callsign = flight_dict.get("callsign")
        if not callsign:
            return
        
        # Get current position and speed
        lat = flight_dict.get("latitude")
        lon = flight_dict.get("longitude")
        altitude = flight_dict.get("altitude")
        groundspeed = flight_dict.get("groundspeed")
        
        if lat is None or lon is None:
            return
        
        # Initialize flight sector states if not exists
        if not hasattr(self, 'flight_sector_states'):
            self.flight_sector_states = {}
        
        # Get current geographic sector
        geographic_sector = self.sector_loader.get_sector_for_point(lat, lon)
        

        
        # Get previous state (combined structure: sector + exit counter)
        previous_state = self.flight_sector_states.get(callsign, {})
        previous_sector = previous_state.get("current_sector") if isinstance(previous_state, dict) else previous_state
        exit_counter = previous_state.get("exit_counter", 0) if isinstance(previous_state, dict) else 0
        
        # Determine current sector based on speed criteria
        current_sector = None
        
        # Entry logic: Must be above 60 knots to enter sector
        if groundspeed is not None and groundspeed >= 60:
            current_sector = geographic_sector
        elif groundspeed is None:
            # Missing speed data - defer entry decision
            current_sector = previous_sector  # Keep previous state
        else:
            # Speed below 60 knots - not in sector
            current_sector = None
        
        # Exit logic: Track consecutive below-30kts polls
        if groundspeed is not None and groundspeed < 30:
            exit_counter += 1
        else:
            # Speed above 30 knots or missing - reset exit counter
            exit_counter = 0
        
        # Check if we should exit due to 2 consecutive below-30kts polls
        should_exit = exit_counter >= 2
        
        # Handle sector transitions
        if current_sector != previous_sector or should_exit:
            await self._handle_sector_transition(
                callsign, previous_sector, current_sector, 
                lat, lon, altitude, session, should_exit
            )
            
            # Update state with combined structure
            self.flight_sector_states[callsign] = new_state = {
                "current_sector": current_sector,
                "exit_counter": exit_counter,
                "last_speed": groundspeed
            }
            
            # Log sector transitions for debugging
            if current_sector != previous_sector:
                if current_sector:
                    self.logger.info(f"Flight {callsign} entered sector {current_sector} (speed: {groundspeed}kts)")
                else:
                    self.logger.info(f"Flight {callsign} exited sector {previous_sector} (speed: {groundspeed}kts)")
            
            if should_exit and previous_sector:
                self.logger.info(f"Flight {callsign} forced exit from sector {previous_sector} due to low speed ({groundspeed}kts, counter: {exit_counter})")
        else:
            # Update state even when no transition occurs (for new aircraft, missing speed data, etc.)
            self.flight_sector_states[callsign] = {
                "current_sector": current_sector,
                "exit_counter": exit_counter,
                "last_speed": groundspeed
            }

    async def _handle_sector_transition(
        self, callsign: str, previous_sector: Optional[str], 
        current_sector: Optional[str], lat: float, lon: float, 
        altitude: int, session: AsyncSession, should_exit: bool = False
    ) -> None:
        """
        Handle sector entry/exit transitions with speed-based criteria.
        
        Args:
            callsign: Flight callsign
            previous_sector: Sector the flight was previously in (None if none)
            current_sector: Sector the flight is currently in (None if none)
            lat: Current latitude
            lon: Current longitude
            altitude: Current altitude in feet
            session: Database session
            should_exit: Whether to force exit due to speed criteria
        """
        timestamp = datetime.now(timezone.utc)
        
        # CRITICAL FIX: Close ALL open sectors for this flight before entering a new one
        # This prevents multiple open sectors when memory state gets corrupted
        if current_sector != previous_sector or should_exit:
            await self._close_all_open_sectors_for_flight(callsign, session)
        
        # Enter new sector (only if different from previous)
        if current_sector and current_sector != previous_sector:
            await self._record_sector_entry(
                callsign, current_sector, lat, lon, altitude, timestamp, session
            )

    async def _record_sector_entry(
        self, callsign: str, sector_name: str, lat: float, lon: float, 
        altitude: int, timestamp: datetime, session: AsyncSession
    ) -> None:
        """
        Record when a flight enters a sector.
        
        Args:
            callsign: Flight callsign
            sector_name: Name of the sector being entered
            lat: Entry latitude
            lon: Entry longitude
            altitude: Entry altitude in feet
            timestamp: Entry timestamp
            session: Database session
        """
        try:
            # Check if there's an open entry record for this flight/sector combination
            existing_entry = await session.execute(text("""
                SELECT id FROM flight_sector_occupancy 
                WHERE callsign = :callsign 
                AND sector_name = :sector_name 
                AND exit_timestamp IS NULL
            """), {"callsign": callsign, "sector_name": sector_name})
            
            if not existing_entry.fetchone():
                # Insert the entry record immediately with exit fields as NULL
                await session.execute(text("""
                    INSERT INTO flight_sector_occupancy (
                        callsign, sector_name, entry_timestamp, exit_timestamp,
                        duration_seconds, entry_lat, entry_lon, exit_lat, exit_lon,
                        entry_altitude, exit_altitude
                    ) VALUES (
                        :callsign, :sector_name, :timestamp, NULL, 0,
                        :lat, :lon, NULL, NULL, :altitude, NULL
                    )
                """), {
                    "callsign": callsign, "sector_name": sector_name,
                    "timestamp": timestamp, "lat": lat, "lon": lon, "altitude": altitude
                })
                
                self.logger.debug(f"Flight {callsign} entered sector {sector_name}")
    
        except Exception as e:
            self.logger.error(f"Failed to record sector entry for {callsign}: {e}")

    async def _close_all_open_sectors_for_flight(
        self, callsign: str, session: AsyncSession
    ) -> None:
        """
        Close ALL open sectors for a flight to prevent multiple open sectors.
        
        This is a critical fix that ensures only one sector is open per flight
        by closing any existing open sectors before entering a new one.
        
        Args:
            callsign: Flight callsign
            session: Database session
        """
        try:
            # Find all open sectors for this flight
            result = await session.execute(text("""
                SELECT sector_name, entry_timestamp
                FROM flight_sector_occupancy 
                WHERE callsign = :callsign 
                AND exit_timestamp IS NULL
            """), {"callsign": callsign})
            
            open_sectors = result.fetchall()
            
            if not open_sectors:
                return  # No open sectors to close
            
            # Get the last known flight record for this callsign
            flight_result = await session.execute(text("""
                SELECT latitude, longitude, altitude, last_updated
                FROM flights 
                WHERE callsign = :callsign 
                ORDER BY last_updated DESC 
                LIMIT 1
            """), {"callsign": callsign})
            
            last_flight = flight_result.fetchone()
            if not last_flight:
                self.logger.warning(f"No flight record found for {callsign}")
                return
            
            self.logger.debug(f"Closing {len(open_sectors)} open sectors for flight {callsign}")
            
            # Close each open sector
            for sector in open_sectors:
                sector_name = sector.sector_name
                entry_timestamp = sector.entry_timestamp
                
                # Calculate duration using last flight record timestamp
                duration_seconds = int((last_flight.last_updated - entry_timestamp).total_seconds())
                
                # Update the sector exit
                await session.execute(text("""
                    UPDATE flight_sector_occupancy 
                    SET exit_timestamp = :exit_timestamp,
                        exit_lat = :exit_lat,
                        exit_lon = :exit_lon,
                        exit_altitude = :exit_altitude,
                        duration_seconds = :duration_seconds
                    WHERE callsign = :callsign 
                    AND sector_name = :sector_name
                    AND exit_timestamp IS NULL
                """), {
                    "exit_timestamp": last_flight.last_updated,  # Use last flight record timestamp
                    "exit_lat": last_flight.latitude,           # Use last known position
                    "exit_lon": last_flight.longitude,          # Use last known position
                    "exit_altitude": last_flight.altitude,      # Use last known altitude
                    "duration_seconds": duration_seconds,
                    "callsign": callsign,
                    "sector_name": sector_name
                })
                
                self.logger.debug(f"Closed sector {sector_name} for flight {callsign} (duration: {duration_seconds}s)")
            
            if len(open_sectors) > 1:
                self.logger.warning(f"Flight {callsign} had {len(open_sectors)} open sectors - all closed to prevent data corruption")
    
        except Exception as e:
            self.logger.error(f"Failed to close open sectors for flight {callsign}: {e}")

    async def _record_sector_exit(
        self, callsign: str, sector_name: str, lat: float, lon: float, 
        altitude: int, timestamp: datetime, session: AsyncSession
    ) -> None:
        """
        Record when a flight exits a sector.
        
        Args:
            callsign: Flight callsign
            sector_name: Name of the sector being exited
            lat: Exit latitude
            lon: Exit longitude
            altitude: Exit altitude in feet
            timestamp: Exit timestamp
            session: Database session
        """
        try:
            # Find and update the open entry record
            result = await session.execute(text("""
                UPDATE flight_sector_occupancy 
                SET exit_timestamp = :timestamp,
                    exit_lat = :lat,
                    exit_lon = :lon,
                    exit_altitude = :altitude,
                    duration_seconds = EXTRACT(EPOCH FROM (:timestamp - entry_timestamp))::INTEGER
                WHERE callsign = :callsign 
                AND sector_name = :sector_name 
                AND exit_timestamp IS NULL
                RETURNING id
            """), {
                "callsign": callsign, "sector_name": sector_name,
                "timestamp": timestamp, "lat": lat, "lon": lon, "altitude": altitude
            })
            
            if result.fetchone():
                self.logger.debug(f"Flight {callsign} exited sector {sector_name}")
            else:
                self.logger.warning(f"No open sector entry found for {callsign} in {sector_name}")
    
        except Exception as e:
            self.logger.error(f"Failed to record sector exit for {callsign}: {e}")

    async def _calculate_sector_breakdown(
        self, callsign: str, session: AsyncSession
    ) -> Dict[str, int]:
        """
        Calculate time spent in each sector for a completed flight.
        
        Args:
            callsign: Flight callsign
            session: Database session
            
        Returns:
            Dict mapping sector names to minutes spent in each sector
        """
        try:
            result = await session.execute(text("""
                SELECT sector_name, 
                       SUM(duration_seconds) / 60 as minutes
                FROM flight_sector_occupancy 
                WHERE callsign = :callsign 
                AND exit_timestamp IS NOT NULL
                GROUP BY sector_name
                ORDER BY minutes DESC
            """), {"callsign": callsign})
            
            breakdown = {}
            for row in result.fetchall():
                sector_name = row.sector_name
                minutes = int(row.minutes) if row.minutes else 0
                if minutes > 0:
                    breakdown[sector_name] = minutes
            
            return breakdown
        
        except Exception as e:
            self.logger.error(f"Failed to calculate sector breakdown for {callsign}: {e}")
            return {}

    def _get_primary_sector(self, sector_breakdown: Dict[str, int]) -> Optional[str]:
        """
        Get the sector with the most time spent.
        
        Args:
            sector_breakdown: Dictionary mapping sector names to minutes spent
            
        Returns:
            Name of the primary sector, or None if no sectors
        """
        if not sector_breakdown:
            return None
        
        return max(sector_breakdown.items(), key=lambda x: x[1])[0]

    async def _cleanup_sector_states(self) -> None:
        """
        Clean up sector states for flights that are no longer active.
        
        This method removes inactive flights from the sector state tracking
        and closes any open sector entries to prevent data inconsistencies.
        """
        if not hasattr(self, 'sector_tracking_enabled') or not self.sector_tracking_enabled:
            return
        
        try:
            # Get current active flights from database (flights updated in last 5 minutes)
            async with get_database_session() as session:
                result = await session.execute(text("""
                    SELECT DISTINCT callsign FROM flights 
                    WHERE last_updated > NOW() - INTERVAL '5 minutes'
                """))
                
                active_callsigns = {row.callsign for row in result.fetchall()}
                
                # Remove inactive flights from sector states
                if hasattr(self, 'flight_sector_states'):
                    inactive_callsigns = set(self.flight_sector_states.keys()) - active_callsigns
                    
                    for callsign in inactive_callsigns:
                        # Close any open sector entries
                        await self._close_open_sector_entries(callsign, session)
                        del self.flight_sector_states[callsign]
                        
                    if inactive_callsigns:
                        self.logger.debug(f"Cleaned up sector states for {len(inactive_callsigns)} inactive flights")
        
        except Exception as e:
            self.logger.error(f"Failed to cleanup sector states: {e}")

    async def _close_open_sector_entries(self, callsign: str, session: AsyncSession) -> None:
        """
        Close any open sector entries for a flight.
        
        This is called when a flight becomes inactive to ensure all sector
        entries have proper exit timestamps and duration calculations.
        
        Args:
            callsign: Flight callsign
            session: Database session
        """
        try:
            # Get the last known flight record for this callsign
            flight_result = await session.execute(text("""
                SELECT latitude, longitude, altitude, last_updated
                FROM flights
                WHERE callsign = :callsign
                ORDER BY last_updated DESC
                LIMIT 1
            """), {"callsign": callsign})

            last_flight = flight_result.fetchone()
            if not last_flight:
                self.logger.warning(f"No flight record found for {callsign}")
                return

            # Get all open sector entries for this callsign to get their entry timestamps
            sector_result = await session.execute(text("""
                SELECT sector_name, entry_timestamp
                FROM flight_sector_occupancy
                WHERE callsign = :callsign
                AND exit_timestamp IS NULL
            """), {"callsign": callsign})

            open_sectors = sector_result.fetchall()
            if not open_sectors:
                return  # No open sectors to close

            # Close each open sector entry with last known position and last flight record timestamp
            for sector in open_sectors:
                sector_name = sector.sector_name
                entry_timestamp = sector.entry_timestamp
                
                # Calculate duration using the last flight record timestamp
                duration_seconds = int((last_flight.last_updated - entry_timestamp).total_seconds())
                
                await session.execute(text("""
                    UPDATE flight_sector_occupancy 
                    SET exit_timestamp = :exit_timestamp,
                        exit_lat = :exit_lat,
                        exit_lon = :exit_lon,
                        exit_altitude = :exit_altitude,
                        duration_seconds = :duration_seconds
                    WHERE callsign = :callsign 
                    AND sector_name = :sector_name
                    AND exit_timestamp IS NULL
                """), {
                    "exit_timestamp": last_flight.last_updated,  # Use last flight record timestamp
                    "exit_lat": last_flight.latitude,           # Use last known position
                    "exit_lon": last_flight.longitude,          # Use last known position
                    "exit_altitude": last_flight.altitude,      # Use last known altitude
                    "duration_seconds": duration_seconds,
                    "callsign": callsign,
                    "sector_name": sector_name
                })
                
                self.logger.debug(f"Closed sector {sector_name} for flight {callsign} (duration: {duration_seconds}s)")
        
        except Exception as e:
            self.logger.error(f"Failed to close open sector entries for {callsign}: {e}")

    def get_sector_tracking_status(self) -> Dict[str, Any]:
        """
        Get current sector tracking status.
        
        Returns:
            Dictionary containing sector tracking status information
        """
        if not hasattr(self, 'sector_tracking_enabled') or not self.sector_tracking_enabled:
            return {
                "enabled": False,
                "status": "disabled",
                "sectors_loaded": 0,
                "active_flights": 0
            }
        
        if not hasattr(self, 'sector_loader'):
            return {
                "enabled": True,
                "status": "error",
                "error": "SectorLoader not initialized",
                "sectors_loaded": 0,
                "active_flights": 0
            }
        
        return {
            "enabled": True,
            "status": "operational" if self.sector_loader.loaded else "error",
            "sectors_loaded": self.sector_loader.get_sector_count(),
            "sectors_with_boundaries": self.sector_loader.get_sectors_with_boundaries_count(),
            "active_flights": len(getattr(self, 'flight_sector_states', {})),
            "update_interval": getattr(self, 'sector_update_interval', 60)
        }

    async def cleanup_stale_sectors(self) -> Dict[str, Any]:
        """
        Clean up stale sector entries for flights that haven't been updated recently.
        
        This method finds flights that haven't been updated for CLEANUP_FLIGHT_TIMEOUT seconds
        and closes their open sector entries with last known position data.
        
        Returns:
            Dict[str, Any]: Result containing count of sectors closed
        """
        try:
            cleanup_timeout = int(os.getenv("CLEANUP_FLIGHT_TIMEOUT", "300"))
            stale_cutoff = datetime.now(timezone.utc) - timedelta(seconds=cleanup_timeout)
            
            sectors_closed = 0
            
            async with get_database_session() as session:
                # Find flights with open sectors that haven't been updated recently
                # Use subquery to get the most recent flight record for each callsign
                result = await session.execute(text("""
                    SELECT DISTINCT fso.callsign, fso.sector_name, fso.entry_timestamp,
                           latest_flight.latitude, latest_flight.longitude, latest_flight.altitude, latest_flight.last_updated
                    FROM flight_sector_occupancy fso
                    JOIN (
                        SELECT DISTINCT ON (callsign) 
                            callsign, latitude, longitude, altitude, last_updated
                        FROM flights 
                        ORDER BY callsign, last_updated DESC
                    ) latest_flight ON fso.callsign = latest_flight.callsign
                    WHERE fso.exit_timestamp IS NULL
                    AND latest_flight.last_updated < :stale_cutoff
                """), {"stale_cutoff": stale_cutoff})
                
                stale_sectors = result.fetchall()
                
                for sector in stale_sectors:
                    callsign = sector.callsign
                    sector_name = sector.sector_name
                    entry_timestamp = sector.entry_timestamp
                    last_lat = sector.latitude
                    last_lon = sector.longitude
                    last_altitude = sector.altitude
                    last_updated = sector.last_updated  # This is the most recent flight record timestamp
                    
                    # Calculate duration using the last flight record timestamp, not current time
                    duration_seconds = int((last_updated - entry_timestamp).total_seconds())
                    
                    # Close the sector entry with last known position and last flight record timestamp
                    await session.execute(text("""
                        UPDATE flight_sector_occupancy 
                        SET exit_timestamp = :exit_timestamp,
                            exit_lat = :exit_lat,
                            exit_lon = :exit_lon,
                            exit_altitude = :exit_altitude,
                            duration_seconds = :duration_seconds
                        WHERE callsign = :callsign 
                        AND sector_name = :sector_name
                        AND exit_timestamp IS NULL
                    """), {
                        "exit_timestamp": last_updated,  # Use last flight record timestamp, not current time
                        "exit_lat": last_lat,
                        "exit_lon": last_lon,
                        "exit_altitude": last_altitude,
                        "duration_seconds": duration_seconds,
                        "callsign": callsign,
                        "sector_name": sector_name
                    })
                    
                    sectors_closed += 1
                    self.logger.info(f"Closed stale sector {sector_name} for flight {callsign} (duration: {duration_seconds}s, exit at: {last_updated})")
                
                if sectors_closed > 0:
                    self.logger.info(f"Cleanup completed: {sectors_closed} stale sectors closed")
                
                return {
                    "sectors_closed": sectors_closed,
                    "stale_cutoff": stale_cutoff.isoformat(),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup stale sectors: {e}")
            return {
                "sectors_closed": 0,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    # ============================================================================
    # FLIGHT SUMMARY PROCESSING METHODS
    # ============================================================================

    async def _identify_completed_flights(self, completion_hours: int) -> List[dict]:
        """Identify flights that have been completed for the specified number of hours."""
        try:
            completion_threshold = datetime.now(timezone.utc) - timedelta(hours=completion_hours)
            
            query = """
                SELECT DISTINCT callsign, departure, arrival, cid, deptime
                FROM flights 
                WHERE last_updated < :completion_threshold
                AND callsign NOT IN (
                    SELECT DISTINCT callsign FROM flight_summaries
                )
            """
            
            async with get_database_session() as session:
                result = await session.execute(text(query), {"completion_threshold": completion_threshold})
                completed_flights = result.fetchall()
                
                self.logger.debug(f"Identified {len(completed_flights)} completed flights older than {completion_hours} hours")
                return completed_flights
            
        except Exception as e:
            self.logger.error(f"Error identifying completed flights: {e}")
            raise

    async def _create_flight_summaries(self, completed_flights: List[dict]) -> int:
        """Create summary records for completed flights."""
        processed_count = 0
        async with get_database_session() as session:
            for flight_key in completed_flights:
                callsign, departure, arrival, cid, deptime = flight_key
                
                try:
                    # Step 2: Get all records for this flight
                    flight_records = await session.execute(text("""
                        SELECT * FROM flights 
                        WHERE callsign = :callsign 
                        AND departure = :departure 
                        AND arrival = :arrival 
                        AND cid = :cid
                        AND deptime = :deptime
                        ORDER BY last_updated
                    """), {
                        "callsign": callsign,
                        "departure": departure,
                        "arrival": arrival,
                        "cid": cid,
                        "deptime": deptime
                    })
                    
                    records = flight_records.fetchall()
                    if not records:
                        continue
                    
                    # Step 3: Create summary record
                    first_record = records[0]
                    last_record = records[-1]
                    
                    # Calculate time online (handle gaps)
                    total_minutes = 0
                    if len(records) > 1:
                        # Simple calculation: assume continuous tracking
                        time_diff = last_record.last_updated - first_record.last_updated
                        total_minutes = int(time_diff.total_seconds() / 60)
                    
                    # Detect ATC interactions for this flight with timeout protection
                    atc_data = await self.atc_detection_service.detect_flight_atc_interactions_with_timeout(
                        callsign, departure, arrival, first_record.logon_time, timeout_seconds=30.0
                    )
                    
                    # NEW: Calculate sector breakdown for this completed flight
                    sector_breakdown = await self._calculate_sector_breakdown(callsign, session)
                    primary_sector = self._get_primary_sector(sector_breakdown)
                    total_sectors = len(sector_breakdown)
                    total_enroute_time = sum(sector_breakdown.values())
                    
                    # Create summary data
                    summary_data = {
                        "callsign": callsign,
                        "aircraft_type": first_record.aircraft_type,
                        "departure": departure,
                        "arrival": arrival,
                        "deptime": deptime,
                        "logon_time": first_record.logon_time,
                        "route": first_record.route,
                        "flight_rules": first_record.flight_rules,
                        "aircraft_faa": first_record.aircraft_faa,
                        "planned_altitude": first_record.planned_altitude,
                        "aircraft_short": first_record.aircraft_type,
                        "cid": first_record.cid,
                        "name": first_record.name,
                        "server": first_record.server,
                        "pilot_rating": first_record.pilot_rating,
                        "military_rating": first_record.military_rating,
                        "controller_callsigns": json.dumps(self._convert_for_json(atc_data["controller_callsigns"])),
                        "controller_time_percentage": atc_data["controller_time_percentage"],
                        "airborne_controller_time_percentage": atc_data["airborne_controller_time_percentage"],
                        "time_online_minutes": total_minutes,
                        "primary_enroute_sector": primary_sector,
                        "total_enroute_sectors": total_sectors,
                        "total_enroute_time_minutes": total_enroute_time,
                        "sector_breakdown": json.dumps(self._convert_for_json(sector_breakdown)),
                        "completion_time": last_record.last_updated
                    }
                    
                    # Insert summary
                    await session.execute(text("""
                        INSERT INTO flight_summaries (
                            callsign, aircraft_type, departure, arrival, deptime, logon_time,
                            route, flight_rules, aircraft_faa, planned_altitude, aircraft_short,
                            cid, name, server, pilot_rating, military_rating,
                            controller_callsigns, controller_time_percentage, airborne_controller_time_percentage, time_online_minutes,
                            primary_enroute_sector, total_enroute_sectors, total_enroute_time_minutes, sector_breakdown,
                            completion_time
                        ) VALUES (
                            :callsign, :aircraft_type, :departure, :arrival, :deptime, :logon_time,
                            :route, :flight_rules, :aircraft_faa, :planned_altitude, :aircraft_short,
                            :cid, :name, :server, :pilot_rating, :military_rating,
                            :controller_callsigns, :controller_time_percentage, :airborne_controller_time_percentage, :time_online_minutes,
                            :primary_enroute_sector, :total_enroute_sectors, :total_enroute_time_minutes, :sector_breakdown,
                            :completion_time
                        )
                    """), summary_data)
                    
                    processed_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Failed to process flight {callsign}: {e}")
                    continue
            
            # Commit all changes
            await session.commit()
            
            return processed_count

    async def process_completed_flights(self) -> Dict[str, Any]:
        """
        Process completed flights by creating summaries and archiving detailed records.
        
        This is the main entry point for flight summary processing that:
        1. Identifies completed flights (older than completion threshold)
        2. Creates flight summaries with sector breakdown data
        3. Archives detailed flight records
        4. Cleans up old data based on retention policy
        
        Returns:
            Dict containing processing results and statistics
        """
        try:
            self.logger.info("🔄 Starting flight summary processing...")
            
            # Get configuration values
            completion_hours = getattr(self.config.flight_summary, 'completion_hours', 14)
            retention_hours = getattr(self.config.flight_summary, 'retention_hours', 168)
            
            # Step 1: Identify completed flights
            completed_flights = await self._identify_completed_flights(completion_hours)
            
            if not completed_flights:
                self.logger.info("📭 No completed flights found to process")
                return {
                    "status": "success",
                    "summaries_created": 0,
                    "records_archived": 0,
                    "records_deleted": 0,
                    "status": "no_work"
                }
            
            self.logger.info(f"📊 Found {len(completed_flights)} completed flights to process")
            
            # Step 2: Create summaries
            summaries_created = await self._create_flight_summaries(completed_flights)
            
            # Step 3: Archive completed records
            records_archived = await self._archive_completed_flights(completed_flights)
            
            # Step 4: Delete completed records
            records_deleted = await self._delete_completed_flights(completed_flights)
            
            result = {
                "status": "success",
                "summaries_created": summaries_created,
                "records_archived": records_archived,
                "records_deleted": records_deleted
            }
            
            self.logger.info(f"✅ Flight summary processing completed: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Flight summary processing failed: {e}")
            raise

    @handle_service_errors
    @log_operation("process_completed_controllers")
    async def process_completed_controllers(self) -> Dict[str, Any]:
        """Main entry point for controller summary processing."""
        try:
            self.logger.info("🚀 Starting controller summary processing")
            
            # Get configuration
            completion_minutes = getattr(self.config.controller_summary, 'completion_minutes', 30)
            retention_hours = getattr(self.config.controller_summary, 'retention_hours', 168)
            
            # Step 1: Identify completed controllers
            completed_controllers = await self._identify_completed_controllers(completion_minutes)
            
            if not completed_controllers:
                self.logger.info("✅ No completed controllers found for processing")
                return {
                    "summaries_created": 0,
                    "records_archived": 0,
                    "records_deleted": 0,
                    "status": "no_work"
                }
            
            self.logger.info(f"📊 Found {len(completed_controllers)} completed controllers to process")
            
            # Step 2: Create summaries
            summaries_created_result = await self._create_controller_summaries(completed_controllers)
            summaries_created = summaries_created_result["processed_count"]
            failed_count = summaries_created_result["failed_count"]
            successful_controllers = summaries_created_result["successful_controllers"]
            
            # CRITICAL: Validate summaries were created before proceeding
            if summaries_created == 0:
                self.logger.error("❌ No summaries were created - aborting archiving to prevent data loss")
                return {
                    "summaries_created": 0,
                    "records_archived": 0,
                    "records_deleted": 0,
                    "status": "failed_no_summaries",
                    "error": "No summaries created - archiving aborted to prevent data loss"
                }
            
            self.logger.info(f"✅ Successfully created {summaries_created} summaries - proceeding with archiving")
            
            # Step 3: Archive completed records (only if summaries were created)
            records_archived = await self._archive_completed_controllers(successful_controllers)
            
            # Step 4: Delete completed records (only if summaries were created)
            records_deleted = await self._delete_completed_controllers(successful_controllers)
            
            # Log the results clearly
            self.logger.info(f"📊 Summary Processing Results:")
            self.logger.info(f"   ✅ Successfully processed: {summaries_created} controllers")
            self.logger.info(f"   ❌ Failed to process: {failed_count} controllers")
            self.logger.info(f"   📦 Archived: {records_archived} controller records")
            self.logger.info(f"   🗑️ Deleted: {records_deleted} controller records")
            
            if failed_count > 0:
                self.logger.warning(f"⚠️ {failed_count} controllers were NOT archived due to summary creation failures")
                self.logger.warning(f"⚠️ These controllers remain in the main table for retry")
            
            result = {
                "summaries_created": summaries_created,
                "failed_count": failed_count,
                "records_archived": records_archived,
                "records_deleted": records_deleted,
                "status": "completed"
            }
            
            self.logger.info(f"✅ Controller summary processing completed: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Controller summary processing failed: {e}")
            raise

    async def _identify_completed_controllers(self, completion_minutes: int) -> List[tuple]:
        """Identify controllers that have been inactive for the specified time."""
        try:
            completion_threshold = datetime.now(timezone.utc) - timedelta(minutes=completion_minutes)
            
            query = """
                SELECT DISTINCT callsign, logon_time
                FROM controllers 
                WHERE last_updated < :completion_threshold
                AND callsign NOT IN (
                    SELECT DISTINCT callsign FROM controller_summaries
                )
            """
            
            async with get_database_session() as session:
                result = await session.execute(text(query), {"completion_threshold": completion_threshold})
                completed_controllers = result.fetchall()
                
                self.logger.debug(f"Identified {len(completed_controllers)} completed controllers older than {completion_minutes} minutes")
                return completed_controllers
            
        except Exception as e:
            self.logger.error(f"Error identifying completed controllers: {e}")
            raise

    def _convert_for_json(self, obj):
        """Convert objects to JSON-serializable types, handling Decimal and other non-serializable types."""
        import json
        from decimal import Decimal
        
        if isinstance(obj, Decimal):
            # Convert Decimal to float for JSON serialization
            return float(obj)
        elif isinstance(obj, dict):
            return {key: self._convert_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_for_json(item) for item in obj]
        elif isinstance(obj, (datetime, date)):
            # Convert datetime objects to ISO format strings
            return obj.isoformat()
        else:
            return obj

    async def _create_controller_summaries(self, completed_controllers: List[tuple]) -> Dict[str, Any]:
        """Create summary records for completed controllers with session merging."""
        processed_count = 0
        failed_count = 0
        successful_controllers = []  # Track which controllers got summaries
        
        # Configuration for session merging - configurable threshold for reconnections
        reconnection_threshold_minutes = int(os.getenv("CONTROLLER_RECONNECTION_THRESHOLD_MINUTES", "5"))
        
        async with get_database_session() as session:
            for controller_key in completed_controllers:
                callsign, logon_time = controller_key
                
                try:
                    # Get all records for this controller including potential reconnections within 5 minutes
                    controller_records = await session.execute(text("""
                        SELECT * FROM controllers 
                        WHERE callsign = :callsign 
                        AND (
                            logon_time = :logon_time  -- Original session
                            OR (
                                logon_time > :logon_time 
                                AND logon_time <= :logon_time + (INTERVAL '1 minute' * :reconnection_threshold)
                            )
                        )
                        ORDER BY created_at
                    """), {
                        "callsign": callsign,
                        "logon_time": logon_time,
                        "reconnection_threshold": reconnection_threshold_minutes
                    })
                    
                    records = controller_records.fetchall()
                    if not records:
                        self.logger.warning(f"No records found for controller {callsign} with logon_time {logon_time}")
                        failed_count += 1
                        continue
                    
                    # Get first and last records across merged sessions
                    first_record = records[0]
                    last_record = records[-1]
                    
                    # Calculate total session duration including reconnections
                    session_duration_minutes = int((last_record.last_updated - first_record.logon_time).total_seconds() / 60)
                    
                    # Get all frequencies used across merged sessions
                    frequencies_used = await self._get_session_frequencies(callsign, logon_time, session)
                    
                    # Get aircraft interaction data across merged sessions
                    aircraft_data = await self._get_aircraft_interactions(callsign, logon_time, last_record.last_updated, session)
                    
                    # Create merged summary data
                    summary_data = {
                        "callsign": callsign,
                        "cid": first_record.cid,
                        "name": first_record.name,
                        "session_start_time": first_record.logon_time,
                        "session_end_time": last_record.last_updated,
                        "session_duration_minutes": session_duration_minutes,
                        "rating": first_record.rating,
                        "facility": first_record.facility,
                        "server": first_record.server,
                        "total_aircraft_handled": aircraft_data["total_aircraft"],
                        "peak_aircraft_count": aircraft_data["peak_count"],
                        "hourly_aircraft_breakdown": json.dumps(self._convert_for_json(aircraft_data["hourly_breakdown"])),
                        "frequencies_used": json.dumps(self._convert_for_json(frequencies_used)),
                        "aircraft_details": json.dumps(self._convert_for_json(aircraft_data["details"]))
                    }
                    
                    # Insert merged summary
                    await session.execute(text("""
                        INSERT INTO controller_summaries (
                            callsign, cid, name, session_start_time, session_end_time,
                            session_duration_minutes, rating, facility, server,
                            total_aircraft_handled, peak_aircraft_count,
                            hourly_aircraft_breakdown, frequencies_used, aircraft_details
                        ) VALUES (
                            :callsign, :cid, :name, :session_start_time, :session_end_time,
                            :session_duration_minutes, :rating, :facility, :server,
                            :total_aircraft_handled, :peak_aircraft_count,
                            :hourly_aircraft_breakdown, :frequencies_used, :aircraft_details
                        )
                    """), summary_data)
                    
                    processed_count += 1
                    successful_controllers.append(controller_key)  # Track successful summary creation
                    
                    # Log whether sessions were merged
                    if len(records) > 1:
                        self.logger.debug(f"✅ Created merged summary for controller {callsign} (duration: {session_duration_minutes} min, {len(records)} sessions merged)")
                    else:
                        self.logger.debug(f"✅ Created summary for controller {callsign} (duration: {session_duration_minutes} min)")
                    
                except Exception as e:
                    self.logger.error(f"❌ Failed to process controller {callsign}: {e}")
                    failed_count += 1
                    continue
            
            # Commit all changes
            await session.commit()
            
            if failed_count > 0:
                self.logger.warning(f"⚠️ Summary creation completed with {failed_count} failures out of {len(completed_controllers)} controllers")
            
            return {
                "processed_count": processed_count,
                "failed_count": failed_count,
                "successful_controllers": successful_controllers
            }

    async def _get_session_frequencies(self, callsign: str, logon_time: datetime, session) -> List[str]:
        """Get all frequencies used during a controller session."""
        try:
            result = await session.execute(text("""
                SELECT DISTINCT frequency 
                FROM controllers 
                WHERE callsign = :callsign 
                AND logon_time = :logon_time
                AND frequency IS NOT NULL
                ORDER BY frequency
            """), {
                "callsign": callsign,
                "logon_time": logon_time
            })
            
            frequencies = [str(row.frequency) for row in result.fetchall()]
            return frequencies
            
        except Exception as e:
            self.logger.error(f"Error getting frequencies for {callsign}: {e}")
            return []

    async def _get_aircraft_interactions(self, callsign: str, session_start: datetime, session_end: datetime, session) -> Dict[str, Any]:
        """Get aircraft interaction data for a controller session using Flight Detection Service."""
        try:
            # Use the Flight Detection Service for accurate controller-pilot pairing
            # This ensures dynamic geographic proximity validation based on controller type and proper frequency matching
            # Controller types get appropriate ranges: Ground/Tower (15nm), Approach (60nm), Center (400nm), FSS (1000nm)
            
            # Log controller type and proximity range for debugging
            controller_info = self.flight_detection_service.controller_type_detector.get_controller_info(callsign)
            self.logger.info(f"Controller {callsign} detected as {controller_info['type']} with {controller_info['proximity_threshold']}nm proximity range")
            
            flight_data = await self.flight_detection_service.detect_controller_flight_interactions_with_timeout(
                callsign, session_start, session_end, timeout_seconds=30.0
            )
            
            if not flight_data.get("flights_detected", False):
                self.logger.debug(f"No flight interactions detected for controller {callsign}")
                return self._empty_aircraft_data()
            
            # Convert Flight Detection Service format to existing summary format
            return {
                "total_aircraft": flight_data["total_aircraft"],
                "peak_count": flight_data["peak_count"],
                "hourly_breakdown": flight_data["hourly_breakdown"],
                "details": flight_data["details"]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting aircraft interactions for {callsign}: {e}")
            return self._empty_aircraft_data()

    def _empty_aircraft_data(self) -> Dict[str, Any]:
        """Return empty aircraft data structure."""
        return {
            "total_aircraft": 0,
            "peak_count": 0,
            "hourly_breakdown": {},
            "details": []
        }

    async def _archive_completed_controllers(self, completed_controllers: List[tuple]) -> int:
        """Archive completed controller records."""
        archived_count = 0
        async with get_database_session() as session:
            for controller_key in completed_controllers:
                callsign, logon_time = controller_key
                
                try:
                    # Archive all records for this session
                    result = await session.execute(text("""
                        INSERT INTO controllers_archive (
                            id, callsign, frequency, cid, name, rating, facility,
                            visual_range, text_atis, server, last_updated, logon_time,
                            created_at, updated_at
                        )
                        SELECT 
                            id, callsign, frequency, cid, name, rating, facility,
                            visual_range, text_atis, server, last_updated, logon_time,
                            created_at, updated_at
                        FROM controllers
                        WHERE callsign = :callsign AND logon_time = :logon_time
                    """), {
                        "callsign": callsign,
                        "logon_time": logon_time
                    })
                    
                    archived_count += result.rowcount
                    
                except Exception as e:
                    self.logger.error(f"Failed to archive controller {callsign}: {e}")
                    continue
            
            await session.commit()
            return archived_count

    async def _delete_completed_controllers(self, completed_controllers: List[tuple]) -> int:
        """Delete completed controller records from main table."""
        deleted_count = 0
        async with get_database_session() as session:
            for controller_key in completed_controllers:
                callsign, logon_time = controller_key
                
                try:
                    result = await session.execute(text("""
                        DELETE FROM controllers
                        WHERE callsign = :callsign AND logon_time = :logon_time
                    """), {
                        "callsign": callsign,
                        "logon_time": logon_time
                    })
                    
                    deleted_count += result.rowcount
                    
                except Exception as e:
                    self.logger.error(f"Failed to delete controller {callsign}: {e}")
                    continue
            
            await session.commit()
            return deleted_count

    async def _archive_completed_flights(self, completed_flights: List[dict]) -> int:
        """Archive detailed records for completed flights."""
        processed_count = 0
        async with get_database_session() as session:
            for flight_key in completed_flights:
                callsign, departure, arrival, cid, deptime = flight_key
                
                try:
                    # Get all records for this flight
                    flight_records = await session.execute(text("""
                        SELECT * FROM flights 
                        WHERE callsign = :callsign 
                        AND departure = :departure 
                        AND arrival = :arrival 
                        AND cid = :cid
                        AND deptime = :deptime
                        ORDER BY last_updated
                    """), {
                        "callsign": callsign,
                        "departure": departure,
                        "arrival": arrival,
                        "cid": cid,
                        "deptime": deptime
                    })
                    
                    records = flight_records.fetchall()
                    if not records:
                        continue
                    
                    # Archive each record
                    for record in records:
                        await session.execute(text("""
                            INSERT INTO flights_archive (
                                callsign, aircraft_type, departure, arrival, logon_time,
                                route, flight_rules, aircraft_faa, planned_altitude, aircraft_short,
                                cid, name, server, pilot_rating, military_rating,
                                latitude, longitude, altitude, groundspeed, heading,
                                last_updated, deptime, controller_callsigns, controller_time_percentage,
                                time_online_minutes, primary_enroute_sector, total_enroute_sectors,
                                total_enroute_time_minutes, sector_breakdown, completion_time
                            ) VALUES (
                                :callsign, :aircraft_type, :departure, :arrival, :logon_time,
                                :route, :flight_rules, :aircraft_faa, :planned_altitude, :aircraft_short,
                                :cid, :name, :server, :pilot_rating, :military_rating,
                                :latitude, :longitude, :altitude, :groundspeed, :heading,
                                :last_updated, :deptime, :controller_callsigns, :controller_time_percentage,
                                :time_online_minutes, :primary_enroute_sector, :total_enroute_sectors,
                                :total_enroute_time_minutes, :sector_breakdown, :completion_time
                            )
                        """), {
                            "callsign": record.callsign,
                            "aircraft_type": record.aircraft_type,
                            "departure": record.departure,
                            "arrival": record.arrival,
                            "logon_time": record.logon_time,
                            "route": record.route,
                            "flight_rules": record.flight_rules,
                            "aircraft_faa": record.aircraft_faa,
                            "planned_altitude": record.planned_altitude,
                            "aircraft_short": record.aircraft_type,
                            "cid": record.cid,
                            "name": record.name,
                            "server": record.server,
                            "pilot_rating": record.pilot_rating,
                            "military_rating": record.military_rating,
                            "latitude": record.latitude,
                            "longitude": record.longitude,
                            "altitude": record.altitude,
                            "groundspeed": record.groundspeed,
                            "heading": record.heading,
                            "last_updated": record.last_updated,
                            "deptime": getattr(record, 'deptime', None),
                            "controller_callsigns": getattr(record, 'controller_callsigns', None),
                            "controller_time_percentage": getattr(record, 'controller_time_percentage', None),
                            "time_online_minutes": getattr(record, 'time_online_minutes', None),
                            "primary_enroute_sector": getattr(record, 'primary_enroute_sector', None),
                            "total_enroute_sectors": getattr(record, 'total_enroute_sectors', None),
                            "total_enroute_time_minutes": getattr(record, 'total_enroute_time_minutes', None),
                            "sector_breakdown": getattr(record, 'sector_breakdown', None),
                            "completion_time": getattr(record, 'completion_time', None)
                        })
                    
                    processed_count += len(records)
                    
                except Exception as e:
                    self.logger.error(f"Failed to archive flight {callsign}: {e}")
                    continue
            
            # Commit all changes
            await session.commit()
            
            return processed_count

    async def _delete_completed_flights(self, completed_flights: List[dict]) -> int:
        """Delete completed flights from the main flights table."""
        processed_count = 0
        async with get_database_session() as session:
            for flight_key in completed_flights:
                callsign, departure, arrival, cid, deptime = flight_key
                
                try:
                    # Delete all records for this flight
                    result = await session.execute(text("""
                        DELETE FROM flights 
                        WHERE callsign = :callsign 
                        AND departure = :departure 
                        AND arrival = :arrival 
                        AND cid = :cid
                        AND deptime = :deptime
                    """), {
                        "callsign": callsign,
                        "departure": departure,
                        "arrival": arrival,
                        "cid": cid,
                        "deptime": deptime
                    })
                    
                    processed_count += result.rowcount
                    self.logger.debug(f"Deleted {processed_count} completed flights from main table")
                    
                except Exception as e:
                    self.logger.error(f"Failed to delete completed flight {callsign}: {e}")
                    continue
            
            # Commit changes
            await session.commit()
            
            return processed_count

    async def _cleanup_old_archived_records(self, retention_hours: int) -> int:
        """Delete old archived records beyond the retention period."""
        try:
            retention_threshold = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
            
            async with get_database_session() as session:
                # Delete from flights_archive
                result = await session.execute(text("""
                    DELETE FROM flights_archive 
                    WHERE last_updated < :retention_threshold
                """), {"retention_threshold": retention_threshold})
                
                processed_count = result.rowcount
                self.logger.debug(f"Deleted {processed_count} old archived records from flights_archive")
                
                # Commit changes
                await session.commit()
                
                return processed_count
                
        except Exception as e:
            self.logger.error(f"Failed to delete old archived records from flights_archive: {e}")
            raise

    async def populate_flights_archive_summary_fields(self) -> int:
        """Populate summary fields in flights_archive from flight_summaries table."""
        try:
            processed_count = 0
            async with get_database_session() as session:
                # Update flights_archive with summary data from flight_summaries
                result = await session.execute(text("""
                    UPDATE flights_archive 
                    SET 
                        deptime = fs.deptime,
                        controller_callsigns = fs.controller_callsigns,
                        controller_time_percentage = fs.controller_time_percentage,
                        time_online_minutes = fs.time_online_minutes,
                        primary_enroute_sector = fs.primary_enroute_sector,
                        total_enroute_sectors = fs.total_enroute_sectors,
                        total_enroute_time_minutes = fs.total_enroute_time_minutes,
                        sector_breakdown = fs.sector_breakdown,
                        completion_time = fs.completion_time,
                        updated_at = NOW()
                    FROM flight_summaries fs
                    WHERE flights_archive.callsign = fs.callsign
                    AND flights_archive.departure = fs.departure
                    AND flights_archive.arrival = fs.arrival
                    AND flights_archive.cid = fs.cid
                    AND flights_archive.deptime = fs.deptime
                    AND (
                        flights_archive.controller_callsigns IS NULL
                        OR flights_archive.controller_time_percentage IS NULL
                        OR flights_archive.time_online_minutes IS NULL
                        OR flights_archive.primary_enroute_sector IS NULL
                        OR flights_archive.total_enroute_sectors IS NULL
                        OR flights_archive.total_enroute_time_minutes IS NULL
                        OR flights_archive.sector_breakdown IS NULL
                        OR flights_archive.completion_time IS NULL
                    )
                """))
                
                processed_count = result.rowcount
                await session.commit()
                
                self.logger.info(f"✅ Updated {processed_count} flights_archive records with summary data")
                return processed_count
                
        except Exception as e:
            self.logger.error(f"Failed to populate flights_archive summary fields: {e}")
            raise

    async def start_scheduled_flight_processing(self):
        """Start automatic scheduled flight summary processing."""
        try:
            # Validate configuration before starting
            self._validate_flight_summary_config()
            
            # Get interval from config (convert minutes to seconds)
            interval_minutes = getattr(self.config, 'flight_summary_interval_minutes', 60)
            interval_seconds = interval_minutes * 60
            
            self.logger.info(f"🚀 Starting scheduled flight summary processing - interval: {interval_minutes} minutes ({interval_seconds} seconds)")
            
            # Start background task and store reference
            self.flight_summary_task = asyncio.create_task(self._scheduled_processing_loop(interval_seconds))
            
            # Add callback to handle task completion/failure
            self.flight_summary_task.add_done_callback(self._on_flight_summary_task_done)
            
        except Exception as e:
            self.logger.error(f"Failed to start scheduled flight processing: {e}")

    async def start_scheduled_controller_processing(self):
        """Start automatic scheduled controller summary processing."""
        try:
            # Validate configuration before starting
            self._validate_controller_summary_config()
            
            # Get interval from config (convert minutes to seconds)
            interval_minutes = getattr(self.config.controller_summary, 'summary_interval_minutes', 60)
            interval_seconds = interval_minutes * 60
            
            self.logger.info(f"🚀 Starting scheduled controller summary processing - interval: {interval_minutes} minutes ({interval_seconds} seconds)")
            
            # Start background task and store reference
            self.controller_summary_task = asyncio.create_task(self._scheduled_controller_processing_loop(interval_seconds))
            
            # Add callback to handle task completion/failure
            self.controller_summary_task.add_done_callback(self._on_controller_summary_task_done)
            
        except Exception as e:
            self.logger.error(f"Failed to start scheduled controller processing: {e}")

    def _validate_controller_summary_config(self):
        """Validate controller summary configuration before starting scheduled processing."""
        try:
            if not hasattr(self.config, 'controller_summary'):
                raise ValueError("Controller summary configuration not found")
            
            config = self.config.controller_summary
            
            if not config.enabled:
                self.logger.info("Controller summary processing is disabled")
                return
            
            if config.summary_interval_minutes < 1:
                raise ValueError("CONTROLLER_SUMMARY_INTERVAL must be at least 1 minute")
            
            if config.completion_minutes < 1:
                raise ValueError("CONTROLLER_COMPLETION_MINUTES must be at least 1 minute")
            
            if config.retention_hours < 1:
                raise ValueError("CONTROLLER_RETENTION_HOURS must be at least 1 hour")
            
            self.logger.info(f"✅ Controller summary configuration validated: interval={config.summary_interval_minutes}min, completion={config.completion_minutes}min, retention={config.retention_hours}h")
            
        except Exception as e:
            self.logger.error(f"❌ Controller summary configuration validation failed: {e}")
            raise

    def _validate_flight_summary_config(self):
        """Validate flight summary configuration before starting scheduled processing."""
        try:
            if not hasattr(self.config, 'flight_summary'):
                raise ValueError("Flight summary configuration not found")
            
            config = self.config.flight_summary
            
            if not config.enabled:
                self.logger.info("Flight summary processing is disabled")
                return
            
            if config.summary_interval_minutes < 1:
                raise ValueError("FLIGHT_SUMMARY_INTERVAL must be at least 1 minute")
            
            if config.completion_hours < 1:
                raise ValueError("FLIGHT_COMPLETION_HOURS must be at least 1 hour")
            
            if config.retention_hours < config.completion_hours:
                raise ValueError("FLIGHT_RETENTION_HOURS must be greater than FLIGHT_COMPLETION_HOURS")
            
            self.logger.info(f"✅ Flight summary configuration validated: interval={config.summary_interval_minutes}min, completion={config.completion_hours}h, retention={config.retention_hours}h")
            
        except Exception as e:
            self.logger.error(f"❌ Flight summary configuration validation failed: {e}")
            raise

    async def _scheduled_processing_loop(self, interval_seconds: int):
        """Background loop for scheduled flight summary processing."""
        self.logger.info(f"⏰ Scheduled flight summary processing loop started at {datetime.now(timezone.utc)}")
        
        while True:
            try:
                # Log the scheduled run
                self.logger.info(f"⏰ Scheduled flight summary processing started at {datetime.now(timezone.utc)}")
                
                # Process completed flights
                result = await self.process_completed_flights()
                
                # Log the results
                self.logger.info(f"✅ Scheduled processing completed: {result['summaries_created']} summaries created, {result['records_archived']} records archived")
                
                # Wait for next interval
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                self.logger.info("Scheduled flight summary processing task was cancelled")
                break
            except Exception as e:
                self.logger.error(f"❌ Error in scheduled flight processing: {e}")
                # Wait a bit before retrying, but don't wait the full interval
                await asyncio.sleep(60)  # Wait 1 minute before retry

    async def _scheduled_controller_processing_loop(self, interval_seconds: int):
        """Background loop for scheduled controller summary processing."""
        self.logger.info(f"⏰ Scheduled controller summary processing loop started at {datetime.now(timezone.utc)}")
        
        while True:
            try:
                # Log the scheduled run
                self.logger.info(f"⏰ Scheduled controller summary processing started at {datetime.now(timezone.utc)}")
                
                # Process completed controllers
                result = await self.process_completed_controllers()
                
                # Log the results
                self.logger.info(f"✅ Scheduled controller processing completed: {result['summaries_created']} summaries created, {result['records_archived']} records archived")
                
                # Wait for next interval
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                self.logger.info("Scheduled controller summary processing task was cancelled")
                break
            except Exception as e:
                self.logger.error(f"❌ Error in scheduled controller processing: {e}")
                # Wait a bit before retrying, but don't wait the full interval
                await asyncio.sleep(60)  # Wait 1 minute before retry

    async def trigger_flight_summary_processing(self) -> Dict[str, Any]:
        """Manually trigger flight summary processing (for testing/admin use)."""
        try:
            self.logger.info("🔧 Manual flight summary processing triggered")
            result = await self.process_completed_flights()
            self.logger.info(f"✅ Manual processing completed: {result}")
            return result
        except Exception as e:
            self.logger.error(f"❌ Manual processing failed: {e}")
            raise

    async def trigger_controller_summary_processing(self) -> Dict[str, Any]:
        """Manually trigger controller summary processing (for testing/admin use)."""
        try:
            self.logger.info("🔧 Manual controller summary processing triggered")
            result = await self.process_completed_controllers()
            self.logger.info(f"✅ Manual processing completed: {result}")
            return result
        except Exception as e:
            self.logger.error(f"❌ Manual processing failed: {e}")
            raise

    def _on_flight_summary_task_done(self, task):
        """Callback when flight summary task completes or fails."""
        try:
            if task.cancelled():
                self.logger.info("Flight summary task was cancelled")
            elif task.exception():
                self.logger.error(f"Flight summary task failed with exception: {task.exception()}")
                # Restart the task after a delay
                asyncio.create_task(self._restart_flight_summary_task())
            else:
                self.logger.info("Flight summary task completed normally")
        except Exception as e:
            self.logger.error(f"Error in flight summary task callback: {e}")

    def _on_controller_summary_task_done(self, task):
        """Callback when controller summary task completes or fails."""
        try:
            if task.cancelled():
                self.logger.info("Controller summary task was cancelled")
            elif task.exception():
                self.logger.error(f"Controller summary task failed with exception: {task.exception()}")
                # Restart the task after a delay
                asyncio.create_task(self._restart_controller_summary_task())
            else:
                self.logger.info("Controller summary task completed normally")
        except Exception as e:
            self.logger.error(f"Error in controller summary task callback: {e}")

    async def _restart_flight_summary_task(self):
        """Restart the flight summary processing task after a failure."""
        try:
            await asyncio.sleep(30)  # Wait 30 seconds before restarting
            self.logger.info("🔄 Restarting flight summary processing task...")
            await self.start_scheduled_flight_processing()
        except Exception as e:
            self.logger.error(f"Failed to restart flight summary task: {e}")

    async def _restart_controller_summary_task(self):
        """Restart the controller summary processing task after a failure."""
        try:
            await asyncio.sleep(30)  # Wait 30 seconds before restarting
            self.logger.info("🔄 Restarting controller summary processing task...")
            await self.start_scheduled_controller_processing()
        except Exception as e:
            self.logger.error(f"Failed to restart controller summary task: {e}")

    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get processing statistics for the data service.
        
        Returns:
            Dict containing processing statistics
        """
        try:
            stats = {
                "sector_tracking_enabled": getattr(self, 'sector_tracking_enabled', False),
                "sector_loader_available": self.sector_loader is not None if hasattr(self, 'sector_loader') else False,
                "sector_count": self.sector_loader.get_sector_count() if hasattr(self, 'sector_loader') and self.sector_loader else 0,
                "geographic_filter_enabled": self.geographic_boundary_filter.config.enabled if hasattr(self, 'geographic_boundary_filter') else False,
                "callsign_filter_enabled": self.callsign_pattern_filter.config.enabled if hasattr(self, 'callsign_pattern_filter') else False,
                "flight_summary_enabled": getattr(self.config.flight_summary, 'enabled', False) if hasattr(self, 'config') and hasattr(self.config, 'flight_summary') else False,
                "active_flight_sector_states": len(getattr(self, 'flight_sector_states', {})),
                "last_processing_time": getattr(self, '_last_processing_time', None),
                "processing_errors": getattr(self, '_processing_errors', 0),
                "successful_processing_count": getattr(self, '_successful_processing_count', 0),
                "flight_summary_task_status": {
                    "running": self.flight_summary_task is not None and not self.flight_summary_task.done(),
                    "done": self.flight_summary_task is not None and self.flight_summary_task.done(),
                    "cancelled": self.flight_summary_task is not None and self.flight_summary_task.cancelled(),
                    "exception": str(self.flight_summary_task.exception()) if self.flight_summary_task and self.flight_summary_task.done() and self.flight_summary_task.exception() else None
                },
                "controller_summary_task_status": {
                    "running": self.controller_summary_task is not None and not self.controller_summary_task.done(),
                    "done": self.controller_summary_task is not None and self.controller_summary_task.done(),
                    "cancelled": self.controller_summary_task is not None and self.controller_summary_task.cancelled(),
                    "exception": str(self.controller_summary_task.exception()) if self.controller_summary_task and self.controller_summary_task.done() and self.controller_summary_task.exception() else None
                }
            }
            return stats
        except Exception as e:
            self.logger.error(f"Failed to get processing stats: {e}")
            return {"error": str(e)}


# Global service instance
_data_service: Optional[DataService] = None


async def get_data_service() -> DataService:
    """
    Get the global data service instance.
    
    Returns:
        DataService: The global data service instance
        
    Raises:
        RuntimeError: If the data service fails to initialize (critical failure)
    """
    global _data_service
    if _data_service is None:
        _data_service = DataService()
        # Critical: If initialization fails, the app must fail
        if not await _data_service.initialize():
            error_msg = "CRITICAL: Data service initialization failed - application cannot function"
            _data_service.logger.critical(error_msg)
            raise RuntimeError(error_msg)
    return _data_service


def get_data_service_sync() -> DataService:
    """
    Get the global data service instance synchronously (for testing).
    
    Returns:
        DataService: The global data service instance
    """
    global _data_service
    if _data_service is None:
        _data_service = DataService()
        # Note: This won't initialize async components, use only for testing
        # Set a flag to indicate it's a test instance
        _data_service._test_mode = True
    return _data_service 
