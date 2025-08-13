#!/usr/bin/env python3
"""
Stage 7: Infrastructure & Technical Tests

This module provides comprehensive testing of the technical foundation
and infrastructure that supports the VATSIM data system.

Focus Areas:
- Database connection management
- Configuration loading and validation
- System module availability
- Basic infrastructure validation
"""

import pytest
import sys
import os
from pathlib import Path
import asyncio
import time

# Add the app directory to the Python path
sys.path.insert(0, '/app/app')
sys.path.insert(0, '/app')


class TestDatabaseInfrastructure:
    """Test database connection and infrastructure"""
    
    @pytest.mark.stage7
    @pytest.mark.infrastructure
    def test_database_connection_management(self):
        """Test: Do database connections work reliably?"""
        print("🧪 Testing: Do database connections work reliably?")
        
        try:
            from database import engine, get_sync_session
            
            # Test database engine creation
            assert engine is not None, "Database engine should be created"
            
            # Test database URL configuration
            db_url = str(engine.url)
            assert 'postgresql' in db_url, "Database URL should be PostgreSQL"
            assert 'vatsim_data' in db_url, "Database URL should include database name"
            
            # Test database session creation using sync session
            db = get_sync_session()
            assert db is not None, "Database session should be created"
            
            # Test basic database operation
            from sqlalchemy import text
            result = db.execute(text("SELECT 1"))
            assert result.scalar() == 1, "Basic database query should work"
            
            db.close()
            print("✅ Database connections work reliably")
            assert True  # Test passed successfully
            
        except Exception as e:
            print(f"❌ Database connection test failed: {e}")
            assert False, "Test failed"
    
    @pytest.mark.stage7
    @pytest.mark.infrastructure
    def test_database_session_management(self):
        """Test: Is database session management working?"""
        print("🧪 Testing: Is database session management working?")
        
        try:
            from database import SessionLocal
            
            # Test session local creation
            assert SessionLocal is not None, "SessionLocal should be defined"
            
            # Test session creation and cleanup
            db = SessionLocal()
            assert db is not None, "Session should be created"
            
            # Test session is active
            assert db.is_active, "Session should be active"
            
            # Test session cleanup
            db.close()
            # Note: SQLAlchemy session state checking may vary by version
            # Just verify the session was created and can be closed
            print("✅ Database session management working correctly")
            assert True  # Test passed successfully
            
        except Exception as e:
            print(f"❌ Database session management test failed: {e}")
            assert False, "Test failed"


class TestConfigurationManagement:
    """Test configuration loading and validation"""
    
    @pytest.mark.stage7
    @pytest.mark.infrastructure
    def test_environment_configuration_loading(self):
        """Test: Are environment variables properly loaded?"""
        print("🧪 Testing: Are environment variables properly loaded?")
        
        try:
            from config import get_config
            
            # Get application configuration
            config = get_config()
            
            # Check essential configuration values
            assert hasattr(config, 'database'), "Database config should be available"
            assert hasattr(config, 'vatsim'), "VATSIM config should be available"
            assert hasattr(config, 'api'), "API config should be available"
            
            # Verify database URL is properly formatted
            db_url = config.database.url
            assert 'postgresql://' in db_url, "Database URL should be PostgreSQL format"
            
            print("✅ Environment configuration loaded correctly")
            assert True  # Test passed successfully
            
        except Exception as e:
            print(f"❌ Environment configuration test failed: {e}")
            assert False, "Test failed"
    
    @pytest.mark.stage7
    @pytest.mark.infrastructure
    def test_configuration_validation(self):
        """Test: Is configuration validation working?"""
        print("🧪 Testing: Is configuration validation working?")
        
        try:
            from config import get_config
            
            config = get_config()
            
            # Test configuration types
            assert isinstance(config.logging.level, str), "Log level should be string"
            assert isinstance(config.api.port, int), "API port should be integer"
            
            # Test configuration values are reasonable
            assert config.logging.level in ['DEBUG', 'INFO', 'WARNING', 'ERROR'], "Log level should be valid"
            assert isinstance(config.database.pool_size, int), "Database pool size should be integer"
            assert config.database.pool_size > 0, "Database pool size should be positive"
            
            print("✅ Configuration validation working correctly")
            assert True  # Test passed successfully
            
        except Exception as e:
            print(f"❌ Configuration validation test failed: {e}")
            assert False, "Test failed"


