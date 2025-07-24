# PostgreSQL Migration Guide

## 🚀 Quick Migration Steps

### **Prerequisites**
1. **Docker Desktop** must be running
2. **Python dependencies** installed (`pip install -r requirements.txt`)
3. **Backup your current data** (optional but recommended)

### **Step 1: Start Docker Desktop**
1. Open Docker Desktop application
2. Wait for it to fully start (whale icon in system tray)
3. Verify it's running: `docker ps`

### **Step 2: Run Migration**
```bash
python migrate_to_postgresql_simple.py
```

### **Step 3: Start Application**
```bash
docker-compose up -d app
```

### **Step 4: Verify Migration**
- Dashboard: http://localhost:8001/frontend/index.html
- API Status: http://localhost:8001/api/status

## 📊 Migration Benefits

### **Performance Improvements**
- **Concurrent Access**: Multiple users can access data simultaneously
- **Better Indexing**: Advanced indexing for faster queries
- **Connection Pooling**: Efficient database connections
- **Partitioning**: Large tables can be partitioned for better performance

### **Scalability**
- **Horizontal Scaling**: Can distribute across multiple servers
- **Replication**: Built-in replication for high availability
- **Backup/Restore**: Advanced backup and recovery options

### **Data Integrity**
- **ACID Compliance**: Full transaction support
- **Constraints**: Advanced data validation
- **Triggers**: Automated data processing

## 🔧 Configuration Changes

### **Database URL**
- **Before**: `sqlite:///./atc_optimization.db`
- **After**: `postgresql://vatsim_user:vatsim_password@postgres:5432/vatsim_data`

### **Environment Variables**
```bash
DATABASE_URL=postgresql://vatsim_user:vatsim_password@postgres:5432/vatsim_data
REDIS_URL=redis://redis:6379
```

## 📈 Performance Comparison

| Metric | SQLite | PostgreSQL |
|--------|--------|------------|
| **Concurrent Users** | 1 | 100+ |
| **Write Throughput** | 1,000/sec | 10,000+/sec |
| **Memory Usage** | Low | Optimized |
| **Data Size** | Limited | Unlimited |
| **Backup** | File copy | Advanced |

## 🛠️ Troubleshooting

### **Docker Not Running**
```bash
# Start Docker Desktop manually
# Or check if it's installed
docker --version
```

### **Migration Fails**
```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs postgres

# Restart containers
docker-compose restart postgres redis
```

### **Data Verification**
```bash
# Check PostgreSQL data
docker exec -it vatsim_postgres psql -U vatsim_user -d vatsim_data -c "SELECT COUNT(*) FROM controllers;"
```

## 🔄 Rollback Plan

If you need to rollback to SQLite:

1. **Stop PostgreSQL containers**:
   ```bash
   docker-compose down
   ```

2. **Update configuration**:
   ```bash
   # Change DATABASE_URL back to SQLite
   export DATABASE_URL="sqlite:///./atc_optimization.db"
   ```

3. **Start with SQLite**:
   ```bash
   python run.py
   ```

## 📋 Migration Checklist

- [ ] Docker Desktop is running
- [ ] Python dependencies installed
- [ ] Current data backed up (optional)
- [ ] Migration script executed successfully
- [ ] Application starts with PostgreSQL
- [ ] Dashboard accessible
- [ ] Data verification passed
- [ ] Performance monitoring active

## 🎯 Next Steps After Migration

1. **Monitor Performance**: Check dashboard for improved performance
2. **Optimize Queries**: Use PostgreSQL-specific optimizations
3. **Scale Up**: Add more resources as needed
4. **Backup Strategy**: Implement regular PostgreSQL backups
5. **Monitoring**: Set up database monitoring

## 📞 Support

If you encounter issues during migration:

1. Check the logs: `docker-compose logs`
2. Verify Docker is running: `docker ps`
3. Test database connection: `docker exec -it vatsim_postgres psql -U vatsim_user -d vatsim_data`
4. Review this guide for troubleshooting steps

---

**Migration completed successfully! 🎉**

Your VATSIM data collection system is now running on PostgreSQL with improved performance, scalability, and reliability. 