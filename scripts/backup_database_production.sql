-- Production Database Backup Scripts
-- 
-- This script provides multiple methods to backup your PostgreSQL database
-- for production use. Choose the method that best fits your needs.
--
-- Usage: Run these commands from your host system (not inside Docker)
--

-- Method 1: Full Database Dump (Recommended for complete backups)
-- Creates a compressed SQL dump file with all data and schema
-- Usage: ./backup_full_database.sh

-- Method 2: Schema-Only Backup (Structure without data)
-- Useful for version control and schema migrations
-- Usage: ./backup_schema_only.sh

-- Method 3: Data-Only Backup (Data without schema)
-- Useful for data migration between environments
-- Usage: ./backup_data_only.sh

-- Method 4: Custom Format Backup (Most flexible)
-- Creates a custom format file that can be selectively restored
-- Usage: ./backup_custom_format.sh

-- Method 5: Automated Backup with Timestamp
-- Creates timestamped backup files for easy organization
-- Usage: ./backup_automated.sh

-- Method 6: Backup with Compression and Encryption
-- Creates compressed, encrypted backups for security
-- Usage: ./backup_secure.sh

-- Note: All backup files will be created in the ./backups/ directory
-- Make sure this directory exists and has sufficient disk space
