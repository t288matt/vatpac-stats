# rebuild_sector_occupancy.py

## Overview

`rebuild_sector_occupancy.py` is a utility script for rebuilding flight sector occupancy records based on raw flight data and sector boundaries. It implements the same sector tracking algorithm as the production system, ensuring accurate sector entry/exit records that reflect actual flight movements through different airspace sectors.

## Features

- Rebuilds sector occupancy records for individual flights or all flights in the database
- Implements exact production sector tracking logic, including speed thresholds
- Handles data gaps and flight session boundaries correctly
- Supports both current and archived flight data
- Provides options for priority rebuilds, batch processing, and interactive mode

## Requirements

- Python 3.8+
- SQLAlchemy
- asyncpg
- Shapely
- GeoJSON sector boundaries file

## Installation

1. Copy the script to your target environment:
   ```bash
   cp rebuild_sector_occupancy.py /path/to/target/directory/
   ```

2. Install required dependencies:
   ```bash
   pip install sqlalchemy asyncpg shapely
   ```

3. Ensure the GeoJSON sector boundaries file is available:
   ```bash
   # Default location
   config/australian_airspace_sectors.geojson
   ```

## Usage

### Rebuild All Flights

To rebuild sector occupancy records for all flights:

```bash
python rebuild_sector_occupancy.py --all
```

### Rebuild Priority Flights

To rebuild only flights with missing sector data:

```bash
python rebuild_sector_occupancy.py --priority
```

### Rebuild a Specific Flight

To rebuild sector records for a specific flight:

```bash
python rebuild_sector_occupancy.py --callsign QFA501 --cid 1612853 --completion "2025-10-01 07:25:23+00:00"
```

### Interactive Mode

For testing and debugging:

```bash
python rebuild_sector_occupancy.py --interactive
```

## Command Line Arguments

- `--all`: Rebuild all flights in the database
- `--priority`: Rebuild only flights with missing sector data
- `--callsign`: Specify a flight callsign to rebuild
- `--cid`: Specify the CID (pilot ID) for the flight
- `--completion`: Specify the completion time for the flight
- `--interactive`: Run in interactive mode
- `--db-url`: Override the default database URL
- `--geojson`: Override the default GeoJSON file path

## How It Works

1. The script identifies flights to rebuild based on command-line arguments
2. For each flight, it:
   - Deletes existing sector occupancy records
   - Fetches flight data from both current and archive tables
   - Processes the flight data using the sector tracking algorithm
   - Generates new sector occupancy records
   - Inserts the rebuilt records into the database

## Sector Tracking Algorithm

The script implements the same sector tracking algorithm as the production system:

- Aircraft must be ≥60 knots to enter a sector
- Aircraft must be <30 knots for 2 consecutive polls (120 seconds) to exit a sector
- Sector boundaries are defined in the GeoJSON file
- Flight session boundaries are determined by completion_time

## Production Deployment

For production deployment:

1. Back up existing sector occupancy data:
   ```bash
   pg_dump -t flight_sector_occupancy -U db_user -d db_name > flight_sector_occupancy_backup.sql
   ```

2. Transfer the script to the production server:
   ```bash
   scp rebuild_sector_occupancy.py user@production-server:/path/to/application/
   ```

3. Run the rebuild process:
   ```bash
   python rebuild_sector_occupancy.py --all
   ```

4. Monitor the output for progress and any errors

## Troubleshooting

- **Database connection issues**: Verify the database URL is correct
- **Missing sector boundaries**: Ensure the GeoJSON file path is correct
- **Memory usage**: For large datasets, consider rebuilding in batches
- **Performance**: The script uses async I/O for optimal performance

## Notes

- The rebuild process is idempotent - running it multiple times will produce the same results
- The script is designed to handle data gaps and flight session boundaries correctly
- Sector occupancy records are rebuilt based solely on flight data and sector boundaries
