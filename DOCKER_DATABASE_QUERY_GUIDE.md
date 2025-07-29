# Docker Database Query Tools Guide

## 🐳 **Running in Docker Container**

You're correct - this is a Docker container environment. Here's how to properly access the database query tools:

## 🚀 **Quick Start**

### **1. Start the Docker Services**
```bash
# Start all services (PostgreSQL, Redis, App)
docker-compose up -d

# Check if services are running
docker-compose ps
```

### **2. Access the Web Interface**
Once the services are running, you can access the database query tools from your **host machine** (outside Docker):

- **Database Query Tool**: http://localhost:8001/frontend/database-query.html
- **Main Dashboard**: http://localhost:8001/frontend/index.html
- **API Status**: http://localhost:8001/api/status
- **Database Status**: http://localhost:8001/api/database/status

## 🛠️ **Free Windows Database Tools**

Since you're running in Docker, you have several options for querying the database:

### **Option 1: Web-Based Query Tool (Recommended)**
- **URL**: http://localhost:8001/frontend/database-query.html
- **Features**: 
  - ✅ No installation required
  - ✅ Works in any browser
  - ✅ Predefined queries
  - ✅ Custom SQL support
  - ✅ Query history
  - ✅ Export results

### **Option 2: Connect to PostgreSQL Database**
The Docker setup includes PostgreSQL. You can connect using:

**Connection Details:**
- **Host**: localhost
- **Port**: 5432
- **Database**: vatsim_data
- **Username**: vatsim_user
- **Password**: vatsim_password

**Free Windows Tools for PostgreSQL:**

#### **1. DBeaver Community** (Best Overall)
- **Download**: https://dbeaver.io/download/
- **Setup**:
  1. Install DBeaver Community
  2. Create new connection → PostgreSQL
  3. Host: `localhost`, Port: `5432`
  4. Database: `vatsim_data`
  5. Username: `vatsim_user`, Password: `vatsim_password`

#### **2. pgAdmin** (PostgreSQL Native)
- **Download**: https://www.pgadmin.org/download/
- **Features**: Official PostgreSQL admin tool

#### **3. HeidiSQL** (Lightweight)
- **Download**: https://www.heidisql.com/
- **Features**: Fast and simple

## 🔧 **Docker Commands**

### **Start Services**
```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d app
```

### **Check Service Status**
```bash
# View running services
docker-compose ps

# View logs
docker-compose logs app

# View real-time logs
docker-compose logs -f app
```

### **Access Container Shell**
```bash
# Access the app container
docker-compose exec app bash

# Access PostgreSQL container
docker-compose exec postgres psql -U vatsim_user -d vatsim_data
```

### **Stop Services**
```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## 📊 **Database Schema**

Your PostgreSQL database contains these tables:

### **Core Tables**
- **controllers** - ATC controller information
- **flights** - Active flight data
- **traffic_movements** - Airport traffic movements
- **sectors** - Airspace sector data

### **Analytics Tables**
- **flight_summaries** - Aggregated flight statistics
- **movement_summaries** - Movement pattern analysis

## 🔍 **Useful Queries**

### **Active Controllers**
```sql
SELECT callsign, facility, position, status, last_seen, workload_score
FROM controllers 
WHERE status = 'online' 
ORDER BY last_seen DESC 
LIMIT 20;
```

### **Recent Flights**
```sql
SELECT callsign, aircraft_type, departure, arrival, altitude, speed, last_updated
FROM flights 
WHERE status = 'active' 
ORDER BY last_updated DESC 
LIMIT 20;
```

### **Controller Workload Analysis**
```sql
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
LIMIT 15;
```

## 🌐 **Web Interface Features**

### **Database Query Tool** (http://localhost:8001/frontend/database-query.html)
- **Predefined Queries**: Click to run common queries
- **Custom SQL**: Write your own SQL queries
- **Query History**: Save and reuse queries
- **Results Export**: Export to CSV/JSON
- **Real-time Stats**: Database overview

### **Main Dashboard** (http://localhost:8001/frontend/index.html)
- **Real-time Data**: Live VATSIM data
- **Performance Metrics**: System monitoring
- **Traffic Analysis**: Movement patterns
- **Controller Status**: ATC positions

## 🔧 **Troubleshooting**

### **Service Not Starting**
```bash
# Check logs
docker-compose logs

# Restart services
docker-compose restart

# Rebuild and start
docker-compose up -d --build
```

### **Database Connection Issues**
```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready -U vatsim_user -d vatsim_data

# Check database tables
docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c "\dt"
```

### **Port Already in Use**
```bash
# Check what's using port 8001
netstat -tulpn | grep 8001

# Stop conflicting service
sudo systemctl stop conflicting-service
```

## 📈 **Performance Tips**

### **For Large Queries**
- Use `LIMIT` clauses
- Add `WHERE` conditions
- Use indexes on frequently queried columns
- Export results to CSV for analysis

### **For Real-time Data**
- Use the web interface for live data
- Set up automated queries
- Monitor database performance

## 🎯 **Recommended Workflow**

1. **Start Docker services**: `docker-compose up -d`
2. **Access web interface**: http://localhost:8001/frontend/database-query.html
3. **Use predefined queries** for common tasks
4. **Write custom SQL** for specific needs
5. **Export results** to CSV for further analysis
6. **Use DBeaver** for advanced database management

## 📞 **Support**

- **Docker Issues**: Check `docker-compose logs`
- **Database Issues**: Connect directly to PostgreSQL
- **Web Interface**: Check browser console for errors
- **Performance**: Monitor system resources

---

**Happy Querying from Docker!** 🐳✈️ 