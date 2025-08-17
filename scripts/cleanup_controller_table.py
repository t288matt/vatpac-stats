#!/usr/bin/env python3
"""
Controller Table Cleanup Script

This script removes all rows from the controller table where the callsign
is not in the valid Australian controller callsigns list.

Usage:
    python scripts/cleanup_controller_table.py [--dry-run] [--callsign-file PATH]

Options:
    --dry-run          Show what would be deleted without actually deleting
    --callsign-file    Path to callsign list file (default: config/controller_callsigns_list.txt)
    --help             Show this help message

Example:
    # Dry run to see what would be deleted
    python scripts/cleanup_controller_table.py --dry-run
    
    # Actually perform the cleanup
    python scripts/cleanup_controller_table.py
    
    # Use custom callsign file
    python scripts/cleanup_controller_table.py --callsign-file /custom/path/callsigns.txt
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Set, List, Tuple
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_config
from app.database import get_sync_session
from app.models import Controller
from app.filters.controller_callsign_filter import ControllerCallsignFilter


def setup_logging() -> logging.Logger:
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'controller_cleanup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    return logging.getLogger(__name__)


def load_valid_callsigns(callsign_file_path: str) -> Set[str]:
    """
    Load valid callsigns from the specified file.
    
    Args:
        callsign_file_path: Path to the callsign list file
        
    Returns:
        Set of valid callsigns
        
    Raises:
        FileNotFoundError: If the callsign file doesn't exist
        ValueError: If the file is empty or can't be read
    """
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


def get_controller_stats(session) -> Tuple[int, List[Tuple[str, int]]]:
    """
    Get statistics about controllers in the database.
    
    Args:
        session: Database session
        
    Returns:
        Tuple of (total_count, list of (callsign, count) tuples)
    """
    # Get total count
    total_count = session.query(Controller).count()
    
    # Get callsign distribution
    callsign_counts = session.query(
        Controller.callsign,
        session.query(Controller).filter(Controller.callsign == Controller.callsign).count()
    ).distinct().all()
    
    return total_count, callsign_counts


def get_invalid_controllers(session, valid_callsigns: Set[str]) -> List[Controller]:
    """
    Get all controllers with invalid callsigns.
    
    Args:
        session: Database session
        valid_callsigns: Set of valid callsigns
        
    Returns:
        List of Controller objects with invalid callsigns
    """
    return session.query(Controller).filter(
        ~Controller.callsign.in_(valid_callsigns)
    ).all()


def cleanup_controller_table(
    session,
    valid_callsigns: Set[str],
    dry_run: bool = False
) -> Tuple[int, int, int]:
    """
    Clean up the controller table by removing invalid callsigns.
    
    Args:
        session: Database session
        valid_callsigns: Set of valid callsigns
        dry_run: If True, don't actually delete, just show what would be deleted
        
    Returns:
        Tuple of (total_controllers, valid_controllers, invalid_controllers)
    """
    logger = logging.getLogger(__name__)
    
    # Get current statistics
    total_count, callsign_distribution = get_controller_stats(session)
    logger.info(f"Current controller table stats:")
    logger.info(f"  Total controllers: {total_count}")
    logger.info(f"  Unique callsigns: {len(callsign_distribution)}")
    
    # Show callsign distribution
    logger.info("  Callsign distribution:")
    for callsign, count in sorted(callsign_distribution, key=lambda x: x[1], reverse=True)[:20]:
        status = "✓" if callsign in valid_callsigns else "✗"
        logger.info(f"    {status} {callsign}: {count}")
    
    if len(callsign_distribution) > 20:
        logger.info(f"    ... and {len(callsign_distribution) - 20} more callsigns")
    
    # Get invalid controllers
    invalid_controllers = get_invalid_controllers(session, valid_callsigns)
    invalid_count = len(invalid_controllers)
    valid_count = total_count - invalid_count
    
    logger.info(f"\nCleanup analysis:")
    logger.info(f"  Valid callsigns loaded: {len(valid_callsigns)}")
    logger.info(f"  Controllers with valid callsigns: {valid_count}")
    logger.info(f"  Controllers with invalid callsigns: {invalid_count}")
    
    if invalid_count == 0:
        logger.info("  ✓ No cleanup needed - all controllers have valid callsigns!")
        return total_count, valid_count, invalid_count
    
    # Show some examples of invalid callsigns
    invalid_callsigns = list(set(c.callsign for c in invalid_controllers))
    logger.info(f"\nExamples of invalid callsigns that would be removed:")
    for callsign in sorted(invalid_callsigns)[:10]:
        count = sum(1 for c in invalid_controllers if c.callsign == callsign)
        logger.info(f"  {callsign}: {count} controllers")
    
    if len(invalid_callsigns) > 10:
        logger.info(f"  ... and {len(invalid_callsigns) - 10} more invalid callsigns")
    
    if dry_run:
        logger.info(f"\n🔍 DRY RUN MODE - No changes will be made")
        logger.info(f"  Would remove {invalid_count} controllers with invalid callsigns")
        logger.info(f"  Would keep {valid_count} controllers with valid callsigns")
        return total_count, valid_count, invalid_count
    
    # Perform the actual cleanup
    logger.info(f"\n🗑️  Starting cleanup...")
    
    try:
        # Delete invalid controllers
        deleted_count = session.query(Controller).filter(
            ~Controller.callsign.in_(valid_callsigns)
        ).delete()
        
        # Commit the changes
        session.commit()
        
        logger.info(f"✅ Cleanup completed successfully!")
        logger.info(f"  Removed {deleted_count} controllers with invalid callsigns")
        logger.info(f"  Kept {valid_count} controllers with valid callsigns")
        
        # Verify the cleanup
        remaining_count = session.query(Controller).count()
        logger.info(f"  Total controllers remaining: {remaining_count}")
        
        if remaining_count != valid_count:
            logger.warning(f"  ⚠️  Expected {valid_count} controllers, but found {remaining_count}")
        
        return total_count, valid_count, deleted_count
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        session.rollback()
        raise


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Clean up controller table by removing invalid callsigns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    
    parser.add_argument(
        '--callsign-file',
        default='config/controller_callsigns_list.txt',
        help='Path to callsign list file (default: config/controller_callsigns_list.txt)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging()
    
    logger.info("🚀 Controller Table Cleanup Script")
    logger.info("=" * 50)
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = get_config()
        logger.info(f"Database: {config.database.url}")
        logger.info(f"Callsign file: {args.callsign_file}")
        
        # Load valid callsigns
        logger.info("Loading valid callsigns...")
        valid_callsigns = load_valid_callsigns(args.callsign_file)
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
            # Perform cleanup
            total, valid, invalid = cleanup_controller_table(
                session=session,
                valid_callsigns=valid_callsigns,
                dry_run=args.dry_run
            )
            
            # Summary
            logger.info("\n" + "=" * 50)
            if args.dry_run:
                logger.info("🔍 DRY RUN COMPLETED")
                logger.info(f"Would remove {invalid} controllers")
                logger.info(f"Would keep {valid} controllers")
            else:
                logger.info("✅ CLEANUP COMPLETED")
                logger.info(f"Removed {invalid} controllers")
                logger.info(f"Kept {valid} controllers")
            
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
