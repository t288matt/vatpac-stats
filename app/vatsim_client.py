import httpx
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class VATSIMController:
    """VATSIM controller data structure"""
    callsign: str
    facility: str
    position: str
    status: str
    frequency: str
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
    
    def parse_controllers(self, data: Dict) -> List[VATSIMController]:
        """Parse controller data from VATSIM response"""
        controllers = []
        
        for controller_data in data.get("controllers", []):
            try:
                controller = VATSIMController(
                    callsign=controller_data.get("callsign", ""),
                    facility=controller_data.get("facility", ""),
                    position=controller_data.get("position", ""),
                    status=controller_data.get("status", "offline"),
                    frequency=controller_data.get("frequency", ""),
                    last_seen=datetime.utcnow()
                )
                controllers.append(controller)
            except Exception as e:
                logger.warning(f"Failed to parse controller {controller_data.get('callsign', 'unknown')}: {e}")
                continue
        
        return controllers
    
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
                "controllers": self.parse_controllers(data),
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