#!/usr/bin/env python3
"""
Simple API Status Test
Quick test without curl
"""

import requests
import json
from datetime import datetime

def test_simple():
    """Simple test of working endpoints"""
    base_url = "http://localhost:8001"
    
    print("🔍 Simple API Test (No curl)")
    print("=" * 40)
    
    # Test the main status endpoint
    try:
        response = requests.get(f"{base_url}/api/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ API Status Endpoint Working")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Timestamp: {data.get('timestamp', 'unknown')}")
            print(f"   ATC Positions: {data.get('atc_positions_count', 0)}")
            print(f"   Flights: {data.get('flights_count', 0)}")
        else:
            print(f"❌ API Status failed: {response.status_code}")
    except Exception as e:
        print(f"❌ API Status error: {str(e)}")
    
    print()
    
    # Test performance metrics
    try:
        response = requests.get(f"{base_url}/api/performance/metrics", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Performance Metrics Working")
            print(f"   Timestamp: {data.get('timestamp', 'unknown')}")
        else:
            print(f"❌ Performance Metrics failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Performance Metrics error: {str(e)}")
    
    print()
    print("🏁 Test completed without curl")

if __name__ == "__main__":
    test_simple() 