#!/usr/bin/env python3
"""
Container API Testing Script
Run this inside the Docker container for detailed testing
"""

import requests
import json
import time
from datetime import datetime

def test_endpoint_detailed(url: str, description: str = ""):
    """Test endpoint with detailed error information"""
    print(f"🔍 Testing: {description}")
    print(f"   URL: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
        
        if response.status_code == 200:
            print(f"   ✅ Success")
            try:
                data = response.json()
                if isinstance(data, dict):
                    print(f"   Response Keys: {list(data.keys())}")
                    if "total" in data:
                        print(f"   Total Items: {data['total']}")
                    if "status" in data:
                        print(f"   Status: {data['status']}")
            except json.JSONDecodeError:
                print(f"   Response Size: {len(response.content)} bytes")
        else:
            print(f"   ❌ Failed with status {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error Details: {json.dumps(error_data, indent=2)}")
            except json.JSONDecodeError:
                print(f"   Error Text: {response.text[:200]}...")
                
    except requests.exceptions.Timeout:
        print(f"   ❌ Timeout")
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection Error")
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
    
    print()

def main():
    """Main function"""
    base_url = "http://localhost:8001"
    
    print("🐳 Container API Testing (Detailed)")
    print("=" * 60)
    
    # Test working endpoints first
    working_endpoints = [
        ("/api/status", "System Status"),
        ("/api/atc-positions", "ATC Positions"),
        ("/api/flights", "Active Flights"),
        ("/api/database/status", "Database Status"),
        ("/api/performance/metrics", "Performance Metrics"),
    ]
    
    print("✅ Testing Working Endpoints:")
    for endpoint, description in working_endpoints:
        test_endpoint_detailed(f"{base_url}{endpoint}", description)
    
    # Test failing endpoints with detailed error info
    failing_endpoints = [
        ("/api/network/status", "Network Status"),
        ("/api/health/comprehensive", "Health Check"),
        ("/api/flights/memory", "Flight Memory"),
        ("/api/traffic/movements/KJFK", "Traffic Movements KJFK"),
        ("/api/traffic/trends/KJFK", "Traffic Trends KJFK"),
        ("/traffic-dashboard", "Traffic Dashboard"),
    ]
    
    print("❌ Testing Failing Endpoints (with error details):")
    for endpoint, description in failing_endpoints:
        test_endpoint_detailed(f"{base_url}{endpoint}", description)
    
    print("🏁 Container testing completed!")

if __name__ == "__main__":
    main() 