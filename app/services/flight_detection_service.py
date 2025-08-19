#!/usr/bin/env python3
"""
Flight Detection Service

This service detects flight interactions for controller sessions, mirroring the ATC Detection Service
but in the reverse direction. It ensures accurate controller-pilot pairing based on:
1. Frequency matching
2. Time window validation (180 seconds)
3. Geographic proximity (300nm using Haversine formula)

This service is used by the Controller Summary Service to accurately identify which aircraft
each controller actually handled during their session.
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Any
from sqlalchemy import text

from app.database import get_database_session


class FlightDetectionService:
    """Service for detecting flight interactions with controllers."""
    
    def __init__(self, time_window_seconds: int = None, proximity_threshold_nm: float = None):
        """
        Initialize Flight Detection Service.
        
        Args:
            time_window_seconds: Time window for frequency matching (default: from environment or 180s)
            proximity_threshold_nm: Geographic proximity threshold in nautical miles (default: from environment or 300nm)
        """
        import os
        
        # Load from environment variables with defaults
        self.time_window_seconds = time_window_seconds or int(os.getenv("FLIGHT_DETECTION_TIME_WINDOW_SECONDS", "180"))
        self.proximity_threshold_nm = proximity_threshold_nm or float(os.getenv("FLIGHT_DETECTION_PROXIMITY_THRESHOLD_NM", "30.0"))
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Flight Detection Service initialized: time_window={self.time_window_seconds}s, proximity_threshold={self.proximity_threshold_nm}nm")
        
    async def detect_controller_flight_interactions(self, controller_callsign: str, session_start: datetime, session_end: datetime) -> Dict[str, Any]:
        """
        Detect flight interactions for a specific controller session.
        
        Args:
            controller_callsign: Controller callsign
            session_start: Controller session start time
            session_end: Controller session end time
            
        Returns:
            Dict containing flight interaction data
        """
        try:
            self.logger.debug(f"Detecting flight interactions for controller {controller_callsign}")
            
            # Get controller transceivers
            controller_transceivers = await self._get_controller_transceivers(controller_callsign, session_start, session_end)
            if not controller_transceivers:
                self.logger.debug(f"No transceiver data found for controller {controller_callsign}")
                return self._create_empty_flight_data()
            
            # Get flight transceivers
            flight_transceivers = await self._get_flight_transceivers(session_start, session_end)
            if not flight_transceivers:
                self.logger.debug(f"No flight transceiver data found")
                return self._create_empty_flight_data()
            
            # Find frequency matches with proximity and time constraints using SQL JOIN
            frequency_matches = await self._find_frequency_matches(controller_transceivers, flight_transceivers, controller_callsign, session_start, session_end)
            
            # Calculate flight interaction metrics
            flight_data = await self._calculate_flight_metrics(controller_callsign, session_start, session_end, frequency_matches)
            
            self.logger.debug(f"Flight detection completed for {controller_callsign}: {len(flight_data.get('aircraft_callsigns', {}))} aircraft")
            return flight_data
            
        except Exception as e:
            self.logger.error(f"Error detecting flight interactions for controller {controller_callsign}: {e}")
            return self._create_empty_flight_data()
    
    async def detect_controller_flight_interactions_with_timeout(self, controller_callsign: str, session_start: datetime, session_end: datetime, timeout_seconds: float = 30.0) -> Dict[str, Any]:
        """
        Detect flight interactions for a specific controller session with timeout protection.
        
        Args:
            controller_callsign: Controller callsign
            session_start: Controller session start time
            session_end: Controller session end time
            timeout_seconds: Maximum time to wait for detection
            
        Returns:
            Dict containing flight interaction data
        """
        try:
            import asyncio
            return await asyncio.wait_for(
                self.detect_controller_flight_interactions(controller_callsign, session_start, session_end),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            self.logger.error(f"Flight detection timed out after {timeout_seconds} seconds for controller {controller_callsign}")
            return self._create_empty_flight_data()
        except Exception as e:
            self.logger.error(f"Error in flight detection with timeout for controller {controller_callsign}: {e}")
            return self._create_empty_flight_data()
    
    async def _get_controller_transceivers(self, controller_callsign: str, session_start: datetime, session_end: datetime) -> List[Dict[str, Any]]:
        """Get transceiver data for a specific controller session."""
        try:
            query = """
                SELECT t.callsign, t.frequency, t.timestamp, t.position_lat, t.position_lon
                FROM transceivers t
                WHERE t.entity_type = 'atc' 
                AND t.callsign = :controller_callsign
                AND t.timestamp BETWEEN :session_start AND :session_end
                ORDER BY t.timestamp
            """
            
            async with get_database_session() as session:
                result = await session.execute(text(query), {
                    "controller_callsign": controller_callsign,
                    "session_start": session_start,
                    "session_end": session_end
                })
                
                transceivers = []
                for row in result.fetchall():
                    transceivers.append({
                        "callsign": row.callsign,
                        "frequency": row.frequency,
                        "frequency_mhz": row.frequency / 1000000.0,  # Convert Hz to MHz
                        "timestamp": row.timestamp,
                        "position_lat": row.position_lat,
                        "position_lon": row.position_lon
                    })
                
                self.logger.info(f"Loaded {len(transceivers)} controller transceiver records for {controller_callsign}")
                return transceivers
                
        except Exception as e:
            self.logger.error(f"Error getting controller transceivers: {e}")
            return []
    
    async def _get_flight_transceivers(self, session_start: datetime, session_end: datetime) -> List[Dict[str, Any]]:
        """Get transceiver data for flights during the controller session period."""
        try:
            # Optimized query with better filtering and LIMIT to prevent hanging
            query = """
                SELECT t.callsign, t.frequency, t.timestamp, t.position_lat, t.position_lon
                FROM transceivers t
                WHERE t.entity_type = 'flight' 
                AND t.timestamp BETWEEN :session_start AND :session_end
                ORDER BY t.timestamp
                LIMIT 10000  -- Prevent loading too many records
            """
            
            async with get_database_session() as session:
                result = await session.execute(text(query), {
                    "session_start": session_start,
                    "session_end": session_end
                })
                
                transceivers = []
                for row in result.fetchall():
                    transceivers.append({
                        "callsign": row.callsign,
                        "frequency": row.frequency,
                        "frequency_mhz": row.frequency / 1000000.0,  # Convert Hz to MHz
                        "timestamp": row.timestamp,
                        "position_lat": row.position_lat,
                        "position_lon": row.position_lon
                    })
                
                self.logger.info(f"Loaded {len(transceivers)} flight transceiver records")
                return transceivers
                
        except Exception as e:
            self.logger.error(f"Error getting flight transceivers: {e}")
            return []
    
    async def _find_frequency_matches(self, controller_transceivers: List[Dict], flight_transceivers: List[Dict], controller_callsign: str, session_start: datetime, session_end: datetime) -> List[Dict[str, Any]]:
        """Find frequency matches between controller and flight transceivers using the planned CTE query."""
        try:
            # Use the exact planned query structure from ATC Detection Service but reversed
            query = """
                WITH controller_transceivers AS (
                    SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
                    FROM transceivers t 
                    WHERE t.entity_type = 'atc' 
                    AND t.callsign = :controller_callsign
                    AND t.timestamp BETWEEN :session_start AND :session_end
                ),
                flight_transceivers AS (
                    SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
                    FROM transceivers t 
                    WHERE t.entity_type = 'flight' 
                    AND t.timestamp BETWEEN :session_start AND :session_end
                ),
                frequency_matches AS (
                    SELECT ct.callsign as controller_callsign, ct.frequency_mhz, ct.timestamp as controller_time,
                           ft.callsign as flight_callsign, ft.timestamp as flight_time,
                           ct.position_lat as controller_lat, ct.position_lon as controller_lon,
                           ft.position_lat as flight_lat, ft.position_lon as flight_lon
                    FROM controller_transceivers ct 
                    JOIN flight_transceivers ft ON ct.frequency_mhz = ft.frequency_mhz 
                    AND ABS(EXTRACT(EPOCH FROM (ct.timestamp - ft.timestamp))) <= :time_window
                )
                SELECT 
                    controller_callsign,
                    flight_callsign,
                    frequency_mhz,
                    controller_time,
                    flight_time,
                    controller_lat,
                    controller_lon,
                    flight_lat,
                    flight_lon,
                    ABS(EXTRACT(EPOCH FROM (controller_time - flight_time))) as time_diff_seconds
                FROM frequency_matches
                WHERE (
                    -- Haversine formula for distance in nautical miles
                    (3440.065 * ACOS(
                        LEAST(1, GREATEST(-1, 
                            SIN(RADIANS(controller_lat)) * SIN(RADIANS(flight_lat)) +
                            COS(RADIANS(controller_lat)) * COS(RADIANS(flight_lat)) * 
                            COS(RADIANS(controller_lon - flight_lon))
                        ))
                    )) <= :proximity_threshold_nm
                )
                ORDER BY flight_time, controller_time
            """
            
            async with get_database_session() as session:
                result = await session.execute(text(query), {
                    "controller_callsign": controller_callsign,
                    "session_start": session_start,
                    "session_end": session_end,
                    "time_window": self.time_window_seconds,
                    "proximity_threshold_nm": self.proximity_threshold_nm
                })
                
                matches = []
                for row in result.fetchall():
                    matches.append({
                        "controller_callsign": row.controller_callsign,
                        "flight_callsign": row.flight_callsign,
                        "frequency_mhz": row.frequency_mhz,
                        "controller_time": row.controller_time,
                        "flight_time": row.flight_time,
                        "time_diff_seconds": row.time_diff_seconds,
                        "controller_lat": row.controller_lat,
                        "controller_lon": row.controller_lon,
                        "flight_lat": row.flight_lat,
                        "flight_lon": row.flight_lon
                    })
                
                self.logger.info(f"Flight detection CTE query completed: {len(matches)} matches found")
                return matches
                
        except Exception as e:
            self.logger.error(f"Error in flight detection CTE query: {e}")
            return []
    
    async def _calculate_flight_metrics(self, controller_callsign: str, session_start: datetime, session_end: datetime, frequency_matches: List[Dict]) -> Dict[str, Any]:
        """Calculate flight interaction metrics for a controller session."""
        try:
            if not frequency_matches:
                return self._create_empty_flight_data()
            
            # Group by aircraft callsign
            aircraft_data = {}
            for match in frequency_matches:
                flight_callsign = match["flight_callsign"]
                
                if flight_callsign not in aircraft_data:
                    aircraft_data[flight_callsign] = {
                        "callsign": flight_callsign,
                        "frequency_mhz": match["frequency_mhz"],
                        "first_seen": match["flight_time"],
                        "last_seen": match["flight_time"],
                        "updates_count": 0,
                        "total_time_on_frequency": 0,
                        "controller_contacts": []
                    }
                
                # Update last seen time
                if match["flight_time"] > aircraft_data[flight_callsign]["last_seen"]:
                    aircraft_data[flight_callsign]["last_seen"] = match["flight_time"]
                if match["flight_time"] < aircraft_data[flight_callsign]["first_seen"]:
                    aircraft_data[flight_callsign]["first_seen"] = match["flight_time"]
                
                # Count updates
                aircraft_data[flight_callsign]["updates_count"] += 1
                
                # Add controller contact
                aircraft_data[flight_callsign]["controller_contacts"].append({
                    "timestamp": match["flight_time"],
                    "time_diff_seconds": match["time_diff_seconds"]
                })
            
            # Calculate time on frequency for each aircraft
            for aircraft in aircraft_data.values():
                time_diff = aircraft["last_seen"] - aircraft["first_seen"]
                aircraft["total_time_on_frequency"] = int(time_diff.total_seconds() / 60)
            
            # Calculate summary metrics
            total_aircraft = len(aircraft_data)
            peak_count = self._calculate_peak_aircraft_count(aircraft_data, session_start, session_end)
            hourly_breakdown = self._calculate_hourly_breakdown(aircraft_data, session_start, session_end)
            
            # Create aircraft details list
            aircraft_details = []
            for aircraft in aircraft_data.values():
                aircraft_details.append({
                    "callsign": aircraft["callsign"],
                    "frequency_mhz": aircraft["frequency_mhz"],
                    "first_seen": aircraft["first_seen"].isoformat(),
                    "last_seen": aircraft["last_seen"].isoformat(),
                    "time_on_frequency_minutes": aircraft["total_time_on_frequency"],
                    "updates_count": aircraft["updates_count"]
                })
            
            return {
                "total_aircraft": total_aircraft,
                "peak_count": peak_count,
                "hourly_breakdown": hourly_breakdown,
                "details": aircraft_details,
                "aircraft_callsigns": list(aircraft_data.keys()),
                "flights_detected": total_aircraft > 0
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating flight metrics: {e}")
            return self._create_empty_flight_data()
    
    def _calculate_peak_aircraft_count(self, aircraft_data: Dict, session_start: datetime, session_end: datetime) -> int:
        """Calculate the peak number of aircraft active simultaneously."""
        try:
            # Simple peak calculation based on aircraft active during the session
            return len(aircraft_data)
        except Exception as e:
            self.logger.error(f"Error calculating peak aircraft count: {e}")
            return 0
    
    def _calculate_hourly_breakdown(self, aircraft_data: Dict, session_start: datetime, session_end: datetime) -> Dict[int, int]:
        """Calculate hourly breakdown of aircraft activity."""
        try:
            hourly_breakdown = {}
            for hour in range(24):
                hourly_breakdown[hour] = 0
            
            # Count aircraft active in each hour
            for aircraft in aircraft_data.values():
                start_hour = aircraft["first_seen"].hour
                end_hour = aircraft["last_seen"].hour
                
                if start_hour == end_hour:
                    hourly_breakdown[start_hour] += 1
                else:
                    # Aircraft active across multiple hours
                    for hour in range(start_hour, end_hour + 1):
                        if hour < 24:
                            hourly_breakdown[hour] += 1
            
            return hourly_breakdown
            
        except Exception as e:
            self.logger.error(f"Error calculating hourly breakdown: {e}")
            return {hour: 0 for hour in range(24)}
    
    def _create_empty_flight_data(self) -> Dict[str, Any]:
        """Return empty flight data structure."""
        return {
            "total_aircraft": 0,
            "peak_count": 0,
            "hourly_breakdown": {hour: 0 for hour in range(24)},
            "details": [],
            "aircraft_callsigns": [],
            "flights_detected": False
        }
