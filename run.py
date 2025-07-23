#!/usr/bin/env python3
"""
ATC Position Recommendation Engine - Startup Script
"""

import uvicorn
import os
import sys

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🚁 Starting ATC Position Recommendation Engine...")
    print("📊 Backend API will be available at: http://localhost:8001")
    print("📈 Dashboard will be available at: http://localhost:8001/frontend/index.html")
    print("📚 API Documentation at: http://localhost:8001/docs")
    print("📄 Development Plan at: http://localhost:8000/development_plan.md")
    print("\nPress Ctrl+C to stop the server")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    ) 