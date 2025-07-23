#!/usr/bin/env python3
"""
PostgreSQL Setup Script for VATSIM Data Collection System

This script sets up PostgreSQL with optimized configuration for high-performance
data collection and concurrent access.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PostgreSQLSetup:
    """Handles PostgreSQL installation and configuration"""
    
    def __init__(self, db_name="vatsim_data", db_user="vatsim_user", db_password="vatsim_password"):
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.pg_data_dir = None
        self.pg_bin_dir = None
        
    def detect_platform(self):
        """Detect the operating system platform"""
        import platform
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "macos"
        else:
            return "linux"
    
    def install_postgresql_windows(self):
        """Install PostgreSQL on Windows"""
        try:
            logger.info("Installing PostgreSQL on Windows...")
            
            # Check if PostgreSQL is already installed
            result = subprocess.run(["pg_config", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("PostgreSQL is already installed")
                return True
            
            # Download and install PostgreSQL
            # Note: This is a simplified version. In production, you'd want to:
            # 1. Download the installer from https://www.postgresql.org/download/windows/
            # 2. Run the installer with silent installation options
            # 3. Configure the service
            
            logger.info("Please install PostgreSQL manually from https://www.postgresql.org/download/windows/")
            logger.info("After installation, ensure the PostgreSQL service is running")
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to install PostgreSQL on Windows: {e}")
            return False
    
    def install_postgresql_linux(self):
        """Install PostgreSQL on Linux"""
        try:
            logger.info("Installing PostgreSQL on Linux...")
            
            # Check if PostgreSQL is already installed
            result = subprocess.run(["which", "psql"], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("PostgreSQL is already installed")
                return True
            
            # Install PostgreSQL using package manager
            # Detect package manager
            if os.path.exists("/etc/debian_version"):
                # Debian/Ubuntu
                subprocess.run(["sudo", "apt-get", "update"], check=True)
                subprocess.run(["sudo", "apt-get", "install", "-y", "postgresql", "postgresql-contrib"], check=True)
            elif os.path.exists("/etc/redhat-release"):
                # RHEL/CentOS/Fedora
                subprocess.run(["sudo", "yum", "install", "-y", "postgresql-server", "postgresql-contrib"], check=True)
                subprocess.run(["sudo", "postgresql-setup", "initdb"], check=True)
                subprocess.run(["sudo", "systemctl", "enable", "postgresql"], check=True)
                subprocess.run(["sudo", "systemctl", "start", "postgresql"], check=True)
            else:
                logger.error("Unsupported Linux distribution")
                return False
            
            logger.info("PostgreSQL installed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to install PostgreSQL on Linux: {e}")
            return False
    
    def install_postgresql_macos(self):
        """Install PostgreSQL on macOS"""
        try:
            logger.info("Installing PostgreSQL on macOS...")
            
            # Check if PostgreSQL is already installed
            result = subprocess.run(["which", "psql"], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("PostgreSQL is already installed")
                return True
            
            # Install using Homebrew
            subprocess.run(["brew", "install", "postgresql"], check=True)
            subprocess.run(["brew", "services", "start", "postgresql"], check=True)
            
            logger.info("PostgreSQL installed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to install PostgreSQL on macOS: {e}")
            return False
    
    def install_postgresql(self):
        """Install PostgreSQL based on platform"""
        platform = self.detect_platform()
        
        if platform == "windows":
            return self.install_postgresql_windows()
        elif platform == "linux":
            return self.install_postgresql_linux()
        elif platform == "macos":
            return self.install_postgresql_macos()
        else:
            logger.error(f"Unsupported platform: {platform}")
            return False
    
    def create_database_and_user(self):
        """Create database and user for the application"""
        try:
            logger.info("Creating database and user...")
            
            # Connect as postgres user to create database and user
            create_user_sql = f"""
            CREATE USER {self.db_user} WITH PASSWORD '{self.db_password}';
            CREATE DATABASE {self.db_name} OWNER {self.db_user};
            GRANT ALL PRIVILEGES ON DATABASE {self.db_name} TO {self.db_user};
            """
            
            # Execute SQL commands
            subprocess.run([
                "sudo", "-u", "postgres", "psql", "-c", create_user_sql
            ], check=True)
            
            logger.info(f"Created database '{self.db_name}' and user '{self.db_user}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create database and user: {e}")
            return False
    
    def configure_postgresql(self):
        """Configure PostgreSQL for optimal performance"""
        try:
            logger.info("Configuring PostgreSQL for optimal performance...")
            
            # PostgreSQL configuration file location
            config_file = "/etc/postgresql/*/main/postgresql.conf"
            
            # Backup original configuration
            subprocess.run(["sudo", "cp", config_file, f"{config_file}.backup"], check=True)
            
            # Configuration optimizations for high-performance data collection
            config_updates = {
                "max_connections": "100",
                "shared_buffers": "256MB",
                "effective_cache_size": "1GB",
                "maintenance_work_mem": "64MB",
                "checkpoint_completion_target": "0.9",
                "wal_buffers": "16MB",
                "default_statistics_target": "100",
                "random_page_cost": "1.1",
                "effective_io_concurrency": "200",
                "work_mem": "4MB",
                "min_wal_size": "1GB",
                "max_wal_size": "4GB",
                "checkpoint_timeout": "5min",
                "autovacuum": "on",
                "autovacuum_max_workers": "3",
                "autovacuum_naptime": "1min",
                "log_min_duration_statement": "1000",
                "log_checkpoints": "on",
                "log_connections": "on",
                "log_disconnections": "on",
                "log_lock_waits": "on",
                "log_temp_files": "0",
                "log_autovacuum_min_duration": "0",
                "track_activities": "on",
                "track_counts": "on",
                "track_io_timing": "on",
                "track_functions": "all",
                "shared_preload_libraries": "pg_stat_statements"
            }
            
            # Update configuration file
            for key, value in config_updates.items():
                subprocess.run([
                    "sudo", "sed", "-i", f"s/#{key} = .*/{key} = {value}/", config_file
                ], check=True)
            
            # Restart PostgreSQL to apply changes
            subprocess.run(["sudo", "systemctl", "restart", "postgresql"], check=True)
            
            logger.info("PostgreSQL configured successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure PostgreSQL: {e}")
            return False
    
    def create_connection_string(self):
        """Create the database connection string"""
        connection_string = f"postgresql://{self.db_user}:{self.db_password}@localhost:5432/{self.db_name}"
        
        # Save to .env file
        env_file = Path(".env")
        env_content = f"""
