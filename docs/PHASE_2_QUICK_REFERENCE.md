# Phase 2 Quick Reference - Error Handling & Event Architecture

## 🚀 **Quick Start Commands**

### **1. Start the Application**
```bash
# Start with Docker
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f app
```

### **2. Test Core Functionality**
```bash
# Health check
curl http://localhost:8001/api/status

# Get flights
curl http://localhost:8001/api/flights

# Get ATC positions
curl http://localhost:8001/api/atc-positions
```

### **3. Test Event System**
```bash
# Publish event
curl -X POST http://localhost:8001/api/events/publish \
  -H "Content-Type: application/json" \
  -d '{"event_type": "flight_update", "data": {"callsign": "ABC123"}}'

# Get event status
curl http://localhost:8001/api/events/status
```

## 🔧 **Service Usage Examples**

### **Database Service**
```python
from app.services.database_service import get_database_service

db_service = get_database_service()
track = await db_service.get_flight_track("ABC123")
```

### **Event Bus (Simplified)**
```python
from app.services.event_bus import publish_event, EventType

# Publish event
await publish_event(EventType.FLIGHT_UPDATE, {"callsign": "ABC123"})
```

### **VATSIM Service**
```python
from app.services.vatsim_service import get_vatsim_service

vatsim_service = get_vatsim_service()
data = await vatsim_service.fetch_vatsim_data()
``` 