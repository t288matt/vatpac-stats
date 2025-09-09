#!/usr/bin/env python3
"""Check how many flight summaries have sector_breakdown JSONB data for today."""
from app.database import _get_engine
from sqlalchemy import text

def main():
    engine = _get_engine()
    sql = """
    SELECT 
        COUNT(*) as total_today,
        COUNT(CASE WHEN sector_breakdown IS NOT NULL AND sector_breakdown != '{}'::jsonb THEN 1 END) as with_sector_data,
        COUNT(CASE WHEN sector_breakdown IS NULL OR sector_breakdown = '{}'::jsonb THEN 1 END) as without_sector_data
    FROM flight_summaries 
    WHERE DATE(updated_at) = CURRENT_DATE
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        row = result.fetchone()
        print(f"Today's flight summaries:")
        print(f"  Total: {row[0]}")
        print(f"  With sector_breakdown data: {row[1]}")
        print(f"  Without sector_breakdown data: {row[2]}")
        print(f"  Percentage with data: {(row[1]/row[0]*100):.1f}%" if row[0] > 0 else "  No data")

if __name__ == '__main__':
    main()
