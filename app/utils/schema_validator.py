#!/usr/bin/env python3
"""
Database Schema Validation Utility

This module provides schema validation to ensure all required tables and fields
exist in the database. It's designed to run on application startup to catch
schema mismatches early and provide helpful error messages.

USAGE:
    from app.utils.schema_validator import validate_database_schema
    validate_database_schema(db_session)
"""

import logging
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

# Required tables and their expected columns
REQUIRED_TABLES = {
    'controllers': [
        'id', 'callsign', 'facility', 'position', 'status', 'frequency',
        'last_seen', 'workload_score', 'preferences', 'created_at', 'updated_at'
    ],
    'flights': [
        'id', 'callsign', 'aircraft_type', 'position_lat', 'position_lng',
        'altitude', 'heading',
        'transponder', 'last_updated', 'created_at',
        'departure', 'arrival', 'route', 'status', 'updated_at'
    ],
    'traffic_movements': [
        'id', 'airport_code', 'movement_type', 'aircraft_callsign',
        'aircraft_type', 'timestamp', 'runway', 'altitude',
        'heading', 'metadata_json', 'created_at', 'updated_at'
    ],
    'airports': [
        'id', 'icao_code', 'name', 'latitude', 'longitude', 'elevation',
        'country', 'region'
    ],
    'transceivers': [
        'id', 'callsign', 'transceiver_id', 'frequency', 'position_lat',
        'position_lon', 'height_msl', 'height_agl', 'entity_type',
        'entity_id', 'timestamp', 'updated_at'
    ]
}

def validate_database_schema(db_session) -> Tuple[bool, List[str]]:
    """
    Validate that all required tables and columns exist in the database.
    
    Args:
        db_session: SQLAlchemy database session
        
    Returns:
        Tuple[bool, List[str]]: (is_valid, list_of_errors)
    """
    errors = []
    inspector = inspect(db_session.bind)
    
    # Get all existing tables
    existing_tables = inspector.get_table_names()
    
    logger.info(f"Validating database schema. Found {len(existing_tables)} existing tables.")
    
    # Check each required table
    for table_name, required_columns in REQUIRED_TABLES.items():
        if table_name not in existing_tables:
            error_msg = f"Missing required table: {table_name}"
            logger.error(error_msg)
            errors.append(error_msg)
            continue
            
        # Get existing columns for this table
        try:
            existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
        except Exception as e:
            error_msg = f"Failed to get columns for table {table_name}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            continue
            
        # Check for missing columns
        missing_columns = set(required_columns) - set(existing_columns)
        if missing_columns:
            error_msg = f"Table '{table_name}' missing columns: {', '.join(missing_columns)}"
            logger.error(error_msg)
            errors.append(error_msg)
        else:
            logger.info(f"✓ Table '{table_name}' schema is valid")
    
    # Check for extra tables (optional warning)
    extra_tables = set(existing_tables) - set(REQUIRED_TABLES.keys())
    if extra_tables:
        logger.warning(f"Found extra tables in database: {', '.join(extra_tables)}")
    
    is_valid = len(errors) == 0
    
    if is_valid:
        logger.info("✓ Database schema validation passed")
    else:
        logger.error(f"✗ Database schema validation failed with {len(errors)} errors")
        
    return is_valid, errors

def create_missing_tables_and_columns(db_session) -> Tuple[bool, List[str]]:
    """
    Attempt to create missing tables and columns based on the init.sql script.
    This is a fallback for when the init script didn't run properly.
    
    Args:
        db_session: SQLAlchemy database session
        
    Returns:
        Tuple[bool, List[str]]: (success, list_of_errors)
    """
    errors = []
    
    try:
        # Read and execute the init.sql script
        with open('database/init.sql', 'r') as f:
            init_script = f.read()
            
        # Split the script into individual statements
        statements = [stmt.strip() for stmt in init_script.split(';') if stmt.strip()]
        
        for statement in statements:
            if statement and not statement.startswith('--'):
                try:
                    db_session.execute(text(statement))
                    logger.info(f"Executed: {statement[:50]}...")
                except Exception as e:
                    # Ignore errors for statements that might already exist
                    if "already exists" not in str(e).lower():
                        error_msg = f"Failed to execute statement: {str(e)}"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        
        db_session.commit()
        logger.info("✓ Database initialization script executed")
        
    except Exception as e:
        error_msg = f"Failed to execute database initialization: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
        db_session.rollback()
    
    return len(errors) == 0, errors

def ensure_database_schema(db_session) -> bool:
    """
    Main function to ensure database schema is correct.
    Validates schema and attempts to fix issues if found.
    
    Args:
        db_session: SQLAlchemy database session
        
    Returns:
        bool: True if schema is valid, False otherwise
    """
    logger.info("Starting database schema validation...")
    
    # First, validate the current schema
    is_valid, errors = validate_database_schema(db_session)
    
    if is_valid:
        return True
        
    logger.warning(f"Schema validation failed with {len(errors)} errors. Attempting to fix...")
    
    # Try to fix the schema by running the init script
    fix_success, fix_errors = create_missing_tables_and_columns(db_session)
    
    if fix_success:
        # Re-validate after fix attempt
        is_valid, errors = validate_database_schema(db_session)
        if is_valid:
            logger.info("✓ Database schema fixed and validated successfully")
            return True
        else:
            logger.error(f"✗ Schema still invalid after fix attempt: {errors}")
            return False
    else:
        logger.error(f"✗ Failed to fix database schema: {fix_errors}")
        return False

def get_schema_status(db_session) -> Dict[str, any]:
    """
    Get a detailed status report of the database schema.
    
    Args:
        db_session: SQLAlchemy database session
        
    Returns:
        Dict containing schema status information
    """
    inspector = inspect(db_session.bind)
    existing_tables = inspector.get_table_names()
    
    status = {
        'total_required_tables': len(REQUIRED_TABLES),
        'existing_tables': len(existing_tables),
        'missing_tables': [],
        'valid_tables': [],
        'invalid_tables': [],
        'extra_tables': list(set(existing_tables) - set(REQUIRED_TABLES.keys()))
    }
    
    for table_name, required_columns in REQUIRED_TABLES.items():
        if table_name not in existing_tables:
            status['missing_tables'].append(table_name)
            continue
            
        try:
            existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
            missing_columns = set(required_columns) - set(existing_columns)
            
            if missing_columns:
                status['invalid_tables'].append({
                    'table': table_name,
                    'missing_columns': list(missing_columns)
                })
            else:
                status['valid_tables'].append(table_name)
        except Exception:
            status['invalid_tables'].append({
                'table': table_name,
                'error': 'Failed to inspect table'
            })
    
    status['is_valid'] = len(status['missing_tables']) == 0 and len(status['invalid_tables']) == 0
    
    return status 
