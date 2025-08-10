#!/usr/bin/env python3
"""
Database Service for VATSIM Data Collection System

This service handles all database operations including storing and retrieving
flight data, controller data, and transceiver data.

INPUTS:
- Flight data from VATSIM API
- Controller data from VATSIM API
- Transceiver data from VATSIM API
- Database connection and session management

OUTPUTS:
- Stored flight records in database
- Stored controller records in database
- Stored transceiver records in database
- Flight tracking and statistics
- Database health and performance metrics

FEATURES:
- Connection pooling for performance
- Comprehensive error handling and logging
- Health monitoring and statistics
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models import Flight, Controller, Transceiver
from ..database import SessionLocal
from ..utils.logging import get_logger_for_module
from ..utils.error_handling import handle_service_errors, log_operation

class DatabaseService:
    """Database service implementation using existing models."""
    
    def __init__(self):
        self.logger = get_logger_for_module(__name__)
        self.query_count = 0
        self.last_cleanup = datetime.now(timezone.utc)
    
    async def initialize(self):
        """Initialize database service."""
        self.logger.info("Initializing database service")
    
    async def cleanup(self):
        """Cleanup database service resources."""
        self.logger.info("Cleaning up database service")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform database service health check."""
        try:
            session = SessionLocal()
            
            # Test basic connectivity
            result = session.execute(text("SELECT 1"))
            result.fetchone()
            
            # Get basic stats
            flight_count = session.query(Flight).count()
            controller_count = session.query(Controller).count()
            
            session.close()
            
            return {
                "database_connected": True,
                "flight_count": flight_count,
                "controller_count": controller_count,
                "last_cleanup": self.last_cleanup.isoformat(),
                "query_count": self.query_count
            }
            
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return {
                "database_connected": False,
                "error": str(e)
            }
    
    @handle_service_errors
    @log_operation("store_flights")
    async def store_flights(self, flights: List[Dict[str, Any]]) -> int:
        """Store flight data using existing Flight model."""
        try:
            session = SessionLocal()
            stored_count = 0
            
            for flight_data in flights:
                try:
                    flight = Flight(**flight_data)
                    session.add(flight)
                    stored_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to store flight {flight_data.get('callsign', 'unknown')}: {e}")
                    continue
            
            await session.commit()
            session.close()
            
            self.logger.info(f"Stored {stored_count} flights")
            return stored_count
            
        except Exception as e:
            self.logger.error(f"Failed to store flights: {e}")
            raise
    
    @handle_service_errors
    @log_operation("store_controllers")
    async def store_controllers(self, controllers: List[Dict[str, Any]]) -> int:
        """Store controller data using existing Controller model."""
        try:
            session = SessionLocal()
            stored_count = 0
            
            for controller_data in controllers:
                try:
                    controller = Controller(**controller_data)
                    session.add(controller)
                    stored_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to store controller {controller_data.get('callsign', 'unknown')}: {e}")
                    continue
            
            await session.commit()
            session.close()
            
            self.logger.info(f"Stored {stored_count} controllers")
            return stored_count
            
        except Exception as e:
            self.logger.error(f"Failed to store controllers: {e}")
            raise
    
    @handle_service_errors
    @log_operation("store_transceivers")
    async def store_transceivers(self, transceivers: List[Dict[str, Any]]) -> int:
        """Store transceiver data using existing Transceiver model."""
        try:
            session = SessionLocal()
            stored_count = 0
            
            for transceiver_data in transceivers:
                try:
                    transceiver = Transceiver(**transceiver_data)
                    session.add(transceiver)
                    stored_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to store transceiver {transceiver_data.get('callsign', 'unknown')}: {e}")
                    continue
            
            await session.commit()
            session.close()
            
            self.logger.info(f"Stored {stored_count} transceivers")
            return stored_count
            
        except Exception as e:
            self.logger.error(f"Failed to store transceivers: {e}")
            raise
    
    @handle_service_errors
    @log_operation("get_flight_track")
    async def get_flight_track(self, callsign: str, start_time: Optional[datetime] = None, 
                              end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get complete flight track using existing Flight model."""
        try:
            session = SessionLocal()
            
            query = session.query(Flight).filter(Flight.callsign == callsign)
            
            if start_time:
                query = query.filter(Flight.last_updated >= start_time)
            if end_time:
                query = query.filter(Flight.last_updated <= end_time)
            
            flights = query.order_by(Flight.last_updated).all()
            
            track_data = []
            for flight in flights:
                track_data.append({
                    "callsign": flight.callsign,
                    "latitude": flight.latitude,
                    "longitude": flight.longitude,
                    "altitude": flight.altitude,
                    "groundspeed": flight.groundspeed,
                    "heading": flight.heading,
                    "last_updated": flight.last_updated.isoformat() if flight.last_updated else None,
                    "aircraft_type": flight.aircraft_type,
                    "departure": flight.departure,
                    "arrival": flight.arrival
                })
            
            session.close()
            
            self.logger.debug(f"Retrieved {len(track_data)} position updates for {callsign}")
            return track_data
            
        except Exception as e:
            self.logger.error(f"Failed to get flight track for {callsign}: {e}")
            raise
    
    @handle_service_errors
    @log_operation("get_flight_stats")
    async def get_flight_stats(self, callsign: str) -> Dict[str, Any]:
        """Get flight statistics using existing Flight model."""
        try:
            session = SessionLocal()
            
            flights = session.query(Flight).filter(Flight.callsign == callsign).all()
            
            if not flights:
                session.close()
                return {"error": "Flight not found"}
            
            total_positions = len(flights)
            first_position = min(flights, key=lambda f: f.last_updated) if flights else None
            last_position = max(flights, key=lambda f: f.last_updated) if flights else None
            
            duration = None
            if first_position and last_position:
                duration = (last_position.last_updated - first_position.last_updated).total_seconds() / 60
            
            altitudes = [f.altitude for f in flights if f.altitude is not None]
            max_altitude = max(altitudes) if altitudes else None
            min_altitude = min(altitudes) if altitudes else None
            avg_altitude = sum(altitudes) / len(altitudes) if altitudes else None
            
            speeds = [f.groundspeed for f in flights if f.groundspeed is not None]
            max_speed = max(speeds) if speeds else None
            avg_speed = sum(speeds) / len(speeds) if speeds else None
            
            stats = {
                "callsign": callsign,
                "total_positions": total_positions,
                "first_position": first_position.last_updated.isoformat() if first_position else None,
                "last_position": last_position.last_updated.isoformat() if last_position else None,
                "duration_minutes": duration,
                "max_altitude": max_altitude,
                "min_altitude": min_altitude,
                "avg_altitude": avg_altitude,
                "max_speed": max_speed,
                "avg_speed": avg_speed,
                "aircraft_type": first_position.aircraft_type if first_position else None,
                "departure": first_position.departure if first_position else None,
                "arrival": first_position.arrival if first_position else None
            }
            
            session.close()
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get flight stats for {callsign}: {e}")
            raise
    
    @handle_service_errors
    @log_operation("get_active_flights")
    async def get_active_flights(self) -> List[Dict[str, Any]]:
        """Get active flights using existing Flight model."""
        try:
            session = SessionLocal()
            
            active_flights = session.query(Flight).all()
            
            flights_data = []
            for flight in active_flights:
                flights_data.append({
                    "callsign": flight.callsign,
                    "latitude": flight.latitude,
                    "longitude": flight.longitude,
                    "altitude": flight.altitude,
                    "groundspeed": flight.groundspeed,
                    "heading": flight.heading,
                    "aircraft_type": flight.aircraft_type,
                    "departure": flight.departure,
                    "arrival": flight.arrival,
                    "last_updated": flight.last_updated.isoformat() if flight.last_updated else None
                })
            
            session.close()
            
            self.logger.debug(f"Retrieved {len(flights_data)} active flights")
            return flights_data
            
        except Exception as e:
            self.logger.error(f"Failed to get active flights: {e}")
            raise
    
    @handle_service_errors
    @log_operation("get_active_controllers")
    async def get_active_controllers(self) -> List[Dict[str, Any]]:
        """Get active controllers using existing Controller model."""
        try:
            session = SessionLocal()
            
            active_controllers = session.query(Controller).filter(
                Controller.status == "online"
            ).all()
            
            controllers_data = []
            for controller in active_controllers:
                controllers_data.append({
                    "callsign": controller.callsign,
                    "facility": controller.facility,
                    "position": controller.position,
                    "frequency": controller.frequency,
                    "controller_name": controller.controller_name,
                    "controller_rating": controller.controller_rating,
                    "last_seen": controller.last_seen.isoformat() if controller.last_seen else None
                })
            
            session.close()
            
            self.logger.debug(f"Retrieved {len(controllers_data)} active controllers")
            return controllers_data
            
        except Exception as e:
            self.logger.error(f"Failed to get active controllers: {e}")
            raise
    
    @handle_service_errors
    @log_operation("get_database_stats")
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and health information."""
        try:
            session = SessionLocal()
            
            flight_count = session.query(Flight).count()
            controller_count = session.query(Controller).count()
            transceiver_count = session.query(Transceiver).count()
            
            active_flights = session.query(Flight).count()
            active_controllers = session.query(Controller).filter(Controller.status == "online").count()
            
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            recent_flights = session.query(Flight).filter(
                Flight.last_updated >= recent_cutoff
            ).count()
            
            stats = {
                "total_flights": flight_count,
                "total_controllers": controller_count,
                "total_transceivers": transceiver_count,
                "active_flights": active_flights,
                "active_controllers": active_controllers,
                "recent_flights": recent_flights,
                "last_cleanup": self.last_cleanup.isoformat(),
                "query_count": self.query_count
            }
            
            session.close()
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {e}")
            raise

# Global database service instance
database_service = DatabaseService()

def get_database_service() -> DatabaseService:
    """Get the global database service instance."""
    return database_service 