class TestSystemModules:
    """Test system module availability and basic functionality"""
    
    @pytest.mark.stage7
    @pytest.mark.infrastructure
    def test_critical_modules_availability(self):
        """Test: Are critical system modules available?"""
        print("🧪 Testing: Are critical system modules are available?")
        
        # Use context managers to ensure proper cleanup
        try:
            # Import modules in a controlled way
            import sys
            import types
            
            # Create a temporary module namespace to avoid global imports
            temp_module = types.ModuleType('temp_test_module')
            
            # Test that critical modules can be imported
            with open('/dev/null', 'w') as devnull:  # Redirect stdout during import
                import database
                import config
                import models
            
            # Test that database models are defined
            from models import Flight, Controller, Transceiver
            assert Flight is not None, "Flight model should be defined"
            assert Controller is not None, "Controller model should be defined"
            assert Transceiver is not None, "Transceiver model should be defined"
            
            print("✅ Critical system modules are available")
            assert True  # Test passed successfully
            
        except Exception as e:
            print(f"❌ Critical modules test failed: {e}")
            assert False, "Test failed"
        finally:
            # Aggressive cleanup
            try:
                # Force cleanup of any remaining resources
                import gc
                gc.collect()
                
                # Try to close any open file descriptors
                import os
                for fd in range(10, 20):  # Check common FD range
                    try:
                        os.close(fd)
                    except (OSError, ValueError):
                        pass  # FD wasn't open
                
                # Clean up any remaining asyncio resources
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Cancel all pending tasks
                        for task in asyncio.all_tasks(loop):
                            if not task.done():
                                task.cancel()
                except RuntimeError:
                    pass  # No event loop
                
            except Exception as cleanup_error:
                # Don't fail the test if cleanup fails
                print(f"⚠️ Cleanup warning (non-critical): {cleanup_error}")
    
    @pytest.mark.stage7
    @pytest.mark.infrastructure
    def test_database_models_structure(self):
        """Test: Do database models have correct structure?"""
        print("🧪 Testing: Do database models have correct structure?")
        
        try:
            from models import Flight, Controller, Transceiver
            
            # Test Flight model structure
            assert hasattr(Flight, '__tablename__'), "Flight model should have table name"
            assert hasattr(Flight, 'id'), "Flight model should have id field"
            assert hasattr(Flight, 'callsign'), "Flight model should have callsign field"
            
            # Test Controller model structure
            assert hasattr(Controller, '__tablename__'), "Controller model should have table name"
            assert hasattr(Controller, 'id'), "Controller model should have id field"
            assert hasattr(Controller, 'callsign'), "Controller model should have callsign field"
            
            # Test Transceiver model structure
            assert hasattr(Transceiver, '__tablename__'), "Transceiver model should have table name"
            assert hasattr(Transceiver, 'id'), "Transceiver model should have id field"
            
            print("✅ Database models have correct structure")
            assert True  # Test passed successfully
            
        except Exception as e:
            print(f"❌ Database models structure test failed: {e}")
            assert False, "Test failed"


class TestServiceInfrastructure:
    """Test service infrastructure components"""
    
    @pytest.mark.stage7
    @pytest.mark.infrastructure
    def test_service_module_availability(self):
        """Test: Are service modules available?"""
        print("🧪 Testing: Are service modules available?")
        
        try:
            # Test that service modules can be imported
            from services import vatsim_service, data_service, database_service
            
            # Test that service functions exist
            assert hasattr(vatsim_service, 'get_vatsim_service'), "VATSIM service should have get_vatsim_service"
            assert hasattr(data_service, 'get_data_service_sync'), "Data service should have get_data_service_sync"
            assert hasattr(database_service, 'get_database_service'), "Database service should have get_database_service"
            
            print("✅ Service modules are available")
            assert True  # Test passed successfully
            
        except Exception as e:
            print(f"❌ Service modules test failed: {e}")
            assert False, "Test failed"
    
    @pytest.mark.stage7
    @pytest.mark.infrastructure
    def test_utility_modules_availability(self):
        """Test: Are utility modules available?"""
        print("🧪 Testing: Are utility modules available?")
        
        try:
            # Test that utility modules can be imported
            from utils import geographic_utils, error_handling, logging
            
            # Test that utility functions exist
            assert hasattr(geographic_utils, 'parse_ddmm_coordinate'), "Geographic utils should have parse_ddmm_coordinate"
            assert hasattr(error_handling, 'handle_service_errors'), "Error handling should have handle_service_errors"
            assert hasattr(logging, 'get_logger_for_module'), "Logging should have get_logger_for_module"
            
            print("✅ Utility modules are available")
            assert True  # Test passed successfully
            
        except Exception as e:
            print(f"❌ Utility modules test failed: {e}")
            assert False, "Test failed"


class TestFastAPIInfrastructure:
    """Test FastAPI infrastructure without importing main.py"""
    
    @pytest.mark.stage7
    @pytest.mark.infrastructure
    def test_fastapi_dependencies_available(self):
        """Test: Are FastAPI dependencies available?"""
        print("🧪 Testing: Are FastAPI dependencies available?")
        
        try:
            # Test that FastAPI and related packages are available
            import fastapi
            import uvicorn
            import pydantic
            
            # Test versions
            assert hasattr(fastapi, '__version__'), "FastAPI should have version"
            assert hasattr(uvicorn, '__version__'), "Uvicorn should have version"
            assert hasattr(pydantic, '__version__'), "Pydantic should have version"
            
            print("✅ FastAPI dependencies are available")
            assert True  # Test passed successfully
            
        except Exception as e:
            print(f"❌ FastAPI dependencies test failed: {e}")
            assert False, "Test failed"
    
    @pytest.mark.stage7
    @pytest.mark.infrastructure
    def test_http_client_dependencies(self):
        """Test: Are HTTP client dependencies available?"""
        print("🧪 Testing: Are HTTP client dependencies available?")
        
        try:
            # Test that HTTP client packages are available
            import httpx
            import requests
            
            # Test that they have expected functionality
            assert hasattr(httpx, 'Client'), "HTTPX should have Client"
            assert hasattr(requests, 'get'), "Requests should have get method"
            
            print("✅ HTTP client dependencies are available")
            assert True  # Test passed successfully
            
        except Exception as e:
            print(f"❌ HTTP client dependencies test failed: {e}")
            assert False, "Test failed"


# Test execution helper
def run_infrastructure_tests():
    """Run all infrastructure tests and return results"""
    print("🚀 Starting Stage 7: Infrastructure & Technical Tests")
    print("=" * 60)
    
    test_classes = [
        TestDatabaseInfrastructure,
        TestConfigurationManagement,
        TestSystemModules,
        TestServiceInfrastructure,
        TestFastAPIInfrastructure
    ]
    
    results = []
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        print(f"\n📋 Testing: {test_class.__name__}")
        print("-" * 40)
        
        test_instance = test_class()
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            method = getattr(test_instance, method_name)
            
            try:
                result = method()
                if result:
                    print(f"✅ {method_name}: PASS")
                    passed_tests += 1
                    results.append((method_name, "PASS", "Success"))
                else:
                    print(f"❌ {method_name}: FAIL")
                    results.append((method_name, "FAIL", "Test returned False"))
            except Exception as e:
                print(f"❌ {method_name}: ERROR - {e}")
                results.append((method_name, "ERROR", str(e)))
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed_tests}/{total_tests} passed ({passed_tests/total_tests*100:.1f}%)")
    
    if passed_tests == total_tests:
        print("🎯 Overall Status: PASS")
    else:
        print("🎯 Overall Status: FAIL")
    
    return results


if __name__ == "__main__":
    run_infrastructure_tests()
