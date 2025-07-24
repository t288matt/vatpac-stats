#!/bin/bash

# VATSIM Data Collection System - Docker Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_status "Docker and Docker Compose are installed"
}

# Create necessary directories
create_directories() {
    print_info "Creating necessary directories..."
    
    mkdir -p data/{postgres,redis,cache}
    mkdir -p logs
    mkdir -p backups
    
    print_status "Directories created"
}

# Deploy the application
deploy() {
    print_info "Deploying VATSIM Data Collection System..."
    
    docker-compose up -d --build
    
    print_status "Application deployed successfully"
}

# Show deployment information
show_info() {
    echo ""
    echo "🎉 Deployment completed successfully!"
    echo "======================================"
    echo ""
    echo "📊 Application Access:"
    echo "   - Main Application: http://localhost:8001"
    echo "   - Dashboard: http://localhost:8001/frontend/index.html"
    echo "   - API Documentation: http://localhost:8001/docs"
    echo "   - API Status: http://localhost:8001/api/status"
    echo ""
    echo "🔧 Management Commands:"
    echo "   - View logs: docker-compose logs -f"
    echo "   - Stop services: docker-compose down"
    echo "   - Restart services: docker-compose restart"
    echo "   - View containers: docker-compose ps"
    echo ""
    echo "📋 Database Access:"
    echo "   - PostgreSQL: localhost:5432"
    echo "   - Redis: localhost:6379"
    echo ""
    echo "📚 Documentation:"
    echo "   - Docker Guide: DOCKER_README.md"
    echo "   - Migration Guide: POSTGRESQL_MIGRATION_GUIDE.md"
    echo "   - Remote Installation: REMOTE_INSTALLATION_GUIDE.md"
    echo ""
}

# Main deployment function
main() {
    echo "🚁 VATSIM Data Collection System - Docker Deployment"
    echo "=================================================="
    echo ""
    
    check_prerequisites
    create_directories
    deploy
    show_info
}

# Run main function
main "$@" 