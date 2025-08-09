#!/bin/bash

# ===============================================
# VATSIM Data Collection System - Database Backup Script
# ===============================================

set -e  # Exit on any error

# Configuration
BACKUP_DIR="/opt/vatsim/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="vatsim_backup_$DATE.sql.gz"
LOG_FILE="/opt/vatsim/logs/backup.log"
POSTGRES_USER="${POSTGRES_USER:-vatsim_prod_user}"
DATABASE_NAME="vatsim_data"
CONTAINER_NAME="vatsim_postgres"

# Retention settings
LOCAL_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
S3_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-90}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}$(date '+%Y-%m-%d %H:%M:%S') - ERROR: $1${NC}" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}$(date '+%Y-%m-%d %H:%M:%S') - SUCCESS: $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}$(date '+%Y-%m-%d %H:%M:%S') - WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}$(date '+%Y-%m-%d %H:%M:%S') - INFO: $1${NC}" | tee -a "$LOG_FILE"
}

# Function to check if Docker container is running
check_container() {
    if ! docker ps | grep -q "$CONTAINER_NAME"; then
        log_error "PostgreSQL container '$CONTAINER_NAME' is not running"
        exit 1
    fi
    log_info "PostgreSQL container is running"
}

# Function to create backup directory
create_backup_dir() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        mkdir -p "$BACKUP_DIR"
        log_info "Created backup directory: $BACKUP_DIR"
    fi
}

# Function to perform database backup
backup_database() {
    log_info "Starting database backup..."
    
    # Create the backup
    if docker exec "$CONTAINER_NAME" pg_dump -U "$POSTGRES_USER" -d "$DATABASE_NAME" --verbose | gzip > "$BACKUP_DIR/$BACKUP_FILE"; then
        log_success "Database backup created: $BACKUP_FILE"
        
        # Check backup file size
        BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
        log_info "Backup file size: $BACKUP_SIZE"
        
        # Verify backup integrity
        if gzip -t "$BACKUP_DIR/$BACKUP_FILE"; then
            log_success "Backup file integrity verified"
        else
            log_error "Backup file is corrupted"
            return 1
        fi
    else
        log_error "Failed to create database backup"
        return 1
    fi
}

# Function to upload to S3 (if configured)
upload_to_s3() {
    if [[ -n "$BACKUP_S3_BUCKET" && -n "$AWS_ACCESS_KEY_ID" && -n "$AWS_SECRET_ACCESS_KEY" ]]; then
        log_info "Uploading backup to S3..."
        
        if command -v aws &> /dev/null; then
            if aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" "s3://$BACKUP_S3_BUCKET/database/" --storage-class STANDARD_IA; then
                log_success "Backup uploaded to S3: s3://$BACKUP_S3_BUCKET/database/$BACKUP_FILE"
            else
                log_error "Failed to upload backup to S3"
                return 1
            fi
        else
            log_warning "AWS CLI not installed, skipping S3 upload"
        fi
    else
        log_info "S3 backup not configured, skipping upload"
    fi
}

# Function to clean up old local backups
cleanup_local_backups() {
    log_info "Cleaning up old local backups (keeping $LOCAL_RETENTION_DAYS days)..."
    
    if find "$BACKUP_DIR" -name "vatsim_backup_*.sql.gz" -mtime +$LOCAL_RETENTION_DAYS -type f | grep -q .; then
        DELETED_COUNT=$(find "$BACKUP_DIR" -name "vatsim_backup_*.sql.gz" -mtime +$LOCAL_RETENTION_DAYS -type f -delete -print | wc -l)
        log_success "Deleted $DELETED_COUNT old local backup files"
    else
        log_info "No old local backup files to delete"
    fi
}

# Function to clean up old S3 backups
cleanup_s3_backups() {
    if [[ -n "$BACKUP_S3_BUCKET" && -n "$AWS_ACCESS_KEY_ID" && -n "$AWS_SECRET_ACCESS_KEY" ]]; then
        log_info "Cleaning up old S3 backups (keeping $S3_RETENTION_DAYS days)..."
        
        if command -v aws &> /dev/null; then
            # Calculate cutoff date
            CUTOFF_DATE=$(date -d "$S3_RETENTION_DAYS days ago" '+%Y-%m-%d')
            
            # List and delete old backups
            aws s3 ls "s3://$BACKUP_S3_BUCKET/database/" --recursive | \
            awk '$1 < "'$CUTOFF_DATE'" {print $4}' | \
            while read file; do
                if [[ -n "$file" ]]; then
                    aws s3 rm "s3://$BACKUP_S3_BUCKET/$file"
                    log_info "Deleted old S3 backup: $file"
                fi
            done
        fi
    fi
}

