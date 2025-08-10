#!/usr/bin/env python3
"""
Simple script to run the comprehensive health check
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def main():
    try:
        from app.utils.health_monitor import HealthMonitor
        
        print("🔍 Running comprehensive health check...")
        print("=" * 50)
        
        hm = HealthMonitor()
        result = await hm.get_comprehensive_health_report()
        
        print("📊 COMPREHENSIVE HEALTH REPORT")
        print("=" * 50)
        
        # Print overall health score
        if 'overall_health' in result:
            score = result['overall_health']
            if score >= 90:
                status = "🟢 EXCELLENT"
            elif score >= 80:
                status = "🟡 GOOD"
            elif score >= 70:
                status = "🟠 FAIR"
            else:
                status = "🔴 POOR"
            
            print(f"Overall Health Score: {score:.1f}/100 {status}")
        
        # Print timestamp
        if 'timestamp' in result:
            print(f"Timestamp: {result['timestamp']}")
        
        print("\n📋 DETAILED STATUS:")
        print("-" * 30)
        
        # Print each component status
        components = [
            ('API Endpoints', 'api_endpoints'),
            ('Database', 'database'),
            ('System Resources', 'system_resources'),
            ('Data Freshness', 'data_freshness'),
            ('Cache Service', 'cache_service'),
            ('Services', 'services'),
            ('Error Monitoring', 'error_monitoring'),
            ('Data Service', 'data_service'),
            ('Monitoring Service', 'monitoring_service')
        ]
        
        for name, key in components:
            if key in result:
                status = result[key]
                if isinstance(status, dict):
                    if 'status' in status:
                        status_text = status['status']
                    elif 'connected' in status:
                        status_text = "connected" if status['connected'] else "disconnected"
                    elif 'healthy' in status:
                        status_text = "healthy" if status['healthy'] else "unhealthy"
                    else:
                        status_text = "unknown"
                else:
                    status_text = str(status)
                
                print(f"{name}: {status_text}")
        
        # Print error rates if available
        if 'error_rates' in result and result['error_rates']:
            print("\n⚠️ ERROR RATES:")
            print("-" * 20)
            for endpoint, rate in result['error_rates'].items():
                if rate > 0:
                    print(f"{endpoint}: {rate:.1f}%")
        
        # Print response times if available
        if 'average_response_times' in result and result['average_response_times']:
            print("\n⏱️ AVERAGE RESPONSE TIMES:")
            print("-" * 30)
            for endpoint, time in result['average_response_times'].items():
                print(f"{endpoint}: {time:.3f}s")
        
        print("\n" + "=" * 50)
        
    except Exception as e:
        print(f"❌ Error running health check: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
