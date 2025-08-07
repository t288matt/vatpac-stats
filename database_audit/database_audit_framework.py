#!/usr/bin/env python3
"""
Database Audit Framework
=======================

A comprehensive, reusable audit system for validating database schema against:
- Configuration files
- SQLAlchemy models
- Documentation
- VATSIM API field mappings
- Performance indexes
- Data integrity constraints

Usage:
    python scripts/database_audit_framework.py --audit-type=full
    python scripts/database_audit_framework.py --audit-type=schema
    python scripts/database_audit_framework.py --audit-type=performance
"""

import argparse
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.models import Base
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


@dataclass
class FieldMapping:
    """Represents a field mapping between different sources"""
    field_name: str
    source_type: str  # 'database', 'model', 'api', 'config'
    data_type: str
    nullable: bool
    default_value: Optional[str] = None
    constraints: List[str] = None
    description: str = ""


@dataclass
class TableAudit:
    """Represents audit results for a single table"""
    table_name: str
    database_fields: List[FieldMapping]
    model_fields: List[FieldMapping]
    api_fields: List[FieldMapping]
    missing_fields: List[str]
    extra_fields: List[str]
    type_mismatches: List[Dict[str, Any]]
    index_count: int
    constraint_count: int
    record_count: int
    status: str  # 'pass', 'warn', 'fail'


@dataclass
class AuditResult:
    """Complete audit results"""
    audit_timestamp: str
    audit_type: str
    database_version: str
    total_tables: int
    total_fields: int
    total_indexes: int
    table_audits: List[TableAudit]
    performance_metrics: Dict[str, Any]
    recommendations: List[str]
    overall_status: str


