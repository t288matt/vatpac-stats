#!/usr/bin/env python3
"""
Lightweight PostgreSQL Healthcheck for Docker
Quick checks for database corruption and errors
"""

import subprocess
import sys
import os

def check_postgres_ready():
    """Check if PostgreSQL is accepting connections"""
    try:
        result = subprocess.run([
            "pg_isready", "-U", "vatsim_user", "-d", "vatsim_data"
        ], capture_output=True, timeout=10)
        return result.returncode == 0
    except:
        return False

def check_for_critical_errors():
    """Check for critical errors in recent logs"""
    try:
        # Get last 5 minutes of logs
        result = subprocess.run([
            "docker", "logs", "--since", "5m", "vatsim_postgres"
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode != 0:
            return False
            
        logs = result.stdout.lower()
        
        # Check for critical errors
        critical_patterns = [
            'error: table tid from new index tuple overlaps',
            'error: invalid duplicate tuple',
            'error: index contains unexpected zero page',
            'error: could not read block',
            'fatal:',
            'panic:'
        ]
        
        for pattern in critical_patterns:
            if pattern in logs:
                print(f"CRITICAL ERROR DETECTED: {pattern}")
                return False
                
        return True
    except:
        return False

def check_index_health():
    """Quick check for corrupted indexes"""
    try:
        result = subprocess.run([
            "psql", "-U", "vatsim_user", "-d", "vatsim_data", "-c",
            "SELECT COUNT(*) FROM pg_index WHERE indisvalid = false OR indisready = false;"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return False
            
        # Parse the count
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            count = int(lines[1])
            if count > 0:
                print(f"FOUND {count} CORRUPTED INDEXES!")
                return False
                
        return True
    except:
        return False

def main():
    """Main healthcheck - exit 0 for healthy, 1 for unhealthy"""
    
    # Check 1: PostgreSQL ready
    if not check_postgres_ready():
        print("PostgreSQL not ready")
        sys.exit(1)
    
    # Check 2: No critical errors in logs
    if not check_for_critical_errors():
        print("Critical errors detected in logs")
        sys.exit(1)
    
    # Check 3: Index health
    if not check_index_health():
        print("Index corruption detected")
        sys.exit(1)
    
    print("PostgreSQL healthy")
    sys.exit(0)

if __name__ == "__main__":
    main()



