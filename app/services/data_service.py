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
from datetime import datetime, timezone, timedelta
import json

from ..utils.logging import get_logger_for_module
from ..utils.error_handling import handle_service_errors, log_operation
from ..services.vatsim_service import VATSIMService
from ..filters.geographic_boundary_filter import GeographicBoundaryFilter
from ..filters.callsign_pattern_filter import CallsignPatternFilter
from ..database import get_database_session
from ..models import Flight, Controller, Transceiver
from ..config import get_config
from .atc_detection_service import ATCDetectionService
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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
        
        # Initialize ATC detection service
        self.atc_detection_service = ATCDetectionService()
        
        # Performance tracking - simplified
        self.stats = {
            "flights": 0,
            "controllers": 0,
            "transceivers": 0,
            "last_run": None
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
            
            self.logger.info(f"Filters: geo={self.geographic_boundary_filter.config.enabled}, callsign={self.callsign_pattern_filter.config.enabled}")
            self._initialized = True
            
            # Start scheduled flight summary processing
            await self.start_scheduled_flight_processing()
            
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
            self.stats.update({
                "flights": self.stats["flights"] + flights_processed,
                "controllers": self.stats["controllers"] + controllers_processed,
                "transceivers": self.stats["transceivers"] + transceivers_processed,
                "last_run": datetime.now(timezone.utc)
            })
            
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
        else:
            filtered_flights = flights_data
        
        # Log only summary, not individual flight details
        if len(flights_data) != len(filtered_flights):
            self.logger.info(f"Flights: {len(flights_data)} → {len(filtered_flights)} (filtered)")
        else:
            self.logger.debug(f"Flights: {len(flights_data)} → {len(filtered_flights)}")
        
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
                        session.add_all([Flight(**flight_data) for flight_data in bulk_flights])
                        await session.commit()
                        processed_count = len(bulk_flights)
                        self.logger.debug(f"Bulk inserted {processed_count} flights")
                    
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
        else:
            filtered_controllers = controllers_data
        
        # Log only summary, not individual controller details
        if len(controllers_data) != len(filtered_controllers):
            self.logger.info(f"Controllers: {len(controllers_data)} → {len(filtered_controllers)} (filtered)")
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
        
        # Apply filters
        filtered_transceivers = self.callsign_pattern_filter.filter_transceivers_list(transceivers_data)
        if self.geographic_boundary_filter.config.enabled:
            filtered_transceivers = self.geographic_boundary_filter.filter_transceivers_list(filtered_transceivers)
        
        # Log only summary, not individual transceiver details
        if len(transceivers_data) != len(filtered_transceivers):
            self.logger.info(f"Transceivers: {len(transceivers_data)} → {len(filtered_transceivers)} (filtered)")
        else:
            self.logger.debug(f"Transceivers: {len(transceivers_data)} → {len(filtered_transceivers)}")
        
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
                        session.add_all([Transceiver(**transceiver_data) for transceiver_data in bulk_transceivers])
                        await session.commit()
                        processed_count = len(bulk_transceivers)
                        self.logger.debug(f"Bulk inserted {processed_count} transceivers")
                    
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
            "flights": self.stats.get("flights", 0),
            "controllers": self.stats.get("controllers", 0),
            "transceivers": self.stats.get("transceivers", 0),
            "last_run": self.stats.get("last_run")
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
    
    async def process_completed_flights(self) -> dict:
        """Process completed flights by creating summaries and archiving old records."""
        try:
            # Get configuration
            completion_hours = self.config.flight_summary.completion_hours
            retention_hours = self.config.flight_summary.retention_hours
            
            # Identify completed flights
            completed_flights = await self._identify_completed_flights(completion_hours)
            
            if not completed_flights:
                self.logger.info("No completed flights found for processing")
                return {"summaries_created": 0, "records_archived": 0, "records_deleted": 0}
            
            self.logger.info(f"Found {len(completed_flights)} completed flights to process")
            
            # Create flight summaries
            summaries_created = await self._create_flight_summaries(completed_flights)
            
            # Archive completed flights
            records_archived = await self._archive_completed_flights(completed_flights)
            
            # Delete completed flights from main flights table
            records_deleted = await self._delete_completed_flights(completed_flights)
            
            # Delete old archived records beyond retention period
            old_records_cleaned = await self._cleanup_old_archived_records(retention_hours)
            
            self.logger.info(f"Flight summary processing completed: {summaries_created} summaries, {records_archived} archived, {records_deleted} deleted from flights, {old_records_cleaned} old records cleaned up")
            
            return {
                "summaries_created": summaries_created,
                "records_archived": records_archived,
                "records_deleted": records_deleted,
                "old_records_cleaned": old_records_cleaned
            }
            
        except Exception as e:
            self.logger.error(f"Error processing completed flights: {e}")
            raise

    async def _identify_completed_flights(self, completion_hours: int) -> List[dict]:
        """Identify flights that have been completed for the specified number of hours."""
        try:
            completion_threshold = datetime.now(timezone.utc) - timedelta(hours=completion_hours)
            
            query = """
                SELECT DISTINCT callsign, departure, arrival, logon_time
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
                callsign, departure, arrival, logon_time = flight_key
                
                try:
                    # Step 2: Get all records for this flight
                    flight_records = await session.execute(text("""
                        SELECT * FROM flights 
                        WHERE callsign = :callsign 
                        AND departure = :departure 
                        AND arrival = :arrival 
                        AND logon_time = :logon_time
                        ORDER BY last_updated
                    """), {
                        "callsign": callsign,
                        "departure": departure,
                        "arrival": arrival,
                        "logon_time": logon_time
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
                        callsign, departure, arrival, logon_time, timeout_seconds=30.0
                    )
                    
                    # Create summary data
                    summary_data = {
                        "callsign": callsign,
                        "aircraft_type": first_record.aircraft_type,
                        "departure": departure,
                        "arrival": arrival,
                        "logon_time": logon_time,
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
                        "controller_callsigns": json.dumps(atc_data["controller_callsigns"]),
                        "controller_time_percentage": atc_data["controller_time_percentage"],
                        "time_online_minutes": total_minutes,
                        "primary_enroute_sector": None,  # TODO: Implement sector tracking
                        "total_enroute_sectors": 0,
                        "total_enroute_time_minutes": 0,
                        "sector_breakdown": json.dumps({}),  # Convert dict to JSON string
                        "completion_time": last_record.last_updated
                    }
                    
                    # Insert summary
                    await session.execute(text("""
                        INSERT INTO flight_summaries (
                            callsign, aircraft_type, departure, arrival, logon_time,
                            route, flight_rules, aircraft_faa, planned_altitude, aircraft_short,
                            cid, name, server, pilot_rating, military_rating,
                            controller_callsigns, controller_time_percentage, time_online_minutes,
                            primary_enroute_sector, total_enroute_sectors, total_enroute_time_minutes, sector_breakdown,
                            completion_time
                        ) VALUES (
                            :callsign, :aircraft_type, :departure, :arrival, :logon_time,
                            :route, :flight_rules, :aircraft_faa, :planned_altitude, :aircraft_short,
                            :cid, :name, :server, :pilot_rating, :military_rating,
                            :controller_callsigns, :controller_time_percentage, :time_online_minutes,
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

    async def _archive_completed_flights(self, completed_flights: List[dict]) -> int:
        """Archive detailed records for completed flights."""
        processed_count = 0
        async with get_database_session() as session:
            for flight_key in completed_flights:
                callsign, departure, arrival, logon_time = flight_key
                
                try:
                    # Get all records for this flight
                    flight_records = await session.execute(text("""
                        SELECT * FROM flights 
                        WHERE callsign = :callsign 
                        AND departure = :departure 
                        AND arrival = :arrival 
                        AND logon_time = :logon_time
                        ORDER BY last_updated
                    """), {
                        "callsign": callsign,
                        "departure": departure,
                        "arrival": arrival,
                        "logon_time": logon_time
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
                                last_updated
                            ) VALUES (
                                :callsign, :aircraft_type, :departure, :arrival, :logon_time,
                                :route, :flight_rules, :aircraft_faa, :planned_altitude, :aircraft_short,
                                :cid, :name, :server, :pilot_rating, :military_rating,
                                :latitude, :longitude, :altitude, :groundspeed, :heading,
                                :last_updated
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
                            "last_updated": record.last_updated
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
                callsign, departure, arrival, logon_time = flight_key
                
                try:
                    # Delete all records for this flight
                    result = await session.execute(text("""
                        DELETE FROM flights 
                        WHERE callsign = :callsign 
                        AND departure = :departure 
                        AND arrival = :arrival 
                        AND logon_time = :logon_time
                    """), {
                        "callsign": callsign,
                        "departure": departure,
                        "arrival": arrival,
                        "logon_time": logon_time
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

    async def start_scheduled_flight_processing(self):
        """Start automatic scheduled flight summary processing."""
        try:
            # Validate configuration before starting
            self._validate_flight_summary_config()
            
            # Get interval from config (convert minutes to seconds)
            interval_minutes = getattr(self.config, 'flight_summary_interval_minutes', 60)
            interval_seconds = interval_minutes * 60
            
            self.logger.info(f"🚀 Starting scheduled flight summary processing - interval: {interval_minutes} minutes ({interval_seconds} seconds)")
            
            # Start background task
            asyncio.create_task(self._scheduled_processing_loop(interval_seconds))
            
        except Exception as e:
            self.logger.error(f"Failed to start scheduled flight processing: {e}")

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
                
            except Exception as e:
                self.logger.error(f"❌ Error in scheduled flight processing: {e}")
                # Wait a bit before retrying
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
