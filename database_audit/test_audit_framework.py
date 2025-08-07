#!/usr/bin/env python3
"""
Test Script for Database Audit Framework
========================================

This script tests the database audit framework to ensure it works correctly
and can be used for regular database audits.

Usage:
    python scripts/test_audit_framework.py
"""

import sys
import os
import json
from datetime import datetime

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def test_audit_framework():
    """Test the database audit framework"""
    print("🧪 Testing Database Audit Framework...")
    
    try:
        # Import the audit framework
        from database_audit_framework import DatabaseAuditor, AuditResult
        
        print("✅ Successfully imported DatabaseAuditor")
        
        # Test basic functionality
        with DatabaseAuditor() as auditor:
            print("✅ Successfully created DatabaseAuditor instance")
            
            # Test database info
            db_info = auditor.get_database_info()
            print(f"✅ Database info retrieved: {db_info.get('version', 'unknown')}")
            
            # Test table audit
            tables = auditor.inspector.get_table_names()
            print(f"✅ Found {len(tables)} tables: {', '.join(tables[:5])}{'...' if len(tables) > 5 else ''}")
            
            # Test single table audit
            if tables:
                test_table = tables[0]
                print(f"✅ Testing audit for table: {test_table}")
                table_audit = auditor.audit_table_schema(test_table)
                print(f"✅ Table audit completed: {table_audit.status}")
            
            # Test performance audit
            print("✅ Testing performance audit...")
            performance_metrics = auditor.audit_performance()
            print(f"✅ Performance audit completed: {len(performance_metrics)} metrics collected")
            
            # Test data integrity audit
            print("✅ Testing data integrity audit...")
            integrity_checks = auditor.audit_data_integrity()
            print(f"✅ Data integrity audit completed: {len(integrity_checks)} checks performed")
            
            # Test schema audit
            print("✅ Testing schema audit...")
            schema_result = auditor.run_schema_audit()
            print(f"✅ Schema audit completed: {schema_result.overall_status}")
            
            # Test report saving
            test_report = AuditResult(
                audit_timestamp=datetime.now().isoformat(),
                audit_type='test',
                database_version='test',
                total_tables=1,
                total_fields=10,
                total_indexes=5,
                table_audits=[],
                performance_metrics={},
                recommendations=['Test recommendation'],
                overall_status='pass'
            )
            
            output_file = auditor.save_audit_report(test_report, 'test_audit_report.json')
            print(f"✅ Test report saved to: {output_file}")
            
            # Clean up test file
            if os.path.exists(output_file):
                os.remove(output_file)
                print("✅ Test file cleaned up")
        
        print("\n🎉 All tests passed! Database audit framework is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_configuration():
    """Test the configuration file"""
    print("\n🔧 Testing Configuration File...")
    
    try:
        config_file = 'scripts/database_audit_config.json'
        
        if not os.path.exists(config_file):
            print(f"❌ Configuration file not found: {config_file}")
            return False
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        print("✅ Configuration file loaded successfully")
        
        # Test required sections
        required_sections = ['audit_config', 'expected_schema', 'validation_rules']
        for section in required_sections:
            if section in config:
                print(f"✅ Found required section: {section}")
            else:
                print(f"❌ Missing required section: {section}")
                return False
        
        # Test expected schema
        expected_tables = ['controllers', 'flights', 'transceivers']
        for table in expected_tables:
            if table in config['expected_schema']:
                print(f"✅ Found expected table: {table}")
            else:
                print(f"❌ Missing expected table: {table}")
                return False
        
        print("✅ Configuration file validation passed!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_command_line_interface():
    """Test the command line interface"""
    print("\n🖥️ Testing Command Line Interface...")
    
    try:
        import subprocess
        
        # Test help command
        result = subprocess.run([
            'python', 'scripts/database_audit_framework.py', '--help'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Help command works correctly")
        else:
            print(f"❌ Help command failed: {result.stderr}")
            return False
        
        # Test invalid audit type
        result = subprocess.run([
            'python', 'scripts/database_audit_framework.py', '--audit-type=invalid'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("✅ Invalid audit type correctly rejected")
        else:
            print("❌ Invalid audit type should have been rejected")
            return False
        
        print("✅ Command line interface tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Command line interface test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("🧪 DATABASE AUDIT FRAMEWORK TEST SUITE")
    print("="*60)
    
    tests = [
        ("Framework Import and Basic Functionality", test_audit_framework),
        ("Configuration File Validation", test_configuration),
        ("Command Line Interface", test_command_line_interface)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        if test_func():
            passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")
    
    print("\n" + "="*60)
    print(f"📊 TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The database audit framework is ready for use.")
        print("\n📝 Usage Examples:")
        print("  python scripts/database_audit_framework.py --audit-type=full")
        print("  python scripts/database_audit_framework.py --audit-type=schema --print-summary")
        print("  python scripts/database_audit_framework.py --audit-type=performance")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues before using the framework.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
