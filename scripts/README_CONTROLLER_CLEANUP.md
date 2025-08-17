# Controller Table Cleanup Scripts

This directory contains scripts to clean up the controller table by removing rows with callsigns that aren't in the valid Australian controller callsigns list.

## 🚨 **IMPORTANT WARNING**

**These scripts will permanently delete data from your database!** Always run with `--dry-run` first to see what would be deleted.

## 📁 Files

- `cleanup_controller_table.py` - Main Python script
- `cleanup_controller_table.bat` - Windows batch file (double-click to run)
- `cleanup_controller_table.ps1` - PowerShell script
- `README_CONTROLLER_CLEANUP.md` - This documentation

## 🎯 Purpose

The controller table cleanup script removes all controllers with callsigns that don't match the valid Australian controller callsigns list. This is useful for:

- Cleaning up existing data after implementing the new filter
- Removing worldwide controller data that shouldn't be stored
- Reducing database size and improving performance
- Ensuring data consistency with the new filtering system

## 🚀 Quick Start

### Option 1: Windows Batch File (Easiest)
1. Double-click `cleanup_controller_table.bat`
2. Choose option 1 for dry run first
3. Review the output
4. Choose option 2 to perform actual cleanup

### Option 2: PowerShell
1. Right-click `cleanup_controller_table.ps1` → "Run with PowerShell"
2. Follow the interactive prompts

### Option 3: Command Line
```bash
# Dry run first (recommended)
python scripts/cleanup_controller_table.py --dry-run

# Perform actual cleanup
python scripts/cleanup_controller_table.py

# Use custom callsign file
python scripts/cleanup_controller_table.py --callsign-file /custom/path/callsigns.txt
```

## 📋 Prerequisites

1. **Python 3.7+** installed and in PATH
2. **Database running** and accessible
3. **Valid callsign list file** exists (default: `config/controller_callsigns_list.txt`)
4. **Run from project root** directory (where `docker-compose.yml` is located)

## 🔍 Dry Run Mode

**ALWAYS run with `--dry-run` first!** This shows you:

- Current controller table statistics
- Callsign distribution (✓ for valid, ✗ for invalid)
- How many controllers would be deleted
- Examples of invalid callsigns that would be removed
- **No actual changes are made**

Example dry run output:
```
🔍 DRY RUN MODE - No changes will be made
  Would remove 1,247 controllers with invalid callsigns
  Would keep 53 controllers with valid callsigns
```

## 🗑️ Actual Cleanup

After reviewing the dry run output:

1. **Verify the numbers make sense**
2. **Check the examples of invalid callsigns**
3. **Ensure you have a backup** (if needed)
4. **Run without `--dry-run`** to perform the actual cleanup

The script will:
- Delete all controllers with invalid callsigns
- Commit the changes to the database
- Verify the cleanup was successful
- Show final statistics

## 📊 What Gets Deleted

The script removes controllers where:
- `callsign` is NOT in the valid callsigns list
- `callsign` is empty or NULL
- `callsign` doesn't match Australian patterns (SY_, ML_, BN_, AD_, etc.)

## ✅ What Gets Kept

The script keeps controllers where:
- `callsign` IS in the valid callsigns list
- Matches Australian controller patterns

## 🛡️ Safety Features

- **Dry run mode** - See what would happen before making changes
- **Transaction safety** - Uses database transactions with rollback on error
- **Verification** - Checks results after cleanup
- **Comprehensive logging** - Detailed logs saved to timestamped files
- **Confirmation prompts** - Interactive scripts ask for confirmation

## 📝 Logging

The script creates detailed logs:
- **Console output** - Real-time progress and results
- **Log file** - `controller_cleanup_YYYYMMDD_HHMMSS.log`
- **Database logs** - Check your database logs for SQL operations

## 🔧 Customization

### Custom Callsign File
```bash
python scripts/cleanup_controller_table.py --callsign-file /path/to/custom/callsigns.txt
```

### Environment Variables
The script uses your existing configuration:
- Database connection from `app/config.py`
- Callsign file path from `CONTROLLER_CALLSIGN_LIST_PATH` env var

## 🚨 Troubleshooting

### Common Issues

1. **"File not found" error**
   - Ensure you're running from the project root directory
   - Check that `config/controller_callsigns_list.txt` exists

2. **"Database connection failed"**
   - Ensure your database is running
   - Check database configuration in `app/config.py`

3. **"No valid callsigns loaded"**
   - Check the callsign file format (one callsign per line)
   - Ensure the file isn't empty

4. **Permission errors**
   - Run as administrator if needed
   - Check file permissions on the callsign list file

### Getting Help

1. **Check the logs** - Detailed error information is logged
2. **Run with dry-run** - See what the script is trying to do
3. **Verify prerequisites** - Ensure Python, database, and files are accessible

## 📈 Expected Results

After cleanup, you should see:
- **Significantly fewer controllers** in the database
- **Only Australian controllers** remaining
- **Improved performance** for controller-related queries
- **Reduced storage** requirements
- **Data consistency** with the new filtering system

## 🔄 After Cleanup

1. **Monitor the new filter** - Ensure it's working correctly
2. **Check database size** - Verify storage reduction
3. **Test queries** - Ensure performance improvements
4. **Update monitoring** - Adjust any dashboards or alerts

## 💡 Best Practices

1. **Always dry-run first** - Never skip the dry run
2. **Backup if needed** - Consider backing up before major cleanup
3. **Run during low traffic** - Minimize impact on active users
4. **Monitor results** - Verify the cleanup achieved expected results
5. **Document changes** - Keep records of what was cleaned up

## 🆘 Emergency Recovery

If something goes wrong:
1. **Check the logs** for detailed error information
2. **Database rollback** - The script uses transactions, so partial failures roll back
3. **Restore from backup** - If you have a backup, restore the controller table
4. **Contact support** - If you need help recovering

---

**Remember: Always dry-run first, and ensure you understand what will be deleted before proceeding!**
