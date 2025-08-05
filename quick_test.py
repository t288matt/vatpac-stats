#!/usr/bin/env python3
"""
Quick API Test Script
Simple endpoint testing without curl
"""

import requests
import json
import sys
from datetime import datetime

def test_endpoint(url, description=""):
    """Test a single endpoint"""
    try:
        print(f"🔍 Testing: {description}")
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            print(f"✅ {url} - Status: {response.status_code}")
            
            # Try to parse JSON
            try:
                data = response.json()
                if isinstance(data, dict):
                    print(f"   📊 Response keys: {list(data.keys())}")
                    if "total" in data:
                        print(f"   📈 Total items: {data['total']}")
                    if "timestamp" in data:
                        print(f"   ⏰ Timestamp: {data['timestamp']}")
                else:
                    print(f"   📄 Response type: {type(data)}")
            except json.JSONDecodeError:
                print(f"   📄 Response size: {len(response.content)} bytes")
                
        else:
            print(f"❌ {url} - Status: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print(f"❌ {url} - Connection failed (server not running?)")
    except requests.exceptions.Timeout:
        print(f"❌ {url} - Timeout")
    except Exception as e:
        print(f"❌ {url} - Error: {str(e)}")
    
    print()

def main():
    """Main test function"""
    base_url = "http://localhost:8001"
    
    print("🚀 Quick API Test")
    print(f"📡 Testing endpoints at: {base_url}")
    print("=" * 50)
    
    # Test core endpoints
    endpoints = [
        ("/api/status", "System Status"),
        ("/api/network/status", "Network Status"),
        ("/api/atc-positions", "ATC Positions"),
        ("/api/flights", "Active Flights"),
        ("/api/health/comprehensive", "Health Check"),
        ("/api/database/status", "Database Status"),
        ("/api/performance/metrics", "Performance Metrics"),
    ]
    
    for endpoint, description in endpoints:
        test_endpoint(f"{base_url}{endpoint}", description)
    
    # Test with some parameters
    print("🔧 Testing endpoints with parameters:")
    test_endpoint(f"{base_url}/api/traffic/movements/KJFK", "Traffic Movements (KJFK)")
    test_endpoint(f"{base_url}/api/airports/KJFK/coordinates", "Airport Coordinates (KJFK)")
    
    print("✅ Quick test completed!")

if __name__ == "__main__":
    main() 