#!/usr/bin/env python3
"""
Database Service for VATSIM Data Collection System - Phase 2

This service provides dedicated database operations using existing models.
It implements the DatabaseServiceInterface and preserves all existing
database functionality while providing a clean, focused service layer.

INPUTS:
- Database operations requests from other services
- Existing SQLAlchemy models (Flight, Controller, Sector, etc.)
- Database connection and session management
- Query parameters and filters

OUTPUTS:
- Database records and query results
- Database health and status information
- Database statistics and analytics
- Error handling and recovery information

FEATURES:
- Uses existing models from app/models.py (preserved unchanged)
- Focused database operations only
- Connection pooling and session management
- Error handling with circuit breakers
- Database health monitoring
- Query optimization and performance tracking

PRESERVED MODELS:
- Flight: Complete flight tracking with all position updates
- Controller: ATC controller positions and status
- Sector: Airspace sector definitions
- TrafficMovement: Airport arrival/departure tracking
- All other existing models unchanged
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func, text
import logging

from ..database import SessionLocal, get_db
from ..models import Flight, Controller, Sector, TrafficMovement, FlightSummary, Transceiver, VatsimStatus
from .interfaces.database_service_interface import DatabaseServiceInterface
from .base_service import BaseService
from ..utils.logging import get_logger_for_module
from ..utils.error_handling import handle_service_errors, log_operation
from ..utils.error_manager import ErrorContext, error_manager


class DatabaseService(BaseService, DatabaseServiceInterface):
    """Database service implementation using existing models."""
    
    def __init__(self):
        super().__init__("database_service")
        self.logger = get_logger_for_module(__name__)
        self.session_pool = []
        self.max_pool_size = 10
        self.active_sessions = 0
        
        # Performance tracking
        self.query_count = 0
        self.query_times = []
        self.last_cleanup = datetime.now(timezone.utc)
    
    async def _initialize_service(self):
        """Initialize database service."""
        self.logger.info("Initializing database service")
        # Database service doesn't need special initialization
        # as it uses existing database connection management
    
    async def _cleanup_service(self):
        """Cleanup database service resources."""
        self.logger.info("Cleaning up database service")
        # Close any active sessions
        for session in self.session_pool:
            try:
                session.close()
            except Exception as e:
                self.logger.warning(f"Error closing session: {e}")
        self.session_pool.clear()
    
    async def _perform_health_check(self) -> Dict[str, Any]:
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
                    # Use existing Flight model (preserved unchanged)
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
            context = ErrorContext(
                service_name="database_service",
                operation="store_flights",
                metadata={"flight_count": len(flights)}
            )
            await error_manager.handle_error(e, context)
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
                    # Use existing Controller model (preserved unchanged)
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
            context = ErrorContext(
                service_name="database_service",
                operation="store_controllers",
                metadata={"controller_count": len(controllers)}
            )
            await error_manager.handle_error(e, context)
            raise
    
    @handle_service_errors
    @log_operation("store_sectors")
    async def store_sectors(self, sectors: List[Dict[str, Any]]) -> int:
        """Store sector data using existing Sector model."""
        try:
            session = SessionLocal()
            stored_count = 0
            
            for sector_data in sectors:
                try:
                    # Use existing Sector model (preserved unchanged)
                    sector = Sector(**sector_data)
                    session.add(sector)
                    stored_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to store sector {sector_data.get('name', 'unknown')}: {e}")
                    continue
            
            await session.commit()
            session.close()
            
            self.logger.info(f"Stored {stored_count} sectors")
            return stored_count
            
        except Exception as e:
            self.logger.error(f"Failed to store sectors: {e}")
            context = ErrorContext(
                service_name="database_service",
                operation="store_sectors",
                metadata={"sector_count": len(sectors)}
            )
            await error_manager.handle_error(e, context)
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
                    # Use existing Transceiver model (preserved unchanged)
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
            context = ErrorContext(
                service_name="database_service",
                operation="store_transceivers",
                metadata={"transceiver_count": len(transceivers)}
            )
            await error_manager.handle_error(e, context)
            raise
    
    @handle_service_errors
    @log_operation("get_flight_track")
    async def get_flight_track(self, callsign: str, start_time: Optional[datetime] = None, 
                              end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get complete flight track using existing Flight model."""
        try:
            session = SessionLocal()
            
            # Build query using existing Flight model
            query = session.query(Flight).filter(Flight.callsign == callsign)
            
            if start_time:
                query = query.filter(Flight.last_updated >= start_time)
            if end_time:
                query = query.filter(Flight.last_updated <= end_time)
            
            # Order by timestamp to get complete track
            flights = query.order_by(Flight.last_updated).all()
            
            # Convert to dictionaries
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
                    "arrival": flight.arrival,
                    "status": flight.status
                })
            
            session.close()
            
            self.logger.debug(f"Retrieved {len(track_data)} position updates for {callsign}")
            return track_data
            
        except Exception as e:
            self.logger.error(f"Failed to get flight track for {callsign}: {e}")
            context = ErrorContext(
                service_name="database_service",
                operation="get_flight_track",
                metadata={"callsign": callsign, "start_time": start_time, "end_time": end_time}
            )
            await error_manager.handle_error(e, context)
            raise
    
    @handle_service_errors
    @log_operation("get_flight_stats")
    async def get_flight_stats(self, callsign: str) -> Dict[str, Any]:
        """Get flight statistics using existing Flight model."""
        try:
            session = SessionLocal()
            
            # Get all flights for this callsign
            flights = session.query(Flight).filter(Flight.callsign == callsign).all()
            
            if not flights:
                session.close()
                return {"error": "Flight not found"}
            
            # Calculate statistics
            total_positions = len(flights)
            first_position = min(flights, key=lambda f: f.last_updated) if flights else None
            last_position = max(flights, key=lambda f: f.last_updated) if flights else None
            
            # Calculate duration
            duration = None
            if first_position and last_position:
                duration = (last_position.last_updated - first_position.last_updated).total_seconds() / 60  # minutes
            
            # Calculate altitude statistics
            altitudes = [f.altitude for f in flights if f.altitude is not None]
            max_altitude = max(altitudes) if altitudes else None
            min_altitude = min(altitudes) if altitudes else None
            avg_altitude = sum(altitudes) / len(altitudes) if altitudes else None
            
            # Calculate speed statistics
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
                "arrival": first_position.arrival if first_position else None,
                "status": last_position.status if last_position else None
            }
            
            session.close()
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get flight stats for {callsign}: {e}")
            context = ErrorContext(
                service_name="database_service",
                operation="get_flight_stats",
                metadata={"callsign": callsign}
            )
            await error_manager.handle_error(e, context)
            raise
    
    @handle_service_errors
    @log_operation("get_active_flights")
    async def get_active_flights(self) -> List[Dict[str, Any]]:
        """Get active flights using existing Flight model."""
        try:
            session = SessionLocal()
            
            # Get active flights (status = 'active')
            active_flights = session.query(Flight).filter(
                Flight.status == "active"
            ).all()
            
            # Convert to dictionaries
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
            context = ErrorContext(
                service_name="database_service",
                operation="get_active_flights"
            )
            await error_manager.handle_error(e, context)
            raise
    
    @handle_service_errors
    @log_operation("get_active_controllers")
    async def get_active_controllers(self) -> List[Dict[str, Any]]:
        """Get active controllers using existing Controller model."""
        try:
            session = SessionLocal()
            
            # Get active controllers (status = 'online')
            active_controllers = session.query(Controller).filter(
                Controller.status == "online"
            ).all()
            
            # Convert to dictionaries
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
            context = ErrorContext(
                service_name="database_service",
                operation="get_active_controllers"
            )
            await error_manager.handle_error(e, context)
            raise
    
    @handle_service_errors
    @log_operation("cleanup_old_data")
    async def cleanup_old_data(self, hours: int = 24) -> int:
        """Clean up old data using existing models."""
        try:
            session = SessionLocal()
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Clean up old flights
            old_flights = session.query(Flight).filter(
                Flight.last_updated < cutoff_time
            ).delete()
            
            # Clean up old controllers
            old_controllers = session.query(Controller).filter(
                Controller.last_seen < cutoff_time
            ).delete()
            
            # Clean up old transceivers
            old_transceivers = session.query(Transceiver).filter(
                Transceiver.timestamp < cutoff_time
            ).delete()
            
            session.commit()
            session.close()
            
            total_cleaned = old_flights + old_controllers + old_transceivers
            self.logger.info(f"Cleaned up {total_cleaned} old records")
            
            return total_cleaned
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")
            context = ErrorContext(
                service_name="database_service",
                operation="cleanup_old_data",
                metadata={"hours": hours}
            )
            await error_manager.handle_error(e, context)
            raise
    
    @handle_service_errors
    @log_operation("get_database_stats")
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and health information."""
        try:
            session = SessionLocal()
            
            # Get record counts
            flight_count = session.query(Flight).count()
            controller_count = session.query(Controller).count()
            sector_count = session.query(Sector).count()
            transceiver_count = session.query(Transceiver).count()
            
            # Get active counts
            active_flights = session.query(Flight).count()
            active_controllers = session.query(Controller).filter(Controller.status == "online").count()
            
            # Get recent activity
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            recent_flights = session.query(Flight).filter(
                Flight.last_updated >= recent_cutoff
            ).count()
            
            stats = {
                "total_flights": flight_count,
                "total_controllers": controller_count,
                "total_sectors": sector_count,
                "total_transceivers": transceiver_count,
                "active_flights": active_flights,
                "active_controllers": active_controllers,
                "recent_flights": recent_flights,
                "last_cleanup": self.last_cleanup.isoformat(),
                "query_count": self.query_count,
                "avg_query_time": sum(self.query_times) / len(self.query_times) if self.query_times else 0
            }
            
            session.close()
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {e}")
            context = ErrorContext(
                service_name="database_service",
                operation="get_database_stats"
            )
            await error_manager.handle_error(e, context)
            raise
    
    @handle_service_errors
    @log_operation("health_check")
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the database service."""
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
                "status": "healthy",
                "database_connected": True,
                "flight_count": flight_count,
                "controller_count": controller_count,
                "last_cleanup": self.last_cleanup.isoformat(),
                "query_count": self.query_count
            }
            
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "database_connected": False,
                "error": str(e)
            }
    
    @handle_service_errors
    @log_operation("get_session")
    async def get_session(self) -> Session:
        """Get database session for direct model operations."""
        try:
            session = SessionLocal()
            self.active_sessions += 1
            return session
        except Exception as e:
            self.logger.error(f"Failed to get database session: {e}")
            context = ErrorContext(
                service_name="database_service",
                operation="get_session"
            )
            await error_manager.handle_error(e, context)
            raise


# Global database service instance
database_service = DatabaseService()


def get_database_service() -> DatabaseService:
    """Get the global database service instance."""
    return database_service 