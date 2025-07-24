#!/bin/bash

# VATSIM Data Collection System - Docker Deployment Script
# Simplified deployment without monitoring stack

set -e

echo "🚁 Deploying VATSIM Data Collection System..."

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

# Set environment variables
export DATABASE_URL="postgresql://vatsim_user:vatsim_password@localhost:5432/vatsim_data"
export REDIS_URL="redis://localhost:6379"

# Build and start services
echo "🔨 Building and starting services..."
docker-compose up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

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

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📊 Services:"
echo "   • Application: http://localhost:8001"
echo "   • API Documentation: http://localhost:8001/docs"
echo "   • Dashboard: http://localhost:8001/frontend/index.html"
echo "   • pgAdmin: http://localhost:5050 (admin@vatsim.local / admin)"
echo "   • Redis Commander: http://localhost:8081"
echo ""
echo "🗄️  Database:"
echo "   • PostgreSQL: localhost:5432"
echo "   • Redis: localhost:6379"
echo ""
echo "📝 Useful commands:"
echo "   • View logs: docker-compose logs -f"
echo "   • Stop services: docker-compose down"
echo "   • Restart services: docker-compose restart"
echo "   • Update and restart: docker-compose up -d --build"
echo ""
echo "🔍 Monitoring:"
echo "   • Application logs: docker-compose logs -f app"
echo "   • Database logs: docker-compose logs -f postgres"
echo "   • Redis logs: docker-compose logs -f redis" 