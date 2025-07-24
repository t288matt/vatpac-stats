#!/bin/bash

# VATSIM Data Collection System - Write-Optimized Deployment
# OPTIMIZED FOR 99.9% WRITES - MINIMAL READS

set -e

echo "🚁 Deploying Write-Optimized VATSIM Data Collection System..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data logs backups

# Set environment variables for write optimization
export DATABASE_URL="postgresql://vatsim_user:vatsim_password@localhost:5432/vatsim_data"
export REDIS_URL="redis://localhost:6379"

# Stop existing services
echo "🛑 Stopping existing services..."
docker-compose down

# Remove existing database volume for fresh start
echo "🗑️  Removing existing database for write-optimized setup..."
docker volume rm vatsim-data_postgres_data 2>/dev/null || true

# Build and start services with write optimization
echo "🔨 Building and starting write-optimized services..."
docker-compose up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 45

# Check service health
echo "🏥 Checking service health..."

# Check PostgreSQL
if docker-compose exec -T postgres pg_isready -U vatsim_user -d vatsim_data; then
    echo "✅ PostgreSQL is healthy"
else
    echo "❌ PostgreSQL health check failed"
    exit 1
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis is healthy"
else
    echo "❌ Redis health check failed"
    exit 1
fi

# Check Application
if curl -f http://localhost:8001/api/status > /dev/null 2>&1; then
    echo "✅ Application is healthy"
else
    echo "❌ Application health check failed"
    exit 1
fi

# Apply write optimizations
echo "⚡ Applying write optimizations..."
docker-compose exec -T postgres psql -U vatsim_user -d vatsim_data -c "
-- Disable autovacuum for write-heavy tables
ALTER TABLE flights SET (autovacuum_enabled = false);
ALTER TABLE controllers SET (autovacuum_enabled = false);
ALTER TABLE traffic_movements SET (autovacuum_enabled = false);
ALTER TABLE events SET (autovacuum_enabled = false);

-- Set fillfactor for write optimization
ALTER TABLE flights SET (fillfactor = 100);
ALTER TABLE controllers SET (fillfactor = 100);
ALTER TABLE traffic_movements SET (fillfactor = 100);
ALTER TABLE events SET (fillfactor = 100);

-- Verify write optimizations
SELECT schemaname, tablename, autovacuum_enabled, fillfactor 
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('flights', 'controllers', 'traffic_movements', 'events');
"

echo ""
echo "🎉 Write-Optimized Deployment completed successfully!"
echo ""
echo "📊 Write Optimizations Applied:"
echo "   • Synchronous commits: DISABLED (async writes)"
echo "   • WAL buffers: 32MB (increased)"
echo "   • Checkpoint timeout: 10min (longer intervals)"
echo "   • Autovacuum: DISABLED for write-heavy tables"
echo "   • Fillfactor: 100% (no update space)"
echo "   • Foreign keys: REMOVED for write speed"
echo "   • Indexes: MINIMAL (only essential)"
echo "   • Triggers: MINIMAL (only timestamps)"
echo ""
echo "📊 Services:"
echo "   • Application: http://localhost:8001"
echo "   • API Documentation: http://localhost:8001/docs"
echo "   • Dashboard: http://localhost:8001/frontend/index.html"
echo ""
echo "🗄️  Database:"
echo "   • PostgreSQL: localhost:5432 (Write-Optimized)"
echo "   • Redis: localhost:6379"
echo ""
echo "📝 Write Performance Commands:"
echo "   • View logs: docker-compose logs -f"
echo "   • Stop services: docker-compose down"
echo "   • Restart services: docker-compose restart"
echo "   • Monitor writes: docker-compose exec postgres psql -U vatsim_user -d vatsim_data -c \"SELECT * FROM pg_stat_user_tables;\""
echo ""
echo "⚠️  IMPORTANT: This configuration prioritizes WRITE performance over data integrity."
echo "   Foreign key constraints are disabled for maximum write throughput."
echo "   Use this setup for high-frequency data ingestion only." 