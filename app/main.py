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
                <h2>📊 Dashboards & API Endpoints</h2>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/traffic-dashboard</span> - <strong>Traffic Dashboard (User-friendly)</strong>
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <span class="url">/graph-dashboard</span> - <strong>Graph Dashboard (Charts & Analytics)</strong>
                </div>
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

@app.get("/traffic-dashboard", response_class=HTMLResponse)
async def traffic_dashboard(db: Session = Depends(get_db)):
    """Traffic dashboard with user-friendly display"""
    try:
        # Get traffic summary for Australia
        traffic_analysis = get_traffic_analysis_service(db)
        summary = traffic_analysis.get_movements_summary("Australia", 24)
        
        # Format the data for display
        airports_html = ""
        total_movements = 0
        total_arrivals = 0
        total_departures = 0
        
        for icao, data in summary.get("airports", {}).items():
            airport_name = data.get("airport_name", "Unknown")
            movements = data.get("total_movements", 0)
            arrivals = data.get("arrivals", 0)
            departures = data.get("departures", 0)
            last_movement = data.get("last_movement")
            
            total_movements += movements
            total_arrivals += arrivals
            total_departures += departures
            
            # Format last movement time
            last_movement_str = "No recent activity"
            if last_movement:
                try:
                    dt = datetime.fromisoformat(last_movement.replace('Z', '+00:00'))
                    last_movement_str = dt.strftime("%Y-%m-%d %H:%M UTC")
                except:
                    last_movement_str = last_movement
            
            # Color coding based on activity
            activity_class = "no-activity" if movements == 0 else "active"
            
            airports_html += f"""
            <div class="airport-card {activity_class}">
                <h3>{icao} - {airport_name}</h3>
                <div class="airport-stats">
                    <div class="stat">
                        <span class="label">Total Movements:</span>
                        <span class="value">{movements}</span>
                    </div>
                    <div class="stat">
                        <span class="label">Arrivals:</span>
                        <span class="value">{arrivals}</span>
                    </div>
                    <div class="stat">
                        <span class="label">Departures:</span>
                        <span class="value">{departures}</span>
                    </div>
                    <div class="stat">
                        <span class="label">Last Activity:</span>
                        <span class="value">{last_movement_str}</span>
                    </div>
                </div>
            </div>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>VATSIM Traffic Dashboard - Australia</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                }}
                .container {{
                    max-width: 1400px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: rgba(255, 255, 255, 0.95);
                    padding: 30px;
                    border-radius: 15px;
                    margin-bottom: 30px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    color: #2c3e50;
                    font-size: 2.5em;
                    font-weight: 300;
                }}
                .header p {{
                    color: #7f8c8d;
                    margin: 10px 0 0 0;
                    font-size: 1.1em;
                }}
                .summary-stats {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                .summary-card {{
                    background: rgba(255, 255, 255, 0.95);
                    padding: 25px;
                    border-radius: 15px;
                    text-align: center;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                    transition: transform 0.3s ease;
                }}
                .summary-card:hover {{
                    transform: translateY(-5px);
                }}
                .summary-number {{
                    font-size: 3em;
                    font-weight: bold;
                    color: #3498db;
                    margin: 10px 0;
                }}
                .summary-label {{
                    color: #7f8c8d;
                    font-size: 1.1em;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                .airports-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                    gap: 25px;
                }}
                .airport-card {{
                    background: rgba(255, 255, 255, 0.95);
                    padding: 25px;
                    border-radius: 15px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                    transition: all 0.3s ease;
                }}
                .airport-card:hover {{
                    transform: translateY(-3px);
                    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
                }}
                .airport-card h3 {{
                    margin: 0 0 20px 0;
                    color: #2c3e50;
                    font-size: 1.4em;
                    font-weight: 600;
                }}
                .airport-stats {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 15px;
                }}
                .stat {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 10px;
                    background: rgba(52, 152, 219, 0.1);
                    border-radius: 8px;
                }}
                .stat .label {{
                    color: #7f8c8d;
                    font-weight: 500;
                }}
                .stat .value {{
                    color: #2c3e50;
                    font-weight: bold;
                    font-size: 1.1em;
                }}
                .no-activity {{
                    opacity: 0.7;
                    background: rgba(255, 255, 255, 0.8);
                }}
                .active {{
                    border-left: 5px solid #27ae60;
                }}
                .no-activity {{
                    border-left: 5px solid #e74c3c;
                }}
                .refresh-info {{
                    text-align: center;
                    color: rgba(255, 255, 255, 0.8);
                    margin-top: 30px;
                    font-size: 0.9em;
                }}
                @media (max-width: 768px) {{
                    .airports-grid {{
                        grid-template-columns: 1fr;
                    }}
                    .airport-stats {{
                        grid-template-columns: 1fr;
                    }}
                    .summary-stats {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🛩️ VATSIM Traffic Dashboard</h1>
                    <p>Real-time air traffic movements across Australian airports</p>
                </div>
                
                <div class="summary-stats">
                    <div class="summary-card">
                        <div class="summary-label">Total Movements</div>
                        <div class="summary-number">{total_movements}</div>
                    </div>
                    <div class="summary-card">
                        <div class="summary-label">Total Arrivals</div>
                        <div class="summary-number">{total_arrivals}</div>
                    </div>
                    <div class="summary-card">
                        <div class="summary-label">Total Departures</div>
                        <div class="summary-number">{total_departures}</div>
                    </div>
                    <div class="summary-card">
                        <div class="summary-label">Active Airports</div>
                        <div class="summary-number">{len([a for a in summary.get("airports", {}).values() if a.get("total_movements", 0) > 0])}</div>
                    </div>
                </div>
                
                <div class="airports-grid">
                    {airports_html}
                </div>
                
                <div class="refresh-info">
                    <p>Data updates automatically every 30 seconds • Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                </div>
            </div>
            
            <script>
                // Auto-refresh every 30 seconds
                setTimeout(function() {{
                    location.reload();
                }}, 30000);
            </script>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Error generating traffic dashboard: {e}")
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>VATSIM Traffic Dashboard - Error</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 50px; text-align: center; }}
                .error {{ color: #e74c3c; font-size: 1.2em; }}
            </style>
        </head>
        <body>
            <h1>🛩️ VATSIM Traffic Dashboard</h1>
            <div class="error">
                <p>Error loading traffic data: {str(e)}</p>
                <p>Please try refreshing the page or check the server logs.</p>
            </div>
        </body>
        </html>
        """

