#!/bin/bash

# Production Database Full Backup Script
# Creates a complete backup of your PostgreSQL database with compression

# Configuration
DB_NAME="vatsim_data"
DB_USER="vatsim_user"
DB_HOST="localhost"
DB_PORT="5432"
BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/vatsim_data_full_${TIMESTAMP}.sql.gz"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if backup directory exists, create if not
if [ ! -d "$BACKUP_DIR" ]; then
    print_status "Creating backup directory: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
fi

# Check available disk space (require at least 1GB free)
AVAILABLE_SPACE=$(df "$BACKUP_DIR" | awk 'NR==2 {print $4}')
if [ "$AVAILABLE_SPACE" -lt 1048576 ]; then
    print_error "Insufficient disk space. Need at least 1GB free."
    exit 1
fi

print_status "Starting full database backup..."
print_status "Database: $DB_NAME"
print_status "Backup file: $BACKUP_FILE"
print_status "Timestamp: $TIMESTAMP"

# Create the backup using pg_dump with compression
if docker exec vatsim_postgres pg_dump \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --verbose \
    --clean \
    --if-exists \
    --create \
    --no-owner \
    --no-privileges \
    | gzip > "$BACKUP_FILE"; then
    
    # Check if backup was created successfully
    if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        print_status "Backup completed successfully!"
        print_status "Backup size: $BACKUP_SIZE"
        print_status "Backup location: $BACKUP_FILE"
        
        # Optional: Remove backups older than 30 days
        print_status "Cleaning up backups older than 30 days..."
        find "$BACKUP_DIR" -name "vatsim_data_full_*.sql.gz" -mtime +30 -delete
        
    else
        print_error "Backup file was not created or is empty!"
        exit 1
    fi
else
    print_error "Backup failed! Check the error messages above."
    exit 1
fi

print_status "Full database backup completed successfully!"
