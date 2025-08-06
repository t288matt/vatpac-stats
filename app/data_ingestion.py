#!/usr/bin/env python3
"""
Data Ingestion System for VATSIM Data Collection

This module provides the core data ingestion functionality for the VATSIM data
collection system. It handles real-time data processing, storage, and cleanup
of VATSIM network data including ATC positions, flights, sectors, and transceivers.

INPUTS:
- VATSIM API data (controllers, flights, sectors, transceivers)
- Real-time flight tracking information
- ATC position updates and status changes
- Sector traffic density data

OUTPUTS:
- Database records for ATC positions, flights, sectors
- Real-time data updates and status tracking
- Historical data preservation
- Data cleanup and maintenance operations

FEATURES:
- Asynchronous data processing
- Database transaction management
- Real-time status updates
- Historical data cleanup
- Error handling and logging
- Background ingestion service

DATA TYPES PROCESSED:
- ATC Positions: Controller callsigns, facilities, frequencies
- Flights: Aircraft tracking, position, altitude, speed
- Sectors: Airspace definitions and traffic density
- Transceivers: Radio frequency and position data

OPTIMIZATIONS:
- Batch database operations
- Connection pooling
- Transaction rollback on errors
- Automatic cleanup of old data
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta, timezone
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from .database import get_db, SessionLocal
from .models import Controller, Flight, Sector, Transceiver
from .services.vatsim_service import get_vatsim_service

logger = logging.getLogger(__name__)

class DataIngestionService:
    """Service to ingest VATSIM data into our database"""
    
    def __init__(self):
        self.vatsim_service = get_vatsim_service()
    
    async def ingest_current_data(self):
        """Ingest current VATSIM data into database"""
        db = SessionLocal()
        try:
            # Fetch current VATSIM data
            data = await self.vatsim_service.get_current_data()
            
            # Process ATC positions
            await self._process_atc_positions(data.controllers, db)
            
            # Process flights
            await self._process_flights(data.flights, db)
            
            # Process sectors (if available)
            await self._process_sectors(data.sectors, db)
            
            # Process transceivers (if available)
            await self._process_transceivers(data.transceivers, db)
            
            # Commit all changes at once
            db.commit()
            
            logger.info(f"Data ingestion completed: {len(data.controllers)} ATC positions, {len(data.flights)} flights, {len(data.transceivers)} transceivers")
            
        except Exception as e:
            logger.error(f"Error during data ingestion: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def _process_atc_positions(self, atc_positions_data: List, db: Session):
        """Process and store ATC position data"""
        try:
            for atc_position_data in atc_positions_data:
                # Extract ATC position information from dataclass
                callsign = atc_position_data.callsign
                facility = atc_position_data.facility
                position = atc_position_data.position
                frequency = atc_position_data.frequency
                controller_id = atc_position_data.controller_id
                controller_name = atc_position_data.controller_name
                controller_rating = atc_position_data.controller_rating
                
                # Check if ATC position already exists
                existing_atc_position = db.query(Controller).filter(
                    Controller.callsign == callsign
                ).first()
                
                if existing_atc_position:
                    # Update existing ATC position with all fields
                    existing_atc_position.facility = facility
                    existing_atc_position.position = position
                    existing_atc_position.frequency = frequency
                    existing_atc_position.controller_id = controller_id
                    existing_atc_position.controller_name = controller_name
                    existing_atc_position.controller_rating = controller_rating
                    existing_atc_position.status = "online"
                    existing_atc_position.last_seen = datetime.now(timezone.utc)
                    
                    # Update missing VATSIM API fields - 1:1 mapping
                    existing_atc_position.visual_range = atc_position_data.visual_range
                    existing_atc_position.text_atis = atc_position_data.text_atis
                else:
                    # Create new ATC position with all fields
                    new_atc_position = Controller(
                        callsign=callsign,
                        facility=facility,
                        position=position,
                        frequency=frequency,
                        controller_id=controller_id,
                        controller_name=controller_name,
                        controller_rating=controller_rating,
                        status="online",
                        last_seen=datetime.now(timezone.utc),
                        workload_score=0.0,
                        
                        # Missing VATSIM API fields - 1:1 mapping
                        visual_range=atc_position_data.visual_range,
                        text_atis=atc_position_data.text_atis
                    )
                    db.add(new_atc_position)
            
            logger.info(f"Processed {len(atc_positions_data)} ATC positions")
            
        except Exception as e:
            logger.error(f"Error processing ATC positions: {e}")
            raise
    
    async def _process_flights(self, flights_data: List, db: Session):
        """Process and store flight data"""
        try:
            for flight_data in flights_data:
                # Extract flight information from dataclass
                callsign = flight_data.callsign
                aircraft_type = flight_data.aircraft_type
                departure = flight_data.departure
                arrival = flight_data.arrival
                route = flight_data.route
                altitude = flight_data.altitude
                speed = flight_data.speed
                
                # Position data - store as separate lat/lng fields
                position_lat = flight_data.position.get("lat", 0) if flight_data.position else 0
                position_lng = flight_data.position.get("lng", 0) if flight_data.position else 0
                
                # Controller assignment is handled separately through business logic
                # VATSIM API doesn't provide controller information for flights
                controller_id = None
                
                # Check if flight already exists
                existing_flight = db.query(Flight).filter(
                    Flight.callsign == callsign
                ).first()
                
                if existing_flight:
                    # Update existing flight with all fields
                    existing_flight.aircraft_type = aircraft_type
                    existing_flight.departure = departure
                    existing_flight.arrival = arrival
                    existing_flight.route = route
                    existing_flight.altitude = altitude
                    existing_flight.speed = speed
                    existing_flight.position_lat = position_lat
                    existing_flight.position_lng = position_lng
                    existing_flight.controller_id = controller_id
                    existing_flight.last_updated = datetime.now(timezone.utc)
                    
                    # Update missing VATSIM API fields - 1:1 mapping
                    existing_flight.cid = flight_data.cid
                    existing_flight.name = flight_data.name
                    existing_flight.server = flight_data.server
                    existing_flight.pilot_rating = flight_data.pilot_rating
                    existing_flight.military_rating = flight_data.military_rating
                    existing_flight.latitude = flight_data.latitude
                    existing_flight.longitude = flight_data.longitude
                    existing_flight.groundspeed = flight_data.groundspeed
                    existing_flight.transponder = flight_data.transponder
                    existing_flight.heading = flight_data.heading
                    existing_flight.qnh_i_hg = flight_data.qnh_i_hg
                    existing_flight.qnh_mb = flight_data.qnh_mb
                    existing_flight.logon_time = flight_data.logon_time
                    existing_flight.last_updated_api = flight_data.last_updated
                    
                    # Flight plan fields
                    existing_flight.flight_rules = flight_data.flight_rules
                    existing_flight.aircraft_faa = flight_data.aircraft_faa
                    existing_flight.aircraft_short = flight_data.aircraft_short
                    existing_flight.alternate = flight_data.alternate
                    existing_flight.cruise_tas = flight_data.cruise_tas
                    existing_flight.planned_altitude = flight_data.planned_altitude
                    existing_flight.deptime = flight_data.deptime
                    existing_flight.enroute_time = flight_data.enroute_time
                    existing_flight.fuel_time = flight_data.fuel_time
                    existing_flight.remarks = flight_data.remarks
                    existing_flight.revision_id = flight_data.revision_id
                    existing_flight.assigned_transponder = flight_data.assigned_transponder
                else:
                    # Create new flight with all fields
                    new_flight = Flight(
                        callsign=callsign,
                        aircraft_type=aircraft_type,
                        departure=departure,
                        arrival=arrival,
                        route=route,
                        altitude=altitude,
                        speed=speed,
                        position_lat=position_lat,
                        position_lng=position_lng,
                        controller_id=controller_id,
                        last_updated=datetime.now(timezone.utc),
                        
                        # Missing VATSIM API fields - 1:1 mapping
                        cid=flight_data.cid,
                        name=flight_data.name,
                        server=flight_data.server,
                        pilot_rating=flight_data.pilot_rating,
                        military_rating=flight_data.military_rating,
                        latitude=flight_data.latitude,
                        longitude=flight_data.longitude,
                        groundspeed=flight_data.groundspeed,
                        transponder=flight_data.transponder,
                        heading=flight_data.heading,
                        qnh_i_hg=flight_data.qnh_i_hg,
                        qnh_mb=flight_data.qnh_mb,
                        logon_time=flight_data.logon_time,
                        last_updated_api=flight_data.last_updated,
                        
                        # Flight plan fields
                        flight_rules=flight_data.flight_rules,
                        aircraft_faa=flight_data.aircraft_faa,
                        aircraft_short=flight_data.aircraft_short,
                        alternate=flight_data.alternate,
                        cruise_tas=flight_data.cruise_tas,
                        planned_altitude=flight_data.planned_altitude,
                        deptime=flight_data.deptime,
                        enroute_time=flight_data.enroute_time,
                        fuel_time=flight_data.fuel_time,
                        remarks=flight_data.remarks,
                        revision_id=flight_data.revision_id,
                        assigned_transponder=flight_data.assigned_transponder
                    )
                    db.add(new_flight)
            
            logger.info(f"Processed {len(flights_data)} flights")
            
        except Exception as e:
            logger.error(f"Error processing flights: {e}")
            raise
    
    async def _process_sectors(self, sectors_data: List[Dict[str, Any]], db: Session):
        """
        Process and store sector data.
        
        SECTORS FIELD LIMITATION:
        =========================
        The 'sectors' field is completely missing from VATSIM API v3. This method
        processes sector data that is created by fallback behavior in the parsing
        layer, not from actual API data.
        
        Technical Details:
        - Expected: Real sector data from VATSIM API
        - Actual: Fallback-generated sectors based on facility information
        - Data Source: Created by vatsim_client.parse_sectors() fallback
        - Database Impact: Minimal sector data, mostly empty table
        
        Fallback Data Structure:
        - name: "{facility}_CTR" (e.g., "VECC_CTR")
        - facility: Extracted from controller data
        - status: "unmanned" (default)
        - traffic_density: 0 (default)
        - priority_level: 1 (default)
        
        Database Behavior:
        - Creates sectors if they don't exist
        - Minimal data population
        - No updates to existing sectors (static fallback data)
        - Maintains schema compatibility for future API changes
        
        Future Considerations:
        - Monitor for real sectors data from API
        - Consider manual sector definition
        - Implement sector-based features when data available
        - Add feature flags for sector functionality
        """
        try:
            for sector_data in sectors_data:
                # Extract sector information
                name = sector_data.get("name", "")
                facility = sector_data.get("facility", "")
                status = "unmanned"  # Default status
                
                # Check if sector already exists
                existing_sector = db.query(Sector).filter(
                    Sector.name == name,
                    Sector.facility == facility
                ).first()
                
                if not existing_sector:
                    # Create new sector
                    new_sector = Sector(
                        name=name,
                        facility=facility,
                        status=status,
                        traffic_density=0,
                        priority_level=1
                    )
                    db.add(new_sector)
            
            logger.info(f"Processed {len(sectors_data)} sectors")
            
        except Exception as e:
            logger.error(f"Error processing sectors: {e}")
            raise
    
    async def _process_transceivers(self, transceivers_data: List, db: Session):
        """Process and store transceiver data"""
        try:
            for transceiver_data in transceivers_data:
                # Extract transceiver information from dataclass
                callsign = transceiver_data.callsign
                transceiver_id = transceiver_data.transceiver_id
                frequency = transceiver_data.frequency
                position_lat = transceiver_data.position_lat
                position_lon = transceiver_data.position_lon
                height_msl = transceiver_data.height_msl
                height_agl = transceiver_data.height_agl
                entity_type = transceiver_data.entity_type
                entity_id = transceiver_data.entity_id
                
                # Check if transceiver already exists for this callsign and transceiver_id
                existing_transceiver = db.query(Transceiver).filter(
                    Transceiver.callsign == callsign,
                    Transceiver.transceiver_id == transceiver_id
                ).first()
                
                if existing_transceiver:
                    # Update existing transceiver
                    existing_transceiver.frequency = frequency
                    existing_transceiver.position_lat = position_lat
                    existing_transceiver.position_lon = position_lon
                    existing_transceiver.height_msl = height_msl
                    existing_transceiver.height_agl = height_agl
                    existing_transceiver.entity_type = entity_type
                    existing_transceiver.entity_id = entity_id
                    existing_transceiver.timestamp = datetime.now(timezone.utc)
                else:
                    # Create new transceiver
                    new_transceiver = Transceiver(
                        callsign=callsign,
                        transceiver_id=transceiver_id,
                        frequency=frequency,
                        position_lat=position_lat,
                        position_lon=position_lon,
                        height_msl=height_msl,
                        height_agl=height_agl,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        timestamp=datetime.now(timezone.utc)
                    )
                    db.add(new_transceiver)
            
            logger.info(f"Processed {len(transceivers_data)} transceivers")
            
        except Exception as e:
            logger.error(f"Error processing transceivers: {e}")
            raise
    
    async def cleanup_old_data(self):
        """Clean up old data (flights that are no longer active)"""
        db = SessionLocal()
        try:
            # Remove flights that haven't been updated in the last 5 minutes
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)
            old_flights = db.query(Flight).filter(
                Flight.last_updated < cutoff_time
            ).all()
            
            for flight in old_flights:
                db.delete(flight)
            
            # Remove controllers that haven't been seen in the last 10 minutes
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=10)
            old_controllers = db.query(Controller).filter(
                Controller.last_seen < cutoff_time
            ).all()
            
            for controller in old_controllers:
                controller.status = "offline"
            
            db.commit()
            logger.info(f"Cleaned up {len(old_flights)} old flights and {len(old_controllers)} offline controllers")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def close(self):
        """Close the VATSIM client"""
        await self.vatsim_service.close()

# Background task for continuous data ingestion
async def background_data_ingestion():
    """Background task to continuously ingest VATSIM data"""
    import os
    service = DataIngestionService()
    
    # Get polling interval from environment variable
    polling_interval = int(os.getenv('VATSIM_POLLING_INTERVAL', 30))
    
    # Log the configured interval
    logger.info(f"Background data ingestion configured with polling interval: {polling_interval}s")
    
    while True:
        try:
            await service.ingest_current_data()
            await service.cleanup_old_data()
            await asyncio.sleep(polling_interval)  # Update based on environment variable
        except Exception as e:
            logger.error(f"Background ingestion error: {e}")
            await asyncio.sleep(60)  # Wait longer on error
        finally:
            await service.close() 
