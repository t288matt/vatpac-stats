#!/usr/bin/env python3
"""
Production monitoring script for zero minutes bug fix validation.

This script checks if the zero minutes bug fix is working by monitoring:
1. Recent flight summaries for zero-minute flights
2. Flight duration accuracy
3. Processing patterns
4. System health

Usage:
    python check_zero_minutes_fix.py [--hours 24] [--alert-threshold 5]
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import asyncio
import asyncpg
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('zero_minutes_monitor.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class MonitoringResult:
    """Results from monitoring check"""
    check_name: str
    status: str  # 'PASS', 'FAIL', 'WARN'
    message: str
    details: Optional[Dict] = None

class ZeroMinutesFixMonitor:
    """Monitor for zero minutes bug fix effectiveness"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.connection = None
    
    async def connect(self):
        """Connect to database"""
        try:
            self.connection = await asyncpg.connect(self.database_url)
            logger.info("[OK] Connected to database")
        except Exception as e:
            logger.error(f"[ERROR] Failed to connect to database: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from database"""
        if self.connection:
            await self.connection.close()
            logger.info("[OK] Disconnected from database")
    
    async def check_recent_zero_minute_flights(self, hours: int = 24) -> MonitoringResult:
        """Check for zero-minute flights created in recent hours"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = """
                SELECT 
                    COUNT(*) as zero_minute_count,
                    COUNT(CASE WHEN created_at >= $1 THEN 1 END) as recent_zero_minute_count,
                    MIN(created_at) as first_zero_minute,
                    MAX(created_at) as last_zero_minute
                FROM flight_summaries 
                WHERE time_online_minutes = 0 
                  AND completion_time > logon_time
                  AND created_at >= $1
            """
            
            row = await self.connection.fetchrow(query, cutoff_time)
            
            zero_count = row['recent_zero_minute_count']
            last_zero = row['last_zero_minute']
            
            if zero_count == 0:
                return MonitoringResult(
                    check_name="Recent Zero-Minute Flights",
                    status="PASS",
                    message=f"[PASS] No zero-minute flights in last {hours} hours",
                    details={"count": 0, "hours_checked": hours}
                )
            else:
                return MonitoringResult(
                    check_name="Recent Zero-Minute Flights", 
                    status="FAIL",
                    message=f"[FAIL] {zero_count} zero-minute flights in last {hours} hours",
                    details={
                        "count": zero_count,
                        "last_created": last_zero,
                        "hours_checked": hours
                    }
                )
                
        except Exception as e:
            return MonitoringResult(
                check_name="Recent Zero-Minute Flights",
                status="FAIL", 
                message=f"[ERROR] Database error: {e}",
                details={"error": str(e)}
            )
    
    async def check_flight_duration_accuracy(self, hours: int = 24) -> MonitoringResult:
        """Check if flight durations are calculated accurately"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = """
                SELECT 
                    callsign,
                    cid,
                    departure,
                    arrival,
                    logon_time,
                    completion_time,
                    time_online_minutes,
                    created_at,
                    EXTRACT(EPOCH FROM (completion_time - logon_time))/60 as actual_minutes
                FROM flight_summaries 
                WHERE created_at >= $1
                  AND completion_time > logon_time
                  AND time_online_minutes > 0
                ORDER BY created_at DESC 
                LIMIT 50
            """
            
            rows = await self.connection.fetch(query, cutoff_time)
            
            if not rows:
                return MonitoringResult(
                    check_name="Flight Duration Accuracy",
                    status="WARN",
                    message="[WARN] No recent flights to check",
                    details={"flights_checked": 0}
                )
            
            # Check for significant discrepancies
            discrepancies = []
            total_checked = 0
            
            for row in rows:
                total_checked += 1
                actual_minutes = float(row['actual_minutes'])
                recorded_minutes = row['time_online_minutes']
                
                # Allow 5% tolerance for timing differences
                tolerance = max(5, actual_minutes * 0.05)
                diff = abs(actual_minutes - recorded_minutes)
                
                if diff > tolerance:
                    discrepancies.append({
                        'callsign': row['callsign'],
                        'actual': actual_minutes,
                        'recorded': recorded_minutes,
                        'diff': diff
                    })
            
            if len(discrepancies) == 0:
                return MonitoringResult(
                    check_name="Flight Duration Accuracy",
                    status="PASS",
                    message=f"[PASS] All {total_checked} flights have accurate durations",
                    details={"flights_checked": total_checked, "discrepancies": 0}
                )
            else:
                return MonitoringResult(
                    check_name="Flight Duration Accuracy",
                    status="WARN",
                    message=f"[WARN] {len(discrepancies)} flights have duration discrepancies",
                    details={
                        "flights_checked": total_checked,
                        "discrepancies": len(discrepancies),
                        "examples": discrepancies[:5]  # Show first 5
                    }
                )
                
        except Exception as e:
            return MonitoringResult(
                check_name="Flight Duration Accuracy",
                status="FAIL",
                message=f"[ERROR] Database error: {e}",
                details={"error": str(e)}
            )
    
    async def check_processing_patterns(self, hours: int = 24) -> MonitoringResult:
        """Check if processing patterns look normal"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Check for flights with very short durations (potential issues)
            query = """
                SELECT COUNT(*) as short_duration_count
                FROM flight_summaries 
                WHERE created_at >= $1
                  AND completion_time > logon_time
                  AND time_online_minutes BETWEEN 1 AND 5
                  AND EXTRACT(EPOCH FROM (completion_time - logon_time))/60 > 10
            """
            
            row = await self.connection.fetchrow(query, cutoff_time)
            short_duration_count = row['short_duration_count']
            
            # Check total flights processed
            total_query = """
                SELECT COUNT(*) as total_flights
                FROM flight_summaries 
                WHERE created_at >= $1
                  AND completion_time > logon_time
            """
            
            total_row = await self.connection.fetchrow(total_query, cutoff_time)
            total_flights = total_row['total_flights']
            
            short_percentage = (short_duration_count / total_flights * 100) if total_flights > 0 else 0
            
            if short_percentage < 10:  # Less than 10% short duration flights is normal
                return MonitoringResult(
                    check_name="Processing Patterns",
                    status="PASS",
                    message=f"[PASS] Processing patterns look normal ({short_percentage:.1f}% short durations)",
                    details={
                        "short_duration_flights": short_duration_count,
                        "total_flights": total_flights,
                        "percentage": short_percentage
                    }
                )
            else:
                return MonitoringResult(
                    check_name="Processing Patterns",
                    status="WARN",
                    message=f"[WARN] High percentage of short duration flights ({short_percentage:.1f}%)",
                    details={
                        "short_duration_flights": short_duration_count,
                        "total_flights": total_flights,
                        "percentage": short_percentage
                    }
                )
                
        except Exception as e:
            return MonitoringResult(
                check_name="Processing Patterns",
                status="FAIL",
                message=f"[ERROR] Database error: {e}",
                details={"error": str(e)}
            )
    
    async def check_system_health(self) -> MonitoringResult:
        """Check overall system health"""
        try:
            # Check if we can query recent data
            query = """
                SELECT 
                    COUNT(*) as recent_flights,
                    MAX(created_at) as latest_created,
                    MIN(created_at) as earliest_created
                FROM flight_summaries 
                WHERE created_at >= NOW() - INTERVAL '24 hours'
            """
            
            row = await self.connection.fetchrow(query)
            
            recent_flights = row['recent_flights']
            latest_created = row['latest_created']
            
            if recent_flights == 0:
                return MonitoringResult(
                    check_name="System Health",
                    status="WARN",
                    message="[WARN] No flights processed in last 24 hours",
                    details={"recent_flights": 0}
                )
            
            # Check if latest flight is recent (within 2 hours)
            if latest_created:
                time_since_latest = datetime.utcnow() - latest_created.replace(tzinfo=None)
                if time_since_latest.total_seconds() > 7200:  # 2 hours
                    return MonitoringResult(
                        check_name="System Health",
                        status="WARN",
                        message=f"[WARN] Latest flight is {time_since_latest} old",
                        details={
                            "recent_flights": recent_flights,
                            "latest_created": latest_created,
                            "time_since_latest": str(time_since_latest)
                        }
                    )
            
            return MonitoringResult(
                check_name="System Health",
                status="PASS",
                message=f"[PASS] System healthy - {recent_flights} flights in last 24h",
                details={
                    "recent_flights": recent_flights,
                    "latest_created": latest_created
                }
            )
            
        except Exception as e:
            return MonitoringResult(
                check_name="System Health",
                status="FAIL",
                message=f"[ERROR] System health check failed: {e}",
                details={"error": str(e)}
            )

async def run_monitoring(database_url: str, hours: int = 24, alert_threshold: int = 5) -> List[MonitoringResult]:
    """Run all monitoring checks"""
    monitor = ZeroMinutesFixMonitor(database_url)
    
    try:
        await monitor.connect()
        
        results = []
        
        # Run all checks
        logger.info(f"[MONITOR] Starting zero minutes fix monitoring (last {hours} hours)")
        
        results.append(await monitor.check_system_health())
        results.append(await monitor.check_recent_zero_minute_flights(hours))
        results.append(await monitor.check_flight_duration_accuracy(hours))
        results.append(await monitor.check_processing_patterns(hours))
        
        return results
        
    finally:
        await monitor.disconnect()

def print_results(results: List[MonitoringResult], alert_threshold: int):
    """Print monitoring results"""
    print("\n" + "="*80)
    print("ZERO MINUTES BUG FIX - PRODUCTION MONITORING REPORT")
    print("="*80)
    print(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print()
    
    # Summary
    pass_count = sum(1 for r in results if r.status == "PASS")
    warn_count = sum(1 for r in results if r.status == "WARN")
    fail_count = sum(1 for r in results if r.status == "FAIL")
    
    print(f"SUMMARY: {pass_count} PASS, {warn_count} WARN, {fail_count} FAIL")
    print()
    
    # Detailed results
    for result in results:
        print(f"{result.status} - {result.check_name}")
        print(f"   {result.message}")
        
        if result.details:
            for key, value in result.details.items():
                if isinstance(value, list) and len(value) > 3:
                    print(f"   {key}: {len(value)} items (showing first 3)")
                    for i, item in enumerate(value[:3]):
                        print(f"     {i+1}. {item}")
                else:
                    print(f"   {key}: {value}")
        print()
    
    # Overall status
    if fail_count > 0:
        print("[CRITICAL] Fix may not be working properly!")
        return 2
    elif warn_count >= alert_threshold:
        print("[WARNING] Multiple issues detected")
        return 1
    else:
        print("[HEALTHY] Zero minutes fix appears to be working")
        return 0

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Monitor zero minutes bug fix in production")
    parser.add_argument("--hours", type=int, default=24, 
                       help="Hours to look back for monitoring (default: 24)")
    parser.add_argument("--alert-threshold", type=int, default=5,
                       help="Number of warnings before alerting (default: 5)")
    parser.add_argument("--database-url", type=str,
                       default=os.getenv("DATABASE_URL", "postgresql://vatsim_user:vatsim_password@localhost:5432/vatsim_data"),
                       help="Database connection URL")
    
    args = parser.parse_args()
    
    # Run monitoring
    try:
        results = asyncio.run(run_monitoring(args.database_url, args.hours, args.alert_threshold))
        exit_code = print_results(results, args.alert_threshold)
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("Monitoring interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Monitoring failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
