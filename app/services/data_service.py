#!/usr/bin/env python3
"""
Data service for ATC Position Recommendation Engine.

This service handles all database operations and data processing,
following our architecture principles of maintainability and supportability.
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..config import get_config
from ..utils.logging import get_logger_for_module
from ..database import get_db, SessionLocal
from ..models import Controller, Flight, Sector, TrafficMovement
from .vatsim_service import VATSIMService, VATSIMData, VATSIMController, VATSIMFlight
from .traffic_analysis_service import get_traffic_analysis_service
from ..models import FlightSummary, MovementSummary


class DataServiceError(Exception):
    """Exception raised when data service operations fail."""
    
    def __init__(self, message: str, operation: str = None):
        super().__init__(message)
        self.message = message
        self.operation = operation


class DataService:
    """
    Service for handling database operations and data processing.
    
    This service provides a clean interface for database operations,
    following our architecture principles.
    """
    
    def __init__(self):
        """Initialize data service with configuration."""
        self.config = get_config()
        self.logger = get_logger_for_module(__name__)
        self.vatsim_service = VATSIMService()
    
    async def ingest_current_data(self) -> Dict[str, int]:
        """
        Ingest current VATSIM data into the database.
        
        Returns:
            Dict[str, int]: Counts of processed data
        """
        try:
            self.logger.info("Starting data ingestion process")
            
            # Fetch current VATSIM data
            vatsim_data = await self.vatsim_service.get_current_data()
            
            # Process data in batches
            controller_count = await self._process_controllers(vatsim_data.controllers)
            flight_count = await self._process_flights(vatsim_data.flights)
            sector_count = await self._process_sectors(vatsim_data.sectors)
            
            # Detect and store traffic movements
            movement_count = await self._detect_traffic_movements()
            
            # Clean up old data
            await self._cleanup_old_data()
            
            result = {
                "controllers": controller_count,
                "flights": flight_count,
                "sectors": sector_count,
                "movements": movement_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.logger.info("Data ingestion completed successfully", extra=result)
            return result
            
        except Exception as e:
            self.logger.exception("Data ingestion failed", extra={
                "error": str(e)
            })
            raise DataServiceError(f"Data ingestion failed: {e}", "ingest_data")
    
    async def _process_controllers(self, controllers: List[VATSIMController]) -> int:
        """
        Process and store controller data.
        
        Args:
            controllers: List of VATSIM controller objects
            
        Returns:
            int: Number of controllers processed
        """
        db = SessionLocal()
        try:
            processed_count = 0
            
            for controller in controllers:
                try:
                    # Check if controller already exists
                    existing = db.query(Controller).filter(
                        Controller.callsign == controller.callsign
                    ).first()
                    
                    if existing:
                        # Update existing controller
                        existing.facility = controller.facility
                        existing.position = controller.position
                        existing.status = controller.status
                        existing.frequency = controller.frequency
                        existing.last_seen = datetime.utcnow()
                    else:
                        # Create new controller
                        new_controller = Controller(
                            callsign=controller.callsign,
                            facility=controller.facility,
                            position=controller.position,
                            status=controller.status,
                            frequency=controller.frequency,
                            last_seen=datetime.utcnow()
                        )
                        db.add(new_controller)
                    
                    processed_count += 1
                    
                except Exception as e:
                    self.logger.warning(
                        f"Failed to process controller {controller.callsign}: {e}",
                        extra={
                            "callsign": controller.callsign,
                            "error": str(e)
                        }
                    )
            
            db.commit()
            self.logger.info(f"Processed {processed_count} controllers")
            return processed_count
            
        except Exception as e:
            db.rollback()
            self.logger.error("Failed to process controllers", extra={
                "error": str(e)
            })
            raise DataServiceError(f"Controller processing failed: {e}", "process_controllers")
        finally:
            db.close()
    
    async def _process_flights(self, flights: List[VATSIMFlight]) -> int:
        """
        Process and store flight data.
        
        Args:
            flights: List of VATSIM flight objects
            
        Returns:
            int: Number of flights processed
        """
        db = SessionLocal()
        try:
            processed_count = 0
            
            for flight in flights:
                try:
                    # Check if flight already exists
                    existing = db.query(Flight).filter(
                        Flight.callsign == flight.callsign
                    ).first()
                    
                    # Prepare position data
                    position_data = None
                    if flight.position:
                        import json
                        position_data = json.dumps({
                            "latitude": flight.position.get("lat", 0),
                            "longitude": flight.position.get("lng", 0),
                            "altitude": flight.altitude
                        })
                    
                    if existing:
                        # Update existing flight
                        existing.pilot_name = flight.pilot_name
                        existing.aircraft_type = flight.aircraft_type
                        existing.departure = flight.departure
                        existing.arrival = flight.arrival
                        existing.route = flight.route
                        existing.altitude = flight.altitude
                        existing.speed = flight.speed
                        existing.position = position_data
                        existing.last_updated = datetime.utcnow()
                    else:
                        # Create new flight
                        new_flight = Flight(
                            callsign=flight.callsign,
                            pilot_name=flight.pilot_name,
                            aircraft_type=flight.aircraft_type,
                            departure=flight.departure,
                            arrival=flight.arrival,
                            route=flight.route,
                            altitude=flight.altitude,
                            speed=flight.speed,
                            position=position_data,
                            last_updated=datetime.utcnow()
                        )
                        db.add(new_flight)
                    
                    processed_count += 1
                    
                except Exception as e:
                    self.logger.warning(
                        f"Failed to process flight {flight.callsign}: {e}",
                        extra={
                            "callsign": flight.callsign,
                            "error": str(e)
                        }
                    )
            
            db.commit()
            self.logger.info(f"Processed {processed_count} flights")
            return processed_count
            
        except Exception as e:
            db.rollback()
            self.logger.error("Failed to process flights", extra={
                "error": str(e)
            })
            raise DataServiceError(f"Flight processing failed: {e}", "process_flights")
        finally:
            db.close()
    
    async def _process_sectors(self, sectors: List[Dict[str, Any]]) -> int:
        """
        Process and store sector data.
        
        Args:
            sectors: List of sector data dictionaries
            
        Returns:
            int: Number of sectors processed
        """
        db = SessionLocal()
        try:
            processed_count = 0
            
            for sector_data in sectors:
                try:
                    sector_name = sector_data.get("name", "")
                    
                    # Check if sector already exists
                    existing = db.query(Sector).filter(
                        Sector.name == sector_name
                    ).first()
                    
                    if existing:
                        # Update existing sector
                        existing.facility = sector_data.get("facility", "")
                        existing.status = sector_data.get("status", "unmanned")
                    else:
                        # Create new sector
                        new_sector = Sector(
                            name=sector_name,
                            facility=sector_data.get("facility", ""),
                            status=sector_data.get("status", "unmanned")
                        )
                        db.add(new_sector)
                    
                    processed_count += 1
                    
                except Exception as e:
                    self.logger.warning(
                        f"Failed to process sector {sector_data.get('name', 'unknown')}: {e}",
                        extra={
                            "sector_data": sector_data,
                            "error": str(e)
                        }
                    )
            
            db.commit()
            self.logger.info(f"Processed {processed_count} sectors")
            return processed_count
            
        except Exception as e:
            db.rollback()
            self.logger.error("Failed to process sectors", extra={
                "error": str(e)
            })
            raise DataServiceError(f"Sector processing failed: {e}", "process_sectors")
        finally:
            db.close()
    
    async def _detect_traffic_movements(self) -> int:
        """
        Detect and store traffic movements from current flight data.
        
        Returns:
            int: Number of movements detected and stored
        """
        try:
            db = SessionLocal()
            try:
                # Get current flights
                flights = db.query(Flight).filter(
                    Flight.last_updated >= datetime.utcnow() - timedelta(minutes=5)
                ).all()
                
                if not flights:
                    return 0
                
                # Initialize traffic analysis service
                traffic_service = get_traffic_analysis_service(db)
                
                # Detect movements
                movements = traffic_service.detect_movements(flights)
                
                # Store movements
                for movement in movements:
                    db.add(movement)
                
                db.commit()
                
                self.logger.info(f"Detected {len(movements)} traffic movements")
                return len(movements)
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error detecting traffic movements: {e}")
            return 0
    
    async def _cleanup_old_data(self):
        """Clean up old data to prevent database bloat while preserving data quality"""
        try:
            db = SessionLocal()
            try:
                # TIER 1: Real-time data (keep current)
                # - Active flights: Keep all data
                # - Active controllers: Keep all data
                # - Recent movements: Keep for 24 hours
                
                # TIER 2: Historical data (aggregate after 1 hour)
                # Clean up old flights (older than 1 hour) - they're no longer active
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                old_flights = db.query(Flight).filter(
                    Flight.last_updated < cutoff_time
                ).all()
                
                for flight in old_flights:
                    # Store flight summary before deletion
                    await self._store_flight_summary(flight)
                    db.delete(flight)
                
                # TIER 3: Controller status management
                # Mark controllers as offline if not seen in 30 minutes
                controller_cutoff = datetime.utcnow() - timedelta(minutes=30)
                offline_controllers = db.query(Controller).filter(
                    and_(
                        Controller.last_seen < controller_cutoff,
                        Controller.status == "online"
                    )
                ).all()
                
                for controller in offline_controllers:
                    controller.status = "offline"
                
                # TIER 4: Movement data retention (7 days for analytics)
                movement_cutoff = datetime.utcnow() - timedelta(days=7)
                old_movements = db.query(TrafficMovement).filter(
                    TrafficMovement.timestamp < movement_cutoff
                ).all()
                
                for movement in old_movements:
                    # Store movement summary before deletion
                    await self._store_movement_summary(movement)
                    db.delete(movement)
                
                db.commit()
                
                cleaned_count = len(old_flights) + len(offline_controllers) + len(old_movements)
                if cleaned_count > 0:
                    self.logger.info(f"Data retention cleanup: {len(old_flights)} old flights, {len(offline_controllers)} offline controllers, {len(old_movements)} old movements")
                
            except Exception as e:
                db.rollback()
                self.logger.error(f"Failed to cleanup old data: {e}")
                raise
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error during data cleanup: {e}")
            raise DataServiceError(f"Data cleanup failed: {e}", "cleanup_old_data")
    
    async def _store_flight_summary(self, flight: Flight):
        """Store flight summary for analytics before deletion - PRESERVES DATA QUALITY"""
        try:
            db = SessionLocal()
            try:
                # Calculate flight duration if we have timestamps
                duration_minutes = 0
                if hasattr(flight, 'created_at') and flight.created_at:
                    duration_minutes = int((flight.last_updated - flight.created_at).total_seconds() / 60)
                
                # Create flight summary with ALL critical data preserved
                summary = FlightSummary(
                    callsign=flight.callsign,
                    aircraft_type=flight.aircraft_type,
                    departure=flight.departure,
                    arrival=flight.arrival,
                    route=flight.route,
                    max_altitude=flight.altitude,
                    duration_minutes=min(duration_minutes, 65535),  # Cap at SMALLINT max
                    controller_id=flight.controller_id,
                    sector_id=flight.sector_id,
                    completed_at=flight.last_updated
                )
                
                db.add(summary)
                db.commit()
                
                self.logger.debug(f"Stored flight summary for {flight.callsign} - DATA QUALITY PRESERVED")
                
            except Exception as e:
                db.rollback()
                self.logger.error(f"Failed to store flight summary: {e}")
            finally:
                db.close()
            
        except Exception as e:
            self.logger.error(f"Failed to store flight summary: {e}")
    
    async def _store_movement_summary(self, movement: TrafficMovement):
        """Store movement summary for analytics before deletion - PRESERVES DATA QUALITY"""
        try:
            db = SessionLocal()
            try:
                # Check if summary already exists for this hour
                existing_summary = db.query(MovementSummary).filter(
                    and_(
                        MovementSummary.airport_icao == movement.airport_icao,
                        MovementSummary.movement_type == movement.movement_type,
                        MovementSummary.aircraft_type == movement.aircraft_type,
                        MovementSummary.date == movement.timestamp.date(),
                        MovementSummary.hour == movement.timestamp.hour
                    )
                ).first()
                
                if existing_summary:
                    # Increment count for existing summary
                    existing_summary.count = min(existing_summary.count + 1, 65535)
                    self.logger.debug(f"Updated movement summary for {movement.airport_icao} - DATA QUALITY PRESERVED")
                else:
                    # Create new summary
                    summary = MovementSummary(
                        airport_icao=movement.airport_icao,
                        movement_type=movement.movement_type,
                        aircraft_type=movement.aircraft_type,
                        date=movement.timestamp.date(),
                        hour=movement.timestamp.hour,
                        count=1
                    )
                    db.add(summary)
                    self.logger.debug(f"Created movement summary for {movement.airport_icao} - DATA QUALITY PRESERVED")
                
                db.commit()
                
            except Exception as e:
                db.rollback()
                self.logger.error(f"Failed to store movement summary: {e}")
            finally:
                db.close()
            
        except Exception as e:
            self.logger.error(f"Failed to store movement summary: {e}")
    
    def get_network_status(self) -> Dict[str, Any]:
        """
        Get current network status from database.
        
        Returns:
            Dict[str, Any]: Network status information
        """
        db = SessionLocal()
        try:
            # Count active controllers
            active_controllers = db.query(Controller).filter(
                Controller.status == "online"
            ).count()
            
            # Count active flights
            active_flights = db.query(Flight).count()
            
            # Count total sectors
            total_sectors = db.query(Sector).count()
            
            return {
                "active_controllers": active_controllers,
                "active_flights": active_flights,
                "total_sectors": total_sectors,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error("Failed to get network status", extra={
                "error": str(e)
            })
            return {
                "active_controllers": 0,
                "active_flights": 0,
                "total_sectors": 0,
                "error": str(e),
                "last_updated": datetime.utcnow().isoformat()
            }
        finally:
            db.close()


# Global service instance
_data_service: Optional[DataService] = None


def get_data_service() -> DataService:
    """
    Get the global data service instance.
    
    Returns:
        DataService: The global data service instance
    """
    global _data_service
    if _data_service is None:
        _data_service = DataService()
    return _data_service 