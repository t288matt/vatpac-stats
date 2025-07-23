#!/usr/bin/env python3
"""
Data Ingestion System for VATSIM Data
Stores real-time VATSIM data in our database
"""

import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from .database import get_db, SessionLocal
from .models import Controller, Flight, Sector
from .vatsim_client import VATSIMClient

logger = logging.getLogger(__name__)

class DataIngestionService:
    """Service to ingest VATSIM data into our database"""
    
    def __init__(self):
        self.vatsim_client = VATSIMClient()
    
    async def ingest_current_data(self):
        """Ingest current VATSIM data into database"""
        try:
            # Fetch current VATSIM data
            data = await self.vatsim_client.get_current_data()
            
            # Process controllers
            await self._process_controllers(data.get("controllers", []))
            
            # Process flights
            await self._process_flights(data.get("flights", []))
            
            # Process sectors (if available)
            await self._process_sectors(data.get("sectors", []))
            
            logger.info(f"Data ingestion completed: {len(data.get('controllers', []))} controllers, {len(data.get('flights', []))} flights")
            
        except Exception as e:
            logger.error(f"Error during data ingestion: {e}")
    
    async def _process_controllers(self, controllers_data: List):
        """Process and store controller data"""
        db = SessionLocal()
        try:
            for controller_data in controllers_data:
                # Extract controller information from dataclass
                callsign = controller_data.callsign
                facility = controller_data.facility
                position = controller_data.position
                frequency = controller_data.frequency
                
                # Check if controller already exists
                existing_controller = db.query(Controller).filter(
                    Controller.callsign == callsign
                ).first()
                
                if existing_controller:
                    # Update existing controller
                    existing_controller.facility = facility
                    existing_controller.position = position
                    existing_controller.frequency = frequency
                    existing_controller.status = "online"
                    existing_controller.last_seen = datetime.utcnow()
                else:
                    # Create new controller
                    new_controller = Controller(
                        callsign=callsign,
                        facility=facility,
                        position=position,
                        frequency=frequency,
                        status="online",
                        last_seen=datetime.utcnow(),
                        workload_score=0.0
                    )
                    db.add(new_controller)
            
            db.commit()
            logger.info(f"Processed {len(controllers_data)} controllers")
            
        except Exception as e:
            logger.error(f"Error processing controllers: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def _process_flights(self, flights_data: List):
        """Process and store flight data"""
        db = SessionLocal()
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
                
                # Position data
                position_data = {
                    "latitude": flight_data.position.get("lat", 0) if flight_data.position else 0,
                    "longitude": flight_data.position.get("lng", 0) if flight_data.position else 0,
                    "altitude": altitude
                }
                
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
                    existing_flight.position = str(position_data)
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
                        position=str(position_data),
                        last_updated=datetime.utcnow()
                    )
                    db.add(new_flight)
            
            db.commit()
            logger.info(f"Processed {len(flights_data)} flights")
            
        except Exception as e:
            logger.error(f"Error processing flights: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def _process_sectors(self, sectors_data: List[Dict[str, Any]]):
        """Process and store sector data"""
        db = SessionLocal()
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
            
            db.commit()
            logger.info(f"Processed {len(sectors_data)} sectors")
            
        except Exception as e:
            logger.error(f"Error processing sectors: {e}")
            db.rollback()
        finally:
            db.close()
    
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