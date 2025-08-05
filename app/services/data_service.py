#!/usr/bin/env python3
"""
Data service for ATC Position Recommendation Engine.

This service handles all database operations and data processing,
following our architecture principles of maintainability and supportability.
"""

import asyncio
import logging
import os
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
from ..models import ATCPosition, Flight, Sector, TrafficMovement, FlightSummary
from .vatsim_service import VATSIMService
from .traffic_analysis_service import TrafficAnalysisService

logger = logging.getLogger(__name__)

class DataService:
    def __init__(self):
        self.vatsim_service = VATSIMService()
        # Get intervals from environment variables
        self.vatsim_polling_interval = int(os.getenv('VATSIM_POLLING_INTERVAL', 30))
        self.vatsim_write_interval = int(os.getenv('VATSIM_WRITE_INTERVAL', 300))
        self.vatsim_cleanup_interval = int(os.getenv('VATSIM_CLEANUP_INTERVAL', 3600))
        
        self.cache = {
            'flights': {},
            'atc_positions': {},
            'last_write': 0,
            'write_interval': self.vatsim_write_interval,  # Write to disk every 5 minutes instead of every 30 seconds
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
                    if current_time - self.last_cleanup >= self.vatsim_cleanup_interval:  # Every hour
                        await self._cleanup_old_data()
                        self.last_cleanup = current_time
                
                # Wait before next cycle
                await asyncio.sleep(self.vatsim_polling_interval)
                
            except Exception as e:
                logger.error(f"Error in data ingestion: {e}")
                await asyncio.sleep(self.vatsim_polling_interval)
    
    async def _process_data_in_memory(self, vatsim_data):
        """Process data in memory to reduce disk writes"""
        try:
            # Import dataclasses for proper conversion
            from dataclasses import asdict
            
            # Convert VATSIMData object to dictionary format
            if hasattr(vatsim_data, 'controllers'):
                atc_positions_data = [asdict(atc_position) for atc_position in vatsim_data.controllers]
            else:
                atc_positions_data = []
                
            if hasattr(vatsim_data, 'flights'):
                flights_data = [asdict(flight) for flight in vatsim_data.flights]
            else:
                flights_data = []
                
            if hasattr(vatsim_data, 'sectors'):
                sectors_data = vatsim_data.sectors
            else:
                sectors_data = []
            
            if hasattr(vatsim_data, 'transceivers'):
                transceivers_data = [asdict(transceiver) for transceiver in vatsim_data.transceivers]
            else:
                transceivers_data = []
            
            # Process ATC positions in memory
            atc_positions_count = await self._process_atc_positions_in_memory(atc_positions_data)
            
            # Process flights in memory
            flights_count = await self._process_flights_in_memory(flights_data)
            
            # Process sectors (if any)
            sectors_count = await self._process_sectors_in_memory(sectors_data)
            
            # Process transceivers in memory
            transceivers_count = await self._process_transceivers_in_memory(transceivers_data)
            
            # Detect traffic movements in memory
            movements_count = await self._detect_movements_in_memory()
            
            logger.info("Data ingestion completed successfully", extra={
                'atc_positions': atc_positions_count,
                'flights': flights_count,
                'sectors': sectors_count,
                'transceivers': transceivers_count,
                'movements': movements_count
            })
            
        except Exception as e:
            logger.error(f"Error processing data in memory: {e}")
    
    async def _process_atc_positions_in_memory(self, atc_positions_data: List[Dict[str, Any]]) -> int:
        """Process ATC positions in memory cache"""
        try:
            processed_count = 0
            
            for atc_position_data in atc_positions_data:
                callsign = atc_position_data.get('callsign', '')
                
                # Update memory cache
                self.cache['atc_positions'][callsign] = {
                    'callsign': callsign,
                    'facility': atc_position_data.get('facility', ''),
                    'position': atc_position_data.get('position', ''),
                    'status': 'online',
                    'frequency': atc_position_data.get('frequency', ''),
                    'controller_id': atc_position_data.get('controller_id', ''),
                    'controller_name': atc_position_data.get('controller_name', ''),
                    'controller_rating': atc_position_data.get('controller_rating', 0),
                    'last_seen': datetime.utcnow(),
                    'workload_score': 0.0,
                    'preferences': json.dumps(atc_position_data.get('preferences', {}))
                }
                processed_count += 1
            
            logger.info(f"Processed {processed_count} ATC positions in memory")
            return processed_count
            
        except Exception as e:
            logger.error(f"Error processing ATC positions in memory: {e}")
            return 0
    
    async def _process_flights_in_memory(self, flights_data: List[Dict[str, Any]]) -> int:
        """Process flights in memory cache - FILTERED FOR AUSTRALIAN AIRPORTS ONLY"""
        try:
            processed_count = 0
            australian_count = 0
            
            for flight_data in flights_data:
                callsign = flight_data.get('callsign', '')
                departure = flight_data.get('departure', '')
                arrival = flight_data.get('arrival', '')
                
                # Import airport configuration
                from ..config import is_australian_airport
                
                # Filter for Australian airports using configuration
                is_australian_flight = (
                    (departure and is_australian_airport(departure)) or 
                    (arrival and is_australian_airport(arrival))
                )
                
                if not is_australian_flight:
                    continue
                
                australian_count += 1
                
                # Update memory cache with correct field mapping
                position_data = flight_data.get('position', {})
                
                # Try to find controlling ATC position for this flight
                atc_position_id = None
                # For now, skip ATC position assignment to avoid database issues
                
                self.cache['flights'][callsign] = {
                    'callsign': callsign,
                    'aircraft_type': flight_data.get('aircraft_type', ''),
                    'departure': departure,
                    'arrival': arrival,
                    'route': flight_data.get('route', ''),
                    'altitude': flight_data.get('altitude', 0),
                    'speed': flight_data.get('speed', 0),
                    'position_lat': position_data.get('lat', 0.0) if position_data else 0.0,
                    'position_lng': position_data.get('lng', 0.0) if position_data else 0.0,
                    'heading': flight_data.get('heading', 0),
                    'ground_speed': flight_data.get('ground_speed', 0),
                    'vertical_speed': flight_data.get('vertical_speed', 0),
                    'squawk': flight_data.get('squawk', ''),
                    'atc_position_id': atc_position_id,
                    'last_updated': datetime.utcnow(),
                    'status': 'active'
                }
                processed_count += 1
            
            logger.info(f"Processed {processed_count} Australian flights out of {len(flights_data)} total flights")
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
    
    async def _process_transceivers_in_memory(self, transceivers_data: List[Dict[str, Any]]) -> int:
        """Process transceivers in memory cache"""
        try:
            processed_count = 0
            
            for transceiver_data in transceivers_data:
                callsign = transceiver_data.get('callsign', '')
                transceiver_id = transceiver_data.get('transceiver_id', 0)
                
                # Create unique key for transceiver
                transceiver_key = f"{callsign}_{transceiver_id}"
                
                # Update memory cache
                self.cache['memory_buffer']['transceivers'].append({
                    'callsign': callsign,
                    'transceiver_id': transceiver_id,
                    'frequency': transceiver_data.get('frequency', 0),
                    'position_lat': transceiver_data.get('position_lat'),
                    'position_lon': transceiver_data.get('position_lon'),
                    'height_msl': transceiver_data.get('height_msl'),
                    'height_agl': transceiver_data.get('height_agl'),
                    'entity_type': transceiver_data.get('entity_type', 'flight'),
                    'entity_id': transceiver_data.get('entity_id'),
                    'timestamp': datetime.utcnow()
                })
                processed_count += 1
            
            logger.info(f"Processed {processed_count} transceivers in memory")
            return processed_count
            
        except Exception as e:
            logger.error(f"Error processing transceivers in memory: {e}")
            return 0
    
    async def _detect_movements_in_memory(self) -> int:
        """Detect traffic movements using memory data"""
        try:
            # Use memory cache for movement detection
            movements_count = 0
            
            # Convert cached flight data to Flight objects for movement detection
            db = SessionLocal()
            try:
                # Get all active flights from database for movement detection
                active_flights = db.query(Flight).filter(Flight.status == 'active').all()
                
                if active_flights:
                    # Use TrafficAnalysisService to detect movements
                    traffic_service = TrafficAnalysisService(db)
                    detected_movements = traffic_service.detect_movements(active_flights)
                    
                    # Store detected movements
                    for movement in detected_movements:
                        # Check if this movement already exists (avoid duplicates)
                        existing = db.query(TrafficMovement).filter(
                            and_(
                                TrafficMovement.aircraft_callsign == movement.aircraft_callsign,
                                TrafficMovement.airport_code == movement.airport_code,
                                TrafficMovement.movement_type == movement.movement_type,
                                TrafficMovement.timestamp >= datetime.utcnow() - timedelta(minutes=5)
                            )
                        ).first()
                        
                        if not existing:
                            db.add(movement)
                            movements_count += 1
                    
                    # Commit movements to database
                    if movements_count > 0:
                        db.commit()
                        logger.info(f"Detected and stored {movements_count} new traffic movements")
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error detecting movements: {e}")
            finally:
                db.close()
            
            return movements_count
            
        except Exception as e:
            logger.error(f"Error detecting movements in memory: {e}")
            return 0
    
    async def _flush_memory_to_disk(self):
        """Flush memory cache to disk with batching and compression (reduced frequency)"""
        try:
            db = SessionLocal()
            try:
                # BATCH 1: ATC Positions (batch write for efficiency)
                atc_position_batch = []
                for callsign, atc_position_data in self.cache['atc_positions'].items():
                    existing = db.query(ATCPosition).filter(ATCPosition.callsign == callsign).first()
                    if existing:
                        # Update existing
                        for key, value in atc_position_data.items():
                            setattr(existing, key, value)
                    else:
                        # Create new
                        atc_position = ATCPosition(**atc_position_data)
                        atc_position_batch.append(atc_position)
                
                # Bulk insert ATC positions
                if atc_position_batch:
                    db.bulk_save_objects(atc_position_batch)
                
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
                
                # BATCH 3: Transceivers (batch write for efficiency)
                from ..models import Transceiver
                transceiver_batch = []
                for transceiver_data in self.cache['memory_buffer']['transceivers']:
                    # Check if transceiver already exists
                    existing = db.query(Transceiver).filter(
                        and_(
                            Transceiver.callsign == transceiver_data['callsign'],
                            Transceiver.transceiver_id == transceiver_data['transceiver_id']
                        )
                    ).first()
                    
                    if existing:
                        # Update existing transceiver
                        for key, value in transceiver_data.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                    else:
                        # Create new transceiver
                        transceiver = Transceiver(**transceiver_data)
                        transceiver_batch.append(transceiver)
                
                # Bulk insert transceivers
                if transceiver_batch:
                    db.bulk_save_objects(transceiver_batch)
                
                # Single commit for all changes (reduces disk writes)
                db.commit()
                self.write_count += 1
                
                # Clear memory cache after successful write
                self.cache['atc_positions'].clear()
                self.cache['flights'].clear()
                self.cache['memory_buffer']['transceivers'].clear()
                
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
                # Mark old flights as completed (older than 1 hour) - preserve historical data
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                old_flights = db.query(Flight).filter(
                    and_(
                        Flight.last_updated < cutoff_time,
                        Flight.status == 'active'
                    )
                ).all()
                
                for flight in old_flights:
                    # Mark as completed instead of deleting
                    flight.status = 'completed'
                    # Store flight summary for analytics
                    await self._store_flight_summary(flight)
                
                # Mark ATC positions as offline if not seen in 30 minutes
                atc_position_cutoff = datetime.utcnow() - timedelta(minutes=30)
                offline_atc_positions = db.query(ATCPosition).filter(
                    and_(
                        ATCPosition.last_seen < atc_position_cutoff,
                        ATCPosition.status == 'online'
                    )
                ).all()
                
                for atc_position in offline_atc_positions:
                    atc_position.status = 'offline'
                
                # Clean up old movements (older than 7 days)
                movement_cutoff = datetime.utcnow() - timedelta(days=7)
                old_movements = db.query(TrafficMovement).filter(
                    TrafficMovement.timestamp < movement_cutoff
                ).all()
                
                for movement in old_movements:
                    db.delete(movement)
                
                db.commit()
                logger.info(f"Marked {len(old_flights)} flights as completed, {len(offline_atc_positions)} offline ATC positions, {len(old_movements)} old movements")
                
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
                    route=flight.route,
                    max_altitude=flight.altitude,
                    duration_minutes=duration_minutes,
                    completed_at=datetime.utcnow()
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
            # Count active ATC positions
            active_atc_positions = db.query(ATCPosition).filter(
                ATCPosition.status == "online"
            ).count()
            
            # Count active flights
            active_flights = db.query(Flight).filter(Flight.status == "active").count()
            
            # Count total flights (active + completed)
            total_flights = db.query(Flight).count()
            
            # Count total sectors
            total_sectors = db.query(Sector).count()
            
            return {
                "active_atc_positions": active_atc_positions,
                "active_flights": active_flights,
                "total_sectors": total_sectors,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get network status", extra={
                "error": str(e)
            })
            return {
                "active_atc_positions": 0,
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