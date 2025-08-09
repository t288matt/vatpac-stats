#!/bin/bash

# ===============================================
# VATSIM Data Collection System - Simple Production Deployment
# ===============================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get server IP
get_server_ip() {
    if [[ -z "$SERVER_IP" ]]; then
        read -p "Enter your server IP address: " SERVER_IP
        if [[ -z "$SERVER_IP" ]]; then
            print_error "Server IP cannot be empty"
            exit 1
        fi
    fi
    print_success "Server IP: $SERVER_IP"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Generate secure passwords
generate_production_env() {
    print_status "Generating production environment overrides..."
    
    # Generate secure passwords
    POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
    GRAFANA_PASSWORD=$(openssl rand -base64 16 | tr -d '\n')
    
    # Create production environment override
    cat > .env.production << EOF
# Production Environment Overrides
# Generated on $(date)

# Security - Change default passwords
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
GRAFANA_ADMIN_PASSWORD=${GRAFANA_PASSWORD}

# Production Mode
PRODUCTION_MODE=true
ERROR_MONITORING_ENABLED=true
LOG_LEVEL=INFO

# Performance for production
MEMORY_LIMIT_MB=4096
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
BATCH_SIZE_THRESHOLD=15000

# API Security (optional - uncomment to enable)
# API_KEY_REQUIRED=true
# API_RATE_LIMIT_ENABLED=true
# API_RATE_LIMIT_PER_MINUTE=100

# Geographic filtering (optional - uncomment to enable)
# ENABLE_BOUNDARY_FILTER=true
EOF
    
    chmod 600 .env.production
    print_success "Production environment file created"
    
    # Save credentials for user
    cat > production-credentials.txt << EOF
VATSIM Production Deployment Credentials
Generated on $(date)

Server IP: ${SERVER_IP}
Database Password: ${POSTGRES_PASSWORD}
Grafana Admin Password: ${GRAFANA_PASSWORD}

Access URLs:
- API: http://${SERVER_IP}:8001
- Grafana: http://${SERVER_IP}:3050
- API Status: http://${SERVER_IP}:8001/api/status
- API Docs: http://${SERVER_IP}:8001/docs

IMPORTANT: Save these credentials securely and delete this file after noting them down.
EOF
    
    chmod 600 production-credentials.txt
    print_warning "Credentials saved to: production-credentials.txt"
}

# Configure firewall
configure_firewall() {
    print_status "Configuring firewall..."
    
    if command -v ufw &> /dev/null; then
        sudo ufw --force enable
        sudo ufw allow ssh
        sudo ufw allow 8001/tcp  # API
        sudo ufw allow 3050/tcp  # Grafana
        print_success "Firewall configured (UFW)"
    elif command -v firewall-cmd &> /dev/null; then
        sudo firewall-cmd --permanent --add-port=8001/tcp
        sudo firewall-cmd --permanent --add-port=3050/tcp
        sudo firewall-cmd --reload
        print_success "Firewall configured (firewalld)"
    else
        print_warning "No firewall tool found. Please manually open ports:"
        print_status "- Port 22 (SSH)"
        print_status "- Port 8001 (API)"
        print_status "- Port 3050 (Grafana)"
    fi
}

# Deploy application
deploy_application() {
    print_status "Deploying VATSIM Data Collection System..."
    
    # Stop any existing containers
    docker-compose down 2>/dev/null || true
    
    # Build and start with production environment
    docker-compose --env-file .env.production up -d --build
    
    print_success "Application deployed"
}

# Verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    # Wait for services to start
    sleep 30
    
    # Check container status
    if docker-compose ps | grep -q "Up"; then
        print_success "Containers are running"
    else
        print_error "Some containers failed to start"
        docker-compose ps
        return 1
    fi
    
    # Test API
    if curl -f -s http://localhost:8001/api/status > /dev/null; then
        print_success "API is responding"
    else
        print_warning "API not responding yet (may still be starting up)"
    fi
    
    print_success "Deployment verification completed"
}

# Show deployment info
show_deployment_info() {
    print_success "=== DEPLOYMENT COMPLETED ==="
    echo ""
    print_status "Your VATSIM Data Collection System is running!"
    echo ""
    print_status "Access URLs:"
    print_status "- API: http://${SERVER_IP}:8001"
    print_status "- API Status: http://${SERVER_IP}:8001/api/status"
    print_status "- API Documentation: http://${SERVER_IP}:8001/docs"
    print_status "- Grafana: http://${SERVER_IP}:3050"
    echo ""
    print_status "Default Grafana Login: admin / ${GRAFANA_PASSWORD}"
    echo ""
    print_warning "NEXT STEPS:"
    print_status "1. Test the API: curl http://${SERVER_IP}:8001/api/status"
    print_status "2. Access Grafana to view dashboards"
    print_status "3. Check logs: docker-compose logs -f"
    print_status "4. Monitor system: docker-compose ps"
    echo ""
    print_status "Credentials saved in: production-credentials.txt"
    print_warning "Please save credentials and delete the file!"
}

# Main function
main() {
    print_status "Starting VATSIM Production Deployment"
    echo ""
    
    check_prerequisites
    get_server_ip
    
    echo ""
    print_warning "This will deploy VATSIM system with production settings."
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Deployment cancelled"
        exit 0
    fi
    
    generate_production_env
    configure_firewall
    deploy_application
    verify_deployment
    show_deployment_info
    
    print_success "Production deployment completed!"
}

# Run main function
main "$@"
