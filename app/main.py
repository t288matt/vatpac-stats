from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from .config import get_config, validate_config
from .database import get_db, init_db
from .models import Controller, Sector, Flight, TrafficMovement, AirportConfig
from .utils.logging import get_logger_for_module
from .services.vatsim_service import get_vatsim_service
from .services.data_service import get_data_service
from .services.traffic_analysis_service import get_traffic_analysis_service

# Configure logging
logger = get_logger_for_module(__name__)

# Background task for data ingestion
background_task = None

async def background_data_ingestion():
    """Background task for continuous data ingestion"""
    global background_task
    while True:
        try:
            data_service = get_data_service()
            await data_service.ingest_current_data()
            await asyncio.sleep(30)  # Update every 30 seconds
        except Exception as e:
            logger.error(f"Background data ingestion error: {e}")
            await asyncio.sleep(30)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global background_task
    
    # Initialize database
    init_db()
    
    # Start background task
    background_task = asyncio.create_task(background_data_ingestion())
    
    yield
    
    # Cleanup
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass

# Create FastAPI app
app = FastAPI(
    title="VATSIM Data Collector",
    description="Real-time VATSIM data collection and traffic analysis system",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with dashboard"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>VATSIM Data Collector</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
            .stat-card { background: #ecf0f1; padding: 20px; border-radius: 5px; text-align: center; }
            .stat-number { font-size: 2em; font-weight: bold; color: #2c3e50; }
            .endpoints { background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }
            .endpoint { margin: 10px 0; padding: 10px; background: white; border-radius: 3px; }
            .method { font-weight: bold; color: #e74c3c; }
            .url { font-family: monospace; color: #3498db; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🛩️ VATSIM Data Collector</h1>
                <p>Real-time VATSIM network data collection and traffic analysis</p>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number" id="controllers">-</div>
                    <div>Controllers</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="flights">-</div>
                    <div>Active Flights</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="movements">-</div>
                    <div>Traffic Movements</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="airports">-</div>
                    <div>Tracked Airports</div>
                </div>
            </div>
            
            <div class="endpoints">
                <h2>📊 API Endpoints</h2>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/api/status</span> - System status
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/api/network/status</span> - Network status
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/api/controllers</span> - All controllers
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/api/flights</span> - All flights
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/api/traffic/movements/{airport}</span> - Airport movements
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/api/traffic/summary/{region}</span> - Regional summary
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/api/traffic/trends/{airport}</span> - Traffic trends
                </div>
            </div>
        </div>
        
        <script>
            async function updateStats() {
                try {
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    
                    document.getElementById('controllers').textContent = data.controllers || 0;
                    document.getElementById('flights').textContent = data.flights || 0;
                    document.getElementById('movements').textContent = data.movements || 0;
                    document.getElementById('airports').textContent = data.airports || 0;
                } catch (error) {
                    console.error('Error updating stats:', error);
                }
            }
            
            // Update stats every 30 seconds
            updateStats();
            setInterval(updateStats, 30000);
        </script>
    </body>
    </html>
    """

@app.get("/api/status")
async def get_status(db: Session = Depends(get_db)):
    """Get system status and statistics"""
    try:
        # Get counts
        controller_count = db.query(Controller).count()
        flight_count = db.query(Flight).count()
        movement_count = db.query(TrafficMovement).filter(
            TrafficMovement.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        airport_count = db.query(AirportConfig).filter(AirportConfig.is_active == True).count()
        
        return {
            "status": "operational",
            "controllers": controller_count,
            "flights": flight_count,
            "movements": movement_count,
            "airports": airport_count,
            "last_updated": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/network/status")
async def get_network_status(db: Session = Depends(get_db)):
    """Get VATSIM network status"""
    try:
        data_service = get_data_service()
        return await data_service.get_network_status()
    except Exception as e:
        logger.error(f"Error getting network status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/controllers")
async def get_controllers(db: Session = Depends(get_db)):
    """Get all controllers"""
    try:
        controllers = db.query(Controller).all()
        return [
            {
                "id": c.id,
                "callsign": c.callsign,
                "facility": c.facility,
                "position": c.position,
                "status": c.status,
                "frequency": c.frequency,
                "last_seen": c.last_seen.isoformat() if c.last_seen else None
            }
            for c in controllers
        ]
    except Exception as e:
        logger.error(f"Error getting controllers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/flights")
async def get_flights(db: Session = Depends(get_db)):
    """Get all flights"""
    try:
        flights = db.query(Flight).all()
        return [
            {
                "id": f.id,
                "callsign": f.callsign,
                "pilot_name": f.pilot_name,
                "aircraft_type": f.aircraft_type,
                "departure": f.departure,
                "arrival": f.arrival,
                "route": f.route,
                "altitude": f.altitude,
                "speed": f.speed,
                "position": f.position,
                "last_updated": f.last_updated.isoformat() if f.last_updated else None
            }
            for f in flights
        ]
    except Exception as e:
        logger.error(f"Error getting flights: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/traffic/movements/{airport_icao}")
async def get_airport_movements(
    airport_icao: str, 
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get traffic movements for a specific airport"""
    try:
        traffic_service = get_traffic_analysis_service(db)
        movements = traffic_service.get_movements_by_airport(airport_icao, hours)
        
        return {
            "airport_icao": airport_icao.upper(),
            "hours": hours,
            "movements": movements,
            "total_movements": len(movements),
            "arrivals": len([m for m in movements if m['movement_type'] == 'arrival']),
            "departures": len([m for m in movements if m['movement_type'] == 'departure'])
        }
    except Exception as e:
        logger.error(f"Error getting movements for {airport_icao}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/traffic/summary/{region}")
async def get_traffic_summary(
    region: str = "Australia",
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get traffic summary for a region"""
    try:
        traffic_service = get_traffic_analysis_service(db)
        summary = traffic_service.get_movements_summary(region, hours)
        
        total_movements = sum(airport['total_movements'] for airport in summary.values())
        total_arrivals = sum(airport['arrivals'] for airport in summary.values())
        total_departures = sum(airport['departures'] for airport in summary.values())
        
        return {
            "region": region,
            "hours": hours,
            "airports": summary,
            "summary": {
                "total_movements": total_movements,
                "total_arrivals": total_arrivals,
                "total_departures": total_departures,
                "active_airports": len(summary)
            }
        }
    except Exception as e:
        logger.error(f"Error getting traffic summary for {region}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/traffic/trends/{airport_icao}")
async def get_traffic_trends(
    airport_icao: str,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Get traffic trends for an airport"""
    try:
        traffic_service = get_traffic_analysis_service(db)
        trends = traffic_service.get_traffic_trends(airport_icao, days)
        
        return {
            "airport_icao": airport_icao.upper(),
            "days": days,
            "trends": trends,
            "total_days": len(trends)
        }
    except Exception as e:
        logger.error(f"Error getting traffic trends for {airport_icao}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 