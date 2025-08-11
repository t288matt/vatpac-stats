# Database Migrations

This directory contains database migration scripts for the VATSIM data project.

## Current Migration

### Migration 001: Transceiver Frequency INTEGER to BIGINT

**Files:**
- `001_alter_transceiver_frequency_to_bigint.sql` - Main migration script
- `001_rollback_transceiver_frequency_to_integer.sql` - Rollback script
- `run_migration.py` - Python migration runner

**Purpose:** Changes the `frequency` column in the `transceivers` table from `INTEGER` to `BIGINT` to support larger frequency values.

**Why BIGINT?** 
- INTEGER range: -2,147,483,648 to 2,147,483,647
- BIGINT range: -9,223,372,036,854,775,808 to 9,223,372,036,854,775,807
- Aviation frequencies can exceed INTEGER range in some edge cases

## Running the Migration

### Option 1: Using Python Script (Recommended)

```bash
# From project root directory
cd migrations
python run_migration.py
```

The script will:
1. Connect to your database
2. Check current schema
3. Run the migration if needed
4. Verify the migration was successful
5. Provide detailed logging

### Option 2: Manual SQL Execution

```bash
# Connect to your PostgreSQL database
psql -h localhost -U your_username -d your_database

# Run the migration
\i migrations/001_alter_transceiver_frequency_to_bigint.sql
```

## Rollback (If Needed)

If you need to revert the migration:

```bash
# Using Python script (if you modify it for rollback)
python run_migration.py --rollback

# Or manually
psql -h localhost -U your_username -d your_database
\i migrations/001_rollback_transceiver_frequency_to_integer.sql
```

**⚠️ Warning:** Rollback will lose any data that exceeds INTEGER range.

## Migration Safety Features

1. **Data Preservation**: Migration copies data before changing column type
2. **Verification**: Automatic verification after migration
3. **Rollback**: Available rollback script if needed
4. **Logging**: Detailed logging throughout the process
5. **Error Handling**: Graceful error handling with rollback capability

## Pre-Migration Checklist

- [ ] Database backup (recommended)
- [ ] Stop application services
- [ ] Verify no active connections to transceivers table
- [ ] Check available disk space
- [ ] Test migration on non-production environment first

## Post-Migration Verification

After migration, verify:

1. **Column Type**: `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'transceivers' AND column_name = 'frequency';`
2. **Data Integrity**: `SELECT COUNT(*) FROM transceivers WHERE frequency IS NOT NULL;`
3. **Index**: `SELECT indexname FROM pg_indexes WHERE tablename = 'transceivers' AND indexdef LIKE '%frequency%';`
4. **Application**: Restart application and verify it works correctly

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure database user has ALTER TABLE privileges
2. **Lock Timeout**: Check for long-running transactions
3. **Disk Space**: Ensure sufficient space for temporary columns
4. **Connection Issues**: Verify DATABASE_URL in config.py

### Getting Help

If migration fails:
1. Check the logs for specific error messages
2. Verify database connectivity
3. Check database user permissions
4. Review the rollback script if needed

## Future Migrations

When adding new migrations:
1. Use sequential numbering (002_, 003_, etc.)
2. Include both forward and rollback scripts
3. Test thoroughly before running in production
4. Document any special requirements or dependencies
