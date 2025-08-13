#!/usr/bin/env python3
"""
Database Service - Simplified

Handles database operations for VATSIM data storage and retrieval.
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Flight, Controller, Transceiver
from app.database import SessionLocal
from app.utils.logging import get_logger_for_module
from app.utils.error_handling import handle_service_errors, log_operation

class DatabaseService:
    """Database service implementation using existing models."""
    
    def __init__(self):
        self.logger = get_logger_for_module(__name__)
    
    async def initialize(self):
        """Initialize database service."""
        pass
    
    async def cleanup(self):
        """Cleanup database service resources."""
        pass
    

    
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
            
            session.commit()
            session.close()
            
            return stored_count
            
        except Exception as e:
            self.logger.error(f"Failed to store flights: {e}")
            if session:
                session.rollback()
                session.close()
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
            
            session.commit()
            session.close()
            
            return stored_count
            
        except Exception as e:
            self.logger.error(f"Failed to store controllers: {e}")
            if session:
                session.rollback()
                session.close()
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
            
            session.commit()
            session.close()
            
            return stored_count
            
        except Exception as e:
            self.logger.error(f"Failed to store transceivers: {e}")
            if session:
                session.rollback()
                session.close()
            raise
    
    @handle_service_errors
    @log_operation("get_flight_track")
    async def get_flight_track(self, callsign: str, start_time: Optional[datetime] = None, 
                              end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get flight track data for a specific callsign."""
        try:
            session = SessionLocal()
            
            query = session.query(Flight).filter(Flight.callsign == callsign)
            
            if start_time:
                query = query.filter(Flight.last_updated >= start_time)
            if end_time:
                query = query.filter(Flight.last_updated <= end_time)
            
            flights = query.order_by(Flight.last_updated).all()
            
            # Convert to dict format
            track_data = []
            for flight in flights:
                track_data.append({
                    'callsign': flight.callsign,
                    'latitude': flight.latitude,
                    'longitude': flight.longitude,
                    'altitude': flight.altitude,
                    'heading': flight.heading,
                    'groundspeed': flight.groundspeed,
                    'timestamp': flight.last_updated.isoformat() if flight.last_updated else None
                })
            
            session.close()
            
            return track_data
            
        except Exception as e:
            self.logger.error(f"Failed to get flight track for {callsign}: {e}")
            if session:
                session.close()
            raise

def get_database_service() -> DatabaseService:
    """Get database service instance."""
    return DatabaseService() 