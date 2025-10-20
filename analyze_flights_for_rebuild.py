#!/usr/bin/env python3
"""
Analyze Every Flight for Issues
Identifies flights that need rebuilding based on data quality issues
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

class FlightIssueAnalyzer:
    def __init__(self, db_url: str):
        self.engine = create_async_engine(db_url)
        self.session_factory = sessionmaker(bind=self.engine, class_=AsyncSession)
        
        # Analysis results
        self.analysis_results = {
            'total_flights_analyzed': 0,
            'flights_with_issues': 0,
            'flights_needing_rebuild': 0,
            'issues_by_type': {
                'no_sector_records': 0,
                'impossible_timestamps': 0,
                'negative_durations': 0,
                'overlapping_entries': 0,
                'missing_flight_data': 0,
                'fragmented_sectors': 0
            },
            'problematic_flights': []
        }
    
    async def analyze_all_flights(self) -> None:
        """Analyze every flight in the database for issues"""
        
        print("[ANALYZE] Starting comprehensive flight analysis...")
        print("=" * 80)
        
        # Get all unique flights
        async with self.session_factory() as session:
            result = await session.execute(text("""
                SELECT DISTINCT fs.callsign, fs.cid, fs.completion_time,
                       COUNT(fso.id) as sector_record_count,
                       COUNT(f.id) as flight_record_count,
                       COUNT(fa.id) as archive_record_count
                FROM flight_summaries fs
                LEFT JOIN flight_sector_occupancy fso ON fs.callsign = fso.callsign
                LEFT JOIN flights f ON fs.callsign = f.callsign AND fs.cid = f.cid
                LEFT JOIN flights_archive fa ON fs.callsign = fa.callsign AND fs.cid = fa.cid
                WHERE fs.completion_time > '2025-09-01'
                GROUP BY fs.callsign, fs.cid, fs.completion_time
                ORDER BY fs.callsign, fs.completion_time
            """))
            
            all_flights = result.fetchall()
        
        print(f"[ANALYZE] Found {len(all_flights)} unique flights to analyze")
        
        # Analyze each flight
        for i, flight in enumerate(all_flights):
            if i % 100 == 0:
                print(f"[PROGRESS] Analyzing flight {i+1}/{len(all_flights)}: {flight.callsign}")
            
            issues = await self._analyze_single_flight(flight)
            if issues:
                self.analysis_results['flights_with_issues'] += 1
                self.analysis_results['problematic_flights'].append({
                    'callsign': flight.callsign,
                    'cid': flight.cid,
                    'completion_time': flight.completion_time,
                    'issues': issues
                })
            
            self.analysis_results['total_flights_analyzed'] += 1
        
        # Print detailed results
        self._print_analysis_summary()
        self._print_problematic_flights()
    
    async def _analyze_single_flight(self, flight) -> List[str]:
        """Analyze a single flight for issues"""
        
        callsign = flight.callsign
        cid = flight.cid
        completion_time = flight.completion_time
        sector_count = flight.sector_record_count
        flight_count = flight.flight_record_count
        archive_count = flight.archive_record_count
        
        issues = []
        
        # Issue 1: No sector records
        if sector_count == 0:
            issues.append('no_sector_records')
            self.analysis_results['issues_by_type']['no_sector_records'] += 1
        
        # Issue 2: No flight data
        if flight_count == 0 and archive_count == 0:
            issues.append('missing_flight_data')
            self.analysis_results['issues_by_type']['missing_flight_data'] += 1
        
        # Issue 3: Check for data quality issues in sector records
        if sector_count > 0:
            async with self.session_factory() as session:
                # Check for impossible timestamps
                result = await session.execute(text("""
                    SELECT COUNT(*) as impossible_count
                    FROM flight_sector_occupancy
                    WHERE callsign = :callsign
                    AND exit_timestamp IS NOT NULL
                    AND exit_timestamp < entry_timestamp
                """), {"callsign": callsign})
                
                impossible_count = result.fetchone().impossible_count
                if impossible_count > 0:
                    issues.append('impossible_timestamps')
                    self.analysis_results['issues_by_type']['impossible_timestamps'] += 1
                
                # Check for negative durations
                result = await session.execute(text("""
                    SELECT COUNT(*) as negative_count
                    FROM flight_sector_occupancy
                    WHERE callsign = :callsign
                    AND duration_seconds < 0
                """), {"callsign": callsign})
                
                negative_count = result.fetchone().negative_count
                if negative_count > 0:
                    issues.append('negative_durations')
                    self.analysis_results['issues_by_type']['negative_durations'] += 1
                
                # Check for overlapping entries
                result = await session.execute(text("""
                    WITH overlapping_check AS (
                        SELECT fso1.id as id1, fso1.sector_name as sector1, fso1.entry_timestamp as entry1, fso1.exit_timestamp as exit1,
                               fso2.id as id2, fso2.sector_name as sector2, fso2.entry_timestamp as entry2, fso2.exit_timestamp as exit2
                        FROM flight_sector_occupancy fso1
                        JOIN flight_sector_occupancy fso2 ON fso1.callsign = fso2.callsign
                        WHERE fso1.callsign = :callsign
                        AND fso1.id < fso2.id
                        AND fso1.sector_name = fso2.sector_name
                        AND fso1.entry_timestamp < fso2.exit_timestamp
                        AND fso1.exit_timestamp > fso2.entry_timestamp
                        AND fso1.exit_timestamp IS NOT NULL
                        AND fso2.exit_timestamp IS NOT NULL
                    )
                    SELECT COUNT(*) as overlap_count FROM overlapping_check
                """), {"callsign": callsign})
                
                overlap_count = result.fetchone().overlap_count
                if overlap_count > 0:
                    issues.append('overlapping_entries')
                    self.analysis_results['issues_by_type']['overlapping_entries'] += 1
                
                # Check for fragmented sectors (multiple entries to same sector)
                result = await session.execute(text("""
                    SELECT sector_name, COUNT(*) as entry_count
                    FROM flight_sector_occupancy
                    WHERE callsign = :callsign
                    AND exit_timestamp IS NOT NULL
                    GROUP BY sector_name
                    HAVING COUNT(*) > 1
                """), {"callsign": callsign})
                
                fragmented_sectors = result.fetchall()
                if fragmented_sectors:
                    issues.append('fragmented_sectors')
                    self.analysis_results['issues_by_type']['fragmented_sectors'] += 1
        
        return issues
    
    def _print_analysis_summary(self) -> None:
        """Print comprehensive analysis summary"""
        
        print("\n" + "=" * 80)
        print("[SUMMARY] COMPREHENSIVE FLIGHT ANALYSIS RESULTS")
        print("=" * 80)
        
        total = self.analysis_results['total_flights_analyzed']
        with_issues = self.analysis_results['flights_with_issues']
        clean = total - with_issues
        
        print(f"[TOTAL] Flights analyzed: {total:,}")
        print(f"[CLEAN] Flights with no issues: {clean:,} ({clean/total*100:.1f}%)")
        print(f"[ISSUES] Flights with issues: {with_issues:,} ({with_issues/total*100:.1f}%)")
        
        print(f"\n[ISSUES] Breakdown by issue type:")
        for issue_type, count in self.analysis_results['issues_by_type'].items():
            if count > 0:
                percentage = count / total * 100
                print(f"  - {issue_type.replace('_', ' ').title()}: {count:,} ({percentage:.1f}%)")
        
        # Determine which flights need rebuilding
        rebuild_candidates = []
        for flight in self.analysis_results['problematic_flights']:
            needs_rebuild = False
            rebuild_reasons = []
            
            if 'no_sector_records' in flight['issues']:
                needs_rebuild = True
                rebuild_reasons.append('missing sector data')
            
            if 'impossible_timestamps' in flight['issues']:
                needs_rebuild = True
                rebuild_reasons.append('impossible timestamps')
            
            if 'negative_durations' in flight['issues']:
                needs_rebuild = True
                rebuild_reasons.append('negative durations')
            
            if 'overlapping_entries' in flight['issues']:
                needs_rebuild = True
                rebuild_reasons.append('overlapping entries')
            
            if 'fragmented_sectors' in flight['issues']:
                needs_rebuild = True
                rebuild_reasons.append('fragmented sectors')
            
            if needs_rebuild:
                rebuild_candidates.append({
                    'callsign': flight['callsign'],
                    'cid': flight['cid'],
                    'completion_time': flight['completion_time'],
                    'reasons': rebuild_reasons
                })
        
        self.analysis_results['flights_needing_rebuild'] = len(rebuild_candidates)
        
        print(f"\n[REBUILD] Flights needing rebuild: {len(rebuild_candidates):,}")
        
        if len(rebuild_candidates) > 0:
            print(f"\n[PRIORITY] Top 20 flights needing rebuild:")
            for i, flight in enumerate(rebuild_candidates[:20]):
                reasons_str = ', '.join(flight['reasons'])
                print(f"  {i+1:2d}. {flight['callsign']} (CID: {flight['cid']}) - {reasons_str}")
    
    def _print_problematic_flights(self) -> None:
        """Print detailed list of problematic flights"""
        
        if not self.analysis_results['problematic_flights']:
            return
        
        print(f"\n[DETAILS] All problematic flights ({len(self.analysis_results['problematic_flights'])}):")
        print("-" * 80)
        
        for flight in self.analysis_results['problematic_flights']:
            issues_str = ', '.join(flight['issues'])
            print(f"{flight['callsign']:<10} | CID: {flight['cid']:<8} | {flight['completion_time']} | Issues: {issues_str}")

async def main():
    """Main analysis function"""
    
    db_url = "postgresql+asyncpg://vatsim_user:vatsim_password@localhost:5432/vatsim_data"
    
    analyzer = FlightIssueAnalyzer(db_url)
    await analyzer.analyze_all_flights()

if __name__ == "__main__":
    asyncio.run(main())



