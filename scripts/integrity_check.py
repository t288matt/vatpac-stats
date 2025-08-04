#!/usr/bin/env python3
"""
VATSIM API and PostgreSQL Database Integrity Check

This script performs comprehensive integrity checks between the VATSIM API
and the PostgreSQL database to ensure data consistency and identify
any discrepancies in the data pipeline.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json
import logging
from dataclasses import dataclass
from collections import defaultdict

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.config import get_config
from app.database import SessionLocal
from app.models import ATCPosition, Flight, Sector, TrafficMovement
from app.services.vatsim_service import VATSIMService, VATSIMData
from app.utils.logging import get_logger_for_module


@dataclass
class IntegrityCheckResult:
    """Result of an integrity check operation."""
    check_name: str
    status: str  # 'PASS', 'FAIL', 'WARNING'
    details: Dict[str, Any]
    timestamp: datetime
    error_message: Optional[str] = None


class IntegrityChecker:
    """
    Comprehensive integrity checker for VATSIM API and PostgreSQL database.
    
    This class performs various checks to ensure data consistency between
    the VATSIM API and the local database.
    """
    
    def __init__(self):
        """Initialize the integrity checker."""
        self.config = get_config()
        self.logger = get_logger_for_module(__name__)
        self.vatsim_service = VATSIMService()
        self.results: List[IntegrityCheckResult] = []
        
    async def run_all_checks(self) -> List[IntegrityCheckResult]:
        """
        Run all integrity checks.
        
        Returns:
            List[IntegrityCheckResult]: Results of all checks
        """
        self.logger.info("Starting comprehensive integrity checks")
        
        # Clear previous results
        self.results = []
        
        # Run all checks
        await self._check_vatsim_api_connectivity()
        await self._check_database_connectivity()
        await self._check_data_freshness()
        await self._check_atc_positions_integrity()
        await self._check_flights_integrity()
        await self._check_data_consistency()
        await self._check_performance_metrics()
        await self._check_data_quality()
        
        self.logger.info(f"Completed {len(self.results)} integrity checks")
        return self.results
    
    async def _check_vatsim_api_connectivity(self) -> None:
        """Check VATSIM API connectivity and response."""
        try:
            self.logger.info("Checking VATSIM API connectivity")
            
            # Test API connectivity
            api_status = await self.vatsim_service.get_api_status()
            
            if api_status["status"] == "healthy":
                # Fetch actual data
                vatsim_data = await self.vatsim_service.get_current_data()
                
                result = IntegrityCheckResult(
                    check_name="VATSIM API Connectivity",
                    status="PASS",
                    details={
                        "api_status": api_status,
                        "controllers_count": vatsim_data.total_controllers,
                        "flights_count": vatsim_data.total_flights,
                        "sectors_count": vatsim_data.total_sectors,
                        "response_time": api_status.get("response_time", 0)
                    },
                    timestamp=datetime.utcnow()
                )
            else:
                result = IntegrityCheckResult(
                    check_name="VATSIM API Connectivity",
                    status="FAIL",
                    details={"api_status": api_status},
                    timestamp=datetime.utcnow(),
                    error_message=f"API status: {api_status.get('status', 'unknown')}"
                )
                
        except Exception as e:
            result = IntegrityCheckResult(
                check_name="VATSIM API Connectivity",
                status="FAIL",
                details={},
                timestamp=datetime.utcnow(),
                error_message=str(e)
            )
        
        self.results.append(result)
    
    async def _check_database_connectivity(self) -> None:
        """Check database connectivity and basic operations."""
        try:
            self.logger.info("Checking database connectivity")
            
            db = SessionLocal()
            try:
                # Test basic database operations
                atc_count = db.query(ATCPosition).count()
                flights_count = db.query(Flight).count()
                sectors_count = db.query(Sector).count()
                
                result = IntegrityCheckResult(
                    check_name="Database Connectivity",
                    status="PASS",
                    details={
                        "atc_positions_count": atc_count,
                        "flights_count": flights_count,
                        "sectors_count": sectors_count,
                        "database_url": self.config.database.url.split("://")[0] + "://***"
                    },
                    timestamp=datetime.utcnow()
                )
                
            except Exception as e:
                result = IntegrityCheckResult(
                    check_name="Database Connectivity",
                    status="FAIL",
                    details={},
                    timestamp=datetime.utcnow(),
                    error_message=str(e)
                )
            finally:
                db.close()
                
        except Exception as e:
            result = IntegrityCheckResult(
                check_name="Database Connectivity",
                status="FAIL",
                details={},
                timestamp=datetime.utcnow(),
                error_message=str(e)
            )
        
        self.results.append(result)
    
    async def _check_data_freshness(self) -> None:
        """Check if data is fresh and up-to-date."""
        try:
            self.logger.info("Checking data freshness")
            
            # Get latest VATSIM data
            vatsim_data = await self.vatsim_service.get_current_data()
            
            # Check database for recent data
            db = SessionLocal()
            try:
                # Check for recent ATC positions (within last 5 minutes)
                recent_atc = db.query(ATCPosition).filter(
                    ATCPosition.last_seen >= datetime.utcnow() - timedelta(minutes=5)
                ).count()
                
                # Check for recent flights (within last 5 minutes)
                recent_flights = db.query(Flight).filter(
                    Flight.last_updated >= datetime.utcnow() - timedelta(minutes=5)
                ).count()
                
                # Calculate freshness metrics
                api_controllers = vatsim_data.total_controllers
                api_flights = vatsim_data.total_flights
                
                atc_freshness_ratio = recent_atc / max(api_controllers, 1)
                flights_freshness_ratio = recent_flights / max(api_flights, 1)
                
                if atc_freshness_ratio >= 0.8 and flights_freshness_ratio >= 0.8:
                    status = "PASS"
                elif atc_freshness_ratio >= 0.5 and flights_freshness_ratio >= 0.5:
                    status = "WARNING"
                else:
                    status = "FAIL"
                
                result = IntegrityCheckResult(
                    check_name="Data Freshness",
                    status=status,
                    details={
                        "api_controllers": api_controllers,
                        "api_flights": api_flights,
                        "recent_atc_positions": recent_atc,
                        "recent_flights": recent_flights,
                        "atc_freshness_ratio": round(atc_freshness_ratio, 3),
                        "flights_freshness_ratio": round(flights_freshness_ratio, 3)
                    },
                    timestamp=datetime.utcnow()
                )
                
            finally:
                db.close()
                
        except Exception as e:
            result = IntegrityCheckResult(
                check_name="Data Freshness",
                status="FAIL",
                details={},
                timestamp=datetime.utcnow(),
                error_message=str(e)
            )
        
        self.results.append(result)
    
    async def _check_atc_positions_integrity(self) -> None:
        """Check ATC positions data integrity."""
        try:
            self.logger.info("Checking ATC positions integrity")
            
            # Get VATSIM data
            vatsim_data = await self.vatsim_service.get_current_data()
            
            # Get database data
            db = SessionLocal()
            try:
                db_atc_positions = db.query(ATCPosition).filter(
                    ATCPosition.status == "online"
                ).all()
                
                # Create sets for comparison
                api_callsigns = {controller.callsign for controller in vatsim_data.controllers}
                db_callsigns = {atc.callsign for atc in db_atc_positions}
                
                # Find discrepancies
                missing_in_db = api_callsigns - db_callsigns
                extra_in_db = db_callsigns - api_callsigns
                
                # Check for data inconsistencies
                inconsistencies = []
                for controller in vatsim_data.controllers:
                    db_atc = next((atc for atc in db_atc_positions if atc.callsign == controller.callsign), None)
                    if db_atc:
                        if db_atc.facility != controller.facility:
                            inconsistencies.append(f"Facility mismatch for {controller.callsign}")
                        if db_atc.frequency != controller.frequency:
                            inconsistencies.append(f"Frequency mismatch for {controller.callsign}")
                
                # Determine status
                if len(missing_in_db) == 0 and len(extra_in_db) == 0 and len(inconsistencies) == 0:
                    status = "PASS"
                elif len(missing_in_db) <= 2 and len(extra_in_db) <= 2 and len(inconsistencies) <= 2:
                    status = "WARNING"
                else:
                    status = "FAIL"
                
                result = IntegrityCheckResult(
                    check_name="ATC Positions Integrity",
                    status=status,
                    details={
                        "api_controllers_count": len(api_callsigns),
                        "db_controllers_count": len(db_callsigns),
                        "missing_in_db": list(missing_in_db),
                        "extra_in_db": list(extra_in_db),
                        "inconsistencies": inconsistencies
                    },
                    timestamp=datetime.utcnow()
                )
                
            finally:
                db.close()
                
        except Exception as e:
            result = IntegrityCheckResult(
                check_name="ATC Positions Integrity",
                status="FAIL",
                details={},
                timestamp=datetime.utcnow(),
                error_message=str(e)
            )
        
        self.results.append(result)
    
    async def _check_flights_integrity(self) -> None:
        """Check flights data integrity."""
        try:
            self.logger.info("Checking flights integrity")
            
            # Get VATSIM data
            vatsim_data = await self.vatsim_service.get_current_data()
            
            # Get database data
            db = SessionLocal()
            try:
                db_flights = db.query(Flight).filter(
                    Flight.status == "active"
                ).all()
                
                # Create sets for comparison
                api_callsigns = {flight.callsign for flight in vatsim_data.flights}
                db_callsigns = {flight.callsign for flight in db_flights}
                
                # Find discrepancies
                missing_in_db = api_callsigns - db_callsigns
                extra_in_db = db_callsigns - api_callsigns
                
                # Check for data inconsistencies
                inconsistencies = []
                for flight in vatsim_data.flights:
                    db_flight = next((f for f in db_flights if f.callsign == flight.callsign), None)
                    if db_flight:
                        if db_flight.aircraft_type != flight.aircraft_type:
                            inconsistencies.append(f"Aircraft type mismatch for {flight.callsign}")
                        if db_flight.departure != flight.departure:
                            inconsistencies.append(f"Departure mismatch for {flight.callsign}")
                        if db_flight.arrival != flight.arrival:
                            inconsistencies.append(f"Arrival mismatch for {flight.callsign}")
                
                # Determine status
                if len(missing_in_db) == 0 and len(extra_in_db) == 0 and len(inconsistencies) == 0:
                    status = "PASS"
                elif len(missing_in_db) <= 5 and len(extra_in_db) <= 5 and len(inconsistencies) <= 5:
                    status = "WARNING"
                else:
                    status = "FAIL"
                
                result = IntegrityCheckResult(
                    check_name="Flights Integrity",
                    status=status,
                    details={
                        "api_flights_count": len(api_callsigns),
                        "db_flights_count": len(db_callsigns),
                        "missing_in_db": list(missing_in_db),
                        "extra_in_db": list(extra_in_db),
                        "inconsistencies": inconsistencies
                    },
                    timestamp=datetime.utcnow()
                )
                
            finally:
                db.close()
                
        except Exception as e:
            result = IntegrityCheckResult(
                check_name="Flights Integrity",
                status="FAIL",
                details={},
                timestamp=datetime.utcnow(),
                error_message=str(e)
            )
        
        self.results.append(result)
    
    async def _check_data_consistency(self) -> None:
        """Check overall data consistency between API and database."""
        try:
            self.logger.info("Checking data consistency")
            
            # Get VATSIM data
            vatsim_data = await self.vatsim_service.get_current_data()
            
            # Get database data
            db = SessionLocal()
            try:
                # Get counts
                db_atc_count = db.query(ATCPosition).filter(ATCPosition.status == "online").count()
                db_flights_count = db.query(Flight).filter(Flight.status == "active").count()
                
                # Calculate consistency ratios
                atc_consistency = db_atc_count / max(vatsim_data.total_controllers, 1)
                flights_consistency = db_flights_count / max(vatsim_data.total_flights, 1)
                
                # Check for orphaned records
                orphaned_atc = db.query(ATCPosition).filter(
                    ATCPosition.status == "online",
                    ATCPosition.last_seen < datetime.utcnow() - timedelta(minutes=30)
                ).count()
                
                orphaned_flights = db.query(Flight).filter(
                    Flight.status == "active",
                    Flight.last_updated < datetime.utcnow() - timedelta(minutes=30)
                ).count()
                
                # Determine status
                if atc_consistency >= 0.9 and flights_consistency >= 0.9 and orphaned_atc == 0 and orphaned_flights == 0:
                    status = "PASS"
                elif atc_consistency >= 0.7 and flights_consistency >= 0.7 and orphaned_atc <= 2 and orphaned_flights <= 5:
                    status = "WARNING"
                else:
                    status = "FAIL"
                
                result = IntegrityCheckResult(
                    check_name="Data Consistency",
                    status=status,
                    details={
                        "api_controllers": vatsim_data.total_controllers,
                        "api_flights": vatsim_data.total_flights,
                        "db_controllers": db_atc_count,
                        "db_flights": db_flights_count,
                        "atc_consistency_ratio": round(atc_consistency, 3),
                        "flights_consistency_ratio": round(flights_consistency, 3),
                        "orphaned_atc": orphaned_atc,
                        "orphaned_flights": orphaned_flights
                    },
                    timestamp=datetime.utcnow()
                )
                
            finally:
                db.close()
                
        except Exception as e:
            result = IntegrityCheckResult(
                check_name="Data Consistency",
                status="FAIL",
                details={},
                timestamp=datetime.utcnow(),
                error_message=str(e)
            )
        
        self.results.append(result)
    
    async def _check_performance_metrics(self) -> None:
        """Check performance metrics and system health."""
        try:
            self.logger.info("Checking performance metrics")
            
            db = SessionLocal()
            try:
                # Check database performance
                start_time = datetime.utcnow()
                db.query(ATCPosition).count()
                db.query(Flight).count()
                query_time = (datetime.utcnow() - start_time).total_seconds()
                
                # Check data volume
                total_atc = db.query(ATCPosition).count()
                total_flights = db.query(Flight).count()
                total_sectors = db.query(Sector).count()
                
                # Check recent activity
                recent_atc = db.query(ATCPosition).filter(
                    ATCPosition.last_seen >= datetime.utcnow() - timedelta(minutes=5)
                ).count()
                
                recent_flights = db.query(Flight).filter(
                    Flight.last_updated >= datetime.utcnow() - timedelta(minutes=5)
                ).count()
                
                # Determine status based on performance
                if query_time < 1.0 and recent_atc > 0 and recent_flights > 0:
                    status = "PASS"
                elif query_time < 2.0 and (recent_atc > 0 or recent_flights > 0):
                    status = "WARNING"
                else:
                    status = "FAIL"
                
                result = IntegrityCheckResult(
                    check_name="Performance Metrics",
                    status=status,
                    details={
                        "query_time_seconds": round(query_time, 3),
                        "total_atc_positions": total_atc,
                        "total_flights": total_flights,
                        "total_sectors": total_sectors,
                        "recent_atc_activity": recent_atc,
                        "recent_flights_activity": recent_flights
                    },
                    timestamp=datetime.utcnow()
                )
                
            finally:
                db.close()
                
        except Exception as e:
            result = IntegrityCheckResult(
                check_name="Performance Metrics",
                status="FAIL",
                details={},
                timestamp=datetime.utcnow(),
                error_message=str(e)
            )
        
        self.results.append(result)
    
    async def _check_data_quality(self) -> None:
        """Check data quality and completeness."""
        try:
            self.logger.info("Checking data quality")
            
            db = SessionLocal()
            try:
                # Check for missing required fields
                atc_without_callsign = db.query(ATCPosition).filter(
                    ATCPosition.callsign.is_(None)
                ).count()
                
                flights_without_callsign = db.query(Flight).filter(
                    Flight.callsign.is_(None)
                ).count()
                
                # Check for invalid data
                invalid_atc = db.query(ATCPosition).filter(
                    ATCPosition.callsign == ""
                ).count()
                
                invalid_flights = db.query(Flight).filter(
                    Flight.callsign == ""
                ).count()
                
                # Check for duplicate records
                from sqlalchemy import func
                duplicate_atc = db.query(ATCPosition.callsign, func.count(ATCPosition.callsign)).group_by(
                    ATCPosition.callsign
                ).having(func.count(ATCPosition.callsign) > 1).count()
                
                duplicate_flights = db.query(Flight.callsign, func.count(Flight.callsign)).group_by(
                    Flight.callsign
                ).having(func.count(Flight.callsign) > 1).count()
                
                # Determine status
                if atc_without_callsign == 0 and flights_without_callsign == 0 and invalid_atc == 0 and invalid_flights == 0 and duplicate_atc == 0 and duplicate_flights == 0:
                    status = "PASS"
                elif (atc_without_callsign + flights_without_callsign + invalid_atc + invalid_flights + duplicate_atc + duplicate_flights) <= 5:
                    status = "WARNING"
                else:
                    status = "FAIL"
                
                result = IntegrityCheckResult(
                    check_name="Data Quality",
                    status=status,
                    details={
                        "atc_without_callsign": atc_without_callsign,
                        "flights_without_callsign": flights_without_callsign,
                        "invalid_atc": invalid_atc,
                        "invalid_flights": invalid_flights,
                        "duplicate_atc": duplicate_atc,
                        "duplicate_flights": duplicate_flights
                    },
                    timestamp=datetime.utcnow()
                )
                
            finally:
                db.close()
                
        except Exception as e:
            result = IntegrityCheckResult(
                check_name="Data Quality",
                status="FAIL",
                details={},
                timestamp=datetime.utcnow(),
                error_message=str(e)
            )
        
        self.results.append(result)
    
    def generate_report(self) -> str:
        """
        Generate a comprehensive integrity check report.
        
        Returns:
            str: Formatted report
        """
        if not self.results:
            return "No integrity check results available."
        
        # Count results by status
        pass_count = sum(1 for r in self.results if r.status == "PASS")
        fail_count = sum(1 for r in self.results if r.status == "FAIL")
        warning_count = sum(1 for r in self.results if r.status == "WARNING")
        
        # Generate report
        report = []
        report.append("=" * 80)
        report.append("VATSIM API AND POSTGRESQL DATABASE INTEGRITY CHECK REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report.append(f"Total Checks: {len(self.results)}")
        report.append(f"Passed: {pass_count}")
        report.append(f"Failed: {fail_count}")
        report.append(f"Warnings: {warning_count}")
        report.append("")
        
        # Overall status
        if fail_count == 0 and warning_count == 0:
            overall_status = "✅ ALL CHECKS PASSED"
        elif fail_count == 0:
            overall_status = "⚠️  SOME WARNINGS - SYSTEM FUNCTIONAL"
        else:
            overall_status = "❌ CRITICAL FAILURES DETECTED"
        
        report.append(f"OVERALL STATUS: {overall_status}")
        report.append("")
        
        # Detailed results
        for result in self.results:
            status_icon = "✅" if result.status == "PASS" else "❌" if result.status == "FAIL" else "⚠️"
            report.append(f"{status_icon} {result.check_name}")
            report.append(f"   Status: {result.status}")
            report.append(f"   Timestamp: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            if result.details:
                report.append("   Details:")
                for key, value in result.details.items():
                    if isinstance(value, list) and len(value) > 10:
                        report.append(f"     {key}: {len(value)} items")
                    else:
                        report.append(f"     {key}: {value}")
            
            if result.error_message:
                report.append(f"   Error: {result.error_message}")
            
            report.append("")
        
        return "\n".join(report)
    
    def save_report(self, filename: str = None) -> str:
        """
        Save the integrity check report to a file.
        
        Args:
            filename: Optional filename, defaults to timestamp-based name
            
        Returns:
            str: Path to saved report file
        """
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"integrity_check_report_{timestamp}.txt"
        
        report_content = self.generate_report()
        
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
        
        filepath = os.path.join("logs", filename)
        with open(filepath, "w") as f:
            f.write(report_content)
        
        return filepath


async def main():
    """Main function to run integrity checks."""
    print("Starting VATSIM API and PostgreSQL Database Integrity Check...")
    print("=" * 80)
    
    # Initialize integrity checker
    checker = IntegrityChecker()
    
    try:
        # Run all checks
        results = await checker.run_all_checks()
        
        # Generate and display report
        report = checker.generate_report()
        print(report)
        
        # Save report
        report_file = checker.save_report()
        print(f"\nReport saved to: {report_file}")
        
        # Exit with appropriate code
        fail_count = sum(1 for r in results if r.status == "FAIL")
        if fail_count > 0:
            print(f"\n❌ Integrity check failed with {fail_count} critical errors")
            sys.exit(1)
        else:
            print("\n✅ Integrity check completed successfully")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Error running integrity checks: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 