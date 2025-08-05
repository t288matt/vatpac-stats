#!/usr/bin/env python3
"""
API Test Summary - No curl used
Demonstrates testing endpoints using pure Python
"""

import requests
import json
from datetime import datetime

def test_api_endpoints():
    """Test API endpoints without using curl"""
    base_url = "http://localhost:8001"
    
    print("🐳 Docker API Testing Summary")
    print("🐍 Pure Python implementation (No curl)")
    print("=" * 60)
    
    endpoints = [
        ("/api/status", "System Status"),
        ("/api/performance/metrics", "Performance Metrics"),
        ("/api/database/status", "Database Status"),
        ("/api/database/tables", "Database Tables"),
    ]
    
    results = []
    
    for endpoint, description in endpoints:
        url = f"{base_url}{endpoint}"
        print(f"🔍 Testing: {description}")
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ {endpoint} - Working")
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        if "status" in data:
                            print(f"   Status: {data['status']}")
                        if "total" in data:
                            print(f"   Total items: {data['total']}")
                        if "timestamp" in data:
                            print(f"   Timestamp: {data['timestamp']}")
                except json.JSONDecodeError:
                    print(f"   Response size: {len(response.content)} bytes")
            else:
                print(f"❌ {endpoint} - Failed ({response.status_code})")
                
        except requests.exceptions.Timeout:
            print(f"❌ {endpoint} - Timeout")
        except requests.exceptions.ConnectionError:
            print(f"❌ {endpoint} - Connection Error")
        except Exception as e:
            print(f"❌ {endpoint} - Error: {str(e)}")
        
        print()
    
    print("📊 Summary:")
    print("✅ API testing completed without using curl")
    print("🐍 Used Python requests library instead")
    print("🐳 Tested within Docker environment")
    print(f"⏰ Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    test_api_endpoints() 