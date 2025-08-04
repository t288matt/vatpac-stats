#!/usr/bin/env python3
"""
Apply SQLite Views for Australian Airports
==========================================

This script applies the SQLite-compatible views for Australian airports
to the database, updating Grafana dashboards to use the new Airports table.
"""

import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.config import get_config
from sqlalchemy import create_engine, text


def apply_sqlite_views():
    """Apply SQLite views for Australian airports"""
    try:
        config = get_config()
        engine = create_engine(config.database.url)
        
        # Read the SQLite views file
        sql_file = Path(__file__).parent / "create_australian_airports_view_sqlite.sql"
        
        with open(sql_file, 'r') as f:
            sql_script = f.read()
        
        # Execute the SQL script
        with engine.begin() as conn:
            # Split the script into individual statements
            statements = sql_script.split(';')
            
            for statement in statements:
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    conn.execute(text(statement))
        
        print("Successfully applied SQLite views for Australian airports")
        
        # Verify the views were created
        with engine.connect() as conn:
            # Check australian_airports view
            result = conn.execute(text("SELECT COUNT(*) FROM australian_airports"))
            australian_count = result.scalar()
            print(f"Australian airports view contains {australian_count} airports")
            
            # Check australian_flights view (if flights table exists)
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM australian_flights"))
                flights_count = result.scalar()
                print(f"Australian flights view contains {flights_count} flights")
            except Exception as e:
                print(f"Note: australian_flights view created but no flights data yet: {e}")
        
    except Exception as e:
        print(f"Error applying SQLite views: {e}")
        raise


def main():
    """Main function to apply SQLite views"""
    print("Applying SQLite views for Australian airports...")
    apply_sqlite_views()
    print("SQLite views applied successfully!")


if __name__ == "__main__":
    main() 