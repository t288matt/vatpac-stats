#!/usr/bin/env python3
"""
Delete Invalid Controllers Script

This script deletes rows from the controllers table where the controller
isn't in the controller callsigns list. Designed to run inside the Docker container.

Usage:
    python scripts/delete_invalid_controllers.py [--dry-run]

Options:
    --dry-run          Show what would be deleted without actually deleting
    --help             Show this help message

Example:
    # Dry run to see what would be deleted
    python scripts/delete_invalid_controllers.py --dry-run
    
    # Actually perform the deletion
    python scripts/delete_invalid_controllers.py
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Set
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_config
from app.database import get_sync_session
from app.models import Controller


def setup_logging() -> logging.Logger:
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'delete_invalid_controllers_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    return logging.getLogger(__name__)


def load_valid_callsigns() -> Set[str]:
    """
    Load valid callsigns from the controller callsigns list file.
    Uses the path that's mounted inside the Docker container.
    
    Returns:
        Set of valid callsigns
        
    Raises:
        FileNotFoundError: If the callsign file doesn't exist
        ValueError: If the file is empty or can't be read
    """
    # Use the path that's mounted inside the Docker container
    # This matches the volume mount in docker-compose.yml
    callsign_file_path = '/app/airspace_sector_data/controller_callsigns_list.txt'
    file_path = Path(callsign_file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Callsign file not found: {callsign_file_path}")
    
    callsigns = set()
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            callsign = line.strip()
            if callsign and not callsign.startswith('#'):
                callsigns.add(callsign)
    
    if not callsigns:
        raise ValueError(f"No valid callsigns found in {callsign_file_path}")
    
    return callsigns


def delete_invalid_controllers(session, valid_callsigns: Set[str], dry_run: bool = False) -> int:
    """
    Delete controllers with invalid callsigns.
    
    Args:
        session: Database session
        valid_callsigns: Set of valid callsigns
        dry_run: If True, don't actually delete, just show what would be deleted
        
    Returns:
        Number of controllers that would be/were deleted
    """
    logger = logging.getLogger(__name__)
    
    # Get current statistics
    total_count = session.query(Controller).count()
    logger.info(f"Total controllers in database: {total_count}")
    
    # Count invalid controllers
    invalid_count = session.query(Controller).filter(
        ~Controller.callsign.in_(valid_callsigns)
    ).count()
    
    valid_count = total_count - invalid_count
    logger.info(f"Controllers with valid callsigns: {valid_count}")
    logger.info(f"Controllers with invalid callsigns: {invalid_count}")
    
    if invalid_count == 0:
        logger.info("✓ No invalid controllers found - no deletion needed!")
        return 0
    
    # Show some examples of invalid callsigns
    invalid_controllers = session.query(Controller).filter(
        ~Controller.callsign.in_(valid_callsigns)
    ).limit(10).all()
    
    logger.info(f"\nExamples of invalid callsigns that would be removed:")
    for controller in invalid_controllers:
        logger.info(f"  {controller.callsign} (ID: {controller.id})")
    
    if invalid_count > 10:
        logger.info(f"  ... and {invalid_count - 10} more invalid controllers")
    
    if dry_run:
        logger.info(f"\n🔍 DRY RUN MODE - No changes will be made")
        logger.info(f"Would delete {invalid_count} controllers with invalid callsigns")
        return invalid_count
    
    # Perform the actual deletion
    logger.info(f"\n🗑️  Starting deletion...")
    
    try:
        # Delete invalid controllers
        deleted_count = session.query(Controller).filter(
            ~Controller.callsign.in_(valid_callsigns)
        ).delete()
        
        # Commit the changes
        session.commit()
        
        logger.info(f"✅ Deletion completed successfully!")
        logger.info(f"Removed {deleted_count} controllers with invalid callsigns")
        
        # Verify the deletion
        remaining_count = session.query(Controller).count()
        logger.info(f"Total controllers remaining: {remaining_count}")
        
        return deleted_count
        
    except Exception as e:
        logger.error(f"❌ Deletion failed: {e}")
        session.rollback()
        raise


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Delete controllers with invalid callsigns from the controllers table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging()
    
    logger.info("🚀 Delete Invalid Controllers Script")
    logger.info("=" * 50)
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = get_config()
        logger.info(f"Database: {config.database.url}")
        
        # Load valid callsigns
        logger.info("Loading valid callsigns...")
        valid_callsigns = load_valid_callsigns()
        logger.info(f"Loaded {len(valid_callsigns)} valid callsigns")
        
        # Show some examples
        sample_callsigns = sorted(list(valid_callsigns))[:10]
        logger.info(f"Sample valid callsigns: {', '.join(sample_callsigns)}")
        if len(valid_callsigns) > 10:
            logger.info(f"... and {len(valid_callsigns) - 10} more")
        
        # Get database session
        logger.info("Connecting to database...")
        session = get_sync_session()
        
        try:
            # Perform deletion
            deleted_count = delete_invalid_controllers(
                session=session,
                valid_callsigns=valid_callsigns,
                dry_run=args.dry_run
            )
            
            # Summary
            logger.info("\n" + "=" * 50)
            if args.dry_run:
                logger.info("🔍 DRY RUN COMPLETED")
                logger.info(f"Would delete {deleted_count} controllers")
            else:
                logger.info("✅ DELETION COMPLETED")
                logger.info(f"Deleted {deleted_count} controllers")
            
        finally:
            session.close()
            logger.info("Database connection closed")
            
    except FileNotFoundError as e:
        logger.error(f"❌ File not found: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"❌ Invalid file content: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)
    
    logger.info("🎉 Script completed successfully!")


if __name__ == '__main__':
    main()
