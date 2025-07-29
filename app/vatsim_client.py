import httpx
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class VATSIMATCPosition:
    """VATSIM ATC position data structure"""
    callsign: str
    facility: str
    position: str
    status: str
    frequency: str
    controller_id: str  # VATSIM user ID (links multiple positions)
    controller_name: str  # Controller's real name
    controller_rating: int  # Controller rating (1-15 from VATSIM)
    last_seen: datetime

@dataclass
class VATSIMFlight:
    """VATSIM flight data structure"""
    callsign: str
    aircraft_type: str
    departure: str
    arrival: str
    route: str
    altitude: int
    speed: int
    position: Dict[str, float]  # lat/lng
    controller_id: Optional[str]

class VATSIMClient:
    """Client for fetching VATSIM network data"""
    
    def __init__(self):
        self.base_url = "https://data.vatsim.net/v3"
        self.data_url = f"{self.base_url}/vatsim-data.json"
        self.status_url = f"{self.base_url}/status.json"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def fetch_network_data(self) -> Dict:
        """Fetch current VATSIM network data"""
        try:
            response = await self.client.get(self.data_url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch VATSIM data: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse VATSIM data: {e}")
            raise
    
    async def fetch_network_status(self) -> Dict:
        """Fetch VATSIM network status"""
        try:
            response = await self.client.get(self.status_url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch VATSIM status: {e}")
            raise
    
    def _map_facility_to_position(self, facility_id: int) -> str:
        """Map VATSIM facility ID to position name"""
        facility_map = {
            0: "OBS",   # Observer
            1: "FSS",   # Flight Service Station
            2: "DEL",   # Clearance Delivery
            3: "GND",   # Ground
            4: "TWR",   # Tower
            5: "APP",   # Approach/Departure
            6: "CTR"    # Enroute (Center)
        }
        return facility_map.get(facility_id, "UNKNOWN")

    def parse_atc_positions(self, data: Dict) -> List[VATSIMATCPosition]:
        """Parse ATC position data from VATSIM response"""
        atc_positions = []
        
        for controller_data in data.get("controllers", []):
            try:
                atc_position = VATSIMATCPosition(
                    callsign=controller_data.get("callsign", ""),
                    facility="VATSIM",  # Generic facility since VATSIM doesn't provide it
                    position=self._map_facility_to_position(controller_data.get("facility", 0)),
                    status="online",  # Assume online if in API response
                    frequency=controller_data.get("frequency", ""),
                                controller_id=str(controller_data.get("cid", "")),  # VATSIM user ID
            controller_name=controller_data.get("name", ""),
            controller_rating=controller_data.get("rating", 0),
                    last_seen=datetime.utcnow()
                )
                atc_positions.append(atc_position)
            except Exception as e:
                logger.warning(f"Failed to parse ATC position {controller_data.get('callsign', 'unknown')}: {e}")
                continue
        
        return atc_positions
    
    def parse_flights(self, data: Dict) -> List[VATSIMFlight]:
        """Parse flight data from VATSIM response"""
        flights = []
        
        for flight_data in data.get("pilots", []):
            try:
                # Parse position data
                position = {}
                if "latitude" in flight_data and "longitude" in flight_data:
                    position = {
                        "lat": float(flight_data["latitude"]),
                        "lng": float(flight_data["longitude"])
                    }
                
                flight = VATSIMFlight(
                    callsign=flight_data.get("callsign", ""),
                    aircraft_type=flight_data.get("aircraft_type", ""),
                    departure=flight_data.get("flight_plan", {}).get("departure", "") if flight_data.get("flight_plan") else "",
                    arrival=flight_data.get("flight_plan", {}).get("arrival", "") if flight_data.get("flight_plan") else "",
                    route=flight_data.get("flight_plan", {}).get("route", "") if flight_data.get("flight_plan") else "",
                    altitude=int(flight_data.get("altitude", 0)),
                    speed=int(flight_data.get("groundspeed", 0)),
                    position=position,
                    controller_id=flight_data.get("controller", "")
                )
                flights.append(flight)
            except Exception as e:
                logger.warning(f"Failed to parse flight {flight_data.get('callsign', 'unknown')}: {e}")
                continue
        
        return flights
    
    def parse_sectors(self, data: Dict) -> List[Dict]:
        """Parse sector data from VATSIM response"""
        # VATSIM doesn't provide sector data directly, so we'll create basic sectors
        # based on facility information
        sectors = []
        facilities = set()
        
        # Extract unique facilities from controllers
        for controller in data.get("controllers", []):
            facility = controller.get("facility", "")
            if facility:
                facilities.add(facility)
        
        # Create basic sectors for each facility
        for facility in facilities:
            sector = {
                "name": f"{facility}_CTR",
                "facility": facility,
                "controller_id": None,
                "traffic_density": 0,
                "status": "unmanned",
                "priority_level": 1
            }
            sectors.append(sector)
        
        return sectors
    
    async def get_current_data(self) -> Dict:
        """Get current VATSIM network data with parsed structures"""
        try:
            data = await self.fetch_network_data()
            
            return {
                "atc_positions": self.parse_atc_positions(data),
                "flights": self.parse_flights(data),
                "sectors": self.parse_sectors(data),
                "raw_data": data,
                "timestamp": datetime.utcnow()
            }
        except Exception as e:
            logger.error(f"Failed to get current VATSIM data: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

# Example usage
async def main():
    """Example of using the VATSIM client"""
    client = VATSIMClient()
    try:
        data = await client.get_current_data()
        print(f"Found {len(data['controllers'])} controllers")
        print(f"Found {len(data['flights'])} flights")
        print(f"Found {len(data['sectors'])} sectors")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main()) 