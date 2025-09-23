#!/usr/bin/env python3
"""
ATC Detection Service

Provides ATC interaction detection for flights by analyzing transceiver data
and calculating controller contact percentages. Implements the planned 4-step
CTE logic for accurate ATC interaction tracking.
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy import text
from app.database import get_database_session
from app.utils.geographic_utils import is_within_proximity
from app.services.controller_type_detector import ControllerTypeDetector
from app.services.detection_common import compute_detection_window

# Configure logging
logger = logging.getLogger(__name__)

class ATCDetectionService:
    """Service for detecting ATC interactions with flights."""
    
    def __init__(self, time_window_seconds: int = None):
        """
        Initialize ATC detection service.
        
        Args:
            time_window_seconds: Time window for frequency matching (default: from environment or 180s)
        """
        import os
        from app.services.detection_common import compute_detection_window
        
        # Load from environment variables with defaults and prefer centralized config
        self.time_window_seconds = time_window_seconds or int(os.getenv("FLIGHT_DETECTION_TIME_WINDOW_SECONDS", "180"))
        
        # Load VATSIM polling interval for accurate time calculations
        self.vatsim_polling_interval_seconds = int(os.getenv("VATSIM_POLLING_INTERVAL", "60"))
        
        # Initialize controller type detector for dynamic proximity ranges
        self.controller_type_detector = ControllerTypeDetector()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"ATC Detection Service initialized: time_window={self.time_window_seconds}s, VATSIM_polling={self.vatsim_polling_interval_seconds}s, dynamic proximity ranges enabled")
        
    async def detect_flight_atc_interactions(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime) -> Dict[str, Any]:
        """
        Detect ATC interactions for a specific flight.
        
        Args:
            flight_callsign: Aircraft callsign
            departure: Departure airport code
            arrival: Arrival airport code
            logon_time: Flight logon time
            
        Returns:
            Dict containing ATC interaction data
        """
        try:
            import asyncio
            
            # Wrap the entire ATC detection process with a timeout
            return await asyncio.wait_for(
                self._detect_flight_atc_interactions_internal(flight_callsign, departure, arrival, logon_time),
                timeout=45.0  # 45 second timeout for entire ATC detection process
            )
            
        except asyncio.TimeoutError:
            self.logger.error(f"ATC detection process timed out after 45 seconds for flight {flight_callsign}")
            return self._create_empty_atc_data()
        except Exception as e:
            self.logger.error(f"Error detecting ATC interactions for flight {flight_callsign}: {e}")
            return self._create_empty_atc_data()
    
    async def _detect_flight_atc_interactions_internal(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime) -> Dict[str, Any]:
        """Internal method for ATC detection (called with timeout wrapper)."""
        try:
            self.logger.debug(f"Detecting ATC interactions for flight {flight_callsign}")
            
            # Get flight transceivers
            flight_transceivers = await self._get_flight_transceivers(flight_callsign, departure, arrival, logon_time)
            self.logger.debug(f"Flight {flight_callsign} transceivers loaded: {len(flight_transceivers)} records")
            if flight_transceivers:
                try:
                    self.logger.debug(f"Flight sample for {flight_callsign}: {flight_transceivers[0:3]}")
                except Exception:
                    self.logger.exception("Failed to log flight transceiver sample")
            else:
                self.logger.debug(f"No transceiver data found for flight {flight_callsign}")
                return self._create_empty_atc_data()
            
            # Get ATC transceivers. Prefer loading ATC transceivers over the full
            # flight time window we just loaded so we don't miss controllers that
            # only appear later in the flight. Fall back to canonical prefilter
            # window when flight transceivers are unavailable.
            # Unified DB-only loader for ATC transceivers within the window
            from app.services.transceiver_loader import load_transceivers_window
            if flight_transceivers:
                atc_start = flight_transceivers[0]["timestamp"]
                atc_end = flight_transceivers[-1]["timestamp"]
            else:
                from app.services.detection_common import compute_prefilter_windows
                win = compute_prefilter_windows(logon_time, self.time_window_seconds)
                atc_start = win["atc_start_time"]
                atc_end = win["atc_end_time"]

            atc_transceivers = await load_transceivers_window(atc_start, atc_end, entity_type='atc')
            self.logger.debug(f"DB loader returned {len(atc_transceivers)} ATC transceivers for {flight_callsign} in window {atc_start} - {atc_end}")
            if not atc_transceivers:
                self.logger.debug(f"No ATC transceiver data found for flight {flight_callsign} after DB fallback")
                return self._create_empty_atc_data()
            
            # Find frequency matches with proximity and time constraints using SQL JOIN
            frequency_matches = await self._find_frequency_matches(flight_transceivers, atc_transceivers, departure, arrival, logon_time)
            self.logger.debug(f"Frequency matching for {flight_callsign} returned {len(frequency_matches)} matches")
            try:
                self.logger.debug(f"Frequency matches sample: {frequency_matches[:5]}")
            except Exception:
                self.logger.exception("Failed to log frequency matches sample")
            
            # Determine completion_time (canonical flight end) and pass it into metrics
            completion_time = await self._get_flight_completion_time(flight_callsign, departure, arrival, logon_time)
            if not completion_time:
                self.logger.info(f"Completion time not found for {flight_callsign}; cannot calculate ATC metrics")
                return self._create_empty_atc_data()

            # Calculate ATC interaction metrics (pass completion_time for accurate enroute counts)
            atc_data = await self._calculate_atc_metrics(flight_callsign, departure, arrival, logon_time, frequency_matches, completion_time)
            
            self.logger.debug(f"ATC detection completed for {flight_callsign}: {len(atc_data.get('controller_callsigns', {}))} controllers")
            # persist a debug artifact to disk for in-depth analysis
            try:
                import json
                debug_path = f"/tmp/atc_debug_{flight_callsign}.json"
                with open(debug_path, 'w') as df:
                    json.dump({
                        'flight_callsign': flight_callsign,
                        'flight_transceivers_count': len(flight_transceivers),
                        'atc_transceivers_count': len(atc_transceivers),
                        'frequency_matches_count': len(frequency_matches),
                        'atc_data_summary': atc_data.get('controller_callsigns')
                    }, df, default=str, indent=2)
                self.logger.debug(f"Wrote ATC debug file: {debug_path}")
            except Exception:
                self.logger.exception("Failed to write ATC debug file")
            return atc_data
            
        except Exception as e:
            self.logger.error(f"Error in internal ATC detection for flight {flight_callsign}: {e}")
            return self._create_empty_atc_data()
    
    async def detect_flight_atc_interactions_with_timeout(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime, timeout_seconds: float = 30.0) -> Dict[str, Any]:
        """
        Detect ATC interactions for a specific flight with timeout protection.
        
        Args:
            flight_callsign: Aircraft callsign
            departure: Departure airport code
            arrival: Arrival airport code
            logon_time: Flight logon time
            timeout_seconds: Maximum time to wait for detection
            
        Returns:
            Dict containing ATC interaction data
        """
        try:
            import asyncio
            return await asyncio.wait_for(
                self.detect_flight_atc_interactions(flight_callsign, departure, arrival, logon_time),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            self.logger.error(f"ATC detection timed out after {timeout_seconds} seconds for flight {flight_callsign}")
            return self._create_empty_atc_data()
        except Exception as e:
            self.logger.error(f"Error in ATC detection with timeout for flight {flight_callsign}: {e}")
            return self._create_empty_atc_data()
    
    async def _get_flight_transceivers(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime) -> List[Dict[str, Any]]:
        """Get transceiver data for a specific flight across ALL sessions using unified loader."""
        try:
            flight_start = logon_time
            completion_time = await self._get_flight_completion_time(flight_callsign, departure, arrival, logon_time)
            if not completion_time:
                self.logger.info(f"Completion time not found for {flight_callsign}; skipping flight transceiver load")
                return []
            flight_end = completion_time
            from app.services.transceiver_loader import load_transceivers_for_callsign
            return await load_transceivers_for_callsign(flight_start, flight_end, 'flight', flight_callsign)
        except Exception as e:
            self.logger.error(f"Error getting flight transceivers: {e}")
            return []
    
    async def _get_atc_transceivers_for_flight(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime) -> List[Dict[str, Any]]:
        """Get ATC transceiver data for a specific flight's time period only."""
        try:
            # Use exact window from flight_summaries only (no fallback to current time)
            flight_start = logon_time
            completion_time = await self._get_flight_completion_time(flight_callsign, departure, arrival, logon_time)
            if not completion_time:
                self.logger.info(f"Completion time not found for {flight_callsign}; skipping ATC transceiver load")
                return []
            atc_end = completion_time
            self.logger.info(f"Loading ATC transceivers for flight {flight_callsign}: {flight_start} to {atc_end}")
            
            # Single query with flight-specific time window and geographic pre-filtering
            query = """
                SELECT t.callsign, t.frequency, t.timestamp, t.position_lat, t.position_lon
                FROM transceivers t
                WHERE t.entity_type = 'atc'
                AND t.callsign IN (  -- 🚀 Pre-filter controllers first
                    SELECT DISTINCT callsign FROM controllers 
                    WHERE facility != 0
                    AND last_updated >= :flight_logon_time  -- Only controllers active since flight came online
                )
                AND t.timestamp >= :atc_start
                AND t.timestamp <= :atc_end
                ORDER BY t.callsign, t.timestamp
            """
            
            # Single database session, single query
            async with get_database_session() as session:
                result = await session.execute(text(query), {
                    "flight_logon_time": logon_time,
                    "atc_start": flight_start,
                    "atc_end": atc_end
                })
                
                # Process results
                atc_transceivers = []
                for row in result.fetchall():
                    atc_transceivers.append({
                        "callsign": row.callsign,
                        "frequency": row.frequency,
                        "frequency_mhz": row.frequency / 1000000.0,  # Convert Hz to MHz
                        "timestamp": row.timestamp,
                        "position_lat": row.position_lat,
                        "position_lon": row.position_lon
                    })
                
                self.logger.info(f"Loaded {len(atc_transceivers)} ATC transceivers for flight {flight_callsign}")
                return atc_transceivers
                
        except Exception as e:
            self.logger.error(f"Error getting ATC transceivers for flight {flight_callsign}: {e}")
            return []
    
    async def _get_flight_completion_time(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime) -> Optional[datetime]:
        """Get completion time for completed flights from flight_summaries table."""
        try:
            query = """
                SELECT completion_time 
                FROM flight_summaries 
                WHERE callsign = :callsign 
                AND departure = :departure 
                AND arrival = :arrival 
                AND logon_time = :logon_time
                AND completion_time IS NOT NULL
                ORDER BY created_at DESC 
                LIMIT 1
            """
            
            async with get_database_session() as session:
                result = await session.execute(text(query), {
                    "callsign": flight_callsign,
                    "departure": departure,
                    "arrival": arrival,
                    "logon_time": logon_time
                })
                
                row = result.fetchone()
                return row.completion_time if row else None
                
        except Exception as e:
            self.logger.warning(f"Could not get completion time for flight {flight_callsign}: {e}")
            return None
    
    async def _find_frequency_matches(self, flight_transceivers: List[Dict], atc_transceivers: List[Dict], departure: str, arrival: str, logon_time: datetime) -> List[Dict[str, Any]]:
        """Find frequency matches using controller-specific proximity ranges."""
        try:
            # 1. Group ATC transceivers by controller callsign
            atc_by_callsign = self._group_atc_by_callsign(atc_transceivers)
            
            # 2. Process each controller with its specific proximity range
            all_matches = []
            for controller_callsign, controllers in atc_by_callsign.items():
                # Get controller type and proximity range
                controller_info = self.controller_type_detector.get_controller_info(controller_callsign)
                proximity_range = controller_info["proximity_threshold"]
                
                self.logger.debug(f"Processing controller {controller_callsign} as {controller_info['type']} with {proximity_range}nm proximity")
                
                # 3. Run proximity query for this specific controller
                controller_matches = await self._find_matches_for_controller(
                    flight_transceivers, controllers, proximity_range, departure, arrival, logon_time
                )
                all_matches.extend(controller_matches)
            
            self.logger.info(f"Controller-specific proximity processing completed: {len(all_matches)} total matches found")
            return all_matches
            
        except Exception as e:
            self.logger.error(f"Error in controller-specific frequency matching: {e}")
            return []
    
    def _group_atc_by_callsign(self, atc_transceivers: List[Dict]) -> Dict[str, List[Dict]]:
        """Group ATC transceivers by controller callsign."""
        grouped = {}
        for transceiver in atc_transceivers:
            callsign = transceiver["callsign"]
            if callsign not in grouped:
                grouped[callsign] = []
            grouped[callsign].append(transceiver)
        return grouped
    
    async def _find_matches_for_controller(self, flight_transceivers: List[Dict], controller_transceivers: List[Dict], proximity_threshold_nm: float, departure: str, arrival: str, logon_time: datetime) -> List[Dict[str, Any]]:
        """Find frequency matches for a specific controller with its proximity range."""
        try:
            # OPTIMIZED: Pre-filter by time window before expensive JOINs
            query = """
                WITH time_filtered_flights AS (
                    SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
                    FROM transceivers t 
                    WHERE t.entity_type = 'flight' 
                    AND t.callsign = :flight_callsign
                    AND t.timestamp >= :flight_start_time  -- Pre-filter by time
                    AND t.timestamp <= :flight_end_time
                ),
                time_filtered_atc AS (
                    SELECT t.callsign, t.frequency/1000000.0 as frequency_mhz, t.timestamp, t.position_lat, t.position_lon 
                    FROM transceivers t 
                    WHERE t.entity_type = 'atc' 
                    AND t.callsign = :controller_callsign
                    AND t.timestamp >= :atc_start_time  -- Pre-filter by time
                    AND t.timestamp <= :atc_end_time
                ),
                frequency_matches AS (
                    SELECT ft.callsign as flight_callsign, ft.frequency_mhz, ft.timestamp as flight_time,
                           at.callsign as atc_callsign, at.timestamp as atc_time,
                           at.position_lat as atc_lat, at.position_lon as atc_lon,
                           ft.position_lat as flight_lat, ft.position_lon as flight_lon
                    FROM time_filtered_flights ft 
                    JOIN time_filtered_atc at
                      ON ABS(ft.frequency_mhz - at.frequency_mhz) <= 0.005  -- ~5 kHz tolerance
                    WHERE ABS(EXTRACT(EPOCH FROM (ft.timestamp - at.timestamp))) <= :time_window
                    AND (
                        -- Haversine formula with controller-specific proximity
                        (3440.065 * ACOS(
                            LEAST(1, GREATEST(-1, 
                                SIN(RADIANS(ft.position_lat)) * SIN(RADIANS(at.position_lat)) +
                                COS(RADIANS(ft.position_lat)) * COS(RADIANS(at.position_lat)) * 
                                COS(RADIANS(ft.position_lon - at.position_lon))
                            ))
                        )) <= :proximity_threshold_nm
                    )
                )
                SELECT 
                    flight_callsign,
                    atc_callsign,
                    frequency_mhz,
                    flight_time,
                    atc_time,
                    flight_lat,
                    flight_lon,
                    atc_lat,
                    atc_lon,
                    ABS(EXTRACT(EPOCH FROM (flight_time - atc_time))) as time_diff_seconds
                FROM frequency_matches
                ORDER BY flight_time, atc_time
            """
            
            # Execute with controller-specific proximity and time window pre-filtering
            async with get_database_session() as session:
                # Calculate time windows for pre-filtering.
                # Use the actual loaded transceivers bounds when available so we don't
                # accidentally limit matching to a narrow window around the flight
                # logon time (which previously caused matches later in the flight to be
                # missed). Fall back to the canonical prefilter window if transceiver
                # lists are empty.
                if flight_transceivers:
                    flight_start_time = flight_transceivers[0]["timestamp"]
                    flight_end_time = flight_transceivers[-1]["timestamp"]
                else:
                    from app.services.detection_common import build_prefilter_and_loader, compute_prefilter_windows
                    win = compute_prefilter_windows(logon_time, self.time_window_seconds)
                    pre = build_prefilter_and_loader(win["flight_start_time"], win["flight_end_time"], win["atc_start_time"], win["atc_end_time"], last_cache_fetch=None, ttl_seconds=120, default_page_size=10000)
                    flight_start_time = pre["flight_start_time"]
                    flight_end_time = pre["flight_end_time"]

                if controller_transceivers:
                    atc_start_time = controller_transceivers[0]["timestamp"]
                    atc_end_time = controller_transceivers[-1]["timestamp"]
                else:
                    # If we don't have controller transceivers (unlikely), use same prefilter
                    from app.services.detection_common import build_prefilter_and_loader, compute_prefilter_windows
                    win = compute_prefilter_windows(logon_time, self.time_window_seconds)
                    pre = build_prefilter_and_loader(win["flight_start_time"], win["flight_end_time"], win["atc_start_time"], win["atc_end_time"], last_cache_fetch=None, ttl_seconds=120, default_page_size=10000)
                    atc_start_time = pre["atc_start_time"]
                    atc_end_time = pre["atc_end_time"]
                
                result = await session.execute(text(query), {
                    "flight_callsign": flight_transceivers[0]["callsign"] if flight_transceivers else "",
                    "controller_callsign": controller_transceivers[0]["callsign"] if controller_transceivers else "",
                    "time_window": self.time_window_seconds,
                    "proximity_threshold_nm": proximity_threshold_nm,
                    "flight_start_time": flight_start_time,
                    "flight_end_time": flight_end_time,
                    "atc_start_time": atc_start_time,
                    "atc_end_time": atc_end_time
                })
                
                matches = []
                for row in result.fetchall():
                    matches.append({
                        "flight_callsign": row.flight_callsign,
                        "atc_callsign": row.atc_callsign,
                        "frequency_mhz": row.frequency_mhz,
                        "flight_time": row.flight_time,
                        "atc_time": row.atc_time,
                        "time_diff_seconds": row.time_diff_seconds,
                        "flight_lat": row.flight_lat,
                        "flight_lon": row.flight_lon,
                        "atc_lat": row.atc_lat,
                        "atc_lon": row.atc_lon
                    })
                
                self.logger.debug(f"Controller {controller_transceivers[0]['callsign'] if controller_transceivers else 'unknown'} query completed: {len(matches)} matches found with {proximity_threshold_nm}nm proximity")
                return matches
                
        except Exception as e:
            self.logger.error(f"Error in controller-specific query: {e}")
            return []
    
    async def _calculate_atc_metrics(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime, frequency_matches: List[Dict], completion_time: datetime) -> Dict[str, Any]:
        """Calculate ATC interaction metrics for a flight."""
        try:
            if not frequency_matches:
                return self._create_empty_atc_data()
            
            # Get total flight records for percentage calculation
            total_records = await self._get_flight_record_count(flight_callsign, departure, arrival, logon_time)
            if total_records == 0:
                return self._create_empty_atc_data()
            
            # Group matches by ATC callsign and calculate timing
            controller_data = {}
            for match in frequency_matches:
                atc_callsign = match["atc_callsign"]
                
                if atc_callsign not in controller_data:
                    controller_data[atc_callsign] = {
                        "callsign": atc_callsign,
                        "type": self._detect_controller_type(atc_callsign),
                        "time_minutes": 0,
                        "first_contact": match["flight_time"].isoformat() if hasattr(match["flight_time"], 'isoformat') else str(match["flight_time"]),
                        "last_contact": match["flight_time"].isoformat() if hasattr(match["flight_time"], 'isoformat') else str(match["flight_time"]),
                        "contact_count": 0
                    }
                
                # Update timing data
                controller_data[atc_callsign]["last_contact"] = match["flight_time"].isoformat() if hasattr(match["flight_time"], 'isoformat') else str(match["flight_time"])
                controller_data[atc_callsign]["contact_count"] += 1
            
            # Calculate time spent with each controller using actual VATSIM polling interval
            for controller in controller_data.values():
                # Convert polling interval from seconds to minutes for accurate time calculation
                controller["time_minutes"] = controller["contact_count"] * (self.vatsim_polling_interval_seconds / 60.0)
            
            # Calculate total controller time percentage
            total_controller_time = sum(ctrl["time_minutes"] for ctrl in controller_data.values())
            
            # Calculate percentage based on actual time, not record count
            # This represents the percentage of flight time that had ATC contact
            controller_time_percentage = min(100.0, (total_controller_time / total_records) * 100) if total_records > 0 else 0.0
            
            # Calculate airborne controller time percentage using transceiver heights (>1500 ft)
            # Use transceiver height_msl (meters) converted to feet for the threshold
            AIRBORNE_ALT_FT = 1500
            AIRBORNE_ALT_M = AIRBORNE_ALT_FT / 3.28084

            # Build a map of match times -> whether that match was airborne (closest transceiver height > threshold)
            airborne_contact_count = 0
            # We'll also compute total enroute (airborne) records for denominator using transceivers
            # Query: count transceiver records for this flight where height_msl > AIRBORNE_ALT_M
            async with get_database_session() as session:
                enroute_count_res = await session.execute(text("""
                    SELECT COUNT(*) FROM transceivers t
                    WHERE t.entity_type = 'flight'
                      AND t.callsign = :callsign
                      AND t.timestamp >= :flight_start
                      AND t.timestamp <= :flight_end
                      AND t.height_msl IS NOT NULL
                      AND t.height_msl > :alt_m
                """), {
                    "callsign": flight_callsign,
                    "flight_start": logon_time,
                    "flight_end": completion_time,
                    "alt_m": AIRBORNE_ALT_M
                })
                enroute_count_row = enroute_count_res.fetchone()
                enroute_records = enroute_count_row[0] if enroute_count_row else 0

            # Classify each frequency match as airborne if we can find a nearby transceiver record with height_msl > AIRBORNE_ALT_M
            async with get_database_session() as session:
                for match in frequency_matches:
                    match_time = match.get("flight_time")
                    # Find the closest transceiver height record for this flight at match_time
                    q = text("""
                        SELECT height_msl FROM transceivers
                        WHERE entity_type = 'flight' AND callsign = :callsign AND height_msl IS NOT NULL
                          AND timestamp <= :t
                        ORDER BY timestamp DESC
                        LIMIT 1
                    """)
                    res = await session.execute(q, {"callsign": flight_callsign, "t": match_time})
                    r = res.fetchone()
                    if r and r[0] is not None and r[0] > AIRBORNE_ALT_M:
                        airborne_contact_count += 1

            poll_min = (self.vatsim_polling_interval_seconds / 60.0)
            total_airborne_controller_time_minutes = airborne_contact_count * poll_min
            total_enroute_time_minutes = enroute_records * poll_min

            if total_enroute_time_minutes <= 0:
                airborne_controller_time_percentage = 0.0
            else:
                airborne_controller_time_percentage = min(100.0, (total_airborne_controller_time_minutes / total_enroute_time_minutes) * 100.0)
            
            return {
                "controller_callsigns": controller_data,
                "controller_time_percentage": round(controller_time_percentage, 1),
                "airborne_controller_time_percentage": round(airborne_controller_time_percentage, 1),
                "total_controller_time_minutes": total_controller_time,
                "total_flight_records": total_records,
                "interactions_detected": len(frequency_matches)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating ATC metrics: {e}")
            return self._create_empty_atc_data()
    
    async def _get_flight_record_count(self, flight_callsign: str, departure: str, arrival: str, logon_time: datetime) -> int:
        """Get total flight transceiver record count within the exact flight window."""
        try:
            # Determine the exact end time from flight_summaries; if absent, no records (ongoing not supported here)
            completion_time = await self._get_flight_completion_time(flight_callsign, departure, arrival, logon_time)
            if not completion_time:
                return 0

            query = """
                SELECT COUNT(*) as record_count
                FROM transceivers 
                WHERE entity_type = 'flight'
                AND callsign = :callsign 
                AND timestamp >= :flight_start
                AND timestamp <= :flight_end
            """

            async with get_database_session() as session:
                result = await session.execute(text(query), {
                    "callsign": flight_callsign,
                    "flight_start": logon_time,
                    "flight_end": completion_time
                })

                row = result.fetchone()
                return row.record_count if row else 0
                
        except Exception as e:
            self.logger.error(f"Error getting flight record count: {e}")
            return 0
    
    def _detect_controller_type(self, callsign: str) -> str:
        """Detect controller type from callsign."""
        callsign_upper = callsign.upper()
        
        if "CTR" in callsign_upper:
            return "CTR"
        elif "APP" in callsign_upper:
            return "TMA"
        elif "DEP" in callsign_upper:
            return "TMA"
        elif "TWR" in callsign_upper:
            return "TWR"
        elif "GND" in callsign_upper:
            return "GND"
        elif "DEL" in callsign_upper:
            return "DEL"
        elif "FSS" in callsign_upper:
            return "FSS"
        else:
            return "OTHER"
    
    def _create_empty_atc_data(self) -> Dict[str, Any]:
        """Create empty ATC data structure."""
        return {
            "controller_callsigns": {},
            "controller_time_percentage": 0.0,
            "airborne_controller_time_percentage": 0.0,
            "total_controller_time_minutes": 0,
            "total_flight_records": 0,
            "interactions_detected": 0
        }
