#!/usr/bin/env python3
"""
VATSIM Data Collection System - Startup Script
"""

import uvicorn
import os
import sys
import socket
import logging

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_port_availability(host: str, port: int) -> bool:
    """Check if a port is available for binding"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            return result != 0  # Port is available if connection fails
    except Exception:
        return False

def setup_startup_logging():
    """Setup logging for startup process"""
    try:
        # Try to create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            try:
                os.makedirs('logs', exist_ok=True)
            except PermissionError:
                pass  # Continue without logs directory if we can't create it
        
        # Setup logging with fallback for permission issues
        handlers = [logging.StreamHandler(sys.stdout)]
        
        # Try to add file handler, but fallback gracefully if there are permission issues
        try:
            if os.path.exists('logs') and os.access('logs', os.W_OK):
                handlers.append(logging.FileHandler('logs/startup.log'))
            else:
                # Use NullHandler if we can't write to logs directory
                handlers.append(logging.NullHandler())
        except (PermissionError, OSError):
            # If we can't create file handler, just use console logging
            handlers.append(logging.NullHandler())
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
        
        logger = logging.getLogger(__name__)
        logger.info("Startup logging configured successfully")
        return logger
        
    except Exception as e:
        # Fallback to basic console logging if setup fails
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to setup advanced logging, using console only: {e}")
        return logger

if __name__ == "__main__":
    logger = setup_startup_logging()
    
    print("🚁 Starting VATSIM Data Collection System...")
    print("📊 Backend API will be available at: http://localhost:8001")
    print("📚 API Documentation at: http://localhost:8001/docs")
    print("📈 Grafana Dashboards: Configure Grafana to connect to API endpoints")
    print("🔧 Error Monitoring: Centralized error handling enabled")
    print("\nPress Ctrl+C to stop the server")
    
    # Check if we're in production (Docker) or development
    is_production = os.getenv("PRODUCTION_MODE", "false").lower() == "true"
    
    # Check port availability before starting
    host = "0.0.0.0"
    port = 8001
    
    logger.info(f"🔍 Checking port {port} availability on {host}...")
    
    if not check_port_availability(host, port):
        error_msg = f"🚨 CRITICAL: Port {port} is already in use on {host}"
        logger.critical(error_msg)
        logger.critical("🚨 CRITICAL: This usually means:")
        logger.critical("   - Another instance of the application is running")
        logger.critical("   - Another service is using port 8001")
        logger.critical("   - Docker container is already running on this port")
        logger.critical("🚨 CRITICAL: Please check:")
        logger.critical("   - Run 'docker-compose ps' to see running containers")
        logger.critical("   - Run 'netstat -ano | findstr :8001' to see what's using the port")
        logger.critical("   - Stop conflicting services or use a different port")
        
        print(f"\n❌ {error_msg}")
        print("Check the logs above for detailed information")
        sys.exit(1)
    
    logger.info(f"✅ Port {port} is available on {host}")
    
    try:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=not is_production,  # Disable reload in production
            log_level="info"
        )
    except OSError as e:
        if "address already in use" in str(e).lower() or "errno 98" in str(e) or "errno 10048" in str(e):
            error_msg = f"🚨 CRITICAL: Port binding failed - port {port} is already in use"
            logger.critical(error_msg)
            logger.critical(f"🚨 CRITICAL: OS Error: {e}")
            logger.critical("🚨 CRITICAL: This indicates a race condition or port conflict")
            logger.critical("🚨 CRITICAL: Application cannot start without available port")
            
            print(f"\n❌ {error_msg}")
            print("Check the logs above for detailed information")
            sys.exit(1)
        else:
            error_msg = f"🚨 CRITICAL: Unexpected OS error during startup: {e}"
            logger.critical(error_msg)
            print(f"\n❌ {error_msg}")
            sys.exit(1)
    except Exception as e:
        error_msg = f"🚨 CRITICAL: Unexpected error during startup: {e}"
        logger.critical(error_msg)
        print(f"\n❌ {error_msg}")
        sys.exit(1) 