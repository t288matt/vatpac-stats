#!/usr/bin/env python3
"""Check current state of flights and sector occupancy data."""

from app.database import _get_engine
from sqlalchemy import text

def main():
    engine = _get_engine()

    with engine.connect() as conn:
        # Check flights table structure
        result = conn.execute(text('''
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'flights'
            ORDER BY ordinal_position
        '''))
        print('FLIGHTS TABLE STRUCTURE:')
        print('-' * 50)
        for row in result:
            print(f'{row.column_name:<20} | {row.data_type:<15} | {row.is_nullable}')

        # Check if we have recent data
        result = conn.execute(text('''
            SELECT COUNT(*) as total_flights,
                   COUNT(CASE WHEN last_updated_api >= NOW() - INTERVAL '1 hour' THEN 1 END) as recent_flights
            FROM flights
        '''))
        row = result.fetchone()
        print(f'\nTotal flights: {row.total_flights:,}')
        print(f'Recent flights (last hour): {row.recent_flights:,}')

        # Check sector occupancy table
        result = conn.execute(text('''
            SELECT COUNT(*) as total_occupancy,
                   COUNT(CASE WHEN exit_timestamp IS NULL THEN 1 END) as open_sectors
        FROM flight_sector_occupancy
        '''))
        row = result.fetchone()
        print(f'\nSector occupancy records: {row.total_occupancy:,}')
        print(f'Open sectors: {row.open_sectors:,}')

        # Check if transceivers table has data
        result = conn.execute(text('''
            SELECT COUNT(*) as total_transceivers,
                   COUNT(CASE WHEN entity_type = 'flight' THEN 1 END) as flight_transceivers
            FROM transceivers
        '''))
        row = result.fetchone()
        print(f'\nTotal transceivers: {row.total_transceivers:,}')
        print(f'Flight transceivers: {row.flight_transceivers:,}')

        # Check flight_summaries
        result = conn.execute(text('''
            SELECT COUNT(*) as total_summaries
            FROM flight_summaries
            WHERE completion_time >= NOW() - INTERVAL '7 days'
        '''))
        row = result.fetchone()
        print(f'\nFlight summaries (last 7 days): {row.total_summaries:,}')

if __name__ == '__main__':
    main()
