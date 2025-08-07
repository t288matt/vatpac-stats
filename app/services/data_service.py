#!/usr/bin/env python3
"""
Data Service for VATSIM Data Collection System

This service handles all database operations and data processing for the VATSIM
data collection system. It provides memory-optimized data ingestion with SSD
wear optimization and efficient database operations.

INPUTS:
- VATSIM API data (controllers, flights, sectors, transceivers)
- Real-time flight tracking information
- ATC position updates and status changes
- Memory cache for batch processing

OUTPUTS:
- Database records for all VATSIM data types
- Memory-optimized data processing
- Batch database operations
- Data cleanup and maintenance
- Network status and health metrics

FEATURES:
- Memory-based data processing to reduce SSD wear
- Batch database operations for efficiency
- Automatic data cleanup and maintenance
- Real-time status tracking
- Error handling and recovery
- Configurable processing intervals

DATA TYPES PROCESSED:
- ATC Positions: Controller callsigns, facilities, frequencies
- Flights: Aircraft tracking, position, altitude, speed
- Sectors: Airspace definitions and traffic density
- Transceivers: Radio frequency and position data
- Traffic Movements: Airport arrival/departure tracking

OPTIMIZATIONS:
- Memory caching to reduce disk I/O
- Batch database operations
- SSD wear optimization (periodic writes)
- Connection pooling
- Automatic cleanup of old data
"""

import asyncio
import os
from datetime import datetime, timezone, timedelta, timezone, timezone
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, insert, cast, JSON
import json
from collections import defaultdict
import time

from ..database import SessionLocal
from ..models import Controller, Flight, Sector, TrafficMovement, FlightSummary
from .vatsim_service import VATSIMService
from .traffic_analysis_service import TrafficAnalysisService
from .base_service import DatabaseService
from ..utils.error_handling import handle_service_errors, retry_on_failure, log_operation


class BoundedCache:
    """Bounded cache with LRU eviction to prevent memory leaks."""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache = {}
        self.access_times = {}
        self.access_counter = 0
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in the cache with LRU eviction."""
        if len(self.cache) >= self.max_size:
            # Evict least recently used
            oldest_key = min(self.access_times, key=self.access_times.get)
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
        
        self.cache[key] = value
        self.access_times[key] = self.access_counter
        self.access_counter += 1
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache and update access time."""
        if key in self.cache:
            self.access_times[key] = self.access_counter
            self.access_counter += 1
            return self.cache[key]
        return None
    
    def has_key(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self.cache
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.access_times.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)
    
    def keys(self):
        """Get all cache keys."""
        return list(self.cache.keys())
    
    def items(self):
        """Get all cache items."""
        return list(self.cache.items())


