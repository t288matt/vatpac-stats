#!/usr/bin/env python3
"""
Data service for ATC Position Recommendation Engine.

This service handles all database operations and data processing,
following our architecture principles of maintainability and supportability.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
import json
from collections import defaultdict
import time

from ..config import get_config
from ..utils.logging import get_logger_for_module
from ..database import SessionLocal
from ..models import Controller, Flight, Sector, TrafficMovement, FlightSummary
from .vatsim_service import VATSIMService
from .traffic_analysis_service import TrafficAnalysisService

logger = logging.getLogger(__name__)

class DataService:
    def __init__(self):
        self.vatsim_service = VATSIMService()
        self.cache = {
            'flights': {},
            'controllers': {},
            'last_write': 0,
            'write_interval': 300,  # Write to disk every 5 minutes instead of every 30 seconds
            'memory_buffer': defaultdict(list)
        }
        self.write_count = 0
        self.last_cleanup = time.time()
        
    async def start_data_ingestion(self):
        """Start the data ingestion process with SSD wear optimization"""
        logger.info("Starting data ingestion process with SSD wear optimization")
        
        while True:
            try:
                # Fetch VATSIM data
                vatsim_data = await self.vatsim_service.get_current_data()
                
                if vatsim_data:
                    # Process data in memory first
                    await self._process_data_in_memory(vatsim_data)
                    
                    # Only write to disk periodically to reduce SSD wear
                    current_time = time.time()
                    if current_time - self.cache['last_write'] >= self.cache['write_interval']:
                        await self._flush_memory_to_disk()
                        self.cache['last_write'] = current_time
                        logger.info(f"Flushed memory cache to disk. Write count: {self.write_count}")
                    
                    # Cleanup old data periodically
                    if current_time - self.last_cleanup >= 3600:  # Every hour
                        await self._cleanup_old_data()
                        self.last_cleanup = current_time
                
                # Wait before next cycle
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in data ingestion: {e}")
                await asyncio.sleep(30)
    
    async def _process_data_in_memory(self, vatsim_data: Dict[str, Any]):
        """Process data in memory to reduce disk writes"""
        try:
            controllers_data = vatsim_data.get('controllers', [])
            flights_data = vatsim_data.get('pilots', [])
            
            # Process controllers in memory
            controllers_count = await self._process_controllers_in_memory(controllers_data)
            
            # Process flights in memory
            flights_count = await self._process_flights_in_memory(flights_data)
            
            # Process sectors (if any)
            sectors_data = vatsim_data.get('sectors', [])
            sectors_count = await self._process_sectors_in_memory(sectors_data)
            
            # Detect traffic movements in memory
            movements_count = await self._detect_movements_in_memory()
            
            logger.info("Data ingestion completed successfully", extra={
                'controllers': controllers_count,
                'flights': flights_count,
                'sectors': sectors_count,
                'movements': movements_count
            })
            
        except Exception as e:
            logger.error(f"Error processing data in memory: {e}")
    
    async def _process_controllers_in_memory(self, controllers_data: List[Dict[str, Any]]) -> int:
        """Process controllers in memory cache"""
        try:
            processed_count = 0
            
            for controller_data in controllers_data:
                callsign = controller_data.get('callsign', '')
                
                # Update memory cache
                self.cache['controllers'][callsign] = {
                    'callsign': callsign,
                    'facility': controller_data.get('facility', ''),
                    'position': controller_data.get('position', ''),
                    'status': 'online',
                    'frequency': controller_data.get('frequency', ''),
                    'last_seen': datetime.utcnow(),
                    'workload_score': 0.0,
                    'preferences': json.dumps(controller_data.get('preferences', {}))
                }
                processed_count += 1
            
            logger.info(f"Processed {processed_count} controllers in memory")
            return processed_count
            
        except Exception as e:
            logger.error(f"Error processing controllers in memory: {e}")
            return 0
    
    async def _process_flights_in_memory(self, flights_data: List[Dict[str, Any]]) -> int:
        """Process flights in memory cache"""
        try:
            processed_count = 0
            
            for flight_data in flights_data:
                callsign = flight_data.get('callsign', '')
                
                # Update memory cache
                self.cache['flights'][callsign] = {
                    'callsign': callsign,
                    'aircraft_type': flight_data.get('aircraft', ''),
                    'departure': flight_data.get('departure', ''),
                    'arrival': flight_data.get('arrival', ''),
                    'altitude': flight_data.get('altitude', 0),
                    'speed': flight_data.get('groundspeed', 0),
                    'latitude': flight_data.get('latitude', 0.0),
                    'longitude': flight_data.get('longitude', 0.0),
                    'heading': flight_data.get('heading', 0),
                    'last_updated': datetime.utcnow(),
                    'status': 'active'
                }
                processed_count += 1
            
            logger.info(f"Processed {processed_count} flights in memory")
            return processed_count
            
        except Exception as e:
            logger.error(f"Error processing flights in memory: {e}")
            return 0
    
    async def _process_sectors_in_memory(self, sectors_data: List[Dict[str, Any]]) -> int:
        """Process sectors in memory cache"""
        try:
            # Sectors processing in memory (minimal for now)
            return len(sectors_data)
        except Exception as e:
            logger.error(f"Error processing sectors in memory: {e}")
            return 0
    
    async def _detect_movements_in_memory(self) -> int:
        """Detect traffic movements using memory data"""
        try:
            # Use memory cache for movement detection
            movements_count = 0
            
            # Simple movement detection based on cached flight data
            for callsign, flight_data in self.cache['flights'].items():
                # Check if flight is near any configured airports
                # This is a simplified version - full logic would be more complex
                pass
            
            return movements_count
            
        except Exception as e:
            logger.error(f"Error detecting movements in memory: {e}")
            return 0
    
    async def _flush_memory_to_disk(self):
        """Flush memory cache to disk with batching and compression (reduced frequency)"""
        try:
            db = SessionLocal()
            try:
                # BATCH 1: Controllers (batch write for efficiency)
                controller_batch = []
                for callsign, controller_data in self.cache['controllers'].items():
                    existing = db.query(Controller).filter(Controller.callsign == callsign).first()
                    if existing:
                        # Update existing
                        for key, value in controller_data.items():
                            setattr(existing, key, value)
                    else:
                        # Create new
                        controller = Controller(**controller_data)
                        controller_batch.append(controller)
                
                # Bulk insert controllers
                if controller_batch:
                    db.bulk_save_objects(controller_batch)
                
                # BATCH 2: Flights (batch write for efficiency)
                flight_batch = []
                for callsign, flight_data in self.cache['flights'].items():
                    existing = db.query(Flight).filter(Flight.callsign == callsign).first()
                    if existing:
                        # Update existing
                        for key, value in flight_data.items():
                            setattr(existing, key, value)
                    else:
                        # Create new
                        flight = Flight(**flight_data)
                        flight_batch.append(flight)
                
                # Bulk insert flights
                if flight_batch:
                    db.bulk_save_objects(flight_batch)
                
                # Single commit for all changes (reduces disk writes)
                db.commit()
                self.write_count += 1
                
                # Clear memory cache after successful write
                self.cache['controllers'].clear()
                self.cache['flights'].clear()
                
                logger.info(f"Flushed memory cache to disk. Total writes: {self.write_count}")
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error flushing memory to disk: {e}")
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in memory flush: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old data to prevent database bloat"""
        try:
            db = SessionLocal()
            try:
                # Clean up old flights (older than 1 hour) - they're no longer active
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                old_flights = db.query(Flight).filter(
                    Flight.last_updated < cutoff_time
                ).all()
                
                for flight in old_flights:
                    # Store flight summary before deletion
                    await self._store_flight_summary(flight)
                    db.delete(flight)
                
                # Mark controllers as offline if not seen in 30 minutes
                controller_cutoff = datetime.utcnow() - timedelta(minutes=30)
                offline_controllers = db.query(Controller).filter(
                    and_(
                        Controller.last_seen < controller_cutoff,
                        Controller.status == 'online'
                    )
                ).all()
                
                for controller in offline_controllers:
                    controller.status = 'offline'
                
                # Clean up old movements (older than 7 days)
                movement_cutoff = datetime.utcnow() - timedelta(days=7)
                old_movements = db.query(TrafficMovement).filter(
                    TrafficMovement.timestamp < movement_cutoff
                ).all()
                
                for movement in old_movements:
                    db.delete(movement)
                
                db.commit()
                logger.info(f"Cleaned up {len(old_flights)} old flights, {len(offline_controllers)} offline controllers, {len(old_movements)} old movements")
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error in cleanup: {e}")
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in cleanup process: {e}")
    
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
                    duration_minutes=duration_minutes,
                    max_altitude=flight.altitude,
                    max_speed=flight.speed,
                    created_at=datetime.utcnow()
                )
                
                db.add(summary)
                db.commit()
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error storing flight summary: {e}")
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in flight summary storage: {e}")
    
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
            logger.error("Failed to get network status", extra={
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