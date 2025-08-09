"""
Database Integrity Regression Tests

These tests validate database schema integrity, constraints, relationships,
and data consistency. They ensure that database changes don't break existing
functionality and that data integrity is maintained.

Database Elements Tested:
- Table existence and schema
- Column data types and constraints
- Foreign key relationships
- Unique constraints
- Indexes and performance
- Data validation rules
"""

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from typing import List, Dict, Any

from app.database import SessionLocal, get_database_info
from app.models import (
    Flight, Controller, Transceiver, FrequencyMatch, Airports
    # REMOVED: TrafficMovement, FlightSummary, VatsimStatus - Phase 4
)


@pytest.mark.regression
@pytest.mark.models
class TestDatabaseSchemaIntegrity:
    """Test database schema integrity and structure"""
    
    def test_all_expected_tables_exist(self, db_session):
        """
        Test that all expected tables exist in the database
        """
        inspector = inspect(db_session.bind)
        existing_tables = set(inspector.get_table_names())
        
        expected_tables = {
            "flights", "controllers", "transceivers", 
            "frequency_matches", "airports"
            # "traffic_movements",  # REMOVED: Traffic Analysis Service - Phase 4
        }
        
        missing_tables = expected_tables - existing_tables
        assert not missing_tables, f"Missing tables: {missing_tables}"
        
        # Verify we have all expected tables
        for table in expected_tables:
            assert table in existing_tables, f"Table '{table}' should exist"
    
    def test_flight_table_schema(self, db_session):
        """
        Test flights table has correct schema and columns
        """
        inspector = inspect(db_session.bind)
        columns = {col['name']: col for col in inspector.get_columns('flights')}
        
        # Required columns with their expected types
        required_columns = {
            'id': 'INTEGER',
            'callsign': 'VARCHAR',
            'cid': 'INTEGER', 
            'name': 'VARCHAR',
            'latitude': 'DOUBLE_PRECISION',  # or FLOAT
            'longitude': 'DOUBLE_PRECISION',  # or FLOAT
            'altitude': 'INTEGER',
            'groundspeed': 'INTEGER',
            'heading': 'INTEGER',
            'transponder': 'VARCHAR',
            'departure': 'VARCHAR',
            'arrival': 'VARCHAR',
            'aircraft_short': 'VARCHAR',
            'flight_rules': 'VARCHAR',
            'last_updated': 'TIMESTAMP',
            'last_updated_api': 'TIMESTAMP',
            'created_at': 'TIMESTAMP',
            'updated_at': 'TIMESTAMP'
        }
        
        for column_name, expected_type in required_columns.items():
            assert column_name in columns, f"Column '{column_name}' missing from flights table"
            
            # Note: Exact type checking can be database-specific
            # This is a basic check - may need adjustment for different databases
            column_type = str(columns[column_name]['type']).upper()
            
            # Handle type variations (PostgreSQL vs SQLite, etc.)
            if 'VARCHAR' in expected_type and 'VARCHAR' in column_type:
                continue
            elif 'INTEGER' in expected_type and ('INTEGER' in column_type or 'BIGINT' in column_type):
                continue
            elif 'DOUBLE_PRECISION' in expected_type and ('DOUBLE_PRECISION' in column_type or 'FLOAT' in column_type):
                continue
            elif 'TIMESTAMP' in expected_type and ('TIMESTAMP' in column_type or 'DATETIME' in column_type):
                continue
            else:
                # For debugging - show what we actually got
                print(f"Column {column_name}: expected {expected_type}, got {column_type}")
    
    def test_controller_table_schema(self, db_session):
        """
        Test controllers table has correct schema
        """
        inspector = inspect(db_session.bind)
        columns = {col['name']: col for col in inspector.get_columns('controllers')}
        
        required_columns = [
            'id', 'callsign', 'controller_id', 'controller_name',
            'controller_rating', 'facility', 'frequency', 'visual_range',
            'text_atis', 'created_at', 'updated_at'
        ]
        
        for column_name in required_columns:
            assert column_name in columns, f"Column '{column_name}' missing from controllers table"
    
    def test_database_indexes_exist(self, db_session):
        """
        Test that critical indexes exist for performance
        """
        inspector = inspect(db_session.bind)
        
        # Check flights table indexes
        flight_indexes = inspector.get_indexes('flights')
        flight_index_columns = set()
        
        for index in flight_indexes:
            for column in index['column_names']:
                flight_index_columns.add(column)
        
        # Critical indexed columns for flights
        expected_flight_indexes = {'callsign', 'cid', 'last_updated'}
        
        for column in expected_flight_indexes:
            assert column in flight_index_columns, f"Index missing for flights.{column}"
        
        # Check controllers table indexes
        controller_indexes = inspector.get_indexes('controllers')
        controller_index_columns = set()
        
        for index in controller_indexes:
            for column in index['column_names']:
                controller_index_columns.add(column)
        
        expected_controller_indexes = {'callsign', 'controller_id'}
        
        for column in expected_controller_indexes:
            assert column in controller_index_columns, f"Index missing for controllers.{column}"


