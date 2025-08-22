#!/usr/bin/env python3
"""
Script to update all controller names in the controllers table to 'x'
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def get_database_connection():
    """Get database connection from environment variables"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        # Fallback to default values if environment variable not set
        database_url = "postgresql://vatsim_user:vatsim_password@localhost:5432/vatsim_data"
    
    try:
        engine = create_engine(database_url)
        return engine
    except Exception as e:
        print(f"Error creating database connection: {e}")
        return None

def update_controller_names():
    """Update all controller names to 'x'"""
    engine = get_database_connection()
    if not engine:
        print("Failed to establish database connection")
        return False
    
    try:
        with engine.connect() as connection:
            # First, let's see how many records we're about to update
            count_result = connection.execute(text("SELECT COUNT(*) FROM controllers"))
            total_count = count_result.scalar()
            print(f"Found {total_count} records in controllers table")
            
            if total_count == 0:
                print("No records to update")
                return True
            
            # Show a sample of current names
            sample_result = connection.execute(text("SELECT DISTINCT name FROM controllers LIMIT 5"))
            sample_names = [row[0] for row in sample_result]
            print(f"Sample of current names: {sample_names}")
            
            # Confirm the update
            print("\nWARNING: This will update ALL controller names to 'x'")
            print("This action cannot be easily undone!")
            confirm = input("Type 'YES' to confirm: ")
            
            if confirm != 'YES':
                print("Update cancelled")
                return False
            
            # Perform the update
            print("Updating controller names...")
            update_result = connection.execute(
                text("UPDATE controllers SET name = 'x', updated_at = NOW()")
            )
            
            # Commit the transaction
            connection.commit()
            
            print(f"Successfully updated {update_result.rowcount} records")
            
            # Verify the update
            verify_result = connection.execute(text("SELECT COUNT(*) FROM controllers WHERE name = 'x'"))
            updated_count = verify_result.scalar()
            print(f"Verified: {updated_count} records now have name = 'x'")
            
            return True
            
    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
    finally:
        if engine:
            engine.dispose()

def main():
    """Main function"""
    print("Controller Name Update Script")
    print("=" * 40)
    
    success = update_controller_names()
    
    if success:
        print("\n✅ Update completed successfully")
    else:
        print("\n❌ Update failed")
        sys.exit(1)

if __name__ == "__main__":
    main()