# Function to send notification (if configured)
send_notification() {
    local status=$1
    local message=$2
    
    # Add webhook notification here if needed
    # Example: curl -X POST -H 'Content-type: application/json' \
    #          --data '{"text":"'$message'"}' \
    #          "$SLACK_WEBHOOK_URL"
    
    log_info "Notification: $message"
}

# Function to generate backup report
generate_report() {
    local status=$1
    
    cat > "$BACKUP_DIR/backup_report_$DATE.txt" << EOF
VATSIM Database Backup Report
============================
Date: $(date)
Status: $status
Backup File: $BACKUP_FILE
Backup Size: $(du -h "$BACKUP_DIR/$BACKUP_FILE" 2>/dev/null | cut -f1 || echo "N/A")
Database: $DATABASE_NAME
Container: $CONTAINER_NAME

Local Backups:
$(ls -la "$BACKUP_DIR"/vatsim_backup_*.sql.gz 2>/dev/null | tail -10 || echo "No backups found")

S3 Configuration:
Bucket: ${BACKUP_S3_BUCKET:-"Not configured"}
Retention: $S3_RETENTION_DAYS days

Log Entries:
$(tail -20 "$LOG_FILE" 2>/dev/null || echo "No log entries")
EOF

    log_info "Backup report generated: backup_report_$DATE.txt"
}

# Main backup function
main() {
    log_info "Starting VATSIM database backup process"
    
    # Check prerequisites
    check_container
    create_backup_dir
    
    # Perform backup
    if backup_database; then
        # Upload to S3 if configured
        upload_to_s3
        
        # Clean up old backups
        cleanup_local_backups
        cleanup_s3_backups
        
        # Generate report
        generate_report "SUCCESS"
        
        # Send success notification
        send_notification "SUCCESS" "VATSIM database backup completed successfully: $BACKUP_FILE"
        
        log_success "Backup process completed successfully"
        exit 0
    else
        # Generate failure report
        generate_report "FAILED"
        
        # Send failure notification
        send_notification "FAILED" "VATSIM database backup failed"
        
        log_error "Backup process failed"
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    --test)
        log_info "Running backup test (dry run)"
        check_container
        log_success "Backup test passed"
        ;;
    --restore)
        if [[ -z "$2" ]]; then
            log_error "Usage: $0 --restore <backup_file>"
            exit 1
        fi
        
        RESTORE_FILE="$2"
        if [[ ! -f "$RESTORE_FILE" ]]; then
            log_error "Backup file not found: $RESTORE_FILE"
            exit 1
        fi
        
        log_warning "Restoring database from: $RESTORE_FILE"
        log_warning "This will overwrite the current database!"
        read -p "Are you sure? (yes/no): " confirm
        
        if [[ "$confirm" == "yes" ]]; then
            log_info "Starting database restore..."
            if gunzip -c "$RESTORE_FILE" | docker exec -i "$CONTAINER_NAME" psql -U "$POSTGRES_USER" -d "$DATABASE_NAME"; then
                log_success "Database restored successfully"
            else
                log_error "Database restore failed"
                exit 1
            fi
        else
            log_info "Database restore cancelled"
        fi
        ;;
    --list)
        log_info "Available local backups:"
        ls -la "$BACKUP_DIR"/vatsim_backup_*.sql.gz 2>/dev/null || log_info "No local backups found"
        
        if [[ -n "$BACKUP_S3_BUCKET" ]] && command -v aws &> /dev/null; then
            log_info "Available S3 backups:"
            aws s3 ls "s3://$BACKUP_S3_BUCKET/database/" || log_info "No S3 backups found or access denied"
        fi
        ;;
    --help)
        echo "VATSIM Database Backup Script"
        echo "Usage: $0 [option]"
        echo ""
        echo "Options:"
        echo "  (no option)    Perform full backup"
        echo "  --test         Test backup prerequisites"
        echo "  --restore <file> Restore from backup file"
        echo "  --list         List available backups"
        echo "  --help         Show this help"
        echo ""
        echo "Environment Variables:"
        echo "  POSTGRES_USER              Database user (default: vatsim_prod_user)"
        echo "  BACKUP_RETENTION_DAYS      Local retention in days (default: 30)"
        echo "  BACKUP_S3_BUCKET          S3 bucket for remote backup"
        echo "  AWS_ACCESS_KEY_ID         AWS access key"
        echo "  AWS_SECRET_ACCESS_KEY     AWS secret key"
        ;;
    *)
        main
        ;;
esac