class DatabaseAuditor:
    """Comprehensive database audit framework"""
    
    def __init__(self, db_session=None):
        self.db_session = db_session or SessionLocal()
        self.engine = self.db_session.bind
        self.inspector = inspect(self.engine)
        self.audit_results = {}
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db_session:
            self.db_session.close()
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get basic database information"""
        try:
            version_result = self.db_session.execute(text("SELECT version()"))
            version = version_result.scalar()
            
            # Get database statistics
            stats = {
                'version': version,
                'total_tables': len(self.inspector.get_table_names()),
                'total_indexes': 0,
                'total_constraints': 0
            }
            
            # Count indexes and constraints
            for table_name in self.inspector.get_table_names():
                stats['total_indexes'] += len(self.inspector.get_indexes(table_name))
                stats['total_constraints'] += len(self.inspector.get_unique_constraints(table_name))
                stats['total_constraints'] += len(self.inspector.get_foreign_keys(table_name))
            
            return stats
        except Exception as e:
            return {'error': str(e)}
    
    def audit_table_schema(self, table_name: str) -> TableAudit:
        """Audit a single table's schema"""
        try:
            # Get database fields
            db_columns = self.inspector.get_columns(table_name)
            db_fields = []
            
            for col in db_columns:
                field = FieldMapping(
                    field_name=col['name'],
                    source_type='database',
                    data_type=str(col['type']),
                    nullable=col['nullable'],
                    default_value=str(col['default']) if col['default'] else None,
                    description=f"Database column: {col['name']}"
                )
                db_fields.append(field)
            
            # Get model fields (if model exists)
            model_fields = self._get_model_fields(table_name)
            
            # Get API fields (from VATSIM API mapping)
            api_fields = self._get_api_fields(table_name)
            
            # Compare fields
            db_field_names = {f.field_name for f in db_fields}
            model_field_names = {f.field_name for f in model_fields}
            api_field_names = {f.field_name for f in api_fields}
            
            missing_fields = (model_field_names | api_field_names) - db_field_names
            extra_fields = db_field_names - (model_field_names | api_field_names)
            
            # Check type mismatches
            type_mismatches = self._check_type_mismatches(db_fields, model_fields)
            
            # Get indexes and constraints
            indexes = self.inspector.get_indexes(table_name)
            constraints = self.inspector.get_unique_constraints(table_name)
            foreign_keys = self.inspector.get_foreign_keys(table_name)
            
            # Get record count
            try:
                count_result = self.db_session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                record_count = count_result.scalar()
            except:
                record_count = 0
            
            # Determine status
            status = 'pass'
            if missing_fields:
                status = 'fail'
            elif extra_fields or type_mismatches:
                status = 'warn'
            
            return TableAudit(
                table_name=table_name,
                database_fields=db_fields,
                model_fields=model_fields,
                api_fields=api_fields,
                missing_fields=list(missing_fields),
                extra_fields=list(extra_fields),
                type_mismatches=type_mismatches,
                index_count=len(indexes),
                constraint_count=len(constraints) + len(foreign_keys),
                record_count=record_count,
                status=status
            )
            
        except Exception as e:
            return TableAudit(
                table_name=table_name,
                database_fields=[],
                model_fields=[],
                api_fields=[],
                missing_fields=[],
                extra_fields=[],
                type_mismatches=[],
                index_count=0,
                constraint_count=0,
                record_count=0,
                status='fail'
            )
    
    def _get_model_fields(self, table_name: str) -> List[FieldMapping]:
        """Get fields from SQLAlchemy models"""
        model_fields = []
        
        try:
            # Import models dynamically
            from app.models import Flight, Controller, Transceiver, Airports
            
            model_map = {
                'flights': Flight,
                'controllers': Controller,
                'transceivers': Transceiver,
                'airports': Airports
            }
            
            if table_name in model_map:
                model = model_map[table_name]
                mapper = inspect(model)
                
                for column in mapper.columns:
                    field = FieldMapping(
                        field_name=column.name,
                        source_type='model',
                        data_type=str(column.type),
                        nullable=column.nullable,
                        default_value=str(column.default.arg) if column.default else None,
                        description=f"Model field: {column.name}"
                    )
                    model_fields.append(field)
                    
        except Exception as e:
            print(f"Warning: Could not get model fields for {table_name}: {e}")
        
        return model_fields
    
    def _get_api_fields(self, table_name: str) -> List[FieldMapping]:
        """Get VATSIM API field mappings"""
        api_fields = []
        
        # VATSIM API field mappings (from documentation)
        api_mappings = {
            'controllers': [
                ('controller_id', 'INTEGER', 'VATSIM user ID'),
                ('controller_name', 'VARCHAR(100)', 'Controller name'),
                ('controller_rating', 'INTEGER', 'Controller rating'),
                ('callsign', 'VARCHAR(50)', 'ATC callsign'),
                ('facility', 'VARCHAR(50)', 'Facility type'),
                ('frequency', 'VARCHAR(20)', 'Radio frequency'),
                ('position', 'VARCHAR(50)', 'Position description'),
                ('status', 'VARCHAR(20)', 'Online/offline status'),
                ('visual_range', 'INTEGER', 'Visual range in nautical miles'),
                ('text_atis', 'TEXT', 'ATIS text information')
            ],
            'flights': [
                ('cid', 'INTEGER', 'VATSIM user ID'),
                ('name', 'VARCHAR(100)', 'Pilot name'),
                ('server', 'VARCHAR(50)', 'Network server'),
                ('pilot_rating', 'INTEGER', 'Pilot rating'),
                ('military_rating', 'INTEGER', 'Military rating'),
                ('latitude', 'DOUBLE PRECISION', 'Position latitude'),
                ('longitude', 'DOUBLE PRECISION', 'Position longitude'),
                ('groundspeed', 'INTEGER', 'Ground speed'),
                ('transponder', 'VARCHAR(10)', 'Transponder code'),
                ('qnh_i_hg', 'DECIMAL(4,2)', 'QNH in inches Hg'),
                ('qnh_mb', 'INTEGER', 'QNH in millibars'),
                ('logon_time', 'TIMESTAMP', 'When pilot connected'),
                ('last_updated_api', 'TIMESTAMP', 'API last_updated timestamp')
            ],
            'transceivers': [
                ('callsign', 'VARCHAR(50)', 'Entity callsign'),
                ('transceiver_id', 'INTEGER', 'Transceiver ID'),
                ('frequency', 'INTEGER', 'Frequency in Hz'),
                ('position_lat', 'DOUBLE PRECISION', 'Latitude'),
                ('position_lon', 'DOUBLE PRECISION', 'Longitude'),
                ('height_msl', 'DOUBLE PRECISION', 'Height above sea level'),
                ('height_agl', 'DOUBLE PRECISION', 'Height above ground'),
                ('entity_type', 'VARCHAR(20)', 'Flight or ATC'),
                ('entity_id', 'INTEGER', 'Foreign key reference')
            ]
        }
        
        if table_name in api_mappings:
            for field_name, data_type, description in api_mappings[table_name]:
                field = FieldMapping(
                    field_name=field_name,
                    source_type='api',
                    data_type=data_type,
                    nullable=True,  # API fields are typically nullable
                    description=f"VATSIM API: {description}"
                )
                api_fields.append(field)
        
        return api_fields
    
    def _check_type_mismatches(self, db_fields: List[FieldMapping], 
                              model_fields: List[FieldMapping]) -> List[Dict[str, Any]]:
        """Check for data type mismatches between database and models"""
        mismatches = []
        
        db_field_map = {f.field_name: f for f in db_fields}
        model_field_map = {f.field_name: f for f in model_fields}
        
        for field_name in set(db_field_map.keys()) & set(model_field_map.keys()):
            db_field = db_field_map[field_name]
            model_field = model_field_map[field_name]
            
            if db_field.data_type != model_field.data_type:
                mismatches.append({
                    'field_name': field_name,
                    'database_type': db_field.data_type,
                    'model_type': model_field.data_type,
                    'severity': 'high' if 'PRIMARY KEY' in str(db_field.data_type) else 'medium'
                })
        
        return mismatches
    
    def audit_performance(self) -> Dict[str, Any]:
        """Audit database performance metrics"""
        performance_metrics = {}
        
        try:
            # Check index usage
            index_usage_query = """
            SELECT 
                schemaname,
                tablename,
                indexname,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch
            FROM pg_stat_user_indexes
            ORDER BY idx_scan DESC;
            """
            
            index_result = self.db_session.execute(text(index_usage_query))
            performance_metrics['index_usage'] = [dict(row) for row in index_result]
            
            # Check table sizes
            table_sizes_query = """
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
            """
            
            size_result = self.db_session.execute(text(table_sizes_query))
            performance_metrics['table_sizes'] = [dict(row) for row in size_result]
            
            # Check slow queries (if available)
            slow_queries_query = """
            SELECT 
                query,
                calls,
                total_time,
                mean_time,
                rows
            FROM pg_stat_statements 
            WHERE query LIKE '%flights%' OR query LIKE '%controllers%'
            ORDER BY mean_time DESC
            LIMIT 10;
            """
            
            try:
                slow_result = self.db_session.execute(text(slow_queries_query))
                performance_metrics['slow_queries'] = [dict(row) for row in slow_result]
            except:
                performance_metrics['slow_queries'] = []
            
        except Exception as e:
            performance_metrics['error'] = str(e)
        
        return performance_metrics
    
    def audit_data_integrity(self) -> Dict[str, Any]:
        """Audit data integrity constraints"""
        integrity_checks = {}
        
        try:
            # Check for orphaned records
            orphan_checks = {
                'flights_without_controllers': """
                SELECT COUNT(*) as count 
                FROM flights f 
                LEFT JOIN controllers c ON f.cid = c.controller_id 
                WHERE f.cid IS NOT NULL AND c.controller_id IS NULL
                """,
                'transceivers_without_entities': """
                SELECT COUNT(*) as count 
                FROM transceivers t 
                WHERE t.entity_id IS NOT NULL 
                AND NOT EXISTS (
                    SELECT 1 FROM flights WHERE id = t.entity_id
                    UNION
                    SELECT 1 FROM controllers WHERE id = t.entity_id
                )
                """
            }
            
            for check_name, query in orphan_checks.items():
                result = self.db_session.execute(text(query))
                count = result.scalar()
                integrity_checks[check_name] = count
            
            # Check for duplicate records
            duplicate_checks = {
                'duplicate_flight_callsigns': """
                SELECT COUNT(*) as count 
                FROM (
                    SELECT callsign, COUNT(*) 
                    FROM flights 
                    GROUP BY callsign 
                    HAVING COUNT(*) > 1
                ) as duplicates
                """,
                'duplicate_controller_callsigns': """
                SELECT COUNT(*) as count 
                FROM (
                    SELECT callsign, COUNT(*) 
                    FROM controllers 
                    GROUP BY callsign 
                    HAVING COUNT(*) > 1
                ) as duplicates
                """
            }
            
            for check_name, query in duplicate_checks.items():
                result = self.db_session.execute(text(query))
                count = result.scalar()
                integrity_checks[check_name] = count
                
        except Exception as e:
            integrity_checks['error'] = str(e)
        
        return integrity_checks
    
    def generate_recommendations(self, table_audits: List[TableAudit], 
                               performance_metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on audit results"""
        recommendations = []
        
        # Schema recommendations
        for audit in table_audits:
            if audit.missing_fields:
                recommendations.append(
                    f"Add missing fields to {audit.table_name}: {', '.join(audit.missing_fields)}"
                )
            
            if audit.type_mismatches:
                recommendations.append(
                    f"Fix type mismatches in {audit.table_name}: {len(audit.type_mismatches)} issues found"
                )
            
            if audit.index_count < 3:  # Minimum recommended indexes
                recommendations.append(
                    f"Consider adding more indexes to {audit.table_name} (currently {audit.index_count})"
                )
        
        # Performance recommendations
        if 'table_sizes' in performance_metrics:
            for table_info in performance_metrics['table_sizes']:
                size_bytes = table_info.get('size_bytes', 0)
                if size_bytes > 100 * 1024 * 1024:  # 100MB
                    recommendations.append(
                        f"Consider partitioning large table: {table_info['tablename']} ({table_info['size']})"
                    )
        
        # Index usage recommendations
        if 'index_usage' in performance_metrics:
            unused_indexes = [idx for idx in performance_metrics['index_usage'] if idx['idx_scan'] == 0]
            if unused_indexes:
                recommendations.append(
                    f"Consider removing {len(unused_indexes)} unused indexes"
                )
        
        return recommendations
    
    def run_full_audit(self) -> AuditResult:
        """Run a complete database audit"""
        print("🔍 Starting comprehensive database audit...")
        
        # Get database info
        db_info = self.get_database_info()
        
        # Audit all tables
        table_audits = []
        for table_name in self.inspector.get_table_names():
            print(f"  Auditing table: {table_name}")
            audit = self.audit_table_schema(table_name)
            table_audits.append(audit)
        
        # Performance audit
        print("  Auditing performance metrics...")
        performance_metrics = self.audit_performance()
        
        # Data integrity audit
        print("  Auditing data integrity...")
        integrity_checks = self.audit_data_integrity()
        performance_metrics['integrity_checks'] = integrity_checks
        
        # Generate recommendations
        recommendations = self.generate_recommendations(table_audits, performance_metrics)
        
        # Determine overall status
        failed_audits = [a for a in table_audits if a.status == 'fail']
        warned_audits = [a for a in table_audits if a.status == 'warn']
        
        if failed_audits:
            overall_status = 'fail'
        elif warned_audits:
            overall_status = 'warn'
        else:
            overall_status = 'pass'
        
        return AuditResult(
            audit_timestamp=datetime.now().isoformat(),
            audit_type='full',
            database_version=db_info.get('version', 'unknown'),
            total_tables=len(table_audits),
            total_fields=sum(len(a.database_fields) for a in table_audits),
            total_indexes=sum(a.index_count for a in table_audits),
            table_audits=table_audits,
            performance_metrics=performance_metrics,
            recommendations=recommendations,
            overall_status=overall_status
        )
    
    def run_schema_audit(self) -> AuditResult:
        """Run schema-only audit"""
        print("🔍 Starting schema audit...")
        
        db_info = self.get_database_info()
        table_audits = []
        
        for table_name in self.inspector.get_table_names():
            print(f"  Auditing schema: {table_name}")
            audit = self.audit_table_schema(table_name)
            table_audits.append(audit)
        
        recommendations = self.generate_recommendations(table_audits, {})
        
        failed_audits = [a for a in table_audits if a.status == 'fail']
        warned_audits = [a for a in table_audits if a.status == 'warn']
        
        overall_status = 'fail' if failed_audits else ('warn' if warned_audits else 'pass')
        
        return AuditResult(
            audit_timestamp=datetime.now().isoformat(),
            audit_type='schema',
            database_version=db_info.get('version', 'unknown'),
            total_tables=len(table_audits),
            total_fields=sum(len(a.database_fields) for a in table_audits),
            total_indexes=sum(a.index_count for a in table_audits),
            table_audits=table_audits,
            performance_metrics={},
            recommendations=recommendations,
            overall_status=overall_status
        )
    
    def run_performance_audit(self) -> AuditResult:
        """Run performance-only audit"""
        print("🔍 Starting performance audit...")
        
        db_info = self.get_database_info()
        performance_metrics = self.audit_performance()
        
        # Create minimal table audits for performance focus
        table_audits = []
        for table_name in self.inspector.get_table_names():
            audit = self.audit_table_schema(table_name)
            # Only keep performance-relevant info
            audit.missing_fields = []
            audit.extra_fields = []
            audit.type_mismatches = []
            table_audits.append(audit)
        
        recommendations = self.generate_recommendations(table_audits, performance_metrics)
        
        return AuditResult(
            audit_timestamp=datetime.now().isoformat(),
            audit_type='performance',
            database_version=db_info.get('version', 'unknown'),
            total_tables=len(table_audits),
            total_fields=sum(len(a.database_fields) for a in table_audits),
            total_indexes=sum(a.index_count for a in table_audits),
            table_audits=table_audits,
            performance_metrics=performance_metrics,
            recommendations=recommendations,
            overall_status='pass'  # Performance audits don't fail, just provide recommendations
        )
    
    def save_audit_report(self, audit_result: AuditResult, output_file: str = None):
        """Save audit results to file"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"audit_report_{audit_result.audit_type}_{timestamp}.json"
        
        # Convert to dict for JSON serialization
        audit_dict = asdict(audit_result)
        
        with open(output_file, 'w') as f:
            json.dump(audit_dict, f, indent=2, default=str)
        
        print(f"📄 Audit report saved to: {output_file}")
        return output_file
    
    def print_audit_summary(self, audit_result: AuditResult):
        """Print a human-readable audit summary"""
        print("\n" + "="*60)
        print("🔍 DATABASE AUDIT SUMMARY")
        print("="*60)
        print(f"Audit Type: {audit_result.audit_type.upper()}")
        print(f"Timestamp: {audit_result.audit_timestamp}")
        print(f"Database Version: {audit_result.database_version}")
        print(f"Overall Status: {audit_result.overall_status.upper()}")
        print(f"Total Tables: {audit_result.total_tables}")
        print(f"Total Fields: {audit_result.total_fields}")
        print(f"Total Indexes: {audit_result.total_indexes}")
        
        print(f"\n📊 Table Status Summary:")
        status_counts = {}
        for audit in audit_result.table_audits:
            status_counts[audit.status] = status_counts.get(audit.status, 0) + 1
        
        for status, count in status_counts.items():
            print(f"  {status.upper()}: {count} tables")
        
        if audit_result.recommendations:
            print(f"\n💡 Recommendations ({len(audit_result.recommendations)}):")
            for i, rec in enumerate(audit_result.recommendations, 1):
                print(f"  {i}. {rec}")
        
        print("="*60)


def main():
    """Main audit execution function"""
    parser = argparse.ArgumentParser(description='Database Audit Framework')
    parser.add_argument('--audit-type', choices=['full', 'schema', 'performance'], 
                       default='full', help='Type of audit to run')
    parser.add_argument('--output-file', help='Output file for audit report')
    parser.add_argument('--print-summary', action='store_true', 
                       help='Print human-readable summary')
    
    args = parser.parse_args()
    
    try:
        with DatabaseAuditor() as auditor:
            if args.audit_type == 'full':
                result = auditor.run_full_audit()
            elif args.audit_type == 'schema':
                result = auditor.run_schema_audit()
            elif args.audit_type == 'performance':
                result = auditor.run_performance_audit()
            else:
                print("❌ Invalid audit type")
                return 1
            
            # Save report
            output_file = auditor.save_audit_report(result, args.output_file)
            
            # Print summary if requested
            if args.print_summary:
                auditor.print_audit_summary(result)
            
            print(f"✅ Audit completed successfully!")
            print(f"📄 Report saved to: {output_file}")
            print(f"🎯 Overall Status: {result.overall_status.upper()}")
            
            return 0 if result.overall_status != 'fail' else 1
            
    except Exception as e:
        print(f"❌ Audit failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
