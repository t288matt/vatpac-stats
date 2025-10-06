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
from app.filters.frequency_pattern_filter import FrequencyPatternFilter
from app.database import get_database_session
from app.services.session_selector import select_canonical_sessions
from app.models import Flight, Controller, Transceiver
from app.config import get_config, AppConfig
from app.services.atc_detection_service import ATCDetectionService
from app.services.flight_detection_service import FlightDetectionService
from app.utils.sector_loader import SectorLoader
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger_for_module("services.data_service")

# Advisory lock key for cross-process cleanup coordination
_CLEANUP_ADVISORY_LOCK_KEY = 987654321


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
        self.frequency_pattern_filter = FrequencyPatternFilter()

        # (no temporary ingest-only bypass flag required)
        
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
        self.atc_detection_task: Optional[asyncio.Task] = None
        self.flight_detection_task: Optional[asyncio.Task] = None
        # Lock to prevent concurrent cleanup runs
        self._cleanup_lock: asyncio.Lock = asyncio.Lock()
    
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
            
            # Start scheduled flight archiving processing
            await self.start_scheduled_flight_archiving()
            
            # Start scheduled ATC detection processing
            if self.config.detection.enabled:
                await self.start_scheduled_atc_detection_processing()
                await self.start_scheduled_flight_detection_processing()
            
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
                            
                            # NEW: Track sector occupancy for this flight - pass authoritative last_updated when available
                            flight_last_updated = self._parse_timestamp(flight_dict.get('last_updated'))
                            await self._track_sector_occupancy(flight_dict, session, flight_last_updated)
                            
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
        
        # Apply frequency filtering (exclude UNICOM frequencies like 122.800 MHz)
        filtered_transceivers = self.frequency_pattern_filter.filter_transceivers_list(filtered_transceivers)
        
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
    
    async def _track_sector_occupancy(self, flight_dict: Dict[str, Any], session: AsyncSession, flight_last_updated: Optional[datetime] = None) -> None:
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
        
        # Handle sector transitions (pass authoritative timestamp when available)
        if current_sector != previous_sector or should_exit:
            await self._handle_sector_transition(
                callsign, previous_sector, current_sector, 
                lat, lon, altitude, session, should_exit, flight_last_updated, flight_dict
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
        altitude: int, session: AsyncSession, should_exit: bool = False,
        flight_last_updated: Optional[datetime] = None, flight_dict: Dict[str, Any] = None
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
        # Prefer authoritative flight_last_updated when provided to avoid clock/visibility races
        timestamp = flight_last_updated or datetime.now(timezone.utc)
        
        # CRITICAL FIX: Close ALL open sectors for this flight before entering a new one
        # This prevents multiple open sectors when memory state gets corrupted
        if current_sector != previous_sector or should_exit:
            await self._close_all_open_sectors_for_flight(
                callsign, session, flight_last_updated, lat, lon, altitude
            )
        
        # Enter new sector (only if different from previous)
        if current_sector and current_sector != previous_sector:
            # Extract additional flight data for sector tracking
            cid = flight_dict.get("cid") if flight_dict else None
            departure = flight_dict.get("departure") if flight_dict else None
            arrival = flight_dict.get("arrival") if flight_dict else None
            
            await self._record_sector_entry(
                callsign, current_sector, lat, lon, altitude, timestamp, session,
                cid, departure, arrival
            )

    async def _record_sector_entry(
        self, callsign: str, sector_name: str, lat: float, lon: float, 
        altitude: int, timestamp: datetime, session: AsyncSession,
        cid: int = None, departure: str = None, arrival: str = None
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
            cid: VATSIM user ID
            departure: Departure airport code
            arrival: Arrival airport code
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
                        callsign, cid, departure, arrival, sector_name, entry_timestamp, exit_timestamp,
                        duration_seconds, entry_lat, entry_lon, exit_lat, exit_lon,
                        entry_altitude, exit_altitude
                    ) VALUES (
                        :callsign, :cid, :departure, :arrival, :sector_name, :timestamp, NULL, 0,
                        :lat, :lon, NULL, NULL, :altitude, NULL
                    )
                """), {
                    "callsign": callsign, "cid": cid, "departure": departure, "arrival": arrival,
                    "sector_name": sector_name, "timestamp": timestamp, 
                    "lat": lat, "lon": lon, "altitude": altitude
                })
                
                self.logger.debug(f"Flight {callsign} entered sector {sector_name}")
    
        except Exception as e:
            self.logger.error(f"Failed to record sector entry for {callsign}: {e}")

    async def _close_all_open_sectors_for_flight(
        self, callsign: str, session: AsyncSession, flight_last_updated: Optional[datetime] = None,
        current_lat: Optional[float] = None, current_lon: Optional[float] = None, 
        current_altitude: Optional[int] = None
    ) -> None:
        """
        Close ALL open sectors for a flight to prevent multiple open sectors.
        
        This is a critical fix that ensures only one sector is open per flight
        by closing any existing open sectors before entering a new one.
        
        Args:
            callsign: Flight callsign
            session: Database session
            flight_last_updated: Authoritative timestamp for exit (optional)
            current_lat: Current flight latitude (optional)
            current_lon: Current flight longitude (optional)
            current_altitude: Current flight altitude (optional)
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
            
            # Get position data - use current position if provided, otherwise query database
            exit_lat = current_lat
            exit_lon = current_lon
            exit_altitude = current_altitude
            
            if exit_lat is None or exit_lon is None or exit_altitude is None:
                # Fall back to database query for missing position data
                flight_result = await session.execute(text("""
                    SELECT latitude, longitude, altitude, last_updated
                    FROM flights 
                    WHERE callsign = :callsign 
                    ORDER BY last_updated DESC 
                    LIMIT 1
                """), {"callsign": callsign})
                last_flight = flight_result.fetchone()
                if not last_flight:
                    self.logger.warning(f"No flight record found for {callsign} and no current position provided")
                    return
                
                # Use database values for any missing current position data
                exit_lat = exit_lat or last_flight.latitude
                exit_lon = exit_lon or last_flight.longitude
                exit_altitude = exit_altitude or last_flight.altitude
            
            self.logger.debug(f"Closing {len(open_sectors)} open sectors for flight {callsign}")
            
            # Close each open sector
            for sector in open_sectors:
                sector_name = sector.sector_name
                entry_timestamp = sector.entry_timestamp
                
                # Calculate duration using the provided flight_last_updated if present, else current timestamp
                exit_ts = flight_last_updated or datetime.now(timezone.utc)
                duration_seconds = int((exit_ts - entry_timestamp).total_seconds())
                
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
                    "exit_timestamp": exit_ts,
                    "exit_lat": exit_lat,           # Use current position or fallback from database
                    "exit_lon": exit_lon,           # Use current position or fallback from database
                    "exit_altitude": exit_altitude, # Use current position or fallback from database
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
                    duration_seconds = GREATEST(0, FLOOR(EXTRACT(EPOCH FROM (:timestamp - entry_timestamp))))::INTEGER
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
        self, callsign: str, session: AsyncSession, 
        logon_time: datetime = None, completion_time: datetime = None
    ) -> Dict[str, int]:
        """
        Calculate time spent in each sector for a completed flight.
        
        Args:
            callsign: Flight callsign
            session: Database session
            logon_time: Flight logon time to filter sector data
            completion_time: Flight completion time to filter sector data
            
        Returns:
            Dict mapping sector names to minutes spent in each sector
        """
        try:
            # Build the query with optional flight session boundary filtering
            query = """
                SELECT sector_name, 
                       SUM(duration_seconds) / 60 as minutes
                FROM flight_sector_occupancy 
                WHERE callsign = :callsign 
                AND exit_timestamp IS NOT NULL
            """
            
            params = {"callsign": callsign}
            
            # Add flight session boundary filtering if timestamps are provided
            if logon_time and completion_time:
                query += " AND entry_timestamp BETWEEN :logon_time AND :completion_time"
                params["logon_time"] = logon_time
                params["completion_time"] = completion_time
                self.logger.debug(f"Filtering sector data for {callsign} between {logon_time} and {completion_time}")
            else:
                self.logger.warning(f"No flight session boundaries provided for {callsign} - using all sector data (may cause callsign collision issues)")
            
            query += " GROUP BY sector_name ORDER BY minutes DESC"
            
            result = await session.execute(text(query), params)
            
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

    async def _get_total_airborne_time(self, callsign: str, session: AsyncSession, 
                                 logon_time: datetime = None, completion_time: datetime = None) -> int:
        """
        Calculate time spent above 1500ft for a completed flight.
        
        Args:
            callsign: Flight callsign
            session: Database session
            logon_time: Flight logon time to filter data
            completion_time: Flight completion time to filter data
            
        Returns:
            Total minutes spent above 1500ft
        """
        try:
            # Build the query with flight session boundary filtering
            query = """
                SELECT COUNT(*) as airborne_count
                FROM flights
                WHERE callsign = :callsign 
                AND altitude > 1500
            """
            
            params = {"callsign": callsign}
            
            # Add flight session boundary filtering if timestamps are provided
            if logon_time and completion_time:
                query += " AND last_updated BETWEEN :logon_time AND :completion_time"
                params["logon_time"] = logon_time
                params["completion_time"] = completion_time
            
            result = await session.execute(text(query), params)
            
            # Calculate minutes based on polling interval from environment variables
            airborne_count = result.scalar() or 0
            
            # Get polling interval from environment (default to 60 seconds if not set)
            vatsim_polling_interval = int(os.getenv('VATSIM_POLLING_INTERVAL', '60'))
            polling_interval_minutes = vatsim_polling_interval / 60.0
            
            self.logger.info(f"Using VATSIM polling interval of {vatsim_polling_interval} seconds ({polling_interval_minutes} minutes)")
            return int(airborne_count * polling_interval_minutes)
        
        except Exception as e:
            self.logger.error(f"Failed to calculate airborne time for {callsign}: {e}")
            return 0
    
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
                
                # Remove inactive flights from in-memory sector states
                if hasattr(self, 'flight_sector_states'):
                    inactive_callsigns = set(self.flight_sector_states.keys()) - active_callsigns
                    
                    for callsign in inactive_callsigns:
                        # Close any open sector entries for this callsign
                        await self._close_open_sector_entries(callsign, session)
                        try:
                            del self.flight_sector_states[callsign]
                        except Exception:
                            # Already removed or concurrent change
                            pass
                        
                    if inactive_callsigns:
                        self.logger.debug(f"Cleaned up sector states for {len(inactive_callsigns)} inactive flights")

                # ALSO: find open sector callsigns present in DB but not tracked in memory
                # This catches cases where the service restarted or in-memory state was lost.
                open_calls_result = await session.execute(text("""
                    SELECT DISTINCT callsign FROM flight_sector_occupancy WHERE exit_timestamp IS NULL
                """))
                open_callsigns = {r.callsign for r in open_calls_result.fetchall()}

                # Candidate callsigns to close: open in DB and not recently active
                to_close_callsigns = open_callsigns - active_callsigns
                # Avoid closing large numbers synchronously in one pass; process in batches
                if to_close_callsigns:
                    self.logger.info(f"Found {len(to_close_callsigns)} DB-open sector callsigns not active in memory; attempting to close up to 250 of them")
                    batch = list(to_close_callsigns)[:250]
                    for callsign in batch:
                        try:
                            await self._close_open_sector_entries(callsign, session)
                        except Exception as e:
                            self.logger.debug(f"Failed to close DB-open sectors for {callsign}: {e}")

        except Exception as e:
            self.logger.error(f"Failed to cleanup sector states: {e}")

    async def _close_stale_sectors(self, session: AsyncSession, cleanup_timeout: int) -> int:
        """Helper to close stale sectors. Returns number closed."""
        try:
            stale_cutoff = datetime.now(timezone.utc) - timedelta(seconds=cleanup_timeout)
            sectors_closed = 0

            # Find flights with open sectors that haven't been updated recently
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

            self.logger.info(f"_close_stale_sectors: stale_candidates={len(stale_sectors)}")

            for sector in stale_sectors:
                callsign = sector.callsign
                sector_name = sector.sector_name
                entry_timestamp = sector.entry_timestamp
                last_lat = sector.latitude
                last_lon = sector.longitude
                last_altitude = sector.altitude
                last_updated = sector.last_updated

                duration_seconds = int((last_updated - entry_timestamp).total_seconds())

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
                    "exit_timestamp": last_updated,
                    "exit_lat": last_lat,
                    "exit_lon": last_lon,
                    "exit_altitude": last_altitude,
                    "duration_seconds": duration_seconds,
                    "callsign": callsign,
                    "sector_name": sector_name
                })

                sectors_closed += 1

            if sectors_closed > 0:
                await session.commit()
                self.logger.info(f"_close_stale_sectors: closed {sectors_closed} sectors")

            return sectors_closed

        except Exception:
            await session.rollback()
            raise

    async def _cleanup_memory_state_for_closed_sectors(self, session: AsyncSession) -> int:
        """Helper to clear in-memory flight states when DB shows their sectors are closed."""
        try:
            if not hasattr(self, 'flight_sector_states') or not self.flight_sector_states:
                return 0

            # Get callsigns which currently have open sector rows in DB (exit_timestamp IS NULL)
            # We should *retain* in-memory state for those callsigns. Only remove memory
            # entries for callsigns that do NOT have open DB rows (i.e., truly closed).
            open_calls = set()
            try:
                res = await session.execute(text("SELECT DISTINCT callsign FROM flight_sector_occupancy WHERE exit_timestamp IS NULL"))
                try:
                    vals = res.scalars().all()
                    if isinstance(vals, list):
                        open_calls = set(vals)
                except Exception:
                    rows = res.fetchall()
                    for r in rows:
                        try:
                            open_calls.add(r[0])
                        except Exception:
                            if hasattr(r, 'callsign'):
                                open_calls.add(r.callsign)
            except Exception:
                open_calls = set()

            removed = 0
            # Remove any in-memory callsigns that are NOT present in open_calls
            for callsign in list(self.flight_sector_states.keys()):
                if callsign not in open_calls:
                    try:
                        del self.flight_sector_states[callsign]
                        removed += 1
                    except Exception:
                        pass

            return removed

        except Exception:
            return 0

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

    async def backfill_fso_exit_fields(self, batch_size: int = 500) -> int:
        """Backfill exit fields for flight_sector_occupancy in batches.

        Tries flights -> flights_archive -> flight_summaries for a timestamp/altitude.
        Returns number of rows updated in this run.
        """
        updated = 0
        try:
            async with get_database_session() as session:
                # Build candidate CTE and update in a single statement, limited by batch_size
                update_sql = text(f"""
WITH candidates AS (
  SELECT fso.id,
         COALESCE(f.last_updated, fa.last_updated, fs.completion_time) AS chosen_last_updated,
         COALESCE(f.altitude, fa.altitude) AS chosen_altitude,
         COALESCE(f.latitude, fa.latitude) AS chosen_lat,
         COALESCE(f.longitude, fa.longitude) AS chosen_lon
  FROM flight_sector_occupancy fso
  LEFT JOIN LATERAL (
    SELECT altitude, latitude, longitude, last_updated
    FROM flights f
    WHERE f.callsign = fso.callsign
    ORDER BY last_updated DESC
    LIMIT 1
  ) f ON true
  LEFT JOIN LATERAL (
    SELECT altitude, latitude, longitude, last_updated
    FROM flights_archive fa
    WHERE fa.callsign = fso.callsign
    ORDER BY last_updated DESC
    LIMIT 1
  ) fa ON true
  LEFT JOIN LATERAL (
    SELECT completion_time
    FROM flight_summaries fs
    WHERE fs.callsign = fso.callsign
    ORDER BY completion_time DESC
    LIMIT 1
  ) fs ON true
  WHERE fso.exit_timestamp IS NULL
    AND (f.last_updated IS NOT NULL OR fa.last_updated IS NOT NULL OR fs.completion_time IS NOT NULL)
  ORDER BY fso.entry_timestamp
  LIMIT :limit
)
UPDATE flight_sector_occupancy fso
SET exit_timestamp = c.chosen_last_updated,
    exit_altitude  = c.chosen_altitude,
    exit_lat       = COALESCE(fso.exit_lat, c.chosen_lat),
    exit_lon       = COALESCE(fso.exit_lon, c.chosen_lon),
    duration_seconds = EXTRACT(EPOCH FROM (c.chosen_last_updated - fso.entry_timestamp))::INTEGER
FROM candidates c
WHERE fso.id = c.id
  AND c.chosen_last_updated IS NOT NULL
RETURNING fso.id;
""")

                result = await session.execute(update_sql, {"limit": batch_size})
                rows = result.fetchall()
                updated = len(rows)
                if updated > 0:
                    await session.commit()
                    self.logger.info(f"backfill_fso_exit_fields: updated {updated} rows")

        except Exception as e:
            self.logger.error(f"backfill_fso_exit_fields failed: {e}")

        return updated

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
        # Delegate to helper methods so unit tests can mock internals
        cleanup_timeout = int(os.getenv("CLEANUP_FLIGHT_TIMEOUT", "300"))
        # Acquire in-process lock to avoid concurrent cleanup runs
        async with self._cleanup_lock:
            # Try to obtain a Postgres transaction-level advisory lock to coordinate across processes
            # Using pg_try_advisory_xact_lock ensures the lock is automatically released when the transaction ends
            async with get_database_session() as session:
                got_lock = False
                try:
                    res = await session.execute(text('SELECT pg_try_advisory_xact_lock(:k) AS taken'), {"k": _CLEANUP_ADVISORY_LOCK_KEY})
                    # res.fetchone() may be a coroutine in tests/mocks; handle both
                    maybe = res.fetchone()
                    if asyncio.iscoroutine(maybe):
                        took = await maybe
                    else:
                        took = maybe
                    got_lock = bool(took[0]) if took is not None else False
                except Exception:
                    # If advisory lock check fails (e.g., test mocks), assume lock acquired
                    got_lock = True

                # If we didn't get the lock, skip cleanup (another process is handling it)
                if not got_lock:
                    self.logger.debug("Skipping cleanup, another process has the advisory lock")
                    return {
                        "status": "skipped",
                        "sectors_closed": 0,
                        "memory_states_cleaned": 0,
                        "cleanup_time_seconds": 0,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }

                # Call DB-wide close helper
                sectors_closed = await self._close_stale_sectors(session, cleanup_timeout)

                # Clean up in-memory states for closed sectors
                memory_states_cleaned = await self._cleanup_memory_state_for_closed_sectors(session)

                # No need to release the lock in finally block - xact lock is automatically released when transaction ends

            return {
                "status": "success",
                "sectors_closed": sectors_closed,
                "memory_states_cleaned": memory_states_cleaned,
                "cleanup_time_seconds": 0,  # placeholder, measured by caller if needed
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    # ============================================================================
    # FLIGHT SUMMARY PROCESSING METHODS
    # ============================================================================

    async def _find_sessions_with_null_completion(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Find flight summaries that have NULL completion times and need to be fixed.
        These are sessions that exist in flight_summaries but are missing completion data.
        """
        query = text("""
            SELECT 
                callsign,
                cid,
                departure,
                arrival,
                logon_time as session_start,
                logon_time as session_end,  -- Will be updated with actual completion time
                deptime as latest_deptime,
                route as latest_route
            FROM flight_summaries
            WHERE completion_time IS NULL
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        
        async with get_database_session() as session:
            result = await session.execute(query, {"limit": limit})
            rows = result.fetchall()
            sessions = []
            for r in rows:
                sessions.append({
                    "callsign": r.callsign,
                    "cid": r.cid,
                    "departure": r.departure,
                    "arrival": r.arrival,
                    "session_start": r.session_start,
                    "session_end": r.session_end,
                    "latest_deptime": r.latest_deptime,
                    "latest_route": r.latest_route,
                })
            return sessions

    async def _get_actual_completion_time_from_flights(self, callsign: str, departure: str, arrival: str, cid: int, deptime: str, session: AsyncSession) -> datetime:
        """Get actual completion time from the most recent record in flights or flights_archive table."""
        try:
            # Query both flights and flights_archive tables for the most recent record for this specific flight
            result = await session.execute(text("""
                SELECT MAX(last_updated) as actual_completion_time
                FROM (
                    SELECT last_updated FROM flights 
                    WHERE callsign = :callsign 
                    AND departure = :departure 
                    AND arrival = :arrival 
                    AND cid = :cid
                    AND deptime = :deptime
                    UNION ALL
                    SELECT last_updated FROM flights_archive 
                    WHERE callsign = :callsign 
                    AND departure = :departure 
                    AND arrival = :arrival 
                    AND cid = :cid
                    AND deptime = :deptime
                ) combined
            """), {
                "callsign": callsign,
                "departure": departure,
                "arrival": arrival,
                "cid": cid,
                "deptime": deptime
            })
            
            row = result.fetchone()
            if row and row.actual_completion_time:
                self.logger.debug(f"Using actual completion time for {callsign}: {row.actual_completion_time}")
                return row.actual_completion_time
            else:
                # This should not happen if the flight was identified as completed
                self.logger.warning(f"No completion time found for {callsign}, this should not happen")
                return datetime.now(timezone.utc)
                
        except Exception as e:
            self.logger.error(f"Error getting actual completion time for {callsign}: {e}")
            return datetime.now(timezone.utc)

    async def _identify_completed_flights(self, completion_hours: int) -> List[dict]:
        """Identify flights that have been completed for the specified number of hours."""
        try:
            completion_threshold = datetime.now(timezone.utc) - timedelta(hours=completion_hours)
            
            query = """
                SELECT DISTINCT f.callsign, f.departure, f.arrival, f.cid, f.deptime
                FROM flights f
                WHERE f.last_updated < :completion_threshold
                  AND f.logon_time IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1
                      FROM flight_summaries fs
                      WHERE fs.callsign   = f.callsign
                        AND fs.cid        IS NOT DISTINCT FROM f.cid
                        AND fs.departure  IS NOT DISTINCT FROM f.departure
                        AND fs.arrival    IS NOT DISTINCT FROM f.arrival
                        AND fs.logon_time IS NOT DISTINCT FROM f.logon_time
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
        """
        DEPRECATED: Legacy flight summary creation method.
        
        This method is no longer used in production. All flight summary processing
        now goes through _process_completed_flights_canonical() which provides:
        - Better archive table integration
        - Consistent field population  
        - Simplified architecture
        
        This method is kept only for potential test compatibility.
        """
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
                    
                    # Get actual completion time from flights table (most recent record)
                    actual_completion_time = await self._get_actual_completion_time_from_flights(
                        callsign, departure, arrival, cid, deptime, session
                    )
                    
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
                    # DEBUG: log ATC detection raw for this flight (keep concise)
                    try:
                        self.logger.debug(f"ATC detection result for {callsign}: interactions={atc_data.get('interactions_detected')} controllers={len(atc_data.get('controller_callsigns', {}))}")
                        # If this is the flight we are tracing, persist full payload for inspection
                        if callsign == 'FJI917':
                            import json, os
                            debug_path = f"/tmp/flight_enrich_{callsign}_{first_record.logon_time.isoformat()}.json"
                            with open(debug_path, 'w') as df:
                                json.dump({
                                    'callsign': callsign,
                                    'logon_time': str(first_record.logon_time),
                                    'atc_data': atc_data
                                }, df, default=str, indent=2)
                            self.logger.debug(f"Wrote flight enrichment debug file: {debug_path}")
                    except Exception:
                        self.logger.exception(f"Failed to log ATC detection for {callsign}")
                    
                    # NEW: Calculate sector breakdown for this completed flight with flight session boundaries
                    sector_breakdown = await self._calculate_sector_breakdown(
                        callsign, session, 
                        logon_time=first_record.logon_time, 
                        completion_time=actual_completion_time
                    )
                    primary_sector = self._get_primary_sector(sector_breakdown)
                    total_sectors = len(sector_breakdown)
                    total_enroute_time = sum(sector_breakdown.values())
                    
                    # COMMENTED OUT: UNUSED CODE PATH - This code is not being executed by canonical processing
                    # The actual canonical processing uses _process_completed_flights_canonical() method
                    # which has its own logic for creating flight summaries
                    
                    # # Create summary data
                    # # DEBUG: Log aircraft fields for JST458
                    # if callsign == 'JST458':
                    #     self.logger.info(f"🔍 DEBUG: JST458 aircraft fields - type: {getattr(first_record, 'latest_aircraft_type', 'MISSING')}, faa: {getattr(first_record, 'latest_aircraft_faa', 'MISSING')}, short: {getattr(first_record, 'latest_aircraft_short', 'MISSING')}")
                    #     self.logger.info(f"🔍 DEBUG: JST458 first_record attributes: {dir(first_record)}")
                    # 
                    # summary_data = {
                    #     "callsign": callsign,
                    #     "aircraft_type": first_record.get('latest_aircraft_type', None),
                    #     "departure": departure,
                    #     "arrival": arrival,
                    #     "deptime": deptime,
                    #     "logon_time": first_record.get('session_start', first_record.get('logon_time')),
                    #     "route": first_record.get('latest_route', first_record.get('route')),
                    #     "flight_rules": first_record.get('latest_flight_rules', None),
                    #     "aircraft_faa": first_record.get('latest_aircraft_faa', None),
                    #     "planned_altitude": first_record.get('latest_planned_altitude', None),
                    #     "aircraft_short": first_record.get('latest_aircraft_short', None),
                    #     "cid": first_record.get('cid'),
                    #     "name": first_record.get('latest_name', None),
                    #     "server": first_record.get('latest_server', None),
                    #     "pilot_rating": first_record.get('latest_pilot_rating', None),
                    #     "military_rating": first_record.get('latest_military_rating', None),
                    #     "controller_callsigns": json.dumps(self._convert_for_json(atc_data["controller_callsigns"])),
                    #     "controller_time_percentage": atc_data["controller_time_percentage"],
                    #     "airborne_controller_time_percentage": atc_data["airborne_controller_time_percentage"],
                    #     "time_online_minutes": total_minutes,
                    #     "primary_enroute_sector": primary_sector,
                    #     "total_enroute_sectors": total_sectors,
                    #     "total_enroute_time_minutes": total_enroute_time,
                    #     "sector_breakdown": json.dumps(self._convert_for_json(sector_breakdown)),
                    #     "completion_time": actual_completion_time
                    # }
                    
                    # Skip this entire code path as it's unused - canonical processing uses different method
                    continue
                    
                    # REMOVED: All code after continue statement was unreachable dead code
                    # that referenced undefined variables (summary_data was commented out).
                    
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
            # Canonical session pipeline is the default path
            self.logger.info("🧭 Canonical session pipeline (default) - using selector")
            result = await self._process_completed_flights_canonical()
            # Emit a clear info-level summary for monitoring with number of flights processed
            num_processed = (
                result.get("summaries_created")
                if isinstance(result, dict) and result.get("summaries_created") is not None
                else result.get("summaries_processed") if isinstance(result, dict) and result.get("summaries_processed") is not None
                else result.get("sessions_detected") if isinstance(result, dict) and result.get("sessions_detected") is not None
                else 0
            )
            self.logger.info(f"Flight summary processing finished: {num_processed} flights processed")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Flight summary processing failed: {e}")
            raise

    @handle_service_errors
    @log_operation("process_completed_controllers")
    async def process_completed_controllers(self) -> Dict[str, Any]:
        """Main entry point for controller summary processing."""
        try:
            self.logger.debug("Starting controller summary processing")
            
            # Get configuration
            completion_minutes = getattr(self.config.controller_summary, 'completion_minutes', 30)
            retention_hours = getattr(self.config.controller_summary, 'retention_hours', 168)
            self.logger.debug(f"Config: completion_minutes={completion_minutes}, retention_hours={retention_hours}")
            
            # Step 1: Identify completed controllers
            completed_controllers = await self._identify_completed_controllers(completion_minutes)
            self.logger.info(f"Identify completed controllers -> {len(completed_controllers)} candidates")
            
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
            self.logger.info("Creating controller summaries...")
            summaries_created_result = await self._create_controller_summaries(completed_controllers)
            self.logger.info(f"Create summaries result: {summaries_created_result}")
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
            self.logger.debug("Summary Processing Results")
            self.logger.debug(f"Successfully processed: {summaries_created} controllers")
            self.logger.debug(f"Failed to process: {failed_count} controllers")
            self.logger.debug(f"Archived: {records_archived} controller records")
            self.logger.debug(f"Deleted: {records_deleted} controller records")
            
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
            
            self.logger.debug(f"Controller summary processing completed: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Controller summary processing failed: {e}")
            raise

    async def _identify_completed_controllers(self, completion_minutes: int) -> List[tuple]:
        """Identify controllers that have been inactive for the specified time."""
        try:
            completion_threshold = datetime.now(timezone.utc) - timedelta(minutes=completion_minutes)
            self.logger.debug(f"Identify completed controllers: completion_minutes={completion_minutes}, threshold_utc={completion_threshold}")
            
            query = """
                SELECT DISTINCT c.callsign, c.cid, c.logon_time, MAX(c.last_updated) as session_end_time
                FROM controllers c
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM controller_summaries cs
                    WHERE cs.callsign = c.callsign
                      AND cs.cid IS NOT DISTINCT FROM c.cid
                      AND cs.session_start_time = c.logon_time
                )
                GROUP BY c.callsign, c.cid, c.logon_time
                HAVING MAX(c.last_updated) < :completion_threshold
            """
            
            async with get_database_session() as session:
                self.logger.debug("Executing completed controllers query...")
                result = await session.execute(text(query), {"completion_threshold": completion_threshold})
                completed_controllers = result.fetchall()
                count = len(completed_controllers)
                self.logger.debug(f"Query completed: {count} candidates found")
                if count:
                    for idx, row in enumerate(completed_controllers[:3], 1):
                        try:
                            callsign, cid, logon_time, session_end_time = row
                        except Exception:
                            callsign = getattr(row, 'callsign', None)
                            cid = getattr(row, 'cid', None)
                            logon_time = getattr(row, 'logon_time', None)
                            session_end_time = getattr(row, 'session_end_time', None)
                        self.logger.debug(
                            f"Candidate[{idx}]: callsign={callsign}, cid={cid}, logon_time={logon_time}, session_end_time={session_end_time}"
                        )
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
        
        self.logger.debug(f"_create_controller_summaries: received {len(completed_controllers)} completed controllers")
        async with get_database_session() as session:
            for controller_key in completed_controllers:
                callsign, cid, logon_time, session_end_time = controller_key
                
                try:
                    self.logger.debug(
                        f"Processing controller candidate callsign={callsign}, cid={cid}, logon_time={logon_time}, session_end_time={session_end_time}"
                    )
                    # Get all records for this controller including potential reconnections within 5 minutes
                    # The reconnection logic now properly measures the gap between session end and next session start
                    # Calculate the reconnection window in Python to avoid SQL interval arithmetic issues
                    reconnection_window = session_end_time + timedelta(minutes=reconnection_threshold_minutes)
                    
                    controller_records = await session.execute(text("""
                        SELECT * FROM controllers 
                        WHERE callsign = :callsign 
                        AND cid = :cid
                        AND (
                            logon_time = :logon_time  -- Original session
                            OR (
                                logon_time > :logon_time
                                AND logon_time <= :reconnection_window
                            )
                        )
                        ORDER BY created_at
                    """), {
                        "callsign": callsign,
                        "cid": cid,
                        "logon_time": logon_time,
                        "reconnection_window": reconnection_window
                    })
                    
                    records = controller_records.fetchall()
                    self.logger.debug(f"Fetched {len(records)} controller records for {callsign} in merged window")
                    if not records:
                        self.logger.warning(f"No records found for controller {callsign} with logon_time {logon_time}")
                        failed_count += 1
                        continue
                    
                    # Get first and last records across merged sessions
                    first_record = records[0]
                    last_record = records[-1]
                    
                    # Calculate total session duration including reconnections
                    session_duration_minutes = int((last_record.last_updated - first_record.logon_time).total_seconds() / 60)
                    self.logger.debug(
                        f"{callsign} session window: start={first_record.logon_time}, end={last_record.last_updated}, duration_min={session_duration_minutes}"
                    )

                    # Handle 0-minute sessions by adjusting them to 1-minute minimum
                    # This prevents constraint violations while maintaining data integrity
                    if session_duration_minutes == 0:
                        session_duration_minutes = 1
                        # Adjust the end time slightly to satisfy database constraint
                        adjusted_end_time = first_record.logon_time + timedelta(minutes=1)
                        self.logger.debug(f"🔄 Adjusted 0-minute session for {callsign} to 1 minute")
                    else:
                        adjusted_end_time = last_record.last_updated

                    # Get all frequencies used across merged sessions
                    frequencies_used = await self._get_session_frequencies(callsign, logon_time, session_end_time, session)
                    self.logger.debug(f"{callsign} frequencies_used count={len(frequencies_used) if frequencies_used else 0}")
                    
                    # Get aircraft interaction data across merged sessions
                    aircraft_data = await self._get_aircraft_interactions(callsign, logon_time, session_end_time, session)
                    self.logger.debug(
                        f"{callsign} aircraft_interactions total={aircraft_data.get('total_aircraft', 0)}, peak={aircraft_data.get('peak_count', 0)}"
                    )
                    
                    # Create merged summary data
                    summary_data = {
                        "callsign": callsign,
                        "cid": first_record.cid,
                        "name": first_record.name,
                        "session_start_time": first_record.logon_time,
                        "session_end_time": adjusted_end_time,
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
                            hourly_aircraft_breakdown, frequencies_used, aircraft_details,
                            enrichment_status, enrichment_run_after
                        ) VALUES (
                            :callsign, :cid, :name, :session_start_time, :session_end_time,
                            :session_duration_minutes, :rating, :facility, :server,
                            :total_aircraft_handled, :peak_aircraft_count,
                            :hourly_aircraft_breakdown, :frequencies_used, :aircraft_details,
                            'pending', NOW()
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
                    self.logger.error(f"❌ Failed to process controller {callsign} (cid={cid}, logon_time={logon_time}): {e}")
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

    async def _get_session_frequencies(self, callsign: str, logon_time: datetime, session_end_time: datetime, session) -> List[str]:
        """Get all frequencies used during a controller session including reconnections."""
        try:
            result = await session.execute(text("""
                SELECT DISTINCT frequency 
                FROM controllers 
                WHERE callsign = :callsign 
                AND logon_time >= :logon_time
                AND logon_time <= :session_end_time
                AND frequency IS NOT NULL
                ORDER BY frequency
            """), {
                "callsign": callsign,
                "logon_time": logon_time,
                "session_end_time": session_end_time
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

            # DEBUG: persist the returned flight_data to logs for diagnostics
            try:
                # Keep payload size reasonable in logs
                import json
                short = json.dumps({
                    "flights_detected": flight_data.get("flights_detected"),
                    "total_aircraft": flight_data.get("total_aircraft"),
                    "interactions_detected": flight_data.get("interactions_detected"),
                    "aircraft_callsigns_count": len(flight_data.get("aircraft_callsigns") or []),
                    "details_preview": (flight_data.get("details") or [])[:3]
                }, default=str)
                self.logger.debug(f"Flight detection raw for {callsign}: {short}")
            except Exception:
                self.logger.exception(f"Flight detection raw (error serializing) for {callsign}")

            # EXTRA DEBUG: show full details size and sample (non-serializing-safe guard)
            try:
                details = flight_data.get("details")
                if details is None:
                    self.logger.debug(f"Flight detection details for {callsign}: None")
                elif isinstance(details, list):
                    self.logger.debug(f"Flight detection details for {callsign}: len={len(details)}; sample_callsigns={[d.get('callsign') for d in details[:5]]}")
                else:
                    self.logger.debug(f"Flight detection details for {callsign}: type={type(details)}")
            except Exception:
                self.logger.exception(f"Flight detection details logging failed for {callsign}")
            
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
                callsign, cid, logon_time, session_end_time = controller_key
                
                try:
                    # Respect archive delay configuration to avoid archiving very recent sessions
                    import os
                    from datetime import datetime, timezone, timedelta
                    days_str = os.getenv("CONTROLLER_DAYS_BEFORE_ARCHIVE", "0")
                    try:
                        days_before = int(days_str)
                    except Exception:
                        days_before = 0
                    archive_cutoff = datetime.now(timezone.utc) - timedelta(days=days_before) if days_before > 0 else None
                    # Archive all records for this session
                    if archive_cutoff:
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
                            WHERE callsign = :callsign AND logon_time = :logon_time AND last_updated <= :archive_cutoff
                        """), {
                            "callsign": callsign,
                            "logon_time": logon_time,
                            "archive_cutoff": archive_cutoff,
                        })
                    else:
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
                callsign, cid, logon_time, session_end_time = controller_key
                
                try:
                    # Only delete if rows are older than configured archive delay
                    import os
                    from datetime import datetime, timezone, timedelta
                    days_str = os.getenv("CONTROLLER_DAYS_BEFORE_ARCHIVE", "0")
                    try:
                        days_before = int(days_str)
                    except Exception:
                        days_before = 0
                    if days_before > 0:
                        archive_cutoff = datetime.now(timezone.utc) - timedelta(days=days_before)
                        result = await session.execute(text("""
                            DELETE FROM controllers
                            WHERE callsign = :callsign AND logon_time = :logon_time AND last_updated <= :archive_cutoff
                        """), {
                            "callsign": callsign,
                            "logon_time": logon_time,
                            "archive_cutoff": archive_cutoff
                        })
                    else:
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
                    
                    # Respect archive delay configuration to avoid archiving very recent flights
                    import os
                    from datetime import datetime, timezone, timedelta
                    days_str = os.getenv("FLIGHT_DAYS_BEFORE_ARCHIVE", "0")
                    try:
                        days_before = int(days_str)
                    except Exception:
                        days_before = 0
                    archive_cutoff = datetime.now(timezone.utc) - timedelta(days=days_before) if days_before > 0 else None

                    # Archive each record
                    for record in records:
                        # If archive_cutoff is set, only archive records older than cutoff
                        if archive_cutoff and record.last_updated and record.last_updated > archive_cutoff:
                            # Skip archiving this recent record
                            continue

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

    async def _process_completed_flights_canonical(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Process completed flights using the canonical session selector (feature-flagged).
        
        Stage 2: transactional upsert → archive (≤ HWM) → delete per session under advisory xact lock.
        """
        # DEBUG: Log that canonical processing is starting
        self.logger.info("🚀 CANONICAL PROCESSING STARTED - _process_completed_flights_canonical() called")
        async def _process_one_session(session, session_obj) -> int:
            # helper not used externally in this patch, placeholder for future decomposition
            return 1

        try:
            import os
            # Use same horizon as FLIGHT_COMPLETION_HOURS
            completion_hours_env = os.getenv("FLIGHT_COMPLETION_HOURS", "8")
            completion_hours = int(completion_hours_env)
            # Gap and span from decided configuration
            gap_minutes = 120  # 2 hours
            max_span_hours = completion_hours  # align with FLIGHT_COMPLETION_HOURS

            self.logger.info(
                f"🧭 Selecting canonical sessions: horizon={completion_hours}h, gap={gap_minutes}m, max_span={max_span_hours}h"
            )
            # Support optional limit argument passed via env or caller
            limit_env = os.getenv("FLIGHT_SUMMARY_MAX_BATCH")
            try:
                env_limit = int(limit_env) if limit_env is not None else None
            except Exception:
                env_limit = None

            # If caller provided a limit via function arg, prefer it; otherwise use env_limit
            caller_limit = None
            # The scheduled loop will call this function as _process_completed_flights_canonical(limit=N)
            # To preserve backward compatibility we read a possible dynamic attribute
            caller_limit = getattr(self, "_canonical_limit_override", None)

            # Use the limit parameter if provided, otherwise fall back to existing logic
            limit_to_use = limit or caller_limit or env_limit

            # Get canonical sessions (most recent completed flights)
            canonical_sessions = await select_canonical_sessions(
                completion_hours=completion_hours,
                gap_minutes=gap_minutes,
                max_span_hours=max_span_hours,
            )
            self.logger.info(f"🧭 Canonical selector produced {len(canonical_sessions)} sessions")
            
            # Also get sessions with NULL completion times (need fixing)
            null_completion_sessions = await self._find_sessions_with_null_completion(limit=limit_to_use or 1000)
            self.logger.info(f"🔧 Found {len(null_completion_sessions)} sessions with NULL completion times")
            
            # Combine and deduplicate sessions
            all_sessions_map = {
                (s['callsign'], s['cid'], s['departure'], s['arrival']): s
                for s in canonical_sessions
            }
            
            # Add null completion sessions if they're not already in the canonical list
            for s in null_completion_sessions:
                key = (s['callsign'], s['cid'], s['departure'], s['arrival'])
                if key not in all_sessions_map:
                    all_sessions_map[key] = s
            
            sessions = list(all_sessions_map.values())
            
            # Apply limit to the combined list
            if limit_to_use is not None:
                try:
                    limit_int = int(limit_to_use)
                    sessions = sessions[:limit_int]
                except Exception:
                    pass
            
            self.logger.info(f"🧭 Combined sessions (canonical + null completion) = {len(sessions)}")

            processed = 0
            archived = 0
            deleted = 0

            for s in sessions:
                callsign = s["callsign"]
                cid = s["cid"]
                departure = s["departure"]
                arrival = s["arrival"]
                session_start = s["session_start"]
                session_end = s["session_end"]
                latest_deptime = s.get("latest_deptime")
                latest_route = s.get("latest_route")

                # Per-session transaction
                async with get_database_session() as session:
                    # Acquire transaction-level advisory lock (pg_try variant)
                    key_concat = f"{callsign}|{cid}|{departure}|{arrival}"
                    lock_sql = text("""
                        SELECT pg_try_advisory_xact_lock(hashtextextended(:key, 0)) AS acquired
                    """)
                    res = await session.execute(lock_sql, {"key": key_concat})
                    acquired = res.scalar()
                    if not acquired:
                        self.logger.debug(f"🔒 Skipping {callsign} {departure}->{arrival} (cid={cid}) due to lock contention")
                        continue

                    # High-water mark for safe archive/delete
                    hwm_sql = text("""
                        SELECT MAX(last_updated) AS hwm
                        FROM flights
                        WHERE callsign = :callsign
                          AND cid = :cid
                          AND departure = :departure
                          AND arrival = :arrival
                          AND last_updated BETWEEN :start AND :end
                    """)
                    hwm_res = await session.execute(
                        hwm_sql,
                        {
                            "callsign": callsign,
                            "cid": cid,
                            "departure": departure,
                            "arrival": arrival,
                            "start": session_start,
                            "end": session_end,
                        },
                    )
                    hwm_row = hwm_res.fetchone()
                    hwm = hwm_row.hwm if hwm_row and hwm_row.hwm else session_end

                    # Upsert summary: update-first by signature
                    # Load latest-in-session flight fields to populate/backfill summary columns
                    latest_sql = text("""
                        SELECT
                            aircraft_type,
                            flight_rules,
                            aircraft_faa,
                            planned_altitude,
                            aircraft_short,
                            cid,
                            name,
                            server,
                            pilot_rating,
                            military_rating,
                            last_updated
                        FROM (
                            SELECT
                                f.aircraft_type,
                                f.flight_rules,
                                f.aircraft_faa,
                                f.planned_altitude,
                                f.aircraft_short,
                                f.cid,
                                f.name,
                                f.server,
                                f.pilot_rating,
                                f.military_rating,
                                f.last_updated
                            FROM flights f
                            WHERE f.callsign = :callsign
                              AND f.cid = :cid
                              AND f.departure = :departure
                              AND f.arrival = :arrival
                              AND f.last_updated BETWEEN :start AND :end
                            UNION ALL
                            SELECT
                                f.aircraft_type,
                                f.flight_rules,
                                f.aircraft_faa,
                                f.planned_altitude,
                                f.aircraft_short,
                                f.cid,
                                f.name,
                                f.server,
                                f.pilot_rating,
                                f.military_rating,
                                f.last_updated
                            FROM flights_archive f
                            WHERE f.callsign = :callsign
                              AND f.cid = :cid
                              AND f.departure = :departure
                              AND f.arrival = :arrival
                              AND f.last_updated BETWEEN :start AND :end
                        ) combined
                        ORDER BY last_updated DESC
                        LIMIT 1
                    """)

                    # DEBUG: Log query execution for JST458 (and show all callsigns for debugging)
                    if callsign == 'JST458' or callsign.startswith('JST'):
                        self.logger.info(f"🔍 CANONICAL: Processing {callsign} - cid={cid}, dep={departure}, arr={arrival}")
                    if callsign == 'JST458':
                        self.logger.info(f"🔍 CANONICAL: Executing archive query for JST458 - cid={cid}, dep={departure}, arr={arrival}, start={session_start}, end={session_end}")
                        self.logger.info(f"🔍 CANONICAL: JST458 SQL query parameters - callsign={callsign}, cid={cid}, departure={departure}, arrival={arrival}, start={session_start}, end={session_end}")
                    
                    latest_row = await session.execute(
                        latest_sql,
                        {
                            "callsign": callsign,
                            "cid": cid,
                            "departure": departure,
                            "arrival": arrival,
                            "start": session_start,
                            "end": session_end,
                        },
                    )
                    latest_row = latest_row.fetchone()
                    
                    # DEBUG: Log query results for JST458
                    if callsign == 'JST458':
                        if latest_row:
                            self.logger.info(f"🔍 DEBUG: JST458 archive query found data - aircraft_type={latest_row.aircraft_type}, name={latest_row.name}")
                        else:
                            self.logger.info(f"🔍 DEBUG: JST458 archive query returned NO DATA")

                    latest_vals = {
                        "aircraft_type": None,
                        "flight_rules": None,
                        "aircraft_faa": None,
                        "planned_altitude": None,
                        "aircraft_short": None,
                        "cid": cid,
                        "name": None,
                        "server": None,
                        "pilot_rating": None,
                        "military_rating": None,
                    }
                    if latest_row:
                        latest_vals.update({
                            "aircraft_type": latest_row.aircraft_type,
                            "flight_rules": latest_row.flight_rules,
                            "aircraft_faa": latest_row.aircraft_faa,
                            "planned_altitude": latest_row.planned_altitude,
                            "aircraft_short": latest_row.aircraft_short,
                            "cid": latest_row.cid,
                            "name": latest_row.name,
                            "server": latest_row.server,
                            "pilot_rating": latest_row.pilot_rating,
                            "military_rating": latest_row.military_rating,
                        })
                        
                    # DEBUG: Log final latest_vals for JST458
                    if callsign == 'JST458':
                        self.logger.info(f"🔍 DEBUG: JST458 final latest_vals - aircraft_type={latest_vals['aircraft_type']}, name={latest_vals['name']}, server={latest_vals['server']}")

                    # Calculate session time and sector metrics from `flights` table (no archive fallback)
                    time_online_minutes = None
                    sector_breakdown = None
                    primary_sector = None
                    total_sectors = None
                    total_enroute_time = None
                    try:
                        first_last_sql = text("""
                            SELECT MIN(last_updated) AS first_updated, MAX(last_updated) AS last_updated
                            FROM flights
                            WHERE callsign = :callsign
                              AND cid = :cid
                              AND departure = :departure
                              AND arrival = :arrival
                              AND last_updated BETWEEN :start AND :end
                        """)
                        fl_res = await session.execute(
                            first_last_sql,
                            {
                                "callsign": callsign,
                                "cid": cid,
                                "departure": departure,
                                "arrival": arrival,
                                "start": session_start,
                                "end": session_end,
                            },
                        )
                        fl_row = fl_res.fetchone()
                        if fl_row and fl_row.first_updated and fl_row.last_updated:
                            delta = fl_row.last_updated - fl_row.first_updated
                            time_online_minutes = int(delta.total_seconds() / 60)

                            # Sector breakdown uses the same helper as original implementation
                            try:
                                sector_breakdown = await self._calculate_sector_breakdown(
                                    callsign, session,
                                    logon_time=fl_row.first_updated,
                                    completion_time=fl_row.last_updated,
                                )
                                primary_sector = self._get_primary_sector(sector_breakdown)
                                total_sectors = len(sector_breakdown)
                                
                                # Use altitude-based calculation exclusively for total_enroute_time
                                total_enroute_time = await self._get_total_airborne_time(
                                    callsign, session,
                                    logon_time=fl_row.first_updated,
                                    completion_time=fl_row.last_updated
                                )
                            except Exception:
                                sector_breakdown = None
                                primary_sector = None
                                total_sectors = None
                                total_enroute_time = None
                    except Exception:
                        time_online_minutes = None
                        sector_breakdown = None
                        primary_sector = None
                        total_sectors = None
                        total_enroute_time = None
                    upd_sql = text("""
                        UPDATE flight_summaries
                        SET
                            completion_time = GREATEST(completion_time, :session_end),
                            deptime = :latest_deptime,
                            route = COALESCE(:latest_route, route),
                            aircraft_type = COALESCE(aircraft_type, :aircraft_type),
                            name = COALESCE(name, :name),
                            cid = COALESCE(cid, :cid),
                            server = COALESCE(server, :server),
                            pilot_rating = COALESCE(pilot_rating, :pilot_rating),
                            military_rating = COALESCE(military_rating, :military_rating),
                            flight_rules = COALESCE(flight_rules, :flight_rules),
                            aircraft_faa = COALESCE(aircraft_faa, :aircraft_faa),
                            planned_altitude = COALESCE(planned_altitude, :planned_altitude),
                            aircraft_short = COALESCE(aircraft_short, :aircraft_short),
                            -- Do not update time_online_minutes if it already has a value
                            time_online_minutes = CASE
                                WHEN time_online_minutes IS NULL THEN :time_online_minutes
                                ELSE time_online_minutes
                            END,
                            primary_enroute_sector = COALESCE(primary_enroute_sector, :primary_enroute_sector),
                            total_enroute_sectors = COALESCE(total_enroute_sectors, :total_enroute_sectors),
                            -- Do not update total_enroute_time_minutes if it already has a value
                            total_enroute_time_minutes = CASE
                                WHEN total_enroute_time_minutes IS NULL THEN :total_enroute_time_minutes
                                ELSE total_enroute_time_minutes
                            END,
                            sector_breakdown = COALESCE(sector_breakdown, :sector_breakdown),
                            -- Transition from wait_for_completion to pending when flight is completed
                            enrichment_status = CASE 
                                WHEN enrichment_status = 'wait_for_completion' THEN 'pending'
                                ELSE enrichment_status
                            END,
                            enrichment_run_after = CASE 
                                WHEN enrichment_status = 'wait_for_completion' THEN NOW()
                                ELSE enrichment_run_after
                            END,
                            updated_at = NOW()
                        WHERE callsign = :callsign
                          AND cid = :cid
                          AND departure = :departure
                          AND arrival = :arrival
                          AND logon_time = :session_start
                    """)
                    # DEBUG: Log UPDATE parameters for JST458
                    if callsign == 'JST458':
                        self.logger.info(f"🔍 CANONICAL: JST458 UPDATE parameters - aircraft_type={latest_vals['aircraft_type']}, aircraft_faa={latest_vals['aircraft_faa']}, name={latest_vals['name']}")
                        self.logger.info(f"🔍 CANONICAL: JST458 all latest_vals = {latest_vals}")
                    
                    upd_res = await session.execute(
                        upd_sql,
                        {
                            "callsign": callsign,
                            "cid": cid,
                            "departure": departure,
                            "arrival": arrival,
                            "session_start": session_start,
                            "session_end": session_end,
                            "latest_deptime": latest_deptime,
                            "latest_route": latest_route,
                            # Backfill fields
                            "aircraft_type": latest_vals["aircraft_type"],
                            "name": latest_vals["name"],
                            "server": latest_vals["server"],
                            "pilot_rating": latest_vals["pilot_rating"],
                            "military_rating": latest_vals["military_rating"],
                            "flight_rules": latest_vals["flight_rules"],
                            "aircraft_faa": latest_vals["aircraft_faa"],
                            "planned_altitude": latest_vals["planned_altitude"],
                            "aircraft_short": latest_vals["aircraft_short"],
                            # Calculated metrics
                            "time_online_minutes": time_online_minutes,
                            "primary_enroute_sector": primary_sector,
                            "total_enroute_sectors": total_sectors,
                            "total_enroute_time_minutes": total_enroute_time,
                            "sector_breakdown": json.dumps(sector_breakdown) if sector_breakdown is not None else None,
                        },
                    )

                    if upd_res.rowcount and upd_res.rowcount > 0:
                        processed += 1
                    else:
                        # Insert minimal summary row; optional fields left NULL or basic
                        ins_sql = text("""
                            INSERT INTO flight_summaries (
                                callsign, departure, arrival, deptime, logon_time,
                                route, cid, completion_time,
                                aircraft_type, name, server, pilot_rating, military_rating,
                                flight_rules, aircraft_faa, planned_altitude, aircraft_short,
                                time_online_minutes, primary_enroute_sector, total_enroute_sectors, total_enroute_time_minutes, sector_breakdown
                            ) VALUES (
                                :callsign, :departure, :arrival, :latest_deptime, :session_start,
                                :latest_route, :cid, :session_end,
                                :aircraft_type, :name, :server, :pilot_rating, :military_rating,
                                :flight_rules, :aircraft_faa, :planned_altitude, :aircraft_short,
                                :time_online_minutes, :primary_enroute_sector, :total_enroute_sectors, :total_enroute_time_minutes, :sector_breakdown
                            )
                        """)
                        await session.execute(
                            ins_sql,
                            {
                                "callsign": callsign,
                                "departure": departure,
                                "arrival": arrival,
                                "latest_deptime": latest_deptime,
                                "session_start": session_start,
                                "latest_route": latest_route,
                                "cid": cid,
                                "session_end": session_end,
                                # Insert fields (may be NULL if not present)
                                "aircraft_type": latest_vals["aircraft_type"],
                                "name": latest_vals["name"],
                                "server": latest_vals["server"],
                                "pilot_rating": latest_vals["pilot_rating"],
                                "military_rating": latest_vals["military_rating"],
                                "flight_rules": latest_vals["flight_rules"],
                                "aircraft_faa": latest_vals["aircraft_faa"],
                                "planned_altitude": latest_vals["planned_altitude"],
                                "aircraft_short": latest_vals["aircraft_short"],
                                "time_online_minutes": time_online_minutes,
                                "primary_enroute_sector": primary_sector,
                                "total_enroute_sectors": total_sectors,
                                "total_enroute_time_minutes": total_enroute_time,
                                "sector_breakdown": json.dumps(self._convert_for_json(sector_breakdown)) if sector_breakdown is not None else None,
                            },
                        )
                        processed += 1

                    # Enqueue enrichment work for this summary instead of running inline.
                    # If completion_time is set, mark as 'pending', otherwise 'wait_for_completion'
                    try:
                        enqueue_sql = text("""
                            UPDATE flight_summaries
                            SET
                                enrichment_status = CASE 
                                    WHEN completion_time IS NOT NULL THEN 'pending'
                                    ELSE 'wait_for_completion'
                                END,
                                enrichment_attempts = COALESCE(enrichment_attempts, 0),
                                enrichment_run_after = NOW(),
                                updated_at = NOW()
                            WHERE callsign = :callsign
                              AND cid = :cid
                              AND departure = :departure
                              AND arrival = :arrival
                              AND logon_time = :session_start
                        """)
                        await session.execute(
                            enqueue_sql,
                            {
                                "callsign": callsign,
                                "cid": cid,
                                "departure": departure,
                                "arrival": arrival,
                                "session_start": session_start,
                            },
                        )
                    except Exception as e:
                        # Non-fatal: log and continue; the summary was created/updated but enqueue marking failed.
                        self.logger.warning(f"Failed to mark enrichment pending for {callsign} {departure}->{arrival} (cid={cid}) @ {session_start}: {e}")

                    # Archiving and deletion removed - handled by separate independent process
                    # that respects FLIGHT_DAYS_BEFORE_ARCHIVE configuration

            # Backward-compatible result keys so scheduled logger and callers don't KeyError
            return {
                "status": "success",
                "sessions_detected": len(sessions),
                "summaries_processed": processed,
                "records_deleted": 0,  # No longer deleting in canonical process
                # Compatibility with legacy callers/loggers:
                "summaries_created": processed,
                "records_archived": 0,  # No longer archiving in canonical process
            }
        except Exception as e:
            self.logger.error(f"❌ Canonical session processing failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _delete_completed_flights(self, completed_flights: List[dict]) -> int:
        """Delete completed flights from the main flights table."""
        processed_count = 0
        async with get_database_session() as session:
            for flight_key in completed_flights:
                callsign, departure, arrival, cid, deptime = flight_key
                
                try:
                    # Respect archive delay configuration: only delete rows older than cutoff
                    import os
                    from datetime import datetime, timezone, timedelta
                    days_str = os.getenv("FLIGHT_DAYS_BEFORE_ARCHIVE", "0")
                    try:
                        days_before = int(days_str)
                    except Exception:
                        days_before = 0

                    if days_before > 0:
                        archive_cutoff = datetime.now(timezone.utc) - timedelta(days=days_before)
                        result = await session.execute(text("""
                            DELETE FROM flights
                            WHERE callsign = :callsign
                            AND departure = :departure
                            AND arrival = :arrival
                            AND cid = :cid
                            AND deptime = :deptime
                            AND last_updated <= :archive_cutoff
                        """), {
                            "callsign": callsign,
                            "departure": departure,
                            "arrival": arrival,
                            "cid": cid,
                            "deptime": deptime,
                            "archive_cutoff": archive_cutoff
                        })
                    else:
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
        """Start automatic scheduled flight summary processing with adaptive intervals."""
        try:
            # Check if task is already running
            if (self.flight_summary_task is not None and 
                not self.flight_summary_task.done()):
                self.logger.info("Flight summary task already running - not starting another")
                return
                
            # Validate configuration before starting
            self._validate_flight_summary_config()
            
            self.logger.info("🚀 Starting scheduled flight summary processing with adaptive intervals")
            
            # Start background task - uses adaptive sleep logic internally
            self.flight_summary_task = asyncio.create_task(self._scheduled_processing_loop())
            
            # Add callback to handle task completion/failure
            self.flight_summary_task.add_done_callback(self._on_flight_summary_task_done)
            
        except Exception as e:
            self.logger.error(f"Failed to start scheduled flight processing: {e}")

    async def start_scheduled_controller_processing(self):
        """Start automatic scheduled controller summary processing."""
        try:
            # Check if task is already running
            if (self.controller_summary_task is not None and 
                not self.controller_summary_task.done()):
                self.logger.info("Controller summary task already running - not starting another")
                return
                
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
            
            
            if config.completion_hours < 1:
                raise ValueError("FLIGHT_COMPLETION_HOURS must be at least 1 hour")
            
            if config.retention_hours < config.completion_hours:
                raise ValueError("FLIGHT_RETENTION_HOURS must be greater than FLIGHT_COMPLETION_HOURS")
            
            self.logger.info(f"✅ Flight summary configuration validated: completion={config.completion_hours}h, retention={config.retention_hours}h")
            
        except Exception as e:
            self.logger.error(f"❌ Flight summary configuration validation failed: {e}")
            raise

    async def start_scheduled_flight_archiving(self):
        """Start automatic scheduled flight archiving processing."""
        try:
            # Use hourly interval as requested
            interval_seconds = 3600  # 1 hour
            
            self.logger.info(f"🗄️ Starting scheduled flight archiving processing - interval: 60 minutes ({interval_seconds} seconds)")
            
            # Start background task and store reference
            self.flight_archiving_task = asyncio.create_task(self._scheduled_archiving_loop(interval_seconds))
            
            # Add callback to handle task completion/failure
            self.flight_archiving_task.add_done_callback(self._on_flight_archiving_task_done)
            
        except Exception as e:
            self.logger.error(f"Failed to start scheduled flight archiving: {e}")

    async def _scheduled_archiving_loop(self, interval_seconds: int):
        """Background loop for scheduled flight archiving processing."""
        self.logger.info(f"⏰ Scheduled flight archiving loop started at {datetime.now(timezone.utc)}")

        while True:
            try:
                # Log the scheduled run
                self.logger.info(f"⏰ Scheduled flight archiving started at {datetime.now(timezone.utc)}")

                # Process flight archiving
                result = await self.process_flight_archiving()
                
                if result.get("status") == "success":
                    archived = result.get("records_archived", 0)
                    deleted = result.get("records_deleted", 0)
                    self.logger.info(f"✅ Scheduled archiving completed: {archived} archived, {deleted} deleted")
                else:
                    error = result.get("error", "Unknown error")
                    self.logger.error(f"❌ Scheduled archiving failed: {error}")
                
            except Exception as e:
                self.logger.error(f"❌ Error in scheduled flight archiving loop: {e}")
            
            # Sleep for the configured interval
            await asyncio.sleep(interval_seconds)

    def _on_flight_archiving_task_done(self, task):
        """Handle completion/failure of the flight archiving task."""
        if task.cancelled():
            self.logger.info("Flight archiving task was cancelled")
        elif task.exception():
            self.logger.error(f"Flight archiving task failed with exception: {task.exception()}")
        else:
            self.logger.info("Flight archiving task completed")

    async def _scheduled_processing_loop(self):
        """Background loop for scheduled flight summary processing with adaptive intervals.

        Simple adaptive behavior:
        - Process ALL qualifying sessions (no batch limits)
        - If busy (>50 summaries): sleep FLIGHT_SUMMARY_POLL_INTERVAL_SHORT seconds
        - If idle (≤50 summaries): sleep FLIGHT_SUMMARY_POLL_INTERVAL_LONG seconds
        """
        self.logger.info(f"⏰ Scheduled flight summary processing loop started at {datetime.now(timezone.utc)}")

        # Load adaptive interval configuration
        max_batch_env = os.getenv("FLIGHT_SUMMARY_MAX_BATCH")
        max_batch = int(max_batch_env) if max_batch_env else None  # None = unlimited
        short_sleep = self.config.flight_summary.poll_interval_short
        long_sleep = self.config.flight_summary.poll_interval_long

        while True:
            try:
                # Log the scheduled run
                batch_info = "unlimited" if max_batch is None else str(max_batch)
                self.logger.info(f"⏰ Scheduled flight summary processing started at {datetime.now(timezone.utc)}; batch_size={batch_info}")

                # Process completed flights (unlimited processing when max_batch is None)
                self.logger.info(f"🔧 SCHEDULED: Processing flights using canonical method (limit={batch_info})")
                result = await self._process_completed_flights_canonical(limit=max_batch)

                # Log the results
                summaries = result.get('summaries_created', result.get('processed', 0))
                archived = result.get('records_archived', result.get('records_deleted', 0))
                self.logger.info(f"✅ Scheduled processing completed: {summaries} summaries created, {archived} records archived")

                # Simple adaptive sleep logic based on workload:
                # - Created 50+ summaries: System is busy → check again using short interval (might be more work)
                # - Created <50 summaries: System is quiet → wait long interval before checking again
                if isinstance(summaries, int) and summaries >= 50:
                    # High activity - lots of work being processed
                    self.logger.info(f"High activity ({summaries} summaries); sleeping short interval {short_sleep}s")
                    await asyncio.sleep(short_sleep)
                else:
                    # Low activity - little or no work to process
                    self.logger.info(f"Low activity ({summaries} summaries); sleeping long interval {long_sleep}s")
                    await asyncio.sleep(long_sleep)

            except asyncio.CancelledError:
                self.logger.info("Scheduled flight summary processing task was cancelled")
                break
            except Exception as e:
                self.logger.error(f"❌ Error in scheduled flight processing: {e}")
                # Wait a bit before retrying, but don't wait the full interval
                await asyncio.sleep(short_sleep)  # Wait short interval before retry

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
                await asyncio.sleep(self.config.flight_summary.poll_interval_short)  # Wait short interval before retry

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
                },
                "atc_detection_task_status": {
                    "running": self.atc_detection_task is not None and not self.atc_detection_task.done(),
                    "done": self.atc_detection_task is not None and self.atc_detection_task.done(),
                    "cancelled": self.atc_detection_task is not None and self.atc_detection_task.cancelled(),
                    "exception": str(self.atc_detection_task.exception()) if self.atc_detection_task and self.atc_detection_task.done() and self.atc_detection_task.exception() else None
                },
                "flight_detection_task_status": {
                    "running": self.flight_detection_task is not None and not self.flight_detection_task.done(),
                    "done": self.flight_detection_task is not None and self.flight_detection_task.done(),
                    "cancelled": self.flight_detection_task is not None and self.flight_detection_task.cancelled(),
                    "exception": str(self.flight_detection_task.exception()) if self.flight_detection_task and self.flight_detection_task.done() and self.flight_detection_task.exception() else None
                }
            }
            return stats
        except Exception as e:
            self.logger.error(f"Failed to get processing stats: {e}")
            return {"error": str(e)}

    async def _restart_flight_detection_task(self):
        """Restart the flight detection processing task after a failure."""
        try:
            await asyncio.sleep(30)  # Wait 30 seconds before restarting
            self.logger.info("🔄 Restarting flight detection processing task...")
            await self.start_scheduled_flight_detection_processing()
        except Exception as e:
            self.logger.error(f"Failed to restart flight detection task: {e}")

    async def start_scheduled_atc_detection_processing(self):
        """Start automatic scheduled ATC detection processing."""
        try:
            # Validate configuration before starting
            self._validate_detection_config()
            
            # Get interval from config (already in seconds)
            interval_seconds = self.config.detection.time_window_seconds
            
            self.logger.info(f"🚀 Starting scheduled ATC detection processing - interval: {interval_seconds} seconds")
            
            # Start background task and store reference
            self.atc_detection_task = asyncio.create_task(self._scheduled_atc_detection_processing_loop(interval_seconds))
            
            # Add callback to handle task completion/failure
            self.atc_detection_task.add_done_callback(self._on_atc_detection_task_done)
            
        except Exception as e:
            self.logger.error(f"Failed to start scheduled ATC detection processing: {e}")

    async def start_scheduled_flight_detection_processing(self):
        """Start automatic scheduled flight detection processing."""
        try:
            # Validate configuration before starting
            self._validate_detection_config()
            
            # Get interval from config (already in seconds)
            interval_seconds = self.config.detection.time_window_seconds
            
            self.logger.info(f"🚀 Starting scheduled flight detection processing - interval: {interval_seconds} seconds")
            
            # Start background task and store reference
            self.flight_detection_task = asyncio.create_task(self._scheduled_flight_detection_processing_loop(interval_seconds))
            
            # Add callback to handle task completion/failure
            self.flight_detection_task.add_done_callback(self._on_flight_detection_task_done)
            
        except Exception as e:
            self.logger.error(f"Failed to start scheduled flight detection processing: {e}")

    def _validate_detection_config(self):
        """Validate detection configuration before starting scheduled processing."""
        try:
            if not hasattr(self.config, 'detection'):
                raise ValueError("Detection configuration not found")
            
            config = self.config.detection
            
            if not config.enabled:
                self.logger.info("Detection processing is disabled")
                return
            
            if config.time_window_seconds < 30:  # Minimum 30 seconds
                raise ValueError("FLIGHT_DETECTION_TIME_WINDOW_SECONDS must be at least 30 seconds")
            
            self.logger.info(f"✅ Detection configuration validated: time_window={config.time_window_seconds}s, enabled={config.enabled}")
            
        except Exception as e:
            self.logger.error(f"❌ Detection configuration validation failed: {e}")
            raise

    async def _scheduled_atc_detection_processing_loop(self, interval_seconds: int):
        """Background loop for scheduled ATC detection processing."""
        self.logger.info(f"⏰ Scheduled ATC detection processing loop started at {datetime.now(timezone.utc)}")
        
        while True:
            try:
                # Log the scheduled run
                self.logger.info(f"⏰ Scheduled ATC detection processing started at {datetime.now(timezone.utc)}")
                
                # Process real-time ATC detection
                result = await self.process_real_time_atc_detection()
                
                # Log the results
                self.logger.info(f"✅ Scheduled ATC detection completed: {result}")
                
                # Wait for next interval
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                self.logger.info("Scheduled ATC detection processing task was cancelled")
                break
            except Exception as e:
                self.logger.error(f"❌ Error in scheduled ATC detection processing: {e}")
                # Wait a bit before retrying, but don't wait the full interval
                await asyncio.sleep(self.config.flight_summary.poll_interval_short)  # Wait short interval before retry

    async def _scheduled_flight_detection_processing_loop(self, interval_seconds: int):
        """Background loop for scheduled flight detection processing."""
        self.logger.info(f"⏰ Scheduled flight detection processing loop started at {datetime.now(timezone.utc)}")
        
        while True:
            try:
                # Log the scheduled run
                self.logger.info(f"⏰ Scheduled flight detection processing started at {datetime.now(timezone.utc)}")
                
                # Process real-time flight detection
                result = await self.process_real_time_flight_detection()
                
                # Log the results
                self.logger.info(f"✅ Scheduled flight detection completed: {result}")
                
                # Wait for next interval
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                self.logger.info("Scheduled flight detection processing task was cancelled")
                break
            except Exception as e:
                self.logger.error(f"❌ Error in scheduled flight detection processing: {e}")
                # Wait a bit before retrying, but don't wait the full interval
                await asyncio.sleep(self.config.flight_summary.poll_interval_short)  # Wait short interval before retry

    def _on_atc_detection_task_done(self, task):
        """Callback when ATC detection task completes or fails."""
        try:
            if task.cancelled():
                self.logger.info("ATC detection task was cancelled")
            elif task.exception():
                self.logger.error(f"ATC detection task failed with exception: {task.exception()}")
                # Restart the task after a delay
                asyncio.create_task(self._restart_atc_detection_task())
            else:
                self.logger.info("ATC detection task completed normally")
        except Exception as e:
            self.logger.error(f"Error in ATC detection task callback: {e}")

    def _on_flight_detection_task_done(self, task):
        """Callback when flight detection task completes or fails."""
        try:
            if task.cancelled():
                self.logger.info("Flight detection task was cancelled")
            elif task.exception():
                self.logger.error(f"Flight detection task failed with exception: {task.exception()}")
                # Restart the task after a delay
                asyncio.create_task(self._restart_flight_detection_task())
            else:
                self.logger.info("Flight detection task completed normally")
        except Exception as e:
            self.logger.error(f"Error in flight detection task callback: {e}")

    async def _restart_atc_detection_task(self):
        """Restart the ATC detection processing task after a failure."""
        try:
            await asyncio.sleep(30)  # Wait 30 seconds before restarting
            self.logger.info("🔄 Restarting ATC detection processing task...")
            await self.start_scheduled_atc_detection_processing()
        except Exception as e:
            self.logger.error(f"Failed to restart ATC detection task: {e}")

    async def process_real_time_atc_detection(self) -> Dict[str, Any]:
        """
        Process real-time ATC detection to identify flight-controller interactions.
        
        Returns:
            Dict[str, Any]: Processing results and statistics
        """
        try:
            self.logger.info("🔄 Processing real-time ATC detection...")
            
            # Get current flights and controllers from database
            async with get_database_session() as session:
                # Get active flights within the time window
                time_window = datetime.now(timezone.utc) - timedelta(seconds=self.config.detection.time_window_seconds)
                
                # Query for active flights
                flights_result = await session.execute(text("""
                    SELECT DISTINCT callsign, departure, arrival, logon_time 
                    FROM flights 
                    WHERE last_updated >= :time_window 
                    AND departure IS NOT NULL 
                    AND arrival IS NOT NULL
                """), {"time_window": time_window})
                
                flights = flights_result.fetchall()
                
                # Query for active controllers
                controllers_result = await session.execute(text("""
                    SELECT DISTINCT callsign 
                    FROM controllers 
                    WHERE last_updated >= :time_window
                """), {"time_window": time_window})
                
                controllers = controllers_result.fetchall()
            
            self.logger.info(f"Processing {len(flights)} active flights and {len(controllers)} active controllers")
            
            # Process each flight for ATC interactions
            total_interactions = 0
            for flight in flights:
                try:
                    result = await self.atc_detection_service.detect_flight_atc_interactions_with_timeout(
                        flight.callsign, flight.departure, flight.arrival, flight.logon_time, timeout_seconds=20.0
                    )
                    if result.get("interactions_detected", 0) > 0:
                        total_interactions += result["interactions_detected"]
                except Exception as e:
                    self.logger.debug(f"Failed to process flight {flight.callsign} for ATC detection: {e}")
                    continue
            
            self.logger.info(f"✅ Real-time ATC detection completed: {total_interactions} interactions detected")
            return {"interactions_detected": total_interactions, "flights_processed": len(flights)}
            
        except Exception as e:
            self.logger.error(f"❌ Error in real-time ATC detection: {e}")
            return {"error": str(e), "interactions_detected": 0}

    async def process_real_time_flight_detection(self) -> Dict[str, Any]:
        """
        Process real-time flight detection to identify controller-flight interactions.
        
        Returns:
            Dict[str, Any]: Processing results and statistics
        """
        try:
            self.logger.info("🔄 Processing real-time flight detection...")
            
            # Get current controllers from database
            async with get_database_session() as session:
                # Get active controllers within the time window
                time_window = datetime.now(timezone.utc) - timedelta(seconds=self.config.detection.time_window_seconds)
                
                # Query for active controllers
                controllers_result = await session.execute(text("""
                    SELECT DISTINCT callsign, logon_time 
                    FROM controllers 
                    WHERE last_updated >= :time_window
                """), {"time_window": time_window})
                
                controllers = controllers_result.fetchall()
            
            self.logger.info(f"Processing {len(controllers)} active controllers for flight detection")
            
            # Process each controller for flight interactions
            total_interactions = 0
            for controller in controllers:
                try:
                    # Use current time as session end for real-time processing
                    session_end = datetime.now(timezone.utc)
                    result = await self.flight_detection_service.detect_controller_flight_interactions_with_timeout(
                        controller.callsign, controller.logon_time, session_end, timeout_seconds=20.0
                    )
                    if result.get("interactions_detected", 0) > 0:
                        total_interactions += result["interactions_detected"]
                except Exception as e:
                    self.logger.debug(f"Failed to process controller {controller.callsign} for flight detection: {e}")
                    continue
            
            self.logger.info(f"✅ Real-time flight detection completed: {total_interactions} interactions detected")
            return {"interactions_detected": total_interactions, "controllers_processed": len(controllers)}
            
        except Exception as e:
            self.logger.error(f"❌ Error in real-time flight detection: {e}")
            return {"error": str(e), "interactions_detected": 0}

    async def process_flight_archiving(self) -> Dict[str, Any]:
        """
        Independent flight archiving process that respects FLIGHT_DAYS_BEFORE_ARCHIVE.
        
        This runs separately from completion processing to enforce proper data retention.
        Flights are only archived when they exceed the configured age threshold.
        """
        try:
            self.logger.info("🗄️ Starting flight archiving process...")
            
            # Find flights eligible for archiving (respects 60-day delay)
            archivable_flights = await self._get_archivable_flights()
            
            if not archivable_flights:
                self.logger.info("📭 No flights ready for archiving")
                return {
                    "status": "success",
                    "records_archived": 0,
                    "records_deleted": 0,
                    "message": "no_archivable_flights"
                }
            
            self.logger.info(f"📊 Found {len(archivable_flights)} flights ready for archiving")
            
            # Archive the eligible flights
            records_archived = await self._archive_completed_flights(archivable_flights)
            
            # Delete the archived flights
            records_deleted = await self._delete_completed_flights(archivable_flights)
            
            result = {
                "status": "success", 
                "records_archived": records_archived,
                "records_deleted": records_deleted
            }
            
            self.logger.info(f"✅ Flight archiving completed: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Flight archiving failed: {e}")
            return {"status": "error", "error": str(e)}

    async def _get_archivable_flights(self) -> List[tuple]:
        """
        Get flights that are old enough to be archived based on FLIGHT_DAYS_BEFORE_ARCHIVE.
        
        Returns:
            List of flight tuples (callsign, departure, arrival, cid, deptime) ready for archiving
        """
        import os
        from datetime import datetime, timezone, timedelta
        
        # Get archive delay from environment
        days_str = os.getenv("FLIGHT_DAYS_BEFORE_ARCHIVE", "60")
        try:
            days_before = int(days_str)
        except Exception:
            days_before = 60
        
        if days_before <= 0:
            days_before = 60  # Default safety
        
        archive_cutoff = datetime.now(timezone.utc) - timedelta(days=days_before)
        self.logger.info(f"🗓️ Archiving flights older than {days_before} days (before {archive_cutoff})")
        
        async with get_database_session() as session:
            # Find flights old enough to archive
            result = await session.execute(text("""
                SELECT DISTINCT callsign, departure, arrival, cid, deptime, last_updated
                FROM flights 
                WHERE last_updated <= :archive_cutoff
                ORDER BY last_updated
            """), {"archive_cutoff": archive_cutoff})
            
            flights = []
            for row in result.fetchall():
                flights.append((row.callsign, row.departure, row.arrival, row.cid, row.deptime))
            
            return flights


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
