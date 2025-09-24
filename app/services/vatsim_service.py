#!/usr/bin/env python3
"""
VATSIM Service - Simplified

Fetches and processes VATSIM network data from API v3.
Handles flights, controllers, and transceivers data.
"""

import httpx
import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta

from app.database import get_database_session
from sqlalchemy import text
from app.services.detection_common import transceiver_load_strategy

from app.config import get_config
from app.utils.logging import get_logger_for_module
from app.utils.error_handling import handle_service_errors, log_operation

logger = logging.getLogger(__name__)


class VATSIMAPIError(Exception):
    """Exception raised when VATSIM API operations fail."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class VATSIMService:
    """Service for handling VATSIM API v3 interactions."""
    
    def __init__(self):
        """Initialize VATSIM service with configuration."""
        self.service_name = "vatsim_service"
        self.config = get_config()
        self.logger = get_logger_for_module(f"services.{self.service_name}")
        self._initialized = False
        
        self.client: Optional[httpx.AsyncClient] = None
        # Cached transceivers snapshot (parsed, unlinked). Protected by _transceivers_lock.
        self._transceivers_cache: List[Dict[str, Any]] = []
        self._transceivers_last_fetch: Optional[datetime] = None
        self._transceivers_lock: asyncio.Lock = asyncio.Lock()
        self._transceivers_task: Optional[asyncio.Task] = None
        # Track consecutive API failures to control log severity
        self._consecutive_api_failures: int = 0
        # Number of failures before escalating to ERROR level (hardcoded to 5)
        self._api_failure_threshold: int = 5
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._create_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_client()
    
    async def initialize(self) -> bool:
        """Initialize VATSIM service with HTTP client."""
        try:
            await self._create_client()
            self.logger.info("VATSIM service initialized successfully")
            self._initialized = True
            # Start background refresher for transceivers snapshot
            try:
                # create background task but don't await it here
                self._transceivers_task = asyncio.create_task(self._transceivers_refresher_loop())
            except Exception:
                self.logger.exception("Failed to start transceivers refresher task")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize VATSIM service: {e}")
            return False
    
    def is_initialized(self) -> bool:
        """Check if service is properly initialized."""
        return self._initialized
    

    
    async def cleanup(self):
        """Cleanup VATSIM service resources."""
        await self._close_client()
        self.logger.info("VATSIM service cleanup completed")
    
    async def _create_client(self) -> None:
        """Create HTTP client for API requests."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=self.config.vatsim.timeout,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
            self.logger.debug("Created HTTP client for VATSIM API")
    
    async def _close_client(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
            self.logger.debug("Closed HTTP client")
        # Cancel background transceivers refresher task
        if self._transceivers_task:
            try:
                self._transceivers_task.cancel()
                await self._transceivers_task
            except asyncio.CancelledError:
                pass
            except Exception:
                self.logger.exception("Error while cancelling transceivers refresher task")
            finally:
                self._transceivers_task = None
    
    @handle_service_errors
    @log_operation("fetch_vatsim_data")
    async def get_current_data(self) -> Dict[str, Any]:
        """
        Fetch current VATSIM network data.
        
        Returns:
            Dict[str, Any]: Parsed VATSIM network data as dictionary
            
        Raises:
            VATSIMAPIError: When API request fails
        """
        await self._create_client()
        
        try:
            self.logger.info("Fetching current VATSIM data", extra={
                "api_url": self.config.vatsim.api_url,
                "timeout": self.config.vatsim.timeout
            })
            
            response = await self.client.get(self.config.vatsim.api_url)
            
            if response.status_code != 200:
                raise VATSIMAPIError(
                    f"VATSIM API returned status {response.status_code}",
                    status_code=response.status_code
                )
            
            raw_data = response.json()
            
            # Ensure data is a dictionary and handle None
            if not isinstance(raw_data, dict) or raw_data is None:
                parsed_data: Dict[str, Any] = {}
            else:
                parsed_data: Dict[str, Any] = raw_data
            
            # Parse the data with proper null checks
            controllers = self._parse_controllers(parsed_data.get("controllers", []))
            sectors = parsed_data.get("sectors", [])
            
            # Parse all flights - no filtering applied here
            flights = self._parse_flights(parsed_data.get("pilots", []))
            
            # Fetch transceivers data - prefer cached snapshot populated by background refresher
            try:
                cached_snapshot: Optional[List[Dict[str, Any]]] = None
                async with self._transceivers_lock:
                    if self._transceivers_cache:
                        # shallow-copy each dict to avoid mutating the cached objects during linking
                        cached_snapshot = [dict(t) for t in self._transceivers_cache]

                if cached_snapshot is not None:
                    # CRITICAL FIX: Apply the same filtering used in data_service.py
                    # This prevents transceiver misclassification by ensuring entity linking uses
                    # the same filtered flight/controller data that gets stored in the database.
                    # Without this, flights could be misclassified as ATC controllers when their
                    # callsigns exist in the unfiltered VATSIM API controller data.
                    filtered_flights = self._filter_flights(flights)
                    filtered_controllers = self._filter_controllers(controllers)
                    transceivers = self._link_transceivers_to_entities(cached_snapshot, filtered_flights, filtered_controllers)
                else:
                    # Fallback to on-demand fetch if cache is empty
                    transceivers_raw = await self._fetch_transceivers_data()
                    parsed = self._parse_transceivers(transceivers_raw)
                    # CRITICAL FIX: Apply the same filtering used in data_service.py
                    # This prevents transceiver misclassification by ensuring entity linking uses
                    # the same filtered flight/controller data that gets stored in the database.
                    # Without this, flights could be misclassified as ATC controllers when their
                    # callsigns exist in the unfiltered VATSIM API controller data.
                    filtered_flights = self._filter_flights(flights)
                    filtered_controllers = self._filter_controllers(controllers)
                    transceivers = self._link_transceivers_to_entities(parsed, filtered_flights, filtered_controllers)
            except Exception as e:
                self.logger.warning(f"Failed to fetch transceivers: {e}")
                transceivers = []
            
            # Return dictionary directly instead of dataclass
            vatsim_data = {
                "controllers": controllers,
                "flights": flights,
                "sectors": sectors,
                "transceivers": transceivers,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_controllers": len(controllers),
                "total_flights": len(flights),
                "total_sectors": len(sectors),
                "total_transceivers": len(transceivers)
            }
            
            # Log only when there's significant data or changes
            total_entities = len(controllers) + len(flights) + len(transceivers)
            if total_entities > 0:
                self.logger.debug(f"VATSIM data fetched: {len(controllers)} controllers, {len(flights)} flights, {len(transceivers)} transceivers")
            else:
                self.logger.warning("No VATSIM data received from API")
            
            # Successful fetch - reset failure counter
            self._consecutive_api_failures = 0
            return vatsim_data
        except (httpx.TimeoutException, httpx.RequestError) as e:
            # Increment failure counter and log as warning until threshold reached
            self._consecutive_api_failures += 1
            if self._consecutive_api_failures <= self._api_failure_threshold:
                self.logger.warning(f"VATSIM API transient failure (attempt {self._consecutive_api_failures}): {e}")
            else:
                self.logger.error(f"VATSIM API repeated failures (count={self._consecutive_api_failures}): {e}")
            # Return an empty data structure so upstream processing can continue gracefully
            return {
                "controllers": [],
                "flights": [],
                "sectors": [],
                "transceivers": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_controllers": 0,
                "total_flights": 0,
                "total_sectors": 0,
                "total_transceivers": 0
            }
        except Exception as e:
            self._consecutive_api_failures += 1
            if self._consecutive_api_failures <= self._api_failure_threshold:
                self.logger.warning(f"Unexpected VATSIM API error (attempt {self._consecutive_api_failures}): {e}")
            else:
                self.logger.error(f"Unexpected VATSIM API repeated error (count={self._consecutive_api_failures}): {e}")
            return {
                "controllers": [],
                "flights": [],
                "sectors": [],
                "transceivers": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_controllers": 0,
                "total_flights": 0,
                "total_sectors": 0,
                "total_transceivers": 0
            }
    
    def _parse_controllers(self, controllers_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse controller data from VATSIM API response - EXACT field mapping.
        
        Args:
            controllers_data: Raw controller data from API
            
        Returns:
            List[Dict[str, Any]]: Parsed controller dictionaries
        """
        controllers = []
        
        for controller_data in controllers_data:
            try:
                # Parse timestamps - ensure UTC timezone and no subseconds
                last_updated = None
                if controller_data.get("last_updated"):
                    try:
                        # Parse ISO format and ensure UTC timezone
                        dt = datetime.fromisoformat(controller_data["last_updated"].replace("Z", "+00:00"))
                        # Remove subseconds by truncating to seconds
                        last_updated = dt.replace(microsecond=0)
                    except:
                        last_updated = None
                
                logon_time = None
                if controller_data.get("logon_time"):
                    try:
                        # Parse ISO format and ensure UTC timezone
                        dt = datetime.fromisoformat(controller_data["logon_time"].replace("Z", "+00:00"))
                        # Remove subseconds by truncating to seconds
                        logon_time = dt.replace(microsecond=0)
                    except:
                        logon_time = None
                
                controller = {
                    "callsign": controller_data.get("callsign", ""),
                    "frequency": controller_data.get("frequency", ""),
                    "cid": controller_data.get("cid"),
                    "name": controller_data.get("name", ""),
                    "rating": controller_data.get("rating"),
                    "facility": controller_data.get("facility"),
                    "visual_range": controller_data.get("visual_range"),
                    "text_atis": controller_data.get("text_atis"),
                    "server": controller_data.get("server", ""),
                    "last_updated": last_updated,
                    "logon_time": logon_time
                }
                controllers.append(controller)
                
            except Exception as e:
                self.logger.warning(
                    f"Failed to parse controller {controller_data.get('callsign', 'unknown')}: {e}",
                    extra={
                        "controller_data": controller_data,
                        "error": str(e)
                    }
                )
        
        return controllers
    
    def _parse_flights(self, flights_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse flight data from VATSIM API response.
        
        Args:
            flights_data: Raw flight data from API
            
        Returns:
            List[Dict[str, Any]]: Parsed flight dictionaries
        """
        flights = []
        
        for flight_data in flights_data:
            try:
                # Extract position data
                position = None
                if flight_data.get("latitude") and flight_data.get("longitude"):
                    position = {
                        "lat": float(flight_data["latitude"]),
                        "lng": float(flight_data["longitude"])
                    }
                
                # Extract flight plan data - handle null flight plans
                flight_plan = flight_data.get("flight_plan")
                if flight_plan is None:
                    flight_plan = {}
                
                # Parse timestamps - ensure UTC timezone and no subseconds
                logon_time = None
                if flight_data.get("logon_time"):
                    try:
                        # Parse ISO format and ensure UTC timezone
                        dt = datetime.fromisoformat(flight_data["logon_time"].replace("Z", "+00:00"))
                        # Remove subseconds by truncating to seconds
                        logon_time = dt.replace(microsecond=0)
                    except:
                        logon_time = None
                
                last_updated = None
                if flight_data.get("last_updated"):
                    try:
                        # Parse ISO format and ensure UTC timezone
                        dt = datetime.fromisoformat(flight_data["last_updated"].replace("Z", "+00:00"))
                        # Remove subseconds by truncating to seconds
                        last_updated = dt.replace(microsecond=0)
                    except:
                        last_updated = None
                
                flight = {
                    "callsign": flight_data.get("callsign", ""),
                    "pilot_name": flight_data.get("name", ""),
                    "aircraft_type": flight_plan.get("aircraft_short", ""),  # Fixed: API provides aircraft type in flight_plan.aircraft_short
                    "departure": flight_plan.get("departure", ""),
                    "arrival": flight_plan.get("arrival", ""),
                    "route": flight_plan.get("route", ""),
                    "altitude": int(flight_data.get("altitude", 0)),
                    "position": position,
                    
                    # Missing VATSIM API fields - 1:1 mapping with API field names
                    "cid": flight_data.get("cid"),
                    "name": flight_data.get("name"),
                    "server": flight_data.get("server"),
                    "pilot_rating": flight_data.get("pilot_rating"),
                    "military_rating": flight_data.get("military_rating"),
                    "latitude": flight_data.get("latitude"),
                    "longitude": flight_data.get("longitude"),
                    "groundspeed": flight_data.get("groundspeed"),
                    "transponder": flight_data.get("transponder"),
                    "heading": flight_data.get("heading"),

                    "logon_time": logon_time,
                    "last_updated": last_updated,
                    
                    # Flight plan fields (nested object)
                    "flight_rules": flight_plan.get("flight_rules"),
                    "aircraft_faa": flight_plan.get("aircraft_faa"),
                    "aircraft_short": flight_plan.get("aircraft_short"),
                    "alternate": flight_plan.get("alternate"),
                    "cruise_tas": flight_plan.get("cruise_tas"),
                    "planned_altitude": flight_plan.get("altitude"),
                    "deptime": flight_plan.get("deptime"),
                    "enroute_time": flight_plan.get("enroute_time"),
                    "fuel_time": flight_plan.get("fuel_time"),
                    "remarks": flight_plan.get("remarks"),

                }
                flights.append(flight)
                
            except Exception as e:
                self.logger.warning(
                    f"Failed to parse flight {flight_data.get('callsign', 'unknown')}: {e}",
                    extra={
                        "flight_data": flight_data,
                        "error": str(e)
                    }
                )
        
        return flights
    
    async def _fetch_transceivers_data(self) -> List[Dict[str, Any]]:
        """
        Fetch transceivers data from VATSIM transceivers API.
        
        Returns:
            List[Dict[str, Any]]: Raw transceivers data
            
        Raises:
            VATSIMAPIError: When API request fails
        """
        await self._create_client()
        
        try:
            self.logger.info("Fetching transceivers data", extra={
                "api_url": self.config.vatsim.transceivers_api_url,
                "timeout": self.config.vatsim.timeout
            })
            
            response = await self.client.get(self.config.vatsim.transceivers_api_url)
            
            if response.status_code != 200:
                raise VATSIMAPIError(
                    f"VATSIM transceivers API returned status {response.status_code}",
                    status_code=response.status_code
                )
            
            raw_data = response.json()
            
            # Ensure data is a list and handle None
            if not isinstance(raw_data, list) or raw_data is None:
                return []
            
            # Successful fetch - reset failure counter
            self._consecutive_api_failures = 0
            return raw_data
            
        except Exception as e:
            # Increment failure counter and log appropriately
            self._consecutive_api_failures += 1
            if self._consecutive_api_failures <= self._api_failure_threshold:
                self.logger.warning("Failed to fetch transceivers data", extra={
                    "error": str(e),
                    "api_url": self.config.vatsim.transceivers_api_url,
                    "attempt": self._consecutive_api_failures
                })
            else:
                self.logger.error("Repeated failure fetching transceivers data", extra={
                    "error": str(e),
                    "api_url": self.config.vatsim.transceivers_api_url,
                    "consecutive_failures": self._consecutive_api_failures
                })
            # Return empty list so callers can continue gracefully
            return []

    async def _transceivers_refresher_loop(self) -> None:
        """Background loop that periodically refreshes the transceivers snapshot."""
        interval = int(os.getenv("VATSIM_TRANSCEIVERS_POLLING_INTERVAL", "120"))
        while True:
            try:
                self.logger.debug("Transceivers refresher: fetching snapshot")
                raw = await self._fetch_transceivers_data()
                parsed = self._parse_transceivers(raw)
                async with self._transceivers_lock:
                    self._transceivers_cache = parsed
                    self._transceivers_last_fetch = datetime.now(timezone.utc)
                self.logger.info(f"Transceivers refresher: updated snapshot ({len(parsed)} records)")
            except Exception:
                self.logger.exception("Transceivers refresher failed")
            finally:
                await asyncio.sleep(interval)
    
    def _parse_transceivers(self, transceivers_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse transceivers data from VATSIM API response.
        
        Args:
            transceivers_data: Raw transceivers data from API
            
        Returns:
            List[Dict[str, Any]]: Parsed transceivers data as dictionaries
        """
        transceivers = []
        
        for entry in transceivers_data:
            try:
                callsign = entry.get("callsign", "")
                transceivers_list = entry.get("transceivers", [])
                
                for transceiver_data in transceivers_list:
                    # Parse timestamp - ensure UTC timezone and no subseconds
                    timestamp = None
                    if transceiver_data.get("timestamp"):
                        try:
                            # Parse ISO format and ensure UTC timezone
                            dt = datetime.fromisoformat(transceiver_data["timestamp"].replace("Z", "+00:00"))
                            # Remove subseconds by truncating to seconds
                            timestamp = dt.replace(microsecond=0)
                        except:
                            timestamp = None
                    
                    transceiver = {
                        "callsign": callsign,
                        "transceiver_id": transceiver_data.get("id", 0),
                        "frequency": transceiver_data.get("frequency", 0),
                        "position_lat": transceiver_data.get("latDeg"),
                        "position_lon": transceiver_data.get("lonDeg"),
                        "height_msl": transceiver_data.get("heightMslM"),
                        "height_agl": transceiver_data.get("heightAglM"),
                        "entity_type": "flight",  # Default to flight, will be updated later
                        "timestamp": timestamp
                    }
                    transceivers.append(transceiver)
                
            except Exception as e:
                self.logger.warning(
                    f"Failed to parse transceiver for {entry.get('callsign', 'unknown')}: {e}",
                    extra={
                        "entry": entry,
                        "error": str(e)
                    }
                )
        
        return transceivers
    
    def _link_transceivers_to_entities(self, transceivers: List[Dict[str, Any]], 
                                      flights: List[Dict[str, Any]], 
                                      controllers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Link transceivers to flights and ATC positions based on callsign.
        
        IMPORTANT: This method now receives FILTERED flight and controller data to prevent
        misclassification. Previously, it received raw VATSIM API data which could cause
        flights to be misclassified as ATC controllers when their callsigns existed in
        both the flight and controller lists from VATSIM.
        
        Classification Logic:
        1. If callsign exists in flight_lookup → entity_type = "flight"
        2. If callsign exists in controller_lookup → entity_type = "atc"  
        3. If callsign exists in neither → entity_type = "flight" (default)
        
        Args:
            transceivers: List of transceivers to link
            flights: List of FILTERED flights (geographically filtered for Australian flights)
            controllers: List of FILTERED controllers (callsign filtered for Australian controllers)
            
        Returns:
            List[Dict[str, Any]]: Transceivers with entity links
        """
        # Create lookup dictionaries from FILTERED data
        # This ensures classification matches what gets stored in the database
        flight_lookup = {flight["callsign"]: flight for flight in flights}
        controller_lookup = {controller["callsign"]: controller for controller in controllers}
        
        for transceiver in transceivers:
            # Priority 1: Check if callsign matches a flight (checked first)
            if transceiver["callsign"] in flight_lookup:
                transceiver["entity_type"] = "flight"
                # Note: entity_id would be set when storing to database
            # Priority 2: Check if callsign matches a controller
            elif transceiver["callsign"] in controller_lookup:
                transceiver["entity_type"] = "atc"
                # Note: entity_id would be set when storing to database
            # Priority 3: Default fallback (ensures non-Australian flights default to "flight")
            else:
                transceiver["entity_type"] = "flight"
        
        return transceivers

    def _filter_flights(self, flights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply the same geographic filtering used in data_service.py.
        
        This method ensures that only Australian flights are used for transceiver classification,
        preventing non-Australian flights from being misclassified as ATC controllers.
        
        The filtering removes flights that are outside the Australian geographic boundaries,
        keeping only flights that would be stored in the database.
        
        Args:
            flights: Raw flight data from VATSIM API
            
        Returns:
            List[Dict[str, Any]]: Geographically filtered flights (Australian flights only)
        """
        try:
            from app.filters.geographic_boundary_filter import GeographicBoundaryFilter
            filter_instance = GeographicBoundaryFilter()
            if filter_instance.config.enabled:
                filtered_flights = filter_instance.filter_flights_list(flights)
                self.logger.debug(f"Geographic flight filtering: {len(flights)} → {len(filtered_flights)} flights")
                return filtered_flights
        except Exception as e:
            self.logger.warning(f"Failed to apply geographic filtering to flights: {e}")
        return flights

    def _filter_controllers(self, controllers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply the same callsign filtering used in data_service.py.
        
        This method ensures that only Australian controllers are used for transceiver classification,
        preventing non-Australian controllers from being used in entity linking.
        
        The filtering removes controllers that are not in the Australian controller callsign list
        (config/controller_callsigns_list.txt), keeping only controllers that would be stored
        in the database.
        
        Args:
            controllers: Raw controller data from VATSIM API
            
        Returns:
            List[Dict[str, Any]]: Callsign filtered controllers (Australian controllers only)
        """
        try:
            from app.filters.controller_callsign_filter import ControllerCallsignFilter
            filter_instance = ControllerCallsignFilter()
            if filter_instance.config.enabled:
                filtered_controllers = filter_instance.filter_controllers_list(controllers)
                self.logger.debug(f"Controller callsign filtering: {len(controllers)} → {len(filtered_controllers)} controllers")
                return filtered_controllers
        except Exception as e:
            self.logger.warning(f"Failed to apply callsign filtering to controllers: {e}")
        return controllers

    async def load_transceivers_window(self, start: datetime, end: datetime, entity_type: Optional[str] = None, page_size: int = 10000) -> List[Dict[str, Any]]:
        """Load transceivers deterministically using keyset-style pagination.

        Returns a list of transceiver dicts covering [start, end].
        """
        results: List[Dict[str, Any]] = []

        last_ts = start.replace(microsecond=0) if start is not None else datetime.min.replace(tzinfo=timezone.utc)
        last_id = 0

        while True:
            query = text("""
                SELECT id as transceiver_id, callsign, frequency, position_lat, position_lon, timestamp, entity_type
                FROM transceivers
                WHERE timestamp >= :start AND timestamp <= :end
                """)
            if entity_type:
                query = text(str(query) + " AND entity_type = :entity_type")

            # Keyset condition to page deterministically
            query = text(str(query) + " AND (timestamp > :last_ts OR (timestamp = :last_ts AND id > :last_id)) ORDER BY timestamp, id LIMIT :limit")

            async with get_database_session() as session:
                params = {
                    "start": start,
                    "end": end,
                    "last_ts": last_ts,
                    "last_id": last_id,
                    "limit": page_size,
                }
                if entity_type:
                    params["entity_type"] = entity_type

                res = await session.execute(query, params)
                rows = res.fetchall()

            if not rows:
                break

            for row in rows:
                results.append({
                    "transceiver_id": row.transceiver_id,
                    "callsign": row.callsign,
                    "frequency": row.frequency,
                    "position_lat": row.position_lat,
                    "position_lon": row.position_lon,
                    "timestamp": row.timestamp,
                    "entity_type": row.entity_type,
                })

            # Advance keyset markers using last row
            last_row = rows[-1]
            last_ts = last_row.timestamp
            last_id = last_row.transceiver_id

            if len(rows) < page_size:
                break

        return results

    async def get_transceivers_in_window(self, start: datetime, end: datetime, entity_type: Optional[str] = None, ttl_seconds: int = 120, page_size_default: int = 10000, page_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """Decide whether to use cached snapshot or force deterministic DB pagination and return transceivers for the window."""
        # Decide using cache freshness
        strategy = transceiver_load_strategy(start, end, self._transceivers_last_fetch, ttl_seconds, page_size_default)

        # Prefer cache if available and not forcing on-demand
        if not strategy.get("force_on_demand", False) and self._transceivers_cache:
            # Filter cached snapshot deterministically
            filtered = []
            for t in self._transceivers_cache:
                ts = t.get("timestamp")
                if ts is None:
                    continue
                if ts >= start and ts <= end and (entity_type is None or t.get("entity_type") == entity_type):
                    filtered.append(t)
            return filtered

        # Force on-demand deterministic DB pagination
        # Choose page_size from explicit caller arg, then strategy, then default
        use_page_size = page_size if page_size is not None else strategy.get("page_size", page_size_default)
        return await self.load_transceivers_window(start, end, entity_type=entity_type, page_size=use_page_size)
    
    async def get_api_status(self) -> Dict[str, Any]:
        """Get VATSIM API status information."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.config.vatsim.api_url, timeout=self.config.vatsim.timeout)
                
                return {
                    "status": "operational" if response.status_code == 200 else "unhealthy",
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "last_check": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "last_check": datetime.now(timezone.utc).isoformat()
            }


# Global service instance
_vatsim_service: Optional[VATSIMService] = None


def get_vatsim_service() -> VATSIMService:
    """
    Get the global VATSIM service instance.
    
    Returns:
        VATSIMService: The global VATSIM service instance
    """
    global _vatsim_service
    if _vatsim_service is None:
        _vatsim_service = VATSIMService()
        # Initialize the service
        asyncio.create_task(_vatsim_service.initialize())
    return _vatsim_service 
