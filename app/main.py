#!/usr/bin/env python3
"""
VATSIM Data Collection System - Main Application

This module provides the FastAPI application with REST API endpoints for the VATSIM
data collection and analysis system. It handles real-time data ingestion, API requests,
and serves the web dashboard.

INPUTS:
- Environment variables for configuration
- VATSIM API data (via background service)
- Database queries and updates
- HTTP requests from clients

OUTPUTS:
- REST API responses (JSON)
- HTML dashboard pages
- Real-time data updates
- Background data ingestion to database

ENDPOINTS:
- /api/status - System health and status
- /api/atc-positions - ATC position data
- /api/flights - Flight data
- /api/traffic/* - Traffic analysis endpoints
- /dashboard - Web dashboard interface
- /frontend/* - Static frontend files

DEPENDENCIES:
- PostgreSQL database
- Redis cache
- VATSIM API
- Background data ingestion service
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from sqlalchemy import and_, desc, text

from .config import get_config, validate_config
from .database import get_db, init_db, get_database_info, SessionLocal
from .models import ATCPosition, Sector, Flight, TrafficMovement, AirportConfig
from .utils.logging import get_logger_for_module
from .utils.rating_utils import get_rating_name, get_rating_level, get_all_ratings, validate_rating
from .services.vatsim_service import get_vatsim_service
from .services.data_service import get_data_service
from .services.traffic_analysis_service import get_traffic_analysis_service
from .services.cache_service import get_cache_service
from .services.query_optimizer import get_query_optimizer
from .services.resource_manager import get_resource_manager
from .utils.airport_utils import get_airports_by_region, get_region_statistics, get_airport_coordinates

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
            await data_service.start_data_ingestion()
            # Sleep interval is now handled inside the data service
        except Exception as e:
            logger.error(f"Background data ingestion error: {e}")
            await asyncio.sleep(30)  # Fallback sleep on error

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global background_task
    
    # Initialize database
    init_db()
    
    # Initialize cache service
    cache_service = await get_cache_service()
    
    # Initialize resource manager
    resource_manager = get_resource_manager()
    
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

# Add CORS middleware with explicit configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Mount static files for frontend
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

@app.get("/dashboard")
async def get_dashboard():
    """Serve the main dashboard"""
    try:
        with open("frontend/index.html", "r") as f:
            content = f.read()
        return HTMLResponse(content=content, status_code=200)
    except Exception as e:
        logger.error(f"Error serving dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/frontend/index.html")
async def get_frontend_index():
    """Serve the main frontend index.html"""
    try:
        with open("frontend/index.html", "r") as f:
            content = f.read()
        return HTMLResponse(content=content, status_code=200)
    except Exception as e:
        logger.error(f"Error serving frontend index: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/frontend/performance-dashboard.html")
async def get_performance_dashboard():
    """Serve the performance dashboard"""
    try:
        with open("frontend/performance-dashboard.html", "r") as f:
            content = f.read()
        return HTMLResponse(content=content, status_code=200)
    except Exception as e:
        logger.error(f"Error serving performance dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/frontend/sprint3.html")
async def get_sprint3_dashboard():
    """Serve the Sprint 3 dashboard"""
    try:
        with open("frontend/sprint3.html", "r") as f:
            content = f.read()
        return HTMLResponse(content=content, status_code=200)
    except Exception as e:
        logger.error(f"Error serving Sprint 3 dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
            .database-info { background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0; }
            .migration-status { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚁 VATSIM Data Collector</h1>
                <p>Real-time air traffic control data collection and analysis system</p>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number" id="atc-positions-count">-</div>
                    <div>Active ATC Positions</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="flights-count">-</div>
                    <div>Active Flights</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="airports-count">-</div>
                    <div>Monitored Airports</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="movements-count">-</div>
                    <div>Traffic Movements</div>
                </div>
            </div>
            
            <div class="endpoints">
                <h2>📡 API Endpoints</h2>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/api/status</span> - System status and statistics
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/api/atc-positions</span> - Active ATC positions data
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/api/flights</span> - Active flights data
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/api/traffic/movements/{airport}</span> - Airport traffic movements
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/api/database/status</span> - Database status and migration info
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/api/performance/metrics</span> - System performance metrics
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/performance-dashboard</span> - Performance monitoring dashboard
                </div>
            </div>
            
            <div class="database-info">
                <h2>🗄️ Database Status</h2>
                <div id="database-status">Loading...</div>
            </div>
            
            <div class="migration-status">
                <h2>🔄 Migration Status</h2>
                <div id="migration-status">Loading...</div>
            </div>
        </div>
        
        <script>
            async function updateStats() {
                try {
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    
                    document.getElementById('atc-positions-count').textContent = data.atc_positions_count || 0;
                    document.getElementById('flights-count').textContent = data.flights_count || 0;
                    document.getElementById('airports-count').textContent = data.airports_count || 0;
                    document.getElementById('movements-count').textContent = data.movements_count || 0;
                } catch (error) {
                    console.error('Failed to update stats:', error);
                }
            }
            
            async function updateDatabaseStatus() {
                try {
                    const response = await fetch('/api/database/status');
                    const data = await response.json();
                    
                    document.getElementById('database-status').innerHTML = `
                        <strong>Status:</strong> ${data.database.database_type}<br>
                        <strong>Tables:</strong> ${data.database.tables_count}<br>
                        <strong>Total Records:</strong> ${data.database.total_records.toLocaleString()}<br>
                        <strong>Cache:</strong> ${data.cache.hits} hits, ${data.cache.misses} misses, ${data.cache.size} items
                    `;
                } catch (error) {
                    console.error('Failed to update database status:', error);
                }
            }
            
            // Update immediately and then every 30 seconds
            updateStats();
            updateDatabaseStatus();
            setInterval(updateStats, 30000);
            setInterval(updateDatabaseStatus, 60000);
        </script>
    </body>
    </html>
    """

