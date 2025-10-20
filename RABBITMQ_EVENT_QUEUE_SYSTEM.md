# 🚀 RabbitMQ Event Queue System with Cloudflare Tunnel

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Installation & Setup](#installation--setup)
5. [Configuration](#configuration)
6. [Event Types & Triggers](#event-types--triggers)
7. [External Consumer Integration](#external-consumer-integration)
8. [Security Configuration](#security-configuration)
9. [Monitoring & Management](#monitoring--management)
10. [Troubleshooting](#troubleshooting)
11. [API Reference](#api-reference)

---

## 🎯 Overview

This document describes the implementation of a robust, persistent event queue system for the VATSIM data collection system using:

- **RabbitMQ** for message queuing and persistence
- **PostgreSQL triggers** for automatic event detection
- **Cloudflare Tunnel** for secure external access without opening ports
- **Python event listener** for bridging PostgreSQL and RabbitMQ

### Key Benefits

- ✅ **Persistent Queues**: Events survive system restarts
- ✅ **No Open Ports**: Cloudflare Tunnel provides secure external access
- ✅ **Automatic Detection**: PostgreSQL triggers detect events automatically
- ✅ **Scalable**: Multiple consumers can process events
- ✅ **Secure**: Cloudflare Access + RabbitMQ authentication
- ✅ **Home-Friendly**: No need to open router ports

---

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   VATSIM API    │───▶│  Data Service   │───▶│   PostgreSQL    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
                                               ┌─────────────────┐
                                               │  Triggers &     │
                                               │  NOTIFY Events  │
                                               └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  External       │◀───│ Cloudflare      │◀───│  Event Listener │
│  Consumers      │    │ Tunnel          │    │  (Python)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
                                               ┌─────────────────┐
                                               │    RabbitMQ     │
                                               │   (Persistent)  │
                                               └─────────────────┘
```

### Data Flow

1. **VATSIM API** → **Data Service** → **PostgreSQL** (existing flow)
2. **PostgreSQL Triggers** detect data changes and send `NOTIFY` events
3. **Event Listener** receives `NOTIFY` events and publishes to **RabbitMQ**
4. **Cloudflare Tunnel** exposes RabbitMQ to external consumers
5. **External Consumers** connect via `amqps://` and process events

---

## 📋 Prerequisites

### Required Software

- Docker & Docker Compose
- Cloudflare account with tunnel access
- Python 3.12+ (for external consumers)

### Required Access

- Cloudflare account with tunnel capability
- Domain name for tunnel endpoints
- Administrative access to Docker host

---

## 🛠️ Installation & Setup

### Step 1: Update Docker Compose

Add RabbitMQ and event listener to your existing `docker-compose.yml`:

```yaml
version: "3.9"

services:
  # Your existing services...
  postgres:
    image: postgres:16
    container_name: vatsim_postgres
    environment:
      POSTGRES_DB: vatsim_data
      POSTGRES_USER: vatsim_user
      POSTGRES_PASSWORD: vatsim_password
      # Memory optimization settings
      POSTGRES_SHARED_BUFFERS: 4GB
      POSTGRES_EFFECTIVE_CACHE_SIZE: 16GB
      POSTGRES_WORK_MEM: 128MB
      POSTGRES_MAINTENANCE_WORK_MEM: 1GB
    volumes:
      - ./database/vatsim:/var/lib/postgresql/data
      - ./config/init.sql:/docker-entrypoint-initdb.d/01-init.sql
      - ./scripts:/scripts:ro
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U vatsim_user -d vatsim_data"]
      interval: 10s
      timeout: 5s
      retries: 6
      start_period: 30s
    networks:
      - vatsim_network

  # Your existing app service...
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: vatsim_app
    environment:
      DATABASE_URL: postgresql://vatsim_user:vatpac_password@postgres:5432/vatsim_data
      LOG_LEVEL: "INFO"
      # ... your existing environment variables ...
    volumes:
      - ./logs:/app/logs:rw
      - ./config/australian_airspace_polygon.json:/app/airspace_sector_data/australian_airspace_polygon.json:ro
      - ./config/australian_airspace_sectors.geojson:/app/airspace_sector_data/australian_airspace_sectors.geojson:ro
      - ./config/controller_callsigns_list.txt:/app/airspace_sector_data/controller_callsigns_list.txt:ro
      - ./config/init.sql:/app/database/init.sql:ro
      - ./pytest.ini:/app/pytest.ini:ro
      - ./tests:/app/tests:ro
    ports:
      - "8001:8001"
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - vatsim_network

  # RabbitMQ Service
  rabbitmq:
    image: rabbitmq:3-management
    container_name: vatsim_rabbitmq
    environment:
      RABBITMQ_DEFAULT_USER: vatpac
      RABBITMQ_DEFAULT_PASS: vatpac_secure_password_2024
      RABBITMQ_DEFAULT_VHOST: vatpac_events
      RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS: "-rabbit log_levels [{connection,error},{default,error}]"
    ports:
      - "15672:15672"  # Management UI (local access only)
      - "5672:5672"    # AMQP port (local access only)
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
      - ./config/rabbitmq.conf:/etc/rabbitmq/rabbitmq.conf:ro
    networks:
      - vatsim_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s

  # Event Listener Service
  event_listener:
    build: ./event_listener
    container_name: vatsim_event_listener
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://vatsim_user:vatpac_password@postgres:5432/vatsim_data
      RABBITMQ_URL: amqp://vatpac:vatpac_secure_password_2024@rabbitmq:5672/vatpac_events
      LOG_LEVEL: INFO
    volumes:
      - ./logs:/app/logs:rw
    networks:
      - vatsim_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import psycopg2, pika; print('OK')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

volumes:
  rabbitmq_data:
  # Your existing volumes...

networks:
  vatsim_network:
    driver: bridge
```

### Step 2: Create Event Listener Service

Create the `event_listener/` directory structure:

```
event_listener/
├── Dockerfile
├── listener.py
├── requirements.txt
└── config/
    └── logging.conf
```

**`event_listener/Dockerfile`**
```dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/

# Create logs directory
RUN mkdir -p /app/logs

# Set proper permissions
RUN chmod +x /app/listener.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import psycopg2, pika; print('OK')"

# Run the listener
CMD ["python", "listener.py"]
```

**`event_listener/requirements.txt`**
```txt
psycopg2-binary==2.9.9
pika==1.3.2
asyncio==3.4.3
python-dotenv==1.0.0
```

**`event_listener/listener.py`**
```python
#!/usr/bin/env python3
"""
VATSIM Event Listener
Listens for PostgreSQL NOTIFY events and publishes to RabbitMQ

This service bridges PostgreSQL triggers with RabbitMQ message queuing,
enabling external systems to consume VATSIM events in real-time.
"""

import os
import json
import time
import signal
import sys
import logging
import psycopg2
import pika
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/event_listener.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class VATSIMEventListener:
    """
    Event listener that bridges PostgreSQL NOTIFY events with RabbitMQ.
    
    This class:
    1. Connects to PostgreSQL and listens for NOTIFY events
    2. Connects to RabbitMQ and sets up message routing
    3. Processes events and publishes them to appropriate queues
    4. Handles reconnection and error recovery
    """
    
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        self.rabbitmq_url = os.getenv("RABBITMQ_URL")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Connection objects
        self.pg_conn: Optional[psycopg2.extensions.connection] = None
        self.rabbit_conn: Optional[pika.BlockingConnection] = None
        self.rabbit_channel: Optional[pika.channel.Channel] = None
        
        # Control flags
        self.running = False
        self.reconnect_delay = 5
        
        # Event type to queue mapping
        self.event_mappings = {
            'pilot_login': ('vatpac.pilot.events', 'pilot_events'),
            'pilot_logout': ('vatpac.pilot.events', 'pilot_events'),
            'flight_completed': ('vatpac.flight.events', 'flight_events'),
            'controller_login': ('vatpac.controller.events', 'controller_events'),
            'controller_logout': ('vatpac.controller.events', 'controller_events'),
            'sector_entry': ('vatpac.sector.events', 'sector_events'),
            'sector_exit': ('vatpac.sector.events', 'sector_events'),
            'new_pilot_alert': ('vatpac.alerts.events', 'alert_events')
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("VATSIM Event Listener initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self._cleanup()
        sys.exit(0)
    
    def connect_postgres(self):
        """Connect to PostgreSQL with retry logic"""
        max_retries = 10
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info("Connecting to PostgreSQL...")
                self.pg_conn = psycopg2.connect(
                    self.db_url,
                    application_name="vatpac_event_listener"
                )
                self.pg_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
                
                # Test the connection
                cursor = self.pg_conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                
                logger.info("✅ Connected to PostgreSQL")
                return True
                
            except Exception as e:
                retry_count += 1
                logger.error(f"❌ PostgreSQL connection failed (attempt {retry_count}/{max_retries}): {e}")
                
                if retry_count < max_retries:
                    logger.info(f"Retrying in {self.reconnect_delay} seconds...")
                    time.sleep(self.reconnect_delay)
                else:
                    logger.error("Max retries exceeded for PostgreSQL connection")
                    return False
        
        return False
    
    def connect_rabbitmq(self):
        """Connect to RabbitMQ with retry logic"""
        max_retries = 10
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info("Connecting to RabbitMQ...")
                
                # Parse RabbitMQ URL
                parsed = urlparse(self.rabbitmq_url)
                
                # Create connection parameters
                credentials = pika.PlainCredentials(parsed.username, parsed.password)
                parameters = pika.ConnectionParameters(
                    host=parsed.hostname,
                    port=parsed.port,
                    virtual_host=parsed.path[1:] if parsed.path else '/',
                    credentials=credentials,
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
                
                # Create connection
                self.rabbit_conn = pika.BlockingConnection(parameters)
                self.rabbit_channel = self.rabbit_conn.channel()
                
                # Setup RabbitMQ topology
                self._setup_rabbitmq_topology()
                
                logger.info("✅ Connected to RabbitMQ")
                return True
                
            except Exception as e:
                retry_count += 1
                logger.error(f"❌ RabbitMQ connection failed (attempt {retry_count}/{max_retries}): {e}")
                
                if retry_count < max_retries:
                    logger.info(f"Retrying in {self.reconnect_delay} seconds...")
                    time.sleep(self.reconnect_delay)
                else:
                    logger.error("Max retries exceeded for RabbitMQ connection")
                    return False
        
        return False
    
    def _setup_rabbitmq_topology(self):
        """Setup RabbitMQ exchanges, queues, and bindings"""
        try:
            # Declare main events exchange
            self.rabbit_channel.exchange_declare(
                exchange='vatpac_events',
                exchange_type='topic',
                durable=True,
                auto_delete=False
            )
            
            # Declare dead letter exchange for failed messages
            self.rabbit_channel.exchange_declare(
                exchange='vatpac_events_dlx',
                exchange_type='direct',
                durable=True,
                auto_delete=False
            )
            
            # Declare queues for different event types
            queue_configs = {
                'pilot_events': {
                    'durable': True,
                    'arguments': {
                        'x-message-ttl': 86400000,  # 24 hours
                        'x-max-length': 10000,
                        'x-dead-letter-exchange': 'vatpac_events_dlx'
                    }
                },
                'flight_events': {
                    'durable': True,
                    'arguments': {
                        'x-message-ttl': 86400000,
                        'x-max-length': 10000,
                        'x-dead-letter-exchange': 'vatpac_events_dlx'
                    }
                },
                'controller_events': {
                    'durable': True,
                    'arguments': {
                        'x-message-ttl': 86400000,
                        'x-max-length': 10000,
                        'x-dead-letter-exchange': 'vatpac_events_dlx'
                    }
                },
                'sector_events': {
                    'durable': True,
                    'arguments': {
                        'x-message-ttl': 86400000,
                        'x-max-length': 10000,
                        'x-dead-letter-exchange': 'vatpac_events_dlx'
                    }
                },
                'alert_events': {
                    'durable': True,
                    'arguments': {
                        'x-message-ttl': 604800000,  # 7 days
                        'x-max-length': 1000,
                        'x-dead-letter-exchange': 'vatpac_events_dlx'
                    }
                }
            }
            
            # Create queues
            for queue_name, config in queue_configs.items():
                self.rabbit_channel.queue_declare(
                    queue=queue_name,
                    durable=config['durable'],
                    arguments=config['arguments']
                )
                
                # Bind to main exchange
                routing_key = f"vatpac.{queue_name.replace('_', '.')}"
                self.rabbit_channel.queue_bind(
                    exchange='vatpac_events',
                    queue=queue_name,
                    routing_key=routing_key
                )
                
                logger.info(f"✅ Created queue: {queue_name} (routing: {routing_key})")
            
            # Create dead letter queue
            self.rabbit_channel.queue_declare(
                queue='vatpac_events_dlq',
                durable=True
            )
            self.rabbit_channel.queue_bind(
                exchange='vatpac_events_dlx',
                queue='vatpac_events_dlq',
                routing_key='failed'
            )
            
            logger.info("✅ RabbitMQ topology setup complete")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup RabbitMQ topology: {e}")
            raise
    
    def listen_for_events(self):
        """Main event listening loop"""
        if not self.pg_conn or not self.rabbit_channel:
            logger.error("❌ Not connected to required services")
            return
        
        cursor = self.pg_conn.cursor()
        
        # Listen for different event channels
        event_channels = list(self.event_mappings.keys())
        
        for channel in event_channels:
            try:
                cursor.execute(f"LISTEN {channel};")
                logger.info(f"👂 Listening for {channel} events...")
            except Exception as e:
                logger.error(f"❌ Failed to listen to {channel}: {e}")
        
        logger.info("🚀 Event listener started. Waiting for events...")
        self.running = True
        
        while self.running:
            try:
                # Check for notifications with timeout
                import select
                if select.select([self.pg_conn], [], [], 5) == ([], [], []):
                    # Timeout - check if we're still running
                    continue
                
                # Process notifications
                self.pg_conn.poll()
                
                while self.pg_conn.notifies:
                    notify = self.pg_conn.notifies.pop(0)
                    self._process_notification(notify)
                    
            except psycopg2.OperationalError as e:
                logger.error(f"❌ PostgreSQL connection lost: {e}")
                if not self._reconnect_postgres():
                    break
            except pika.exceptions.AMQPConnectionError as e:
                logger.error(f"❌ RabbitMQ connection lost: {e}")
                if not self._reconnect_rabbitmq():
                    break
            except Exception as e:
                logger.error(f"❌ Unexpected error in event loop: {e}")
                time.sleep(1)
        
        logger.info("🛑 Event listener stopped")
    
    def _process_notification(self, notify):
        """Process PostgreSQL notification and publish to RabbitMQ"""
        try:
            # Parse notification payload
            event_data = json.loads(notify.payload)
            channel = notify.channel
            
            # Get routing information
            routing_key, queue_name = self.event_mappings.get(
                channel, 
                ('vatpac.unknown', 'pilot_events')
            )
            
            # Create event message
            event = {
                "event_type": channel,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "vatpac_data_system",
                "version": "1.0",
                "data": event_data
            }
            
            # Publish to RabbitMQ
            self.rabbit_channel.basic_publish(
                exchange='vatpac_events',
                routing_key=routing_key,
                body=json.dumps(event, default=str),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json',
                    timestamp=int(datetime.now().timestamp()),
                    message_id=f"{channel}_{int(datetime.now().timestamp() * 1000)}"
                )
            )
            
            logger.info(f"📤 Published {channel} event: {event_data.get('callsign', 'unknown')}")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse notification payload: {e}")
        except Exception as e:
            logger.error(f"❌ Error processing notification: {e}")
    
    def _reconnect_postgres(self):
        """Reconnect to PostgreSQL"""
        logger.info("Attempting to reconnect to PostgreSQL...")
        if self.pg_conn:
            try:
                self.pg_conn.close()
            except:
                pass
        return self.connect_postgres()
    
    def _reconnect_rabbitmq(self):
        """Reconnect to RabbitMQ"""
        logger.info("Attempting to reconnect to RabbitMQ...")
        if self.rabbit_conn:
            try:
                self.rabbit_conn.close()
            except:
                pass
        return self.connect_rabbitmq()
    
    def _cleanup(self):
        """Clean up connections"""
        logger.info("Cleaning up connections...")
        
        if self.pg_conn:
            try:
                self.pg_conn.close()
                logger.info("✅ PostgreSQL connection closed")
            except:
                pass
        
        if self.rabbit_conn:
            try:
                self.rabbit_conn.close()
                logger.info("✅ RabbitMQ connection closed")
            except:
                pass
    
    def run(self):
        """Main run method"""
        logger.info("🚀 Starting VATSIM Event Listener...")
        
        # Connect to services
        if not self.connect_postgres():
            logger.error("❌ Failed to connect to PostgreSQL")
            return False
        
        if not self.connect_rabbitmq():
            logger.error("❌ Failed to connect to RabbitMQ")
            return False
        
        # Start listening
        try:
            self.listen_for_events()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self._cleanup()
        
        return True

def main():
    """Main entry point"""
    listener = VATSIMEventListener()
    success = listener.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
```

### Step 3: RabbitMQ Configuration

Create `config/rabbitmq.conf`:

```ini
# RabbitMQ Configuration for VATSIM Event Queue System

# Network settings
listeners.tcp.default = 5672
management.tcp.port = 15672

# Memory and disk limits
vm_memory_high_watermark.relative = 0.6
disk_free_limit.absolute = 2GB

# Logging
log.console = true
log.console.level = info
log.file = /var/log/rabbitmq/rabbitmq.log
log.file.level = info

# Security
default_user = vatpac
default_pass = vatpac_secure_password_2024
default_vhost = vatpac_events

# Performance tuning
channel_max = 2047
frame_max = 131072
heartbeat = 600

# Queue settings
queue_master_locator = min-masters

# Management plugin
management.load_definitions = /etc/rabbitmq/definitions.json
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | - | Yes |
| `RABBITMQ_URL` | RabbitMQ connection string | - | Yes |
| `LOG_LEVEL` | Logging level | INFO | No |

### RabbitMQ Connection String Format

```
amqp://username:password@host:port/vhost
```

Example:
```
amqp://vatpac:vatpac_secure_password_2024@rabbitmq:5672/vatpac_events
```

---

## 🎯 Event Types & Triggers

### Supported Event Types

| Event Type | Description | Trigger Table | Queue |
|------------|-------------|---------------|-------|
| `pilot_login` | New pilot connects | `flights` | `pilot_events` |
| `pilot_logout` | Pilot disconnects | `flights` | `pilot_events` |
| `flight_completed` | Flight summary created | `flight_summaries` | `flight_events` |
| `controller_login` | ATC controller connects | `controllers` | `controller_events` |
| `controller_logout` | ATC controller disconnects | `controllers` | `controller_events` |
| `sector_entry` | Flight enters sector | `flight_sector_occupancy` | `sector_events` |
| `sector_exit` | Flight exits sector | `flight_sector_occupancy` | `sector_events` |
| `new_pilot_alert` | New Australian pilot detected | Manual trigger | `alert_events` |

### PostgreSQL Triggers

Add these triggers to your database:

```sql
-- Create notification function
CREATE OR REPLACE FUNCTION notify_event() RETURNS trigger AS $$
DECLARE
    event_data JSONB;
BEGIN
    -- Create event payload based on trigger context
    CASE TG_TABLE_NAME
        WHEN 'flights' THEN
            event_data = jsonb_build_object(
                'callsign', NEW.callsign,
                'cid', NEW.cid,
                'name', NEW.name,
                'aircraft_type', NEW.aircraft_type,
                'departure', NEW.departure,
                'arrival', NEW.arrival,
                'logon_time', NEW.logon_time,
                'last_updated', NEW.last_updated,
                'latitude', NEW.latitude,
                'longitude', NEW.longitude,
                'altitude', NEW.altitude
            );
        WHEN 'flight_summaries' THEN
            event_data = jsonb_build_object(
                'callsign', NEW.callsign,
                'cid', NEW.cid,
                'name', NEW.name,
                'aircraft_type', NEW.aircraft_type,
                'departure', NEW.departure,
                'arrival', NEW.arrival,
                'completion_time', NEW.completion_time,
                'time_online_minutes', NEW.time_online_minutes,
                'controller_time_percentage', NEW.controller_time_percentage
            );
        WHEN 'controllers' THEN
            event_data = jsonb_build_object(
                'callsign', NEW.callsign,
                'cid', NEW.cid,
                'name', NEW.name,
                'rating', NEW.rating,
                'facility', NEW.facility,
                'logon_time', NEW.logon_time,
                'last_updated', NEW.last_updated
            );
        WHEN 'flight_sector_occupancy' THEN
            event_data = jsonb_build_object(
                'callsign', NEW.callsign,
                'sector_name', NEW.sector_name,
                'entry_timestamp', NEW.entry_timestamp,
                'exit_timestamp', NEW.exit_timestamp,
                'entry_lat', NEW.entry_lat,
                'entry_lon', NEW.entry_lon
            );
        ELSE
            event_data = to_jsonb(NEW);
    END CASE;
    
    -- Add trigger context
    event_data = event_data || jsonb_build_object(
        'trigger_table', TG_TABLE_NAME,
        'trigger_operation', TG_OP,
        'trigger_timestamp', NOW()
    );
    
    -- Send notification
    PERFORM pg_notify(TG_ARGV[0], event_data::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Pilot login trigger (when new flight appears)
CREATE TRIGGER pilot_login_notify
    AFTER INSERT ON flights
    FOR EACH ROW
    WHEN (NEW.logon_time IS NOT NULL)
    EXECUTE FUNCTION notify_event('pilot_login');

-- Pilot logout trigger (when flight disappears)
CREATE TRIGGER pilot_logout_notify
    AFTER DELETE ON flights
    FOR EACH ROW
    WHEN (OLD.logon_time IS NOT NULL)
    EXECUTE FUNCTION notify_event('pilot_logout');

-- Flight completed trigger
CREATE TRIGGER flight_completed_notify
    AFTER INSERT ON flight_summaries
    FOR EACH ROW
    EXECUTE FUNCTION notify_event('flight_completed');

-- Controller login trigger
CREATE TRIGGER controller_login_notify
    AFTER INSERT ON controllers
    FOR EACH ROW
    WHEN (NEW.logon_time IS NOT NULL)
    EXECUTE FUNCTION notify_event('controller_login');

-- Controller logout trigger
CREATE TRIGGER controller_logout_notify
    AFTER DELETE ON controllers
    FOR EACH ROW
    WHEN (OLD.logon_time IS NOT NULL)
    EXECUTE FUNCTION notify_event('controller_logout');

-- Sector entry trigger
CREATE TRIGGER sector_entry_notify
    AFTER INSERT ON flight_sector_occupancy
    FOR EACH ROW
    EXECUTE FUNCTION notify_event('sector_entry');

-- Sector exit trigger
CREATE TRIGGER sector_exit_notify
    AFTER UPDATE ON flight_sector_occupancy
    FOR EACH ROW
    WHEN (OLD.exit_timestamp IS NULL AND NEW.exit_timestamp IS NOT NULL)
    EXECUTE FUNCTION notify_event('sector_exit');
```

---

## 🔌 External Consumer Integration

### Python Consumer Example

```python
#!/usr/bin/env python3
"""
VATSIM Event Consumer Example
Consumes events from RabbitMQ via Cloudflare Tunnel
"""

import pika
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VATSIMEventConsumer:
    """Consumer for VATSIM events from RabbitMQ"""
    
    def __init__(self, rabbitmq_url: str, queue_name: str):
        self.rabbitmq_url = rabbitmq_url
        self.queue_name = queue_name
        self.connection = None
        self.channel = None
    
    def connect(self):
        """Connect to RabbitMQ"""
        try:
            # Parse connection URL
            from urllib.parse import urlparse
            parsed = urlparse(self.rabbitmq_url)
            
            credentials = pika.PlainCredentials(parsed.username, parsed.password)
            parameters = pika.ConnectionParameters(
                host=parsed.hostname,
                port=parsed.port,
                virtual_host=parsed.path[1:] if parsed.path else '/',
                credentials=credentials,
                heartbeat=600
            )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare queue (in case it doesn't exist)
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            
            logger.info(f"✅ Connected to RabbitMQ, consuming from {self.queue_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            return False
    
    def consume_events(self):
        """Start consuming events"""
        if not self.connection or not self.channel:
            logger.error("❌ Not connected to RabbitMQ")
            return
        
        def callback(ch, method, properties, body):
            """Process received event"""
            try:
                event = json.loads(body)
                self.process_event(event)
                
                # Acknowledge the message
                ch.basic_ack(delivery_tag=method.delivery_tag)
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse event JSON: {e}")
                # Reject and requeue
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            except Exception as e:
                logger.error(f"❌ Error processing event: {e}")
                # Reject and requeue
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        
        # Set up consumer
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=callback
        )
        
        logger.info("🚀 Starting to consume events...")
        
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            self.channel.stop_consuming()
        finally:
            self.connection.close()
    
    def process_event(self, event: Dict[str, Any]):
        """Process individual event"""
        event_type = event.get('event_type')
        data = event.get('data', {})
        timestamp = event.get('timestamp')
        
        logger.info(f"📨 Processing {event_type} event at {timestamp}")
        
        # Route to appropriate handler
        if event_type == 'pilot_login':
            self.handle_pilot_login(data)
        elif event_type == 'pilot_logout':
            self.handle_pilot_logout(data)
        elif event_type == 'flight_completed':
            self.handle_flight_completed(data)
        elif event_type == 'controller_login':
            self.handle_controller_login(data)
        elif event_type == 'controller_logout':
            self.handle_controller_logout(data)
        elif event_type == 'sector_entry':
            self.handle_sector_entry(data)
        elif event_type == 'sector_exit':
            self.handle_sector_exit(data)
        else:
            logger.warning(f"Unknown event type: {event_type}")
    
    def handle_pilot_login(self, data: Dict[str, Any]):
        """Handle pilot login event"""
        callsign = data.get('callsign')
        name = data.get('name')
        aircraft_type = data.get('aircraft_type')
        
        logger.info(f"✈️ New pilot: {callsign} ({name}) flying {aircraft_type}")
        
        # Your custom logic here
        # - Send notifications
        # - Update external systems
        # - Log to external databases
        # - etc.
    
    def handle_pilot_logout(self, data: Dict[str, Any]):
        """Handle pilot logout event"""
        callsign = data.get('callsign')
        logger.info(f"👋 Pilot logged out: {callsign}")
    
    def handle_flight_completed(self, data: Dict[str, Any]):
        """Handle flight completed event"""
        callsign = data.get('callsign')
        departure = data.get('departure')
        arrival = data.get('arrival')
        duration = data.get('time_online_minutes')
        
        logger.info(f"🏁 Flight completed: {callsign} {departure}→{arrival} ({duration} min)")
    
    def handle_controller_login(self, data: Dict[str, Any]):
        """Handle controller login event"""
        callsign = data.get('callsign')
        name = data.get('name')
        facility = data.get('facility')
        
        logger.info(f"🎧 Controller online: {callsign} ({name}) - Facility {facility}")
    
    def handle_controller_logout(self, data: Dict[str, Any]):
        """Handle controller logout event"""
        callsign = data.get('callsign')
        logger.info(f"🎧 Controller offline: {callsign}")
    
    def handle_sector_entry(self, data: Dict[str, Any]):
        """Handle sector entry event"""
        callsign = data.get('callsign')
        sector = data.get('sector_name')
        
        logger.info(f"📍 {callsign} entered sector {sector}")
    
    def handle_sector_exit(self, data: Dict[str, Any]):
        """Handle sector exit event"""
        callsign = data.get('callsign')
        sector = data.get('sector_name')
        
        logger.info(f"📍 {callsign} exited sector {sector}")

def main():
    """Main entry point"""
    # Configuration
    RABBITMQ_URL = "amqps://external_consumer:secure_password@mq.vatpac.example.com:5672/vatpac_events"
    QUEUE_NAME = "pilot_events"  # or flight_events, controller_events, etc.
    
    # Create and run consumer
    consumer = VATSIMEventConsumer(RABBITMQ_URL, QUEUE_NAME)
    
    if consumer.connect():
        consumer.consume_events()
    else:
        logger.error("Failed to start consumer")

if __name__ == "__main__":
    main()
```

### Node.js Consumer Example

```javascript
const amqp = require('amqplib');

class VATSIMEventConsumer {
    constructor(rabbitmqUrl, queueName) {
        this.rabbitmqUrl = rabbitmqUrl;
        this.queueName = queueName;
        this.connection = null;
        this.channel = null;
    }

    async connect() {
        try {
            this.connection = await amqp.connect(this.rabbitmqUrl);
            this.channel = await this.connection.createChannel();
            
            // Declare queue
            await this.channel.assertQueue(this.queueName, { durable: true });
            
            console.log(`✅ Connected to RabbitMQ, consuming from ${this.queueName}`);
            return true;
        } catch (error) {
            console.error('❌ Failed to connect to RabbitMQ:', error);
            return false;
        }
    }

    async consumeEvents() {
        if (!this.channel) {
            console.error('❌ Not connected to RabbitMQ');
            return;
        }

        console.log('🚀 Starting to consume events...');

        await this.channel.consume(this.queueName, (msg) => {
            if (msg) {
                try {
                    const event = JSON.parse(msg.content.toString());
                    this.processEvent(event);
                    
                    // Acknowledge the message
                    this.channel.ack(msg);
                } catch (error) {
                    console.error('❌ Error processing event:', error);
                    // Reject and requeue
                    this.channel.nack(msg, false, true);
                }
            }
        });
    }

    processEvent(event) {
        const { event_type, data, timestamp } = event;
        
        console.log(`📨 Processing ${event_type} event at ${timestamp}`);

        switch (event_type) {
            case 'pilot_login':
                this.handlePilotLogin(data);
                break;
            case 'pilot_logout':
                this.handlePilotLogout(data);
                break;
            case 'flight_completed':
                this.handleFlightCompleted(data);
                break;
            default:
                console.warn(`Unknown event type: ${event_type}`);
        }
    }

    handlePilotLogin(data) {
        const { callsign, name, aircraft_type } = data;
        console.log(`✈️ New pilot: ${callsign} (${name}) flying ${aircraft_type}`);
    }

    handlePilotLogout(data) {
        const { callsign } = data;
        console.log(`👋 Pilot logged out: ${callsign}`);
    }

    handleFlightCompleted(data) {
        const { callsign, departure, arrival, time_online_minutes } = data;
        console.log(`🏁 Flight completed: ${callsign} ${departure}→${arrival} (${time_online_minutes} min)`);
    }
}

// Usage
const consumer = new VATSIMEventConsumer(
    'amqps://external_consumer:secure_password@mq.vatpac.example.com:5672/vatpac_events',
    'pilot_events'
);

consumer.connect().then(() => {
    consumer.consumeEvents();
});
```

---

## 🔐 Security Configuration

### Cloudflare Tunnel Setup

1. **Install Cloudflare Tunnel**
```bash
# Download cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

2. **Create Tunnel**
```bash
# Login to Cloudflare
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create vatpac-mq-tunnel

# Configure tunnel
cloudflared tunnel route dns vatpac-mq-tunnel mq.vatpac.example.com
cloudflared tunnel route dns vatpac-mq-tunnel mqadmin.vatpac.example.com
```

3. **Tunnel Configuration File**
Create `~/.cloudflared/config.yml`:

```yaml
tunnel: vatpac-mq-tunnel
credentials-file: /root/.cloudflared/vatpac-mq-tunnel.json

ingress:
  # RabbitMQ AMQP port (for consumers)
  - hostname: mq.vatpac.example.com
    service: tcp://localhost:5672
    originRequest:
      noTLSVerify: true
  
  # RabbitMQ Management UI (for administration)
  - hostname: mqadmin.vatpac.example.com
    service: http://localhost:15672
    originRequest:
      noTLSVerify: true
  
  # Catch-all rule
  - service: http_status:404
```

4. **Start Tunnel**
```bash
# Run tunnel
cloudflared tunnel run vatpac-mq-tunnel

# Or run as service
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

### RabbitMQ Security

1. **Create External Consumer User**
```bash
# Create user for external consumers
docker exec vatsim_rabbitmq rabbitmqctl add_user external_consumer secure_password_2024

# Set permissions
docker exec vatsim_rabbitmq rabbitmqctl set_permissions -p vatpac_events external_consumer ".*" ".*" ".*"

# Set user tags
docker exec vatsim_rabbitmq rabbitmqctl set_user_tags external_consumer consumer
```

2. **Enable Management UI Security**
```bash
# Enable management plugin
docker exec vatsim_rabbitmq rabbitmq-plugins enable rabbitmq_management

# Create admin user
docker exec vatsim_rabbitmq rabbitmqctl add_user admin admin_secure_password
docker exec vatsim_rabbitmq rabbitmqctl set_user_tags admin administrator
docker exec vatsim_rabbitmq rabbitmqctl set_permissions -p vatpac_events admin ".*" ".*" ".*"
```

### Cloudflare Access (Optional)

1. **Enable Cloudflare Access**
   - Go to Cloudflare Dashboard > Access > Applications
   - Create application for `mqadmin.vatpac.example.com`
   - Configure authentication (Google, GitHub, etc.)
   - Add allowed users/emails

2. **API Token Access**
   - Create Cloudflare API token
   - Use token for programmatic access

---

## 📊 Monitoring & Management

### RabbitMQ Management UI

Access the management interface at `https://mqadmin.vatpac.example.com`:

- **Overview**: Queue statistics, message rates
- **Queues**: Individual queue details and management
- **Exchanges**: Exchange routing and bindings
- **Connections**: Active consumer connections
- **Channels**: Message flow monitoring

### Health Checks

1. **RabbitMQ Health Check**
```bash
# Check if RabbitMQ is running
docker exec vatsim_rabbitmq rabbitmq-diagnostics ping

# Check queue status
docker exec vatsim_rabbitmq rabbitmqctl list_queues name messages consumers

# Check connections
docker exec vatsim_rabbitmq rabbitmqctl list_connections
```

2. **Event Listener Health Check**
```bash
# Check if listener is running
docker exec vatsim_event_listener ps aux | grep listener.py

# Check logs
docker logs vatsim_event_listener --tail 50

# Check PostgreSQL triggers
docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -c "SELECT * FROM pg_listening_channels();"
```

### Monitoring Scripts

**`scripts/monitor_queues.py`**
```python
#!/usr/bin/env python3
"""
Queue monitoring script
"""

import pika
import json
import time
from datetime import datetime

def monitor_queues():
    """Monitor queue statistics"""
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost', 5672, '/vatpac_events',
                                pika.PlainCredentials('vatpac', 'vatpac_secure_password_2024'))
    )
    channel = connection.channel()
    
    while True:
        try:
            # Get queue info
            method = channel.queue_declare('pilot_events', passive=True)
            messages = method.method.message_count
            consumers = method.method.consumer_count
            
            print(f"[{datetime.now()}] pilot_events: {messages} messages, {consumers} consumers")
            
            time.sleep(10)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
    
    connection.close()

if __name__ == "__main__":
    monitor_queues()
```

---

## 🔧 Troubleshooting

### Common Issues

1. **Event Listener Not Starting**
```bash
# Check logs
docker logs vatsim_event_listener

# Check database connection
docker exec vatsim_event_listener python -c "import psycopg2; print('DB OK')"

# Check RabbitMQ connection
docker exec vatsim_event_listener python -c "import pika; print('RabbitMQ OK')"
```

2. **No Events Being Published**
```bash
# Check PostgreSQL triggers
docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -c "
SELECT schemaname, tablename, triggername 
FROM pg_trigger t 
JOIN pg_class c ON t.tgrelid = c.oid 
JOIN pg_namespace n ON c.relnamespace = n.oid 
WHERE triggername LIKE '%notify%';"

# Test trigger manually
docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -c "
SELECT pg_notify('test_channel', '{\"test\": \"message\"}');"
```

3. **External Consumers Can't Connect**
```bash
# Check tunnel status
cloudflared tunnel list

# Check tunnel logs
cloudflared tunnel run vatpac-mq-tunnel --loglevel debug

# Test connection locally
telnet localhost 5672
```

4. **Messages Not Being Consumed**
```bash
# Check queue status
docker exec vatsim_rabbitmq rabbitmqctl list_queues name messages consumers

# Check dead letter queue
docker exec vatsim_rabbitmq rabbitmqctl list_queues name messages | grep dlq

# Purge queue if needed
docker exec vatsim_rabbitmq rabbitmqctl purge_queue pilot_events
```

### Log Locations

- **Event Listener**: `/app/logs/event_listener.log`
- **RabbitMQ**: `/var/log/rabbitmq/rabbitmq.log`
- **Cloudflare Tunnel**: `~/.cloudflared/logs/`

### Performance Tuning

1. **RabbitMQ Performance**
```ini
# In rabbitmq.conf
vm_memory_high_watermark.relative = 0.6
disk_free_limit.absolute = 2GB
channel_max = 2047
frame_max = 131072
heartbeat = 600
```

2. **PostgreSQL Performance**
```sql
-- Increase work_mem for triggers
SET work_mem = '256MB';

-- Create indexes for trigger performance
CREATE INDEX CONCURRENTLY idx_flights_logon_time ON flights(logon_time) WHERE logon_time IS NOT NULL;
CREATE INDEX CONCURRENTLY idx_controllers_logon_time ON controllers(logon_time) WHERE logon_time IS NOT NULL;
```

---

## 📚 API Reference

### Event Message Format

```json
{
  "event_type": "pilot_login",
  "timestamp": "2024-01-15T10:30:00Z",
  "source": "vatpac_data_system",
  "version": "1.0",
  "data": {
    "callsign": "QFA123",
    "cid": 1234567,
    "name": "John Smith",
    "aircraft_type": "A320",
    "departure": "YSSY",
    "arrival": "YMML",
    "logon_time": "2024-01-15T10:30:00Z",
    "last_updated": "2024-01-15T10:30:00Z",
    "trigger_table": "flights",
    "trigger_operation": "INSERT",
    "trigger_timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Connection Strings

**RabbitMQ (External)**
```
amqps://external_consumer:secure_password@mq.vatpac.example.com:5672/vatpac_events
```

**RabbitMQ (Internal)**
```
amqp://vatpac:vatpac_secure_password_2024@rabbitmq:5672/vatpac_events
```

**Management UI**
```
https://mqadmin.vatpac.example.com
```

### Queue Names

- `pilot_events` - Pilot login/logout events
- `flight_events` - Flight completion events
- `controller_events` - ATC controller events
- `sector_events` - Sector entry/exit events
- `alert_events` - Alert and notification events

### Routing Keys

- `vatpac.pilot.events` - Pilot-related events
- `vatpac.flight.events` - Flight-related events
- `vatpac.controller.events` - Controller-related events
- `vatpac.sector.events` - Sector-related events
- `vatpac.alerts.events` - Alert-related events

---

## 🚀 Getting Started

1. **Update your `docker-compose.yml`** with the RabbitMQ and event listener services
2. **Create the `event_listener/` directory** with the provided files
3. **Add PostgreSQL triggers** to your database
4. **Start the services**: `docker-compose up -d`
5. **Set up Cloudflare Tunnel** for external access
6. **Test with external consumer** using the provided examples

This system provides a robust, persistent, and secure event queue for your VATSIM data collection system, enabling external systems to consume real-time events without requiring direct database access or open ports.

---

*Last updated: January 2024*
*Version: 1.0*
