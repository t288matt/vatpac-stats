#!/usr/bin/env python3
"""
VATSIM Data Collection System - Startup Script
"""

import uvicorn
import os
import sys

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🚁 Starting VATSIM Data Collection System...")
    print("📊 Backend API will be available at: http://localhost:8001")
    print("📚 API Documentation at: http://localhost:8001/docs")
    print("📈 Grafana Dashboards: Configure Grafana to connect to API endpoints")
    print("🔧 Error Monitoring: Centralized error handling enabled")
    print("\nPress Ctrl+C to stop the server")
    
    # Check if we're in production (Docker) or development
    is_production = os.getenv("PRODUCTION_MODE", "false").lower() == "true"
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=not is_production,  # Disable reload in production
        log_level="info"
    ) 