@app.get("/graph-dashboard", response_class=HTMLResponse)
async def graph_dashboard(db: Session = Depends(get_db)):
    """Graph dashboard for Australia's 5 largest airports"""
    try:
        # Australia's 5 largest airports by passenger traffic
        major_airports = ['YSSY', 'YMML', 'YBBN', 'YPPH', 'YBCG']
        airport_names = {
            'YSSY': 'Sydney Airport',
            'YMML': 'Melbourne Airport', 
            'YBBN': 'Brisbane Airport',
            'YPPH': 'Perth Airport',
            'YBCG': 'Gold Coast Airport'
        }
        
        # Get traffic data for each airport
        traffic_analysis = get_traffic_analysis_service(db)
        airport_data = {}
        
        for icao in major_airports:
            # Get movements for last 7 days
            movements = traffic_analysis.get_movements_by_airport(icao, 168)  # 7 days * 24 hours
            airport_data[icao] = {
                'name': airport_names.get(icao, icao),
                'movements': len(movements),
                'arrivals': len([m for m in movements if m.get('movement_type') == 'arrival']),
                'departures': len([m for m in movements if m.get('movement_type') == 'departure']),
                'recent_movements': movements[:10]  # Last 10 movements for timeline
            }
        
        # Prepare chart data
        chart_labels = [airport_data[icao]['name'] for icao in major_airports]
        total_movements = [airport_data[icao]['movements'] for icao in major_airports]
        arrivals = [airport_data[icao]['arrivals'] for icao in major_airports]
        departures = [airport_data[icao]['departures'] for icao in major_airports]
        
        # Create timeline data for recent movements
        timeline_data = []
        for icao in major_airports:
            for movement in airport_data[icao]['recent_movements']:
                timeline_data.append({
                    'airport': airport_data[icao]['name'],
                    'callsign': movement.get('callsign', 'Unknown'),
                    'type': movement.get('movement_type', 'Unknown'),
                    'time': movement.get('timestamp', ''),
                    'aircraft': movement.get('aircraft_type', 'Unknown')
                })
        
        # Sort timeline by timestamp
        timeline_data.sort(key=lambda x: x['time'], reverse=True)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Australia Airport Traffic Graphs</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                }}
                .container {{
                    max-width: 1400px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: rgba(255, 255, 255, 0.95);
                    padding: 30px;
                    border-radius: 15px;
                    margin-bottom: 30px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    color: #2c3e50;
                    font-size: 2.5em;
                    font-weight: 300;
                }}
                .header p {{
                    color: #7f8c8d;
                    margin: 10px 0 0 0;
                    font-size: 1.1em;
                }}
                .charts-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 30px;
                    margin-bottom: 30px;
                }}
                .chart-container {{
                    background: rgba(255, 255, 255, 0.95);
                    padding: 25px;
                    border-radius: 15px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                }}
                .chart-title {{
                    text-align: center;
                    color: #2c3e50;
                    font-size: 1.3em;
                    font-weight: 600;
                    margin-bottom: 20px;
                }}
                .timeline {{
                    background: rgba(255, 255, 255, 0.95);
                    padding: 25px;
                    border-radius: 15px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                    margin-top: 30px;
                }}
                .timeline h3 {{
                    color: #2c3e50;
                    text-align: center;
                    margin-bottom: 20px;
                }}
                .timeline-item {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 15px;
                    margin: 10px 0;
                    background: rgba(52, 152, 219, 0.1);
                    border-radius: 8px;
                    border-left: 4px solid #3498db;
                }}
                .timeline-item.arrival {{
                    border-left-color: #27ae60;
                }}
                .timeline-item.departure {{
                    border-left-color: #e74c3c;
                }}
                .timeline-airport {{
                    font-weight: bold;
                    color: #2c3e50;
                }}
                .timeline-callsign {{
                    font-family: monospace;
                    color: #3498db;
                }}
                .timeline-type {{
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 0.8em;
                    font-weight: bold;
                }}
                .timeline-type.arrival {{
                    background: #27ae60;
                    color: white;
                }}
                .timeline-type.departure {{
                    background: #e74c3c;
                    color: white;
                }}
                .timeline-time {{
                    color: #7f8c8d;
                    font-size: 0.9em;
                }}
                .no-data {{
                    text-align: center;
                    color: #7f8c8d;
                    font-style: italic;
                    padding: 40px;
                }}
                .refresh-info {{
                    text-align: center;
                    color: rgba(255, 255, 255, 0.8);
                    margin-top: 30px;
                    font-size: 0.9em;
                }}
                @media (max-width: 768px) {{
                    .charts-grid {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Australia Airport Traffic Graphs</h1>
                    <p>Real-time traffic data for Australia's 5 largest airports</p>
                </div>
                
                <div class="charts-grid">
                    <div class="chart-container">
                        <div class="chart-title">Total Movements (Last 7 Days)</div>
                        <canvas id="movementsChart"></canvas>
                    </div>
                    
                    <div class="chart-container">
                        <div class="chart-title">Arrivals vs Departures</div>
                        <canvas id="comparisonChart"></canvas>
                    </div>
                </div>
                
                <div class="timeline">
                    <h3>🛩️ Recent Movements Timeline</h3>
                    <div id="timeline-content">
                        {generate_timeline_html(timeline_data)}
                    </div>
                </div>
                
                <div class="refresh-info">
                    <p>Data updates automatically every 30 seconds • Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                </div>
            </div>
            
            <script>
                // Chart 1: Total Movements
                const movementsCtx = document.getElementById('movementsChart').getContext('2d');
                new Chart(movementsCtx, {{
                    type: 'bar',
                    data: {{
                        labels: {chart_labels},
                        datasets: [{{
                            label: 'Total Movements',
                            data: {total_movements},
                            backgroundColor: 'rgba(52, 152, 219, 0.8)',
                            borderColor: 'rgba(52, 152, 219, 1)',
                            borderWidth: 2
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                display: false
                            }}
                        }},
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                ticks: {{
                                    stepSize: 1
                                }}
                            }}
                        }}
                    }}
                }});
                
                // Chart 2: Arrivals vs Departures
                const comparisonCtx = document.getElementById('comparisonChart').getContext('2d');
                new Chart(comparisonCtx, {{
                    type: 'bar',
                    data: {{
                        labels: {chart_labels},
                        datasets: [
                            {{
                                label: 'Arrivals',
                                data: {arrivals},
                                backgroundColor: 'rgba(39, 174, 96, 0.8)',
                                borderColor: 'rgba(39, 174, 96, 1)',
                                borderWidth: 2
                            }},
                            {{
                                label: 'Departures',
                                data: {departures},
                                backgroundColor: 'rgba(231, 76, 60, 0.8)',
                                borderColor: 'rgba(231, 76, 60, 1)',
                                borderWidth: 2
                            }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                display: true,
                                position: 'top'
                            }}
                        }},
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                ticks: {{
                                    stepSize: 1
                                }}
                            }}
                        }}
                    }}
                }});
                
                // Auto-refresh every 30 seconds
                setTimeout(function() {{
                    location.reload();
                }}, 30000);
            </script>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Error generating graph dashboard: {e}")
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Australia Airport Traffic Graphs - Error</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 50px; text-align: center; }}
                .error {{ color: #e74c3c; font-size: 1.2em; }}
            </style>
        </head>
        <body>
            <h1>📊 Australia Airport Traffic Graphs</h1>
            <div class="error">
                <p>Error loading graph data: {str(e)}</p>
                <p>Please try refreshing the page or check the server logs.</p>
            </div>
        </body>
        </html>
        """

def generate_timeline_html(timeline_data):
    """Generate HTML for timeline of recent movements"""
    if not timeline_data:
        return '<div class="no-data">No recent movements detected</div>'
    
    html = ''
    for movement in timeline_data[:20]:  # Show last 20 movements
        movement_type = movement['type']
        type_class = movement_type
        type_label = movement_type.title()
        
        # Format timestamp
        time_str = movement['time']
        if time_str:
            try:
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                time_str = dt.strftime("%m-%d %H:%M UTC")
            except:
                pass
        
        html += f"""
        <div class="timeline-item {type_class}">
            <div>
                <span class="timeline-airport">{movement['airport']}</span>
                <span class="timeline-callsign">{movement['callsign']}</span>
                <span class="timeline-type {type_class}">{type_label}</span>
            </div>
            <div class="timeline-time">{time_str}</div>
        </div>
        """
    
    return html

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 