# Controller Table Cleanup Script - PowerShell Version
# This script runs the Python cleanup script with common options

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Controller Table Cleanup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python and try again" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if we're in the right directory
if (-not (Test-Path "scripts\cleanup_controller_table.py")) {
    Write-Host "❌ ERROR: Please run this script from the project root directory" -ForegroundColor Red
    Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow
    Write-Host "Expected: VATSIM data project root" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Available options:" -ForegroundColor White
Write-Host "1. Dry run (show what would be deleted)" -ForegroundColor Yellow
Write-Host "2. Perform actual cleanup" -ForegroundColor Yellow
Write-Host "3. Custom callsign file path" -ForegroundColor Yellow
Write-Host ""

$choice = Read-Host "Enter your choice (1-3)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "Running DRY RUN mode..." -ForegroundColor Cyan
        Write-Host "This will show what would be deleted without making changes" -ForegroundColor Yellow
        Write-Host ""
        python scripts\cleanup_controller_table.py --dry-run
    }
    "2" {
        Write-Host ""
        Write-Host "⚠️  WARNING: This will permanently delete controllers with invalid callsigns!" -ForegroundColor Red
        Write-Host ""
        $confirm = Read-Host "Are you sure? Type 'YES' to continue"
        if ($confirm -eq "YES") {
            Write-Host ""
            Write-Host "Performing cleanup..." -ForegroundColor Green
            python scripts\cleanup_controller_table.py
        } else {
            Write-Host "Cleanup cancelled." -ForegroundColor Yellow
        }
    }
    "3" {
        Write-Host ""
        $customPath = Read-Host "Enter custom callsign file path"
        if (Test-Path $customPath) {
            Write-Host ""
            Write-Host "Running cleanup with custom file: $customPath" -ForegroundColor Cyan
            python scripts\cleanup_controller_table.py --callsign-file $customPath
        } else {
            Write-Host "❌ ERROR: File not found: $customPath" -ForegroundColor Red
        }
    }
    default {
        Write-Host "Invalid choice. Please run the script again." -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Script completed. Press Enter to exit..." -ForegroundColor Green
Read-Host
