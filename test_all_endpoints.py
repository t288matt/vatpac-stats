#!/usr/bin/env python3
"""
Comprehensive Endpoint Testing Script
Tests all API endpoints in the VATSIM Data Collection System
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8001"

def test_endpoint(method, endpoint, data=None, description=""):
    """Test a single endpoint and return results"""
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}")
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{endpoint}", json=data)
        
        if response.status_code == 200:
            result = response.json()
            return {
                "status": "✅ PASS",
                "endpoint": endpoint,
                "method": method,
                "description": description,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "data_preview": str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
            }
        else:
            return {
                "status": "❌ FAIL",
                "endpoint": endpoint,
                "method": method,
                "description": description,
                "error": f"HTTP {response.status_code}: {response.text[:200]}"
            }
    except Exception as e:
        return {
            "status": "💥 ERROR",
            "endpoint": endpoint,
            "method": "GET",
            "description": description,
            "error": str(e)[:200]
        }

def main():
    """Test all endpoints"""
    print("🚀 VATSIM DATA COLLECTION SYSTEM - COMPREHENSIVE ENDPOINT TESTING")
    print("=" * 80)
    print(f"Testing started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Define all endpoints to test
    endpoints = [
        # System Status Endpoints
        ("GET", "/", "Root Status"),
        ("GET", "/api/status", "System Health"),
        ("GET", "/api/network/status", "Network Status"),
        ("GET", "/api/database/status", "Database Health"),
        
        # Flight Data Endpoints
        ("GET", "/api/flights?limit=3", "All Flights"),
        ("GET", "/api/flights/ANZ103", "Specific Flight"),
        ("GET", "/api/flights/ANZ103/track", "Flight Track"),
        ("GET", "/api/flights/ANZ103/stats", "Flight Stats"),
        ("GET", "/api/flights/memory", "Memory Flights"),
        
        # Controller & ATC Endpoints
        ("GET", "/api/controllers?limit=3", "All Controllers"),
        ("GET", "/api/atc-positions?limit=3", "ATC Positions"),
        ("GET", "/api/atc-positions/by-controller-id", "Controller Positions by ID"),
        
        # Transceiver Endpoints
        ("GET", "/api/transceivers?limit=3", "All Transceivers"),
        
        # Filter & Configuration Endpoints
        ("GET", "/api/filter/flight/status", "Flight Filter Status"),
        ("GET", "/api/filter/boundary/status", "Geographic Filter Status"),
        ("GET", "/api/filter/boundary/info", "Geographic Filter Info"),
        
        # Analytics & Performance Endpoints
        ("GET", "/api/analytics/flights", "Flight Analytics"),
        ("GET", "/api/performance/metrics", "Performance Metrics"),
        ("POST", "/api/performance/optimize", "Trigger Optimization"),
        
        # Database & System Endpoints
        ("GET", "/api/database/tables", "Database Tables"),
        ("POST", "/api/database/query", "Custom Database Query"),
        
        # VATSIM System Endpoints
        ("GET", "/api/vatsim/ratings", "VATSIM Ratings"),
    ]
    
    # Test each endpoint
    results = []
    for method, endpoint, description in endpoints:
        if method == "POST" and endpoint == "/api/database/query":
            # Test with a simple query
            data = {"query": "SELECT COUNT(*) as total FROM flights", "limit": 10}
            result = test_endpoint(method, endpoint, data, description)
        elif method == "POST" and endpoint == "/api/performance/optimize":
            result = test_endpoint(method, endpoint, {}, description)
        else:
            result = test_endpoint(method, endpoint, None, description)
        
        results.append(result)
        print(f"{result['status']} {endpoint:<50} {description}")
    
    # Summary
    print()
    print("=" * 80)
    print("📊 TESTING SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r['status'] == "✅ PASS")
    failed = sum(1 for r in results if r['status'] == "❌ FAIL")
    errors = sum(1 for r in results if r['status'] == "💥 ERROR")
    total = len(results)
    
    print(f"Total Endpoints Tested: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"💥 Errors: {errors}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    # Show failed endpoints
    if failed > 0 or errors > 0:
        print()
        print("🔍 FAILED ENDPOINTS:")
        for result in results:
            if result['status'] != "✅ PASS":
                print(f"  {result['status']} {result['endpoint']}: {result.get('error', 'Unknown error')}")
    
    print()
    print(f"Testing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()

