#!/usr/bin/env python3
"""
Data Ingestion System for VATSIM Data
Stores real-time VATSIM data in our database
"""

import asyncio
import logging
import hashlib
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from .database import get_db, SessionLocal
from .models import ATCPosition, Flight, Sector
from .vatsim_client import VATSIMClient

logger = logging.getLogger(__name__)

class DataIngestionService:
    """Service to ingest VATSIM data into our database"""
    
    def __init__(self):
        self.vatsim_client = VATSIMClient()
    
    async def ingest_current_data(self):
        """Ingest current VATSIM data into database"""
        db = SessionLocal()
        try:
            # Fetch current VATSIM data
            data = await self.vatsim_client.get_current_data()
            
            # Process ATC positions
            await self._process_atc_positions(data.get("atc_positions", []), db)
            
            # Process flights
            await self._process_flights(data.get("flights", []), db)
            
            # Process sectors (if available)
            await self._process_sectors(data.get("sectors", []), db)
            
            # Commit all changes at once
            db.commit()
            
            logger.info(f"Data ingestion completed: {len(data.get('atc_positions', []))} ATC positions, {len(data.get('flights', []))} flights")
            
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
                existing_atc_position = db.query(ATCPosition).filter(
                    ATCPosition.callsign == callsign
                ).first()
                
                if existing_atc_position:
                    # Update existing ATC position
                    existing_atc_position.facility = facility
                    existing_atc_position.position = position
                    existing_atc_position.frequency = frequency
                    existing_atc_position.controller_id = controller_id
                    existing_atc_position.controller_name = controller_name
                    existing_atc_position.controller_rating = controller_rating
                    existing_atc_position.status = "online"
                    existing_atc_position.last_seen = datetime.utcnow()
                else:
                    # Create new ATC position
                    new_atc_position = ATCPosition(
                        callsign=callsign,
                        facility=facility,
                        position=position,
                        frequency=frequency,
                        controller_id=controller_id,
                        controller_name=controller_name,
                        controller_rating=controller_rating,
                        status="online",
                        last_seen=datetime.utcnow(),
                        workload_score=0.0
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
                heading = flight_data.heading
                ground_speed = flight_data.ground_speed
                vertical_speed = flight_data.vertical_speed
                squawk = flight_data.squawk
                
                # Position data - store as separate lat/lng fields
                position_lat = flight_data.position.get("lat", 0) if flight_data.position else 0
                position_lng = flight_data.position.get("lng", 0) if flight_data.position else 0
                
                # Try to find controlling ATC position based on flight position
                # This is a simplified approach - in reality you'd need more sophisticated logic
                atc_position_id = None
                
                # Find online ATC positions for assignment
                online_atc_positions = db.query(ATCPosition).filter(
                    ATCPosition.status == "online"
                ).all()
                
                logger.info(f"Flight {callsign}: Found {len(online_atc_positions)} online ATC positions")
                
                if online_atc_positions:
                    # Simple round-robin assignment based on flight callsign hash
                    # This works regardless of position data availability
                    flight_hash = hashlib.md5(callsign.encode()).hexdigest()
                    position_index = int(flight_hash, 16) % len(online_atc_positions)
                    atc_position_id = online_atc_positions[position_index].id
                    logger.info(f"Flight {callsign}: Assigned to ATC position {atc_position_id}")
                else:
                    logger.warning(f"Flight {callsign}: No online ATC positions available for assignment")
                
                # Check if flight already exists
                existing_flight = db.query(Flight).filter(
                    Flight.callsign == callsign
                ).first()
                
                if existing_flight:
                    # Update existing flight
                    existing_flight.aircraft_type = aircraft_type
                    existing_flight.departure = departure
                    existing_flight.arrival = arrival
                    existing_flight.route = route
                    existing_flight.altitude = altitude
                    existing_flight.speed = speed
                    existing_flight.heading = heading
                    existing_flight.ground_speed = ground_speed
                    existing_flight.vertical_speed = vertical_speed
                    existing_flight.squawk = squawk
                    existing_flight.position_lat = position_lat
                    existing_flight.position_lng = position_lng
                    existing_flight.atc_position_id = atc_position_id
                    existing_flight.last_updated = datetime.utcnow()
                else:
                    # Create new flight
                    new_flight = Flight(
                        callsign=callsign,
                        aircraft_type=aircraft_type,
                        departure=departure,
                        arrival=arrival,
                        route=route,
                        altitude=altitude,
                        speed=speed,
                        heading=heading,
                        ground_speed=ground_speed,
                        vertical_speed=vertical_speed,
                        squawk=squawk,
                        position_lat=position_lat,
                        position_lng=position_lng,
                        atc_position_id=atc_position_id,
                        last_updated=datetime.utcnow()
                    )
                    db.add(new_flight)
            
            logger.info(f"Processed {len(flights_data)} flights")
            
        except Exception as e:
            logger.error(f"Error processing flights: {e}")
            raise
    
    async def _process_sectors(self, sectors_data: List[Dict[str, Any]], db: Session):
        """Process and store sector data"""
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
    
    async def cleanup_old_data(self):
        """Clean up old data (flights that are no longer active)"""
        db = SessionLocal()
        try:
            # Remove flights that haven't been updated in the last 5 minutes
            cutoff_time = datetime.utcnow() - timedelta(minutes=5)
            old_flights = db.query(Flight).filter(
                Flight.last_updated < cutoff_time
            ).all()
            
            for flight in old_flights:
                db.delete(flight)
            
            # Remove controllers that haven't been seen in the last 10 minutes
            cutoff_time = datetime.utcnow() - timedelta(minutes=10)
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
        await self.vatsim_client.close()

# Background task for continuous data ingestion
async def background_data_ingestion():
    """Background task to continuously ingest VATSIM data"""
    service = DataIngestionService()
    
    while True:
        try:
            await service.ingest_current_data()
            await service.cleanup_old_data()
            await asyncio.sleep(30)  # Update every 30 seconds
        except Exception as e:
            logger.error(f"Background ingestion error: {e}")
            await asyncio.sleep(60)  # Wait longer on error
        finally:
            await service.close() 