@app.get("/api/status")
async def get_status(db: Session = Depends(get_db)):
    """Get system status with caching"""
    try:
        # Try to get from cache first
        cache_service = await get_cache_service()
        cached_stats = await cache_service.get_network_stats_cache()
        
        if cached_stats:
            logger.info("Returning cached network stats")
            return cached_stats
        
        # If not cached, get from database
        atc_positions_count = db.query(ATCPosition).filter(ATCPosition.status == "online").count()
        flights_count = db.query(Flight).filter(Flight.status == "active").count()
        airports_count = db.query(AirportConfig).count()
        movements_count = db.query(TrafficMovement).filter(
            TrafficMovement.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        stats = {
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "atc_positions_count": atc_positions_count,
            "flights_count": flights_count,
            "airports_count": airports_count,
            "movements_count": movements_count,
            "data_freshness": "real-time",
            "cache_status": "enabled"
        }
        
        # Cache the result
        await cache_service.set_network_stats_cache(stats)
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/network/status")
async def get_network_status(db: Session = Depends(get_db)):
    """Get network status with caching"""
    try:
        # Try to get from cache first
        cache_service = await get_cache_service()
        cached_data = await cache_service.get_cached_data('network:detailed_status')
        
        if cached_data:
            return cached_data
        
        # Get network data from database
        atc_count = db.query(ATCPosition).filter(ATCPosition.status == "online").count()
        flight_count = db.query(Flight).filter(Flight.status == "active").count()
        sector_count = db.query(Sector).count()
        
        status = {
            "total_controllers": atc_count,
            "total_flights": flight_count,
            "total_sectors": sector_count,
            "last_update": datetime.utcnow().isoformat()
        }
        
        # Cache the result
        await cache_service.set_cached_data('network:detailed_status', status, 60)
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting network status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/atc-positions")
async def get_atc_positions(db: Session = Depends(get_db)):
    """Get active ATC positions with caching"""
    try:
        # Try to get from cache first
        cache_service = await get_cache_service()
        cached_data = await cache_service.get_cached_data('atc_positions:active')
        
        if cached_data:
            return {
                **cached_data,
                "cached": True
            }
        
        # Get from database if not cached
        atc_positions = db.query(ATCPosition).all()
        
        atc_positions_data = []
        for atc_position in atc_positions:
            # Validate rating with error handling
            rating_validation = validate_rating(atc_position.controller_rating) if atc_position.controller_rating else {"is_valid": False, "rating_name": None, "rating_level": None, "error": "No rating provided"}
            
            atc_positions_data.append({
                "id": atc_position.id,
                "callsign": atc_position.callsign,
                "facility": atc_position.facility,
                "position": atc_position.position,
                "status": atc_position.status,
                "frequency": atc_position.frequency,
                "controller_id": atc_position.controller_id,
                "controller_name": atc_position.controller_name,
                "controller_rating": atc_position.controller_rating,
                "controller_rating_name": rating_validation.get("rating_name"),
                "controller_rating_level": rating_validation.get("rating_level"),
                "rating_validation": {
                    "is_valid": rating_validation.get("is_valid", False),
                    "error": rating_validation.get("error")
                },
                "last_seen": atc_position.last_seen.isoformat() if atc_position.last_seen else None,
                "workload_score": atc_position.workload_score
            })
        
        # Count online positions
        online_count = len([pos for pos in atc_positions_data if pos["status"] == "online"])
        
        result = {
            "positions": atc_positions_data,
            "total": len(atc_positions_data),
            "online": online_count,
            "cached": False
        }
        
        # Cache the result for 30 seconds
        await cache_service.set_cached_data('atc_positions:active', result, 30)
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting ATC positions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/atc-positions/by-controller-id")
async def get_atc_positions_by_controller_id(db: Session = Depends(get_db)):
    """Get ATC positions grouped by controller ID (showing multiple positions per controller)"""
    try:
        # Try to get from cache first
        cache_service = await get_cache_service()
        cached_data = await cache_service.get_cached_data('atc_positions:by_controller_id')
        
        if cached_data:
            return {
                **cached_data,
                "cached": True
            }
        
        # Get all ATC positions
        atc_positions = db.query(ATCPosition).all()
        
        # Group by controller ID
        atc_positions_by_controller_id = {}
        for atc_position in atc_positions:
            controller_id = atc_position.controller_id or "unknown"
            if controller_id not in atc_positions_by_controller_id:
                # Validate rating with error handling
                rating_validation = validate_rating(atc_position.controller_rating) if atc_position.controller_rating else {"is_valid": False, "rating_name": None, "rating_level": None, "error": "No rating provided"}
                
                atc_positions_by_controller_id[controller_id] = {
                    "controller_id": controller_id,
                    "controller_name": atc_position.controller_name,
                    "controller_rating": atc_position.controller_rating,
                    "controller_rating_name": rating_validation.get("rating_name"),
                    "controller_rating_level": rating_validation.get("rating_level"),
                    "rating_validation": {
                        "is_valid": rating_validation.get("is_valid", False),
                        "error": rating_validation.get("error")
                    },
                    "positions": [],
                    "total_positions": 0,
                    "facilities": set(),
                    "frequencies": []
                }
            
            atc_positions_by_controller_id[controller_id]["positions"].append({
                "callsign": atc_position.callsign,
                "facility": atc_position.facility,
                "position": atc_position.position,
                "frequency": atc_position.frequency,
                "status": atc_position.status,
                "last_seen": atc_position.last_seen.isoformat() if atc_position.last_seen else None,
                "workload_score": atc_position.workload_score
            })
            atc_positions_by_controller_id[controller_id]["total_positions"] += 1
            atc_positions_by_controller_id[controller_id]["facilities"].add(atc_position.facility)
            if atc_position.frequency:
                atc_positions_by_controller_id[controller_id]["frequencies"].append(atc_position.frequency)
        
        # Convert sets to lists for JSON serialization
        for controller_id, data in atc_positions_by_controller_id.items():
            data["facilities"] = list(data["facilities"])
        
        result = {
            "atc_positions_by_controller_id": list(atc_positions_by_controller_id.values()),
            "total_unique_controllers": len(atc_positions_by_controller_id),
            "total_positions": sum(data["total_positions"] for data in atc_positions_by_controller_id.values())
        }
        
        # Cache the result for 30 seconds
        await cache_service.set_cached_data('atc_positions:by_controller_id', result, 30)
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting ATC positions by controller ID: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/vatsim/ratings")
async def get_vatsim_ratings():
    """Get all available VATSIM controller ratings"""
    try:
        # Try to get from cache first (static data, long cache)
        cache_service = await get_cache_service()
        cached_data = await cache_service.get_cached_data('vatsim:ratings')
        
        if cached_data:
            return {
                **cached_data,
                "cached": True
            }
        
        ratings = get_all_ratings()
        result = {
            "ratings": ratings,
            "total_ratings": len(ratings),
            "description": "VATSIM controller ratings from 1-15",
            "valid_range": "1-15",
            "known_ratings": [1, 2, 3, 4, 5, 8, 10, 11],
            "unknown_ratings": [6, 7, 9, 12, 13, 14, 15]
        }
        
        # Cache the result for 1 hour (static data)
        await cache_service.set_cached_data('vatsim:ratings', result, 3600)
        
        return result
    except Exception as e:
        logger.error(f"Error getting VATSIM ratings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/flights")
async def get_flights(db: Session = Depends(get_db)):
    """Get active flights with caching"""
    try:
        # Try to get from cache first
        cache_service = await get_cache_service()
        cached_flights = await cache_service.get_flights_cache()
        
        if cached_flights:
            logger.info("Returning cached flights data")
            # Count active flights from cached data
            active_count = len([flight for flight in cached_flights['data'] if flight.get("status") == "active"])
            return {
                "flights": cached_flights['data'],
                "total": len(cached_flights['data']),
                "active": active_count,
                "cached": True
            }
        
                # If not cached, get from database using direct SQL to avoid session isolation issues
        result = db.execute(text("SELECT * FROM flights WHERE status = 'active'"))
        flights_data = []
        
        for row in result:
            flight_data = {
                "id": row.id,
                "callsign": row.callsign,
                "aircraft_type": row.aircraft_type,
                "departure": row.departure,
                "arrival": row.arrival,
                "route": row.route,
                "altitude": row.altitude,
                "speed": row.speed,
                "heading": row.heading,
                "ground_speed": row.ground_speed,
                "vertical_speed": row.vertical_speed,
                "squawk": row.squawk,
                "position_lat": row.position_lat,
                "position_lng": row.position_lng,
                "atc_position_id": row.atc_position_id,
                "last_updated": row.last_updated.isoformat() if row.last_updated else None
            }
            
            # Debug: Log flights with atc_position_id
            if row.atc_position_id is not None:
                logger.info(f"Flight {row.callsign} has atc_position_id: {row.atc_position_id}")
            
            flights_data.append(flight_data)
        
        # Debug: Check if any flights have atc_position_id
        flights_with_atc = [f for f in flights_data if f['atc_position_id'] is not None]
        logger.info(f"Found {len(flights_with_atc)} flights with atc_position_id out of {len(flights_data)} total flights")
        
        # Cache the result
        await cache_service.set_flights_cache(flights_data)
        
        # Count active flights
        active_count = len([flight for flight in flights_data if flight.get("status") == "active"])
        
        return {
            "flights": flights_data,
            "total": len(flights_data),
            "active": active_count,
            "cached": False
        }
        
    except Exception as e:
        logger.error(f"Error getting flights: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/traffic/movements/{airport_icao}")
async def get_airport_movements(
    airport_icao: str, 
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get traffic movements for specific airport with caching"""
    try:
        # Try to get from cache first
        cache_service = await get_cache_service()
        cached_movements = await cache_service.get_traffic_movements_cache(airport_icao)
        
        if cached_movements:
            logger.info(f"Returning cached movements for {airport_icao}")
            return {"movements": cached_movements, "cached": True}
        
        # If not cached, get from database
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        movements = db.query(TrafficMovement).filter(
            and_(
                TrafficMovement.airport_icao == airport_icao.upper(),
                TrafficMovement.timestamp >= cutoff_time
            )
        ).order_by(desc(TrafficMovement.timestamp)).all()
        
        movements_data = []
        for movement in movements:
            movements_data.append({
                "id": movement.id,
                "airport_icao": movement.airport_icao,
                "flight_callsign": movement.flight_callsign,
                "movement_type": movement.movement_type,
                "timestamp": movement.timestamp.isoformat(),
                "confidence": movement.confidence,
                "altitude": movement.altitude,
                "speed": movement.speed
            })
        
        # Cache the result
        await cache_service.set_traffic_movements_cache(airport_icao, movements_data)
        
        return {"movements": movements_data, "cached": False}
        
    except Exception as e:
        logger.error(f"Error getting traffic movements for {airport_icao}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/traffic/summary/{region}")
async def get_traffic_summary(
    region: str = "Australia",
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get traffic summary for region with caching"""
    try:
        # Try to get from cache first
        cache_service = await get_cache_service()
        cache_key = f'traffic:summary:{region}:{hours}h'
        cached_summary = await cache_service.get_cached_data(cache_key)
        
        if cached_summary:
            return cached_summary
        
        # If not cached, calculate from database
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get airports for the specified region dynamically
        region_airports = get_airports_by_region(region)
        
        if not region_airports:
            logger.warning(f"No airports found for region '{region}', returning empty summary")
            return {
                "region": region,
                "period_hours": hours,
                "total_movements": 0,
                "arrivals": 0,
                "departures": 0,
                "airport_breakdown": {},
                "timestamp": datetime.utcnow().isoformat()
            }
        
        movements = db.query(TrafficMovement).filter(
            and_(
                TrafficMovement.airport_code.in_(region_airports),
                TrafficMovement.timestamp >= cutoff_time
            )
        ).all()
        
        # Calculate summary statistics
        total_movements = len(movements)
        arrivals = len([m for m in movements if m.movement_type == "arrival"])
        departures = len([m for m in movements if m.movement_type == "departure"])
        
        # Group by airport
        airport_stats = {}
        for movement in movements:
            airport = movement.airport_icao
            if airport not in airport_stats:
                airport_stats[airport] = {"arrivals": 0, "departures": 0}
            
            if movement.movement_type == "arrival":
                airport_stats[airport]["arrivals"] += 1
            else:
                airport_stats[airport]["departures"] += 1
        
        summary = {
            "region": region,
            "period_hours": hours,
            "total_movements": total_movements,
            "arrivals": arrivals,
            "departures": departures,
            "airport_breakdown": airport_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Cache the result
        await cache_service.set_cached_data(cache_key, summary, 300)
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting traffic summary for {region}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/traffic/trends/{airport_icao}")
async def get_traffic_trends(
    airport_icao: str,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Get traffic trends for airport with caching"""
    try:
        # Try to get from cache first
        cache_service = await get_cache_service()
        cache_key = f'traffic:trends:{airport_icao}:{days}d'
        cached_trends = await cache_service.get_cached_data(cache_key)
        
        if cached_trends:
            return cached_trends
        
        # If not cached, calculate from database
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        movements = db.query(TrafficMovement).filter(
            and_(
                TrafficMovement.airport_icao == airport_icao.upper(),
                TrafficMovement.timestamp >= cutoff_time
            )
        ).order_by(TrafficMovement.timestamp).all()
        
        # Group by day
        daily_stats = {}
        for movement in movements:
            date_key = movement.timestamp.date().isoformat()
            if date_key not in daily_stats:
                daily_stats[date_key] = {"arrivals": 0, "departures": 0}
            
            if movement.movement_type == "arrival":
                daily_stats[date_key]["arrivals"] += 1
            else:
                daily_stats[date_key]["departures"] += 1
        
        trends = {
            "airport_icao": airport_icao,
            "period_days": days,
            "daily_stats": daily_stats,
            "total_movements": len(movements),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Cache the result
        await cache_service.set_cached_data(cache_key, trends, 3600)
        
        return trends
        
    except Exception as e:
        logger.error(f"Error getting traffic trends for {airport_icao}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/database/status")
async def get_database_status():
    """Get database status and migration information"""
    try:
        db_info = get_database_info()
        cache_service = await get_cache_service()
        cache_stats = await cache_service.get_cache_stats()
        
        return {
            "database": db_info,
            "cache": cache_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting database status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/performance/metrics")
async def get_performance_metrics():
    """Get system performance metrics"""
    try:
        resource_manager = get_resource_manager()
        performance_metrics = await resource_manager.get_performance_metrics()
        
        return performance_metrics
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/flights/memory")
async def get_flights_from_memory():
    """Get flights directly from memory cache (for debugging)"""
    try:
        data_service = get_data_service()
        logger.info(f"Memory cache has {len(data_service.cache['flights'])} flights")
        flights_data = []
        
        for callsign, flight_data in data_service.cache['flights'].items():
            flights_data.append({
                "callsign": flight_data.get('callsign', ''),
                "aircraft_type": flight_data.get('aircraft_type', ''),
                "departure": flight_data.get('departure', ''),
                "arrival": flight_data.get('arrival', ''),
                "altitude": flight_data.get('altitude', 0),
                "speed": flight_data.get('speed', 0),
                "position_lat": flight_data.get('position_lat', 0.0),
                "position_lng": flight_data.get('position_lng', 0.0),
                "heading": flight_data.get('heading', 0),
                "ground_speed": flight_data.get('ground_speed', 0),
                "vertical_speed": flight_data.get('vertical_speed', 0),
                "squawk": flight_data.get('squawk', ''),
                "atc_position_id": flight_data.get('atc_position_id'),
                "last_updated": flight_data.get('last_updated', '').isoformat() if hasattr(flight_data.get('last_updated', ''), 'isoformat') else str(flight_data.get('last_updated', ''))
            })
        
        return {"flights": flights_data, "total": len(flights_data), "cached": True}
        
    except Exception as e:
        logger.error(f"Error getting flights from memory: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.options("/api/performance/metrics")
async def options_performance_metrics():
    """Handle OPTIONS request for performance metrics"""
    return {"message": "OK"}

@app.get("/api/performance/optimize")
async def optimize_performance():
    """Trigger performance optimization"""
    try:
        resource_manager = get_resource_manager()
        query_optimizer = get_query_optimizer()
        
        # Optimize memory usage
        memory_optimization = await resource_manager.optimize_memory_usage()
        
        # Optimize database queries
        db_optimization = await query_optimizer.optimize_database_queries(None)
        
        return {
            "memory_optimization": memory_optimization,
            "database_optimization": db_optimization,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error optimizing performance: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/traffic-dashboard")
async def get_traffic_dashboard():
    """Get traffic dashboard HTML"""
    try:
        traffic_service = get_traffic_analysis_service()
        dashboard_data = await traffic_service.generate_dashboard_data()
        
        return HTMLResponse(content=dashboard_data, status_code=200)
    except Exception as e:
        logger.error(f"Error generating traffic dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# This route is now handled by the frontend route below
# @app.get("/performance-dashboard")
# async def get_performance_dashboard():
#     """Get performance dashboard HTML"""
#     try:
#         with open("frontend/performance-dashboard.html", "r") as f:
#             content = f.read()
#         return HTMLResponse(content=content, status_code=200)
#     except Exception as e:
#         logger.error(f"Error serving performance dashboard: {e}")
#         raise HTTPException(status_code=500, detail="Internal server error")

# Frontend routes - added at the end to ensure they're registered
@app.get("/frontend/index.html")
async def serve_frontend_index():
    """Serve the main frontend index.html"""
    try:
        with open("frontend/index.html", "r") as f:
            content = f.read()
        return HTMLResponse(content=content, status_code=200)
    except Exception as e:
        logger.error(f"Error serving frontend index: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/frontend/performance-dashboard.html")
async def serve_performance_dashboard():
    """Serve the performance dashboard"""
    try:
        with open("frontend/performance-dashboard.html", "r") as f:
            content = f.read()
        return HTMLResponse(content=content, status_code=200)
    except Exception as e:
        logger.error(f"Error serving performance dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/frontend/sprint3.html")
async def serve_sprint3_dashboard():
    """Serve the Sprint 3 dashboard"""
    try:
        with open("frontend/sprint3.html", "r") as f:
            content = f.read()
        return HTMLResponse(content=content, status_code=200)
    except Exception as e:
        logger.error(f"Error serving Sprint 3 dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/frontend/debug-performance.html")
async def serve_debug_performance():
    """Serve the debug performance dashboard"""
    try:
        with open("frontend/debug-performance.html", "r") as f:
            content = f.read()
        return HTMLResponse(content=content, status_code=200)
    except Exception as e:
        logger.error(f"Error serving debug performance dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")



@app.get("/frontend/database-query.html")
async def serve_database_query():
    """Serve the database query tool"""
    try:
        with open("frontend/database-query.html", "r") as f:
            content = f.read()
        return HTMLResponse(content=content, status_code=200)
    except Exception as e:
        logger.error(f"Error serving database query tool: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str

@app.post("/api/database/query")
async def execute_database_query(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """Execute custom SQL query and return results"""
    try:
        query = request.query
        
        # Security: Only allow SELECT queries
        if not query.strip().upper().startswith('SELECT'):
            raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
        
        # Execute query
        result = db.execute(text(query))
        rows = result.fetchall()
        
        # Convert to JSON-serializable format
        columns = result.keys()
        data = []
        for row in rows:
            row_dict = {}
            for i, column in enumerate(columns):
                value = row[i]
                # Handle datetime objects
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                row_dict[column] = value
            data.append(row_dict)
        
        return {
            "success": True,
            "data": data,
            "row_count": len(data),
            "columns": list(columns),
            "query": query,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/api/airports/region/{region}")
async def get_airports_by_region_api(region: str = "Australia"):
    """Get airports for a specific region"""
    try:
        # Try to get from cache first (static data, long cache)
        cache_service = await get_cache_service()
        cache_key = f'airports:region:{region}'
        cached_data = await cache_service.get_cached_data(cache_key)
        
        if cached_data:
            return {
                **cached_data,
                "cached": True
            }
        
        stats = get_region_statistics(region)
        result = {
            "region": region,
            "total_airports": stats["total_airports"],
            "airports": stats["airports"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Cache the result for 10 minutes (static data)
        await cache_service.set_cached_data(cache_key, result, 600)
        
        return result
    except Exception as e:
        logger.error(f"Error getting airports for region {region}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/airports/{airport_code}/coordinates")
async def get_airport_coordinates_api(airport_code: str):
    """Get coordinates for a specific airport"""
    try:
        # Try to get from cache first (static data, long cache)
        cache_service = await get_cache_service()
        cache_key = f'airport:coords:{airport_code.upper()}'
        cached_data = await cache_service.get_cached_data(cache_key)
        
        if cached_data:
            return {
                **cached_data,
                "cached": True
            }
        
        coords = get_airport_coordinates(airport_code.upper())
        if coords is None:
            raise HTTPException(status_code=404, detail=f"Airport {airport_code} not found")
        
        result = {
            "airport_code": airport_code.upper(),
            "latitude": coords[0],
            "longitude": coords[1],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Cache the result for 1 hour (static data)
        await cache_service.set_cached_data(cache_key, result, 3600)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting coordinates for airport {airport_code}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/database/tables")
async def get_database_tables(db: Session = Depends(get_db)):
    """Get list of database tables and their record counts"""
    try:
        # Get table information
        result = db.execute(text("""
            SELECT 
                table_name,
                (SELECT COUNT(*) FROM information_schema.tables t2 
                 WHERE t2.table_name = t1.table_name) as record_count
            FROM information_schema.tables t1
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """))
        
        tables = []
        for row in result:
            # Get actual record count for each table
            try:
                count_result = db.execute(text(f"SELECT COUNT(*) FROM {row[0]}"))
                count = count_result.scalar()
                tables.append({
                    "name": row[0],
                    "record_count": count
                })
            except:
                tables.append({
                    "name": row[0],
                    "record_count": 0
                })
        
        return {
            "tables": tables,
            "total_tables": len(tables),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting table info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 