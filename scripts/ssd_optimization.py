#!/usr/bin/env python3
"""
SSD Optimization Script - VATSIM Data Collection
Monitors and optimizes SSD wear for long-running data collection
"""

import sqlite3
import os
import time
import logging
from datetime import datetime, timedelta
import psutil
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SSDOptimizer:
    def __init__(self, db_path: str = "atc_optimization.db"):
        self.db_path = db_path
        self.backup_dir = "backups"
        self.optimization_stats = {
            'total_writes': 0,
            'last_optimization': None,
            'database_size': 0,
            'fragmentation_level': 0
        }
        
    def optimize_database(self):
        """Optimize database for SSD wear reduction"""
        try:
            logger.info("Starting SSD optimization...")
            
            # 1. Check database size
            self._check_database_size()
            
            # 2. Analyze fragmentation
            self._analyze_fragmentation()
            
            # 3. Optimize database structure
            self._optimize_structure()
            
            # 4. Create backup if needed
            self._create_backup_if_needed()
            
            # 5. Vacuum database
            self._vacuum_database()
            
            logger.info("SSD optimization completed successfully")
            
        except Exception as e:
            logger.error(f"Error during SSD optimization: {e}")
    
    def _check_database_size(self):
        """Check current database size"""
        try:
            if os.path.exists(self.db_path):
                size = os.path.getsize(self.db_path)
                self.optimization_stats['database_size'] = size
                logger.info(f"Database size: {size / (1024*1024):.2f} MB")
                
                # Warn if database is getting large
                if size > 100 * 1024 * 1024:  # 100MB
                    logger.warning("Database size is large - consider archiving old data")
                    
        except Exception as e:
            logger.error(f"Error checking database size: {e}")
    
    def _analyze_fragmentation(self):
        """Analyze database fragmentation"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get database statistics
            cursor.execute("PRAGMA integrity_check")
            integrity = cursor.fetchone()
            
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            
            cursor.execute("PRAGMA freelist_count")
            freelist_count = cursor.fetchone()[0]
            
            # Calculate fragmentation level
            if page_count > 0:
                fragmentation = (freelist_count / page_count) * 100
                self.optimization_stats['fragmentation_level'] = fragmentation
                logger.info(f"Database fragmentation: {fragmentation:.2f}%")
                
                if fragmentation > 20:
                    logger.warning("High fragmentation detected - vacuum recommended")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error analyzing fragmentation: {e}")
    
    def _optimize_structure(self):
        """Optimize database structure for SSD"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Set SSD-optimized pragmas
            optimizations = [
                ("PRAGMA journal_mode = WAL", "Write-Ahead Logging"),
                ("PRAGMA synchronous = NORMAL", "Reduced sync for performance"),
                ("PRAGMA cache_size = -64000", "64MB cache"),
                ("PRAGMA temp_store = MEMORY", "Memory temp storage"),
                ("PRAGMA mmap_size = 268435456", "256MB memory mapping"),
                ("PRAGMA page_size = 65536", "64KB page size"),
                ("PRAGMA auto_vacuum = INCREMENTAL", "Incremental vacuum"),
                ("PRAGMA wal_autocheckpoint = 1000", "Checkpoint every 1000 pages"),
                ("PRAGMA busy_timeout = 30000", "30 second timeout")
            ]
            
            for pragma, description in optimizations:
                try:
                    cursor.execute(pragma)
                    logger.debug(f"Applied: {description}")
                except Exception as e:
                    logger.warning(f"Failed to apply {description}: {e}")
            
            conn.close()
            logger.info("Database structure optimized for SSD")
            
        except Exception as e:
            logger.error(f"Error optimizing structure: {e}")
    
    def _create_backup_if_needed(self):
        """Create backup if database is large or hasn't been backed up recently"""
        try:
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir)
            
            # Check if backup is needed
            backup_needed = False
            
            # Check database size
            if self.optimization_stats['database_size'] > 50 * 1024 * 1024:  # 50MB
                backup_needed = True
            
            # Check last backup time
            backup_files = [f for f in os.listdir(self.backup_dir) if f.endswith('.db')]
            if not backup_files:
                backup_needed = True
            else:
                # Check if last backup is older than 24 hours
                latest_backup = max(backup_files, key=lambda x: os.path.getctime(os.path.join(self.backup_dir, x)))
                backup_time = os.path.getctime(os.path.join(self.backup_dir, latest_backup))
                if time.time() - backup_time > 86400:  # 24 hours
                    backup_needed = True
            
            if backup_needed:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(self.backup_dir, f"backup_{timestamp}.db")
                
                shutil.copy2(self.db_path, backup_path)
                logger.info(f"Created backup: {backup_path}")
                
                # Clean up old backups (keep last 5)
                backup_files = sorted([f for f in os.listdir(self.backup_dir) if f.endswith('.db')], 
                                    key=lambda x: os.path.getctime(os.path.join(self.backup_dir, x)))
                if len(backup_files) > 5:
                    for old_backup in backup_files[:-5]:
                        os.remove(os.path.join(self.backup_dir, old_backup))
                        logger.info(f"Removed old backup: {old_backup}")
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
    
    def _vacuum_database(self):
        """Vacuum database to reduce fragmentation"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if vacuum is needed
            if self.optimization_stats['fragmentation_level'] > 10:
                logger.info("Running database vacuum to reduce fragmentation...")
                cursor.execute("VACUUM")
                logger.info("Database vacuum completed")
            else:
                logger.info("Fragmentation level acceptable - skipping vacuum")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error vacuuming database: {e}")
    
    def get_optimization_stats(self):
        """Get current optimization statistics"""
        return self.optimization_stats

def main():
    """Main optimization routine"""
    optimizer = SSDOptimizer()
    optimizer.optimize_database()
    
    stats = optimizer.get_optimization_stats()
    logger.info(f"Optimization stats: {stats}")

if __name__ == "__main__":
    main() 