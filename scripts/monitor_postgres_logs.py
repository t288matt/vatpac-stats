#!/usr/bin/env python3
"""
PostgreSQL Log Monitor for VATSIM Database
Monitors Docker logs for ERROR messages and sends alerts
"""

import subprocess
import time
import logging
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os

# Configuration
DOCKER_CONTAINER = "vatsim_postgres"
CHECK_INTERVAL = 30  # seconds
LOG_FILE = "logs/postgres_errors.log"
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "admin@yourdomain.com")
SMTP_SERVER = os.getenv("SMTP_SERVER", "localhost")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

def get_postgres_logs():
    """Get recent PostgreSQL logs from Docker"""
    try:
        result = subprocess.run([
            "docker", "logs", "--since", "1m", DOCKER_CONTAINER
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return result.stdout
        else:
            logging.error(f"Failed to get logs: {result.stderr}")
            return ""
    except subprocess.TimeoutExpired:
        logging.error("Timeout getting Docker logs")
        return ""
    except Exception as e:
        logging.error(f"Error getting logs: {e}")
        return ""

def check_for_errors(logs):
    """Check logs for ERROR messages"""
    errors = []
    lines = logs.split('\n')
    
    for line in lines:
        if 'ERROR:' in line or 'FATAL:' in line or 'PANIC:' in line:
            errors.append(line.strip())
    
    return errors

def send_alert(errors):
    """Send email alert for errors"""
    if not errors:
        return
    
    subject = f"CRITICAL: PostgreSQL Errors Detected - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    body = f"""
PostgreSQL errors detected in VATSIM database:

{chr(10).join(errors)}

Container: {DOCKER_CONTAINER}
Time: {datetime.now().isoformat()}

Check the database immediately!
"""
    
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = "postgres-monitor@vatsim"
        msg['To'] = ALERT_EMAIL
        
        with smtplib.SMTP(SMTP_SERVER) as server:
            server.send_message(msg)
        
        logging.info(f"Alert sent to {ALERT_EMAIL}")
    except Exception as e:
        logging.error(f"Failed to send alert: {e}")

def log_errors(errors):
    """Log errors to file"""
    if not errors:
        return
    
    timestamp = datetime.now().isoformat()
    with open(LOG_FILE, 'a') as f:
        f.write(f"\n=== {timestamp} ===\n")
        for error in errors:
            f.write(f"{error}\n")
        f.write("=" * 50 + "\n")

def main():
    """Main monitoring loop"""
    logging.info("Starting PostgreSQL log monitoring...")
    
    while True:
        try:
            # Get recent logs
            logs = get_postgres_logs()
            
            # Check for errors
            errors = check_for_errors(logs)
            
            if errors:
                logging.warning(f"Found {len(errors)} errors in logs")
                
                # Log errors
                log_errors(errors)
                
                # Send alert
                send_alert(errors)
            else:
                logging.info("No errors detected")
            
            # Wait before next check
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            logging.info("Monitoring stopped by user")
            break
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()