# Database Configuration
DATABASE_URL={connection_string}

# Application Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
"""
        
        with open(env_file, "w") as f:
            f.write(env_content.strip())
        
        logger.info(f"Database connection string saved to .env file")
        logger.info(f"Connection string: {connection_string}")
        
        return connection_string
    
    def test_connection(self):
        """Test the database connection"""
        try:
            import psycopg2
            
            connection_string = f"postgresql://{self.db_user}:{self.db_password}@localhost:5432/{self.db_name}"
            conn = psycopg2.connect(connection_string)
            
            # Test basic operations
            with conn.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()
                logger.info(f"PostgreSQL version: {version[0]}")
                
                cursor.execute("SELECT current_database(), current_user;")
                db_info = cursor.fetchone()
                logger.info(f"Connected to database: {db_info[0]} as user: {db_info[1]}")
            
            conn.close()
            logger.info("Database connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def setup(self):
        """Run the complete PostgreSQL setup"""
        try:
            logger.info("Starting PostgreSQL setup...")
            
            # Step 1: Install PostgreSQL
            if not self.install_postgresql():
                logger.error("PostgreSQL installation failed")
                return False
            
            # Step 2: Create database and user
            if not self.create_database_and_user():
                logger.error("Database and user creation failed")
                return False
            
            # Step 3: Configure PostgreSQL
            if not self.configure_postgresql():
                logger.error("PostgreSQL configuration failed")
                return False
            
            # Step 4: Create connection string
            connection_string = self.create_connection_string()
            
            # Step 5: Test connection
            if not self.test_connection():
                logger.error("Database connection test failed")
                return False
            
            logger.info("PostgreSQL setup completed successfully!")
            logger.info("You can now run the migration script to migrate data from SQLite")
            
            return True
            
        except Exception as e:
            logger.error(f"PostgreSQL setup failed: {e}")
            return False

def main():
    """Main setup function"""
    
    # Check if running as root (for Linux/macOS)
    if os.name != 'nt' and os.geteuid() == 0:
        logger.error("Please run this script as a regular user, not as root")
        sys.exit(1)
    
    # Create setup instance
    setup = PostgreSQLSetup()
    
    # Run setup
    if setup.setup():
        logger.info("PostgreSQL setup completed successfully!")
        logger.info("Next steps:")
        logger.info("1. Run: python migrate_to_postgresql.py")
        logger.info("2. Update your application to use the new DATABASE_URL")
        logger.info("3. Test the application with PostgreSQL")
    else:
        logger.error("PostgreSQL setup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 