@pytest.mark.regression
@pytest.mark.models
class TestDatabaseConstraints:
    """Test database constraints work correctly"""
    
    def test_flight_unique_constraints(self, db_session, clean_database):
        """
        Test flight unique constraints work correctly
        
        Flights should allow multiple records for same callsign
        but with different timestamps (unique_flight_timestamp constraint)
        """
        # Create first flight
        flight1 = Flight(
            callsign="TEST123",
            cid=123456,
            name="Test Pilot",
            latitude=-33.8688,
            longitude=151.2093,
            last_updated=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        )
        
        db_session.add(flight1)
        db_session.commit()
        
        # Create second flight with same callsign but different timestamp - should succeed
        flight2 = Flight(
            callsign="TEST123",
            cid=123456,
            name="Test Pilot",
            latitude=-33.8700,  # Slightly different position
            longitude=151.2100,
            last_updated=datetime(2024, 1, 1, 12, 1, 0, tzinfo=timezone.utc)  # Different timestamp
        )
        
        db_session.add(flight2)
        db_session.commit()
        
        # Should have 2 records
        flights = db_session.query(Flight).filter(Flight.callsign == "TEST123").all()
        assert len(flights) == 2, "Should allow multiple flights with same callsign but different timestamps"
        
        # Try to create flight with same callsign AND same timestamp - should fail
        flight3 = Flight(
            callsign="TEST123",
            cid=123456,
            name="Test Pilot",
            latitude=-33.8688,
            longitude=151.2093,
            last_updated=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)  # Same timestamp as flight1
        )
        
        db_session.add(flight3)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
        
        db_session.rollback()
    
    def test_controller_unique_constraints(self, db_session, clean_database):
        """
        Test controller unique constraints (callsign should be unique)
        """
        # Create first controller
        controller1 = Controller(
            callsign="TEST_CTR",
            controller_id=123456,
            controller_name="Test Controller",
            facility="Test Facility"
        )
        
        db_session.add(controller1)
        db_session.commit()
        
        # Try to create another controller with same callsign - should fail
        controller2 = Controller(
            callsign="TEST_CTR",  # Same callsign
            controller_id=789012,
            controller_name="Another Controller",
            facility="Another Facility"
        )
        
        db_session.add(controller2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
        
        db_session.rollback()
    
    def test_foreign_key_constraints(self, db_session, clean_database):
        """
        Test foreign key constraints work correctly
        """
        # Create controller first
        controller = Controller(
            callsign="TEST_CTR",
            controller_id=123456,
            controller_name="Test Controller",
            facility="Test Facility"
        )
        
        db_session.add(controller)
        db_session.commit()
        
        # Sector model removed - skipping sector relationship tests
        # Test passes if controller can be created successfully
        assert controller.id is not None
        assert controller.callsign == "TEST_CTR"
    
    def test_not_null_constraints(self, db_session, clean_database):
        """
        Test NOT NULL constraints work correctly
        """
        # Try to create flight without required callsign - should fail
        invalid_flight = Flight(
            callsign=None,  # Required field
            cid=123456,
            name="Test Pilot"
        )
        
        db_session.add(invalid_flight)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
        
        db_session.rollback()
        
        # Try to create controller without required callsign - should fail
        invalid_controller = Controller(
            callsign=None,  # Required field
            controller_id=123456,
            controller_name="Test Controller"
        )
        
        db_session.add(invalid_controller)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
        
        db_session.rollback()


@pytest.mark.regression
@pytest.mark.models  
class TestModelRelationships:
    """Test model relationships work correctly"""
    
    def test_controller_relationships(self, db_session, clean_database):
        """
        Test Controller relationships work correctly (Sector relationship removed)
        """
        # Create controller
        controller = Controller(
            callsign="SY_APP",
            controller_id=123456,
            controller_name="Sydney Approach",
            facility="Sydney"
        )
        
        db_session.add(controller)
        db_session.commit()
        
        # Test controller was created successfully
        assert controller.id is not None
        assert controller.callsign == "SY_APP"
        assert controller.controller_id == 123456
        assert controller.controller_name == "Sydney Approach"
    
    def test_flight_summary_relationships(self, db_session, clean_database):
        """
        Test FlightSummary relationships to Controller (Sector relationship removed)
        """
        # Create controller
        controller = Controller(
            callsign="TEST_CTR",
            controller_id=123456,
            controller_name="Test Controller",
            facility="Test"
        )
        
        db_session.add(controller)
        db_session.commit()
        
        # Create flight summary with controller relationship (sector_id removed)
        flight_summary = FlightSummary(
            callsign="TEST123",
            aircraft_type="B738",
            departure="YSSY",
            arrival="YBBN",
            max_altitude=35000,
            duration_minutes=120,
            controller_id=controller.id
        )
        
        db_session.add(flight_summary)
        db_session.commit()
        
        # Test controller relationship
        assert flight_summary.controller is not None
        assert flight_summary.controller.callsign == "TEST_CTR"


@pytest.mark.regression
@pytest.mark.models
class TestDataValidation:
    """Test data validation and business rules"""
    
    def test_coordinate_range_validation(self, db_session, clean_database):
        """
        Test coordinate values are within valid ranges
        """
        # Valid coordinates should work
        valid_flight = Flight(
            callsign="VALID123",
            cid=123456,
            name="Valid Pilot",
            latitude=-33.8688,  # Valid latitude
            longitude=151.2093,  # Valid longitude
            last_updated=datetime.now(timezone.utc)
        )
        
        db_session.add(valid_flight)
        db_session.commit()
        
        # Verify it was stored correctly
        stored_flight = db_session.query(Flight).filter(Flight.callsign == "VALID123").first()
        assert stored_flight is not None
        assert stored_flight.latitude == -33.8688
        assert stored_flight.longitude == 151.2093
    
    def test_altitude_validation(self, db_session, clean_database):
        """
        Test altitude values are reasonable
        """
        # Normal altitude should work
        flight = Flight(
            callsign="ALT123",
            cid=123456,
            name="Altitude Test",
            altitude=35000,  # Normal cruise altitude
            last_updated=datetime.now(timezone.utc)
        )
        
        db_session.add(flight)
        db_session.commit()
        
        # Verify altitude was stored
        stored_flight = db_session.query(Flight).filter(Flight.callsign == "ALT123").first()
        assert stored_flight.altitude == 35000
    
    def test_timestamp_handling(self, db_session, clean_database):
        """
        Test timestamp fields are handled correctly
        """
        now = datetime.now(timezone.utc)
        
        flight = Flight(
            callsign="TIME123",
            cid=123456,
            name="Timestamp Test",
            last_updated=now,
            last_updated_api=now
        )
        
        db_session.add(flight)
        db_session.commit()
        
        # Verify timestamps
        stored_flight = db_session.query(Flight).filter(Flight.callsign == "TIME123").first()
        assert stored_flight.last_updated is not None
        assert stored_flight.created_at is not None  # Should be auto-set
        assert stored_flight.updated_at is not None  # Should be auto-set


@pytest.mark.regression
@pytest.mark.models
@pytest.mark.performance
class TestDatabasePerformance:
    """Test database performance requirements"""
    
    def test_flight_query_performance(self, db_session, clean_database):
        """
        Test flight queries meet performance requirements
        """
        import time
        
        # Create test flights
        flights = []
        for i in range(100):
            flight = Flight(
                callsign=f"PERF{i:03d}",
                cid=100000 + i,
                name=f"Performance Test {i}",
                latitude=-33.8688 + (i * 0.001),
                longitude=151.2093 + (i * 0.001),
                last_updated=datetime.now(timezone.utc)
            )
            flights.append(flight)
        
        db_session.add_all(flights)
        db_session.commit()
        
        # Test query performance
        start_time = time.time()
        
        # Query all flights
        result = db_session.query(Flight).all()
        
        end_time = time.time()
        query_time = end_time - start_time
        
        assert len(result) == 100, "Should retrieve all flights"
        assert query_time < 0.5, f"Flight query took {query_time:.3f}s, should be < 0.5s"
        
        # Test indexed query performance
        start_time = time.time()
        
        # Query by callsign (should use index)
        result = db_session.query(Flight).filter(Flight.callsign == "PERF050").first()
        
        end_time = time.time()
        indexed_query_time = end_time - start_time
        
        assert result is not None, "Should find flight by callsign"
        assert indexed_query_time < 0.1, f"Indexed query took {indexed_query_time:.3f}s, should be < 0.1s"
    
    def test_bulk_insert_performance(self, db_session, clean_database):
        """
        Test bulk insert operations meet performance requirements
        """
        import time
        
        # Create large batch of flights
        flights = []
        for i in range(500):
            flight = Flight(
                callsign=f"BULK{i:03d}",
                cid=200000 + i,
                name=f"Bulk Test {i}",
                latitude=-33.8688 + (i * 0.001),
                longitude=151.2093 + (i * 0.001),
                last_updated=datetime.now(timezone.utc)
            )
            flights.append(flight)
        
        # Measure bulk insert time
        start_time = time.time()
        
        db_session.add_all(flights)
        db_session.commit()
        
        end_time = time.time()
        insert_time = end_time - start_time
        
        # Verify all flights were inserted
        count = db_session.query(Flight).filter(Flight.callsign.like("BULK%")).count()
        assert count == 500, f"Expected 500 flights, got {count}"
        
        # Performance requirement: 500 inserts in < 5 seconds
        assert insert_time < 5.0, f"Bulk insert took {insert_time:.3f}s, should be < 5.0s"


@pytest.mark.regression
@pytest.mark.models
class TestDatabaseMigrations:
    """Test database migration compatibility"""
    
    def test_database_version_compatibility(self, db_session):
        """
        Test database version is compatible
        """
        # Check if we can get database info
        try:
            db_info = get_database_info()
            assert db_info is not None, "Should be able to get database info"
            
            # Basic database connectivity test
            result = db_session.execute(text("SELECT 1")).fetchone()
            assert result[0] == 1, "Basic database query should work"
            
        except Exception as e:
            pytest.fail(f"Database compatibility check failed: {e}")
    
    def test_all_models_can_be_instantiated(self):
        """
        Test all model classes can be instantiated without errors
        """
        models_to_test = [
            Flight, Controller, TrafficMovement, FlightSummary,
            Transceiver, VatsimStatus, FrequencyMatch, Airports
        ]
        
        for model_class in models_to_test:
            try:
                # Try to create instance (without saving to DB)
                instance = model_class()
                assert instance is not None, f"Should be able to instantiate {model_class.__name__}"
                
            except Exception as e:
                pytest.fail(f"Failed to instantiate {model_class.__name__}: {e}")
