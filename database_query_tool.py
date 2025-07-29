#!/usr/bin/env python3
"""
Database Query Tool for VATSIM Data Collection System

This tool provides a comprehensive interface for querying the database
with predefined queries and custom SQL support.
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
from tabulate import tabulate
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseQueryTool:
    """Comprehensive database query tool for VATSIM data"""
    
    def __init__(self, db_path: str = "atc_optimization.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    def connect_database(self):
        """Connect to the database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            logger.info(f"Connected to database: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def close_database(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def get_table_info(self) -> Dict[str, Any]:
        """Get information about all tables"""
        try:
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in self.cursor.fetchall()]
            
            table_info = {}
            for table in tables:
                self.cursor.execute(f"PRAGMA table_info({table})")
                columns = self.cursor.fetchall()
                self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = self.cursor.fetchone()[0]
                
                table_info[table] = {
                    'columns': [col[1] for col in columns],
                    'record_count': count
                }
            
            return table_info
        except Exception as e:
            logger.error(f"Error getting table info: {e}")
            return {}
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a custom SQL query"""
        try:
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []
    
    def get_predefined_queries(self) -> Dict[str, str]:
        """Get predefined useful queries"""
        return {
            "active_controllers": """
                SELECT callsign, facility, position, status, last_seen, workload_score
                FROM controllers 
                WHERE status = 'online' 
                ORDER BY last_seen DESC 
                LIMIT 20
            """,
            
            "recent_flights": """
                SELECT callsign, aircraft_type, departure, arrival, altitude, speed, last_updated
                FROM flights 
                WHERE status = 'active' 
                ORDER BY last_updated DESC 
                LIMIT 20
            """,
            
            "traffic_movements": """
                SELECT airport_code, movement_type, aircraft_callsign, timestamp
                FROM traffic_movements 
                ORDER BY timestamp DESC 
                LIMIT 20
            """,
            
            "controller_workload": """
                SELECT 
                    c.callsign,
                    c.facility,
                    c.workload_score,
                    COUNT(f.id) as flight_count
                FROM controllers c
                LEFT JOIN flights f ON c.id = f.controller_id
                WHERE c.status = 'online'
                GROUP BY c.id
                ORDER BY c.workload_score DESC
                LIMIT 15
            """,
            
            "aircraft_types": """
                SELECT 
                    aircraft_type,
                    COUNT(*) as count
                FROM flights 
                WHERE aircraft_type IS NOT NULL
                GROUP BY aircraft_type 
                ORDER BY count DESC 
                LIMIT 10
            """,
            
            "facility_stats": """
                SELECT 
                    facility,
                    COUNT(*) as controller_count,
                    AVG(workload_score) as avg_workload
                FROM controllers 
                WHERE status = 'online'
                GROUP BY facility 
                ORDER BY controller_count DESC
            """,
            
            "recent_activity": """
                SELECT 
                    'controllers' as table_name,
                    COUNT(*) as count,
                    MAX(last_seen) as latest_update
                FROM controllers 
                WHERE last_seen > datetime('now', '-1 hour')
                UNION ALL
                SELECT 
                    'flights' as table_name,
                    COUNT(*) as count,
                    MAX(last_updated) as latest_update
                FROM flights 
                WHERE last_updated > datetime('now', '-1 hour')
            """,
            
            "database_stats": """
                SELECT 
                    'controllers' as table_name,
                    COUNT(*) as total_records,
                    MAX(last_seen) as latest_data
                FROM controllers
                UNION ALL
                SELECT 
                    'flights' as table_name,
                    COUNT(*) as total_records,
                    MAX(last_updated) as latest_data
                FROM flights
                UNION ALL
                SELECT 
                    'traffic_movements' as table_name,
                    COUNT(*) as total_records,
                    MAX(timestamp) as latest_data
                FROM traffic_movements
            """
        }
    
    def run_predefined_query(self, query_name: str) -> List[Dict[str, Any]]:
        """Run a predefined query by name"""
        queries = self.get_predefined_queries()
        if query_name not in queries:
            logger.error(f"Unknown query: {query_name}")
            return []
        
        return self.execute_query(queries[query_name])
    
    def display_results(self, results: List[Dict[str, Any]], title: str = "Query Results"):
        """Display query results in a formatted table"""
        if not results:
            print(f"\n{title}: No results found")
            return
        
        print(f"\n{title}")
        print("=" * 80)
        
        # Get headers from first row
        headers = list(results[0].keys())
        
        # Prepare data for tabulate
        table_data = []
        for row in results:
            table_data.append([str(row.get(header, '')) for header in headers])
        
        # Display table
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        print(f"\nTotal rows: {len(results)}")
    
    def interactive_mode(self):
        """Run interactive query mode"""
        print("\n🔍 VATSIM Database Query Tool")
        print("=" * 50)
        
        # Show available tables
        table_info = self.get_table_info()
        print("\n📊 Available Tables:")
        for table, info in table_info.items():
            print(f"  • {table}: {info['record_count']} records")
        
        # Show predefined queries
        queries = self.get_predefined_queries()
        print(f"\n📋 Predefined Queries ({len(queries)} available):")
        for i, query_name in enumerate(queries.keys(), 1):
            print(f"  {i}. {query_name}")
        
        while True:
            print("\n" + "=" * 50)
            print("Options:")
            print("1. Run predefined query")
            print("2. Execute custom SQL")
            print("3. Show table structure")
            print("4. Show database stats")
            print("5. Exit")
            
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == "1":
                print("\nAvailable predefined queries:")
                for i, query_name in enumerate(queries.keys(), 1):
                    print(f"  {i}. {query_name}")
                
                try:
                    query_num = int(input("\nEnter query number: ")) - 1
                    query_names = list(queries.keys())
                    if 0 <= query_num < len(query_names):
                        query_name = query_names[query_num]
                        results = self.run_predefined_query(query_name)
                        self.display_results(results, f"Results for: {query_name}")
                    else:
                        print("Invalid query number")
                except ValueError:
                    print("Invalid input")
            
            elif choice == "2":
                sql = input("\nEnter SQL query: ").strip()
                if sql:
                    results = self.execute_query(sql)
                    self.display_results(results, "Custom Query Results")
            
            elif choice == "3":
                table = input("\nEnter table name: ").strip()
                if table in table_info:
                    print(f"\nTable structure for '{table}':")
                    print(f"Columns: {', '.join(table_info[table]['columns'])}")
                    print(f"Records: {table_info[table]['record_count']}")
                else:
                    print(f"Table '{table}' not found")
            
            elif choice == "4":
                results = self.run_predefined_query("database_stats")
                self.display_results(results, "Database Statistics")
            
            elif choice == "5":
                print("Goodbye!")
                break
            
            else:
                print("Invalid choice")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="VATSIM Database Query Tool")
    parser.add_argument("--db", default="atc_optimization.db", help="Database file path")
    parser.add_argument("--query", help="Run predefined query by name")
    parser.add_argument("--sql", help="Execute custom SQL query")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    
    args = parser.parse_args()
    
    # Initialize tool
    tool = DatabaseQueryTool(args.db)
    
    if not tool.connect_database():
        sys.exit(1)
    
    try:
        if args.query:
            # Run predefined query
            results = tool.run_predefined_query(args.query)
            tool.display_results(results, f"Results for: {args.query}")
        
        elif args.sql:
            # Run custom SQL
            results = tool.execute_query(args.sql)
            tool.display_results(results, "Custom Query Results")
        
        elif args.interactive:
            # Interactive mode
            tool.interactive_mode()
        
        else:
            # Default: show database info
            table_info = tool.get_table_info()
            print("\n📊 VATSIM Database Overview")
            print("=" * 40)
            for table, info in table_info.items():
                print(f"  {table}: {info['record_count']} records")
            
            print(f"\nUse --interactive for interactive mode")
            print(f"Use --query <name> for predefined queries")
            print(f"Use --sql \"SELECT * FROM table\" for custom queries")
    
    finally:
        tool.close_database()

if __name__ == "__main__":
    main() 