class DataService(DatabaseService):
    def __init__(self):
        super().__init__("data_service")
        self.vatsim_service = VATSIMService()
        self.traffic_analysis_service = None
        
        # Get intervals from configuration system (with fallback to environment variables for cleanup)
        self.vatsim_polling_interval = self.config.vatsim.refresh_interval
        self.vatsim_write_interval = self.config.vatsim.write_interval  # Uses config with 10-minute fallback
        self.vatsim_cleanup_interval = int(os.getenv('VATSIM_CLEANUP_INTERVAL', 3600))
        
        # Log the configured intervals
        self.logger.info(f"Data service configured with polling interval: {self.vatsim_polling_interval}s, write interval: {self.vatsim_write_interval}s")
        
        # Use bounded caches to prevent memory leaks
        max_cache_size = int(os.getenv('CACHE_MAX_SIZE', 10000))
        self.cache = {
            'flights': BoundedCache(max_cache_size),
            'atc_positions': BoundedCache(max_cache_size),
            'last_write': 0,
            'write_interval': self.vatsim_write_interval,
            'memory_buffer': defaultdict(list)
        }
        self.write_count = 0
        self.last_cleanup = time.time()
    
    async def _initialize_service(self):
        """Initialize data service with dependencies."""
        await super()._initialize_service()
        
        self.logger.info("Data service initialized successfully")
    
    async def _perform_health_check(self) -> Dict[str, Any]:
        """Perform data service health check."""
        try:
            # Check VATSIM service
            vatsim_health = await self.vatsim_service.health_check()
            
            # Check database connectivity
            db_health = await super()._perform_health_check()
            
            # Check cache status
            cache_status = {
                'flights_count': self.cache['flights'].size(),
                'atc_positions_count': self.cache['atc_positions'].size(),
                'memory_buffer_size': len(self.cache['memory_buffer']),
                'cache_max_size': self.cache['flights'].max_size
            }
            
            return {
                'vatsim_service': vatsim_health,
                'database': db_health,
                'cache_status': cache_status,
                'write_count': self.write_count,
                'last_cleanup': self.last_cleanup
            }
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {'error': str(e)}
    
    async def _cleanup_service(self):
        """Cleanup data service resources."""
        await super()._cleanup_service()
        
        # Clear memory cache
        self.cache['flights'].clear()
        self.cache['atc_positions'].clear()
        self.cache['memory_buffer'].clear()
        
        self.logger.info("Data service cleanup completed")
        
    async def start_data_ingestion(self):
        """Start the data ingestion process with SSD wear optimization"""
        self.logger.info("Starting data ingestion process with SSD wear optimization")
        
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
                        self.logger.info(f"Flushed memory cache to disk. Write count: {self.write_count}")
                    
                    # Cleanup old data periodically
                    if current_time - self.last_cleanup >= self.vatsim_cleanup_interval:
                        await self._cleanup_old_data()
                        self.last_cleanup = current_time
                    
                    # Update flight statuses (active ↔ stale) every API polling cycle
                    await self._update_flight_statuses()
                
                # Wait before next cycle
                await asyncio.sleep(self.vatsim_polling_interval)
                
            except Exception as e:
                self.logger.error(f"Error in data ingestion: {e}")
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
            
            # NEW: Detect landings using hybrid completion system
            landing_count = await self._detect_landings_in_memory()
            
            # NEW: Detect pilot disconnects for landed flights
            disconnect_count = await self._detect_pilot_disconnects()
            
            # Detect traffic movements in memory
            # movements_count = await self._detect_movements_in_memory()
            movements_count = 0  # Temporarily disabled
            
            self.logger.info("Data ingestion completed successfully", extra={
                'atc_positions': atc_positions_count,
                'flights': flights_count,
                'sectors': sectors_count,
                'transceivers': transceivers_count,
                'landings_detected': landing_count,
                'pilot_disconnects': disconnect_count,
                'movements': movements_count
            })
            
        except Exception as e:
            self.logger.error(f"Error processing data in memory: {e}")
    
    async def _process_atc_positions_in_memory(self, atc_positions_data: List[Dict[str, Any]]) -> int:
        """Process ATC positions in memory cache"""
        try:
            processed_count = 0
            
            for atc_position_data in atc_positions_data:
                callsign = atc_position_data.get('callsign', '')
                
                # Update memory cache with correct API field mapping
                self.cache['atc_positions'].set(callsign, {
                    'callsign': callsign,
                    'facility': atc_position_data.get('facility', ''),
                    'position': atc_position_data.get('position', ''),
                    'status': 'online',
                    'frequency': atc_position_data.get('frequency', ''),
                    'controller_id': atc_position_data.get('cid', None),  # API "cid" → DB "controller_id"
                    'controller_name': atc_position_data.get('name', ''),  # API "name" → DB "controller_name"
                    'controller_rating': atc_position_data.get('rating', 0),  # API "rating" → DB "controller_rating"
                    'last_seen': datetime.now(timezone.utc),
                    'workload_score': 0.0,
                    'preferences': {}
                })
                processed_count += 1
            
            self.logger.info(f"Processed {processed_count} ATC positions in memory")
            return processed_count
            
        except Exception as e:
            self.logger.error(f"Error processing ATC positions in memory: {e}")
            return 0
    
    async def _process_flights_in_memory(self, flights_data: List[Dict[str, Any]]) -> int:
        """Process flights in memory cache"""
        try:
            processed_count = 0
            
            # Import flight filter configuration
            from ..config import get_config
            config = get_config()
            
            for flight_data in flights_data:
                callsign = flight_data.get('callsign', '')
                departure = flight_data.get('departure', '')
                arrival = flight_data.get('arrival', '')
                
                # Check if flight filter is enabled
                if config.flight_filter.enabled:
                    # Import airport configuration
                    from ..config import is_australian_airport
                    
                    # Filter for Australian airports using configuration
                    is_australian_flight = (
                        (departure and is_australian_airport(departure)) or 
                        (arrival and is_australian_airport(arrival))
                    )
                    
                    if not is_australian_flight:
                        continue
                
                if not callsign:
                    continue
                
                # Get position data
                position_data = {
                    'lat': flight_data.get('latitude', 0.0),
                    'lng': flight_data.get('longitude', 0.0)
                }
                
                # Create flight record
                flight_record = {
                    'callsign': callsign,
                    'aircraft_type': flight_data.get('aircraft_type', ''),
                    'departure': departure,
                    'arrival': arrival,
                    'route': flight_data.get('route', ''),
                    'altitude': flight_data.get('altitude', 0),
                    'heading': flight_data.get('heading', 0),
                    'transponder': flight_data.get('transponder', ''),
                    'position_lat': position_data.get('lat', 0.0) if position_data else 0.0,
                    'position_lng': position_data.get('lng', 0.0) if position_data else 0.0,
                    'groundspeed': flight_data.get('groundspeed', 0),
                    'cruise_tas': flight_data.get('cruise_tas', 0),
                    
                    # VATSIM API fields
                    'cid': flight_data.get('cid'),
                    'name': flight_data.get('name'),
                    'server': flight_data.get('server'),
                    'pilot_rating': flight_data.get('pilot_rating'),
                    'military_rating': flight_data.get('military_rating'),
                    'latitude': flight_data.get('latitude'),
                    'longitude': flight_data.get('longitude'),
                    'qnh_i_hg': flight_data.get('qnh_i_hg'),
                    'qnh_mb': flight_data.get('qnh_mb'),
                    'logon_time': flight_data.get('logon_time'),
                    'last_updated': flight_data.get('last_updated'),
                    
                    # Flight plan fields
                    'flight_rules': flight_data.get('flight_rules'),
                    'aircraft_faa': flight_data.get('aircraft_faa'),
                    'aircraft_short': flight_data.get('aircraft_short'),
                    'alternate': flight_data.get('alternate'),
                    'planned_altitude': flight_data.get('planned_altitude'),
                    'deptime': flight_data.get('deptime'),
                    'enroute_time': flight_data.get('enroute_time'),
                    'fuel_time': flight_data.get('fuel_time'),
                    'remarks': flight_data.get('remarks'),
                    'revision_id': flight_data.get('revision_id'),
                    'assigned_transponder': flight_data.get('assigned_transponder'),
        
                    'last_updated_api': datetime.now(timezone.utc),
                    'status': 'active'
                }
                
                # Store flight data with timestamp to create multiple records
                timestamp_key = f"{callsign}_{int(time.time())}"
                self.cache['flights'].set(timestamp_key, flight_record)
                processed_count += 1
                
                # FIX: Update existing flight records to 'active' status when they appear in current VATSIM data
                # This ensures flights that are currently flying are marked as active
                db = SessionLocal()
                try:
                    existing_flights = db.query(Flight).filter(
                        and_(
                            Flight.callsign == callsign,
                            Flight.status.in_(['stale', 'active'])
                        )
                    ).all()
                    
                    for existing_flight in existing_flights:
                        existing_flight.status = 'active'
                        existing_flight.last_updated = datetime.now(timezone.utc)
                    
                    if existing_flights:
                        db.commit()
                        self.logger.debug(f"Updated {len(existing_flights)} existing records for {callsign} to active status")
                        
                except Exception as e:
                    db.rollback()
                    self.logger.error(f"Error updating existing flight status for {callsign}: {e}")
                finally:
                    db.close()
            
            if config.flight_filter.enabled:
                self.logger.info(f"Processed {processed_count} Australian flights out of {len(flights_data)} total flights")
            else:
                self.logger.info(f"Processed {processed_count} flights out of {len(flights_data)} total flights (filter disabled)")
            return processed_count
            
        except Exception as e:
            self.logger.error(f"Error processing flights in memory: {e}")
            return 0
    
    async def _process_sectors_in_memory(self, sectors_data: List[Dict[str, Any]]) -> int:
        """Process sectors in memory cache"""
        try:
            # Sectors processing in memory (minimal for now)
            return len(sectors_data)
        except Exception as e:
            self.logger.error(f"Error processing sectors in memory: {e}")
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
                    'timestamp': datetime.now(timezone.utc)
                })
                processed_count += 1
            
            self.logger.info(f"Processed {processed_count} transceivers in memory")
            return processed_count
            
        except Exception as e:
            self.logger.error(f"Error processing transceivers in memory: {e}")
            return 0
    
    async def _detect_landings_in_memory(self) -> int:
        """Detect landings and trigger flight completion"""
        try:
            import os
            from ..models import Flight
            
            # Check if landing detection is enabled
            landing_enabled = os.getenv('LANDING_DETECTION_ENABLED', 'true').lower() == 'true'
            if not landing_enabled:
                return 0
            
            # Get active flights from database for landing detection
            db = SessionLocal()
            try:
                active_flights = db.query(Flight).filter(Flight.status.in_(['active', 'stale'])).all()
                
                if not active_flights:
                    return 0
                
                # Use TrafficAnalysisService to detect landings
                from .traffic_analysis_service import TrafficAnalysisService
                traffic_service = TrafficAnalysisService(db)
                landing_detections = traffic_service.detect_landings(active_flights)
                
                landing_count = 0
                for landing in landing_detections:
                    # Complete flight by landing
                    success = await self._complete_flight_by_landing(landing)
                    if success:
                        landing_count += 1
                
                if landing_count > 0:
                    self.logger.info(f"Detected and completed {landing_count} flights by landing")
                
                return landing_count
                
            except Exception as e:
                self.logger.error(f"Error detecting landings: {e}")
                return 0
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error in landing detection process: {e}")
            return 0
    
    async def _complete_flight_by_landing(self, landing_detection: Dict[str, Any]) -> bool:
        """Complete a flight based on landing detection - now sets status to 'landed'"""
        try:
            db = SessionLocal()
            try:
                # Find the flight
                flight = db.query(Flight).filter(
                    and_(
                        Flight.callsign == landing_detection['callsign'],
                        Flight.status.in_(['active', 'stale'])
                    )
                ).first()
                
                if not flight:
                    return False
                
                # Mark flight as landed (not completed - pilot still connected)
                flight.status = 'landed'
                flight.landed_at = landing_detection['timestamp']
                flight.completion_method = 'landing'
                flight.completion_confidence = landing_detection['confidence']
                
                # FIX: Update all existing position records for this flight to 'landed' status
                # This ensures consistent status reporting across all records for the same flight
                existing_flights = db.query(Flight).filter(
                    and_(
                        Flight.callsign == landing_detection['callsign'],
                        Flight.status.in_(['active', 'stale'])
                    )
                ).all()
                
                for existing_flight in existing_flights:
                    if existing_flight.id != flight.id:  # Don't update the main flight record twice
                        existing_flight.status = 'landed'
                        existing_flight.landed_at = landing_detection['timestamp']
                        existing_flight.completion_method = 'landing'
                        existing_flight.completion_confidence = landing_detection['confidence']
                
                # Create traffic movement record for landing
                from ..models import TrafficMovement
                movement = TrafficMovement(
                    airport_code=landing_detection['airport_code'],
                    movement_type='arrival',
                    aircraft_callsign=landing_detection['callsign'],
                    timestamp=landing_detection['timestamp'],
                    flight_completion_triggered=True,
                    completion_timestamp=landing_detection['timestamp'],
                    completion_confidence=landing_detection['confidence']
                )
                db.add(movement)
                
                # Don't store flight summary yet - pilot still connected
                # Summary will be stored when pilot disconnects
                
                db.commit()
                
                self.logger.info(f"Flight {flight.callsign} landed at {landing_detection['airport_code']}", extra={
                    'distance_nm': landing_detection['distance_nm'],
                    'altitude_above_airport': landing_detection['altitude_above_airport'],
                    'groundspeed': landing_detection['groundspeed']
                })
                
                return True
                
            except Exception as e:
                db.rollback()
                self.logger.error(f"Error marking flight as landed: {e}")
                return False
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error in flight landing process: {e}")
            return False
    
    async def _detect_pilot_disconnects(self) -> int:
        """Detect when pilots disconnect from VATSIM and complete landed flights"""
        try:
            import os
            
            # Check if pilot disconnect detection is enabled
            disconnect_enabled = os.getenv('PILOT_DISCONNECT_DETECTION_ENABLED', 'true').lower() == 'true'
            if not disconnect_enabled:
                return 0
            
            db = SessionLocal()
            try:
                # Get all landed flights
                landed_flights = db.query(Flight).filter(
                    Flight.status == 'landed'
                ).all()
                
                if not landed_flights:
                    return 0
                
                # Get current VATSIM data to check for connected pilots
                vatsim_data = await self.vatsim_service.get_current_data()
                connected_callsigns = {flight.callsign for flight in vatsim_data.flights}
                
                # Check for disconnected pilots
                disconnect_count = 0
                for flight in landed_flights:
                    if flight.callsign not in connected_callsigns:
                        # Pilot has disconnected
                        flight.status = 'completed'
                        flight.completed_at = datetime.now(timezone.utc)
                        flight.pilot_disconnected_at = datetime.now(timezone.utc)
                        flight.disconnect_method = 'detected'
                        
                        # FIX: Update all existing landed records for this flight to 'completed' status
                        # This ensures consistent status reporting across all records for the same flight
                        existing_landed_flights = db.query(Flight).filter(
                            and_(
                                Flight.callsign == flight.callsign,
                                Flight.status == 'landed'
                            )
                        ).all()
                        
                        for existing_flight in existing_landed_flights:
                            if existing_flight.id != flight.id:  # Don't update the main flight record twice
                                existing_flight.status = 'completed'
                                existing_flight.completed_at = datetime.now(timezone.utc)
                                existing_flight.pilot_disconnected_at = datetime.now(timezone.utc)
                                existing_flight.disconnect_method = 'detected'
                        
                        # Now store flight summary
                        await self._store_flight_summary(flight)
                        
                        disconnect_count += 1
                        
                        self.logger.info(f"Flight {flight.callsign} completed by pilot disconnect")
                
                if disconnect_count > 0:
                    db.commit()
                    self.logger.info(f"Detected and completed {disconnect_count} flights by pilot disconnect")
                
                return disconnect_count
                
            except Exception as e:
                db.rollback()
                self.logger.error(f"Error detecting pilot disconnects: {e}")
                return 0
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error in pilot disconnect detection process: {e}")
            return 0
    
    async def _complete_flight_by_time(self, flight: Flight) -> bool:
        """Complete a flight based on time-based fallback"""
        try:
            # Mark flight as completed
            flight.status = 'completed'
            flight.completed_at = datetime.now(timezone.utc)
            flight.completion_method = 'time'
            flight.completion_confidence = 1.0  # Binary confidence
            
            # Store flight summary
            await self._store_flight_summary(flight)
            
            self.logger.info(f"Flight {flight.callsign} completed by time-based fallback")
            return True
            
        except Exception as e:
            self.logger.error(f"Error completing flight by time: {e}")
            return False
    
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
                                TrafficMovement.timestamp >= datetime.now(timezone.utc) - timedelta(minutes=5)
                            )
                        ).first()
                        
                        if not existing:
                            db.add(movement)
                            movements_count += 1
                    
                    # Commit movements to database
                    if movements_count > 0:
                        db.commit()
                        self.logger.info(f"Detected and stored {movements_count} new traffic movements")
                
            except Exception as e:
                db.rollback()
                self.logger.error(f"Error detecting movements: {e}")
            finally:
                db.close()
            
            return movements_count
            
        except Exception as e:
            self.logger.error(f"Error detecting movements in memory: {e}")
            return 0
    
    async def _flush_memory_to_disk(self):
        """Flush memory cache to disk with optimized bulk operations"""
        try:
            db = SessionLocal()
            try:
                # OPTIMIZED BATCH 1: ATC Positions with bulk upsert
                atc_positions_data = list(self.cache['atc_positions'].items())
                if atc_positions_data:
                    # Prepare data for bulk upsert
                    atc_positions_values = [data for _, data in atc_positions_data]
                    
                    # Use bulk upsert with conflict resolution
                    try:
                        # Try PostgreSQL-specific upsert first
                        stmt = insert(Controller).values(atc_positions_values)
                        stmt = stmt.on_conflict_do_update(
                            index_elements=['callsign'],
                            set_=dict(
                                facility=stmt.excluded.facility,
                                position=stmt.excluded.position,
                                status=stmt.excluded.status,
                                frequency=stmt.excluded.frequency,
                                last_seen=stmt.excluded.last_seen,
                                workload_score=stmt.excluded.workload_score,
                                preferences=stmt.excluded.preferences
                            )
                        )
                        db.execute(stmt)
                    except AttributeError:
                        # Fallback to manual upsert for other databases
                        for data in atc_positions_values:
                            existing = db.query(Controller).filter(Controller.callsign == data['callsign']).first()
                            if existing:
                                for key, value in data.items():
                                    setattr(existing, key, value)
                            else:
                                atc_position = Controller(**data)
                                db.add(atc_position)
                    
                    self.logger.info(f"Bulk upserted {len(atc_positions_values)} ATC positions")
                
                # OPTIMIZED BATCH 2: Flights with bulk upsert
                flights_data = list(self.cache['flights'].items())
                if flights_data:
                    # Prepare data for bulk upsert
                    flights_values = [data for _, data in flights_data]
                    
                    # Use bulk upsert to handle duplicates gracefully
                    try:
                        # Try PostgreSQL-specific upsert first
                        stmt = insert(Flight).values(flights_values)
                        stmt = stmt.on_conflict_do_nothing()  # Ignore duplicates
                        db.execute(stmt)
                    except AttributeError:
                        # Fallback to manual upsert for other databases
                        for data in flights_values:
                            existing = db.query(Flight).filter(
                                and_(
                                    Flight.callsign == data['callsign'],
                                    Flight.last_updated_api == data['last_updated_api']
                                )
                            ).first()
                            if not existing:
                                flight = Flight(**data)
                                db.add(flight)
                    
                    self.logger.info(f"Bulk inserted {len(flights_values)} flight positions")
                
                # OPTIMIZED BATCH 3: Transceivers with bulk upsert
                from ..models import Transceiver
                transceivers_data = self.cache['memory_buffer'].get('transceivers', [])
                if transceivers_data:
                    # Use bulk upsert with conflict resolution
                    try:
                        # Try PostgreSQL-specific upsert first
                        stmt = insert(Transceiver).values(transceivers_data)
                        stmt = stmt.on_conflict_do_update(
                            index_elements=['callsign', 'transceiver_id'],
                            set_=dict(
                                frequency=stmt.excluded.frequency,
                                position_lat=stmt.excluded.position_lat,
                                position_lng=stmt.excluded.position_lng,
                                last_updated=stmt.excluded.last_updated
                            )
                        )
                        db.execute(stmt)
                    except AttributeError:
                        # Fallback to manual upsert for other databases
                        for data in transceivers_data:
                            existing = db.query(Transceiver).filter(
                                Transceiver.callsign == data['callsign'],
                                Transceiver.transceiver_id == data['transceiver_id']
                            ).first()
                            if existing:
                                for key, value in data.items():
                                    setattr(existing, key, value)
                            else:
                                transceiver = Transceiver(**data)
                                db.add(transceiver)
                    
                    self.logger.info(f"Bulk upserted {len(transceivers_data)} transceivers")
                
                # Single commit for all changes (reduces disk writes)
                db.commit()
                self.write_count += 1
                
                # Clear memory cache after successful write
                self.cache['atc_positions'].clear()
                self.cache['flights'].clear()
                self.cache['memory_buffer']['transceivers'].clear()
                
                self.logger.info(f"Flushed memory cache to disk. Total writes: {self.write_count}")
                
            except Exception as e:
                db.rollback()
                self.logger.error(f"Error flushing memory to disk: {e}")
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error in memory flush: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old data to prevent database bloat with hybrid completion logic"""
        try:
            import os
            db = SessionLocal()
            try:
                # Check if time-based fallback is enabled
                time_based_enabled = os.getenv('TIME_BASED_FALLBACK_ENABLED', 'true').lower() == 'true'
                if not time_based_enabled:
                    return
                
                # Get timeout configuration
                timeout_hours = float(os.getenv('TIME_BASED_TIMEOUT_HOURS', '1'))
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=timeout_hours)
                
                # Find flights that should be completed by time
                old_flights = db.query(Flight).filter(
                    and_(
                        Flight.last_updated < cutoff_time,
                        Flight.status.in_(['active', 'stale', 'landed'])  # Include landed flights
                    )
                ).all()
                
                time_completed_count = 0
                for flight in old_flights:
                    # Check if flight has recent landing detection
                    recent_landing = db.query(TrafficMovement).filter(
                        and_(
                            TrafficMovement.aircraft_callsign == flight.callsign,
                            TrafficMovement.flight_completion_triggered == True,
                            TrafficMovement.timestamp >= cutoff_time
                        )
                    ).first()
                    
                    # Only complete by time if no recent landing detection
                    if not recent_landing:
                        success = await self._complete_flight_by_time(flight)
                        if success:
                            time_completed_count += 1
                
                # Mark ATC positions as offline if not seen in 30 minutes
                atc_position_cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
                offline_atc_positions = db.query(Controller).filter(
                    and_(
                        Controller.last_seen < atc_position_cutoff,
                        Controller.status == 'online'
                    )
                ).all()
                
                for atc_position in offline_atc_positions:
                    atc_position.status = 'offline'
                
                # Clean up old movements (older than 7 days)
                movement_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
                old_movements = db.query(TrafficMovement).filter(
                    TrafficMovement.timestamp < movement_cutoff
                ).all()
                
                for movement in old_movements:
                    db.delete(movement)
                
                db.commit()
                self.logger.info(f"Time-based completion: {time_completed_count} flights, {len(offline_atc_positions)} offline ATC positions, {len(old_movements)} old movements")
                
            except Exception as e:
                db.rollback()
                self.logger.error(f"Error in cleanup: {e}")
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error in cleanup process: {e}")
    
    async def _update_flight_statuses(self):
        """Update flight statuses based on recent activity"""
        try:
            from ..config import get_config
            config = get_config()
            
            # Calculate stale timeout based on API polling interval
            stale_timeout_seconds = config.vatsim.refresh_interval * config.flight_status.stale_timeout_multiplier
            stale_cutoff = datetime.now(timezone.utc) - timedelta(seconds=stale_timeout_seconds)
            
            db = SessionLocal()
            try:
                # Mark active flights as stale if not updated recently
                stale_flights = db.query(Flight).filter(
                    and_(
                        Flight.last_updated < stale_cutoff,
                        Flight.status == 'active'
                    )
                ).all()
                
                for flight in stale_flights:
                    flight.status = 'stale'
                
                # Mark stale flights as active if they get updated
                active_cutoff = datetime.now(timezone.utc) - timedelta(seconds=config.vatsim.refresh_interval)
                recovered_flights = db.query(Flight).filter(
                    and_(
                        Flight.last_updated >= active_cutoff,
                        Flight.status == 'stale'
                    )
                ).all()
                
                for flight in recovered_flights:
                    flight.status = 'active'
                
                db.commit()
                
                if stale_flights or recovered_flights:
                    self.logger.info(f"Updated {len(stale_flights)} flights to stale, {len(recovered_flights)} flights to active")
                    
            except Exception as e:
                db.rollback()
                self.logger.error(f"Error updating flight statuses: {e}")
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error in flight status update process: {e}")
    
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
                    completed_at=datetime.now(timezone.utc)
                )
                
                db.add(summary)
                db.commit()
                
            except Exception as e:
                db.rollback()
                self.logger.error(f"Error storing flight summary: {e}")
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"Error in flight summary storage: {e}")
    
    def get_network_status(self) -> Dict[str, Any]:
        """
        Get current network status from database.
        
        Returns:
            Dict[str, Any]: Network status information
        """
        db = SessionLocal()
        try:
            # Count active ATC positions
            active_atc_positions = db.query(Controller).filter(
                Controller.status == "online"
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
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error("Failed to get network status", extra={
                "error": str(e)
            })
            return {
                "active_atc_positions": 0,
                "active_flights": 0,
                "total_sectors": 0,
                "error": str(e),
                "last_updated": datetime.now(timezone.utc).isoformat()
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
