#!/bin/bash

# ===============================================
# VATSIM Data Collection System - Production Deployment Script
# ===============================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEPLOYMENT_DIR="/opt/vatsim"
REPO_URL="https://github.com/yourusername/vatsim-data.git"  # Update this with your actual repo
SERVER_IP=""

# Function to print colored output
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

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root for security reasons"
        print_status "Please run as a regular user with sudo privileges"
        exit 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        print_status "Visit: https://docs.docker.com/engine/install/"
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        print_status "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # Check if user is in docker group
    if ! groups $USER | grep -q '\bdocker\b'; then
        print_warning "User $USER is not in the docker group"
        print_status "Adding user to docker group..."
        sudo usermod -aG docker $USER
        print_warning "Please log out and log back in for group changes to take effect"
        print_status "Then run this script again"
        exit 1
    fi
    
    # Check if git is installed
    if ! command -v git &> /dev/null; then
        print_error "Git is not installed. Installing git..."
        sudo apt update && sudo apt install -y git
    fi
    
    # Check if curl is installed
    if ! command -v curl &> /dev/null; then
        print_error "Curl is not installed. Installing curl..."
        sudo apt update && sudo apt install -y curl
    fi
    
    print_success "All prerequisites met"
}

# Function to get user input
get_user_input() {
    print_status "Gathering deployment configuration..."
    
    # Get domain name
    while [[ -z "$DOMAIN_NAME" ]]; do
        read -p "Enter your domain name (e.g., vatsim-data.example.com): " DOMAIN_NAME
        if [[ -z "$DOMAIN_NAME" ]]; then
            print_error "Domain name cannot be empty"
        fi
    done
    
    # Get server IP
    while [[ -z "$SERVER_IP" ]]; do
        read -p "Enter your server IP address: " SERVER_IP
        if [[ -z "$SERVER_IP" ]]; then
            print_error "Server IP cannot be empty"
        fi
    done
    
    print_success "Configuration gathered"
    print_status "Domain: $DOMAIN_NAME"
    print_status "Server IP: $SERVER_IP"
}

# Function to create directory structure
create_directories() {
    print_status "Creating directory structure..."
    
    sudo mkdir -p $DEPLOYMENT_DIR/{config,logs,backups,scripts,certs}
    sudo chown -R $USER:docker $DEPLOYMENT_DIR
    sudo chmod -R 755 $DEPLOYMENT_DIR
    sudo chmod 700 $DEPLOYMENT_DIR/config  # Secure config directory
    
    print_success "Directory structure created"
}

# Function to clone repository
clone_repository() {
    print_status "Cloning repository..."
    
    if [[ -d "$DEPLOYMENT_DIR/app" ]]; then
        print_warning "Application directory already exists. Updating..."
        cd $DEPLOYMENT_DIR/app
        git pull
    else
        cd $DEPLOYMENT_DIR
        git clone $REPO_URL app
    fi
    
    print_success "Repository cloned/updated"
}

# Function to generate secure passwords
generate_passwords() {
    print_status "Generating secure passwords..."
    
    # Generate random passwords
    JWT_SECRET=$(openssl rand -base64 64 | tr -d '\n')
    API_MASTER_KEY=$(openssl rand -base64 32 | tr -d '\n')
    POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
    REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
    GRAFANA_PASSWORD=$(openssl rand -base64 16 | tr -d '\n')
    
    print_success "Secure passwords generated"
}

# Function to create production environment file
create_env_file() {
    print_status "Creating production environment file..."
    
    cat > $DEPLOYMENT_DIR/config/production.env << EOF
# VATSIM Data Collection System - Production Environment
# Generated on $(date)

# Domain Configuration
DOMAIN_NAME=$DOMAIN_NAME

# Security Configuration
JWT_SECRET_KEY=$JWT_SECRET
API_MASTER_KEY=$API_MASTER_KEY

# Database Security
POSTGRES_USER=vatsim_prod_user
POSTGRES_PASSWORD=$POSTGRES_PASSWORD

# Redis Security
REDIS_PASSWORD=$REDIS_PASSWORD

# Grafana Security
GRAFANA_ADMIN_PASSWORD=$GRAFANA_PASSWORD

# API Security
API_KEY_REQUIRED=true
API_RATE_LIMIT_ENABLED=true
API_RATE_LIMIT_PER_MINUTE=100
API_MAX_CONCURRENT_REQUESTS=50

# CORS Configuration
CORS_ORIGINS=https://api.$DOMAIN_NAME,https://grafana.$DOMAIN_NAME,https://$DOMAIN_NAME

# Performance Settings
MEMORY_LIMIT_MB=4096
BATCH_SIZE_THRESHOLD=15000
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# VATSIM Data Collection
VATSIM_POLLING_INTERVAL=10

WRITE_TO_DISK_INTERVAL=15
VATSIM_API_TIMEOUT=30
VATSIM_API_RETRY_ATTEMPTS=3

# Logging & Monitoring
LOG_LEVEL=INFO

# Flight Filtering
FLIGHT_FILTER_ENABLED=true
FLIGHT_FILTER_LOG_LEVEL=INFO

# Geographic Boundary Filter
ENABLE_BOUNDARY_FILTER=false
BOUNDARY_DATA_PATH=australian_airspace_polygon.json
BOUNDARY_FILTER_LOG_LEVEL=INFO
BOUNDARY_FILTER_PERFORMANCE_THRESHOLD=10.0



# Backup Configuration
BACKUP_ENABLED=true
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=30
EOF
    
    # Secure the environment file
    chmod 600 $DEPLOYMENT_DIR/config/production.env
    
    print_success "Production environment file created"
}

# Function to configure firewall
configure_firewall() {
    print_status "Configuring firewall..."
    
    # Check if UFW is installed
    if command -v ufw &> /dev/null; then
        # Enable UFW if not already enabled
        sudo ufw --force enable
        
        # Allow SSH
        sudo ufw allow ssh
        
        # Allow HTTP and HTTPS
        sudo ufw allow 80/tcp
        sudo ufw allow 443/tcp
        
        print_success "Firewall configured"
    else
        print_warning "UFW not installed. Please configure firewall manually:"
        print_status "- Allow port 22 (SSH)"
        print_status "- Allow port 80 (HTTP)"
        print_status "- Allow port 443 (HTTPS)"
    fi
}

# Function to create Docker Compose override
create_docker_override() {
    print_status "Creating Docker Compose production configuration..."
    
    cd $DEPLOYMENT_DIR/app
    
    # Create production override file
    cat > docker-compose.override.yml << EOF
version: '3.8'

services:
  app:
    env_file:
      - $DEPLOYMENT_DIR/config/production.env
    volumes:
      - $DEPLOYMENT_DIR/logs:/app/logs:rw
      - $DEPLOYMENT_DIR/backups:/app/backups:rw
  
  postgres:
    env_file:
      - $DEPLOYMENT_DIR/config/production.env
  
  redis:
    env_file:
      - $DEPLOYMENT_DIR/config/production.env
  
  grafana:
    env_file:
      - $DEPLOYMENT_DIR/config/production.env
EOF
    
    print_success "Docker Compose override created"
}

# Function to deploy application
deploy_application() {
    print_status "Deploying application..."
    
    cd $DEPLOYMENT_DIR/app
    
    # Build and start services
    docker-compose -f docker-compose.prod.yml --env-file $DEPLOYMENT_DIR/config/production.env up -d --build
    
    print_success "Application deployed"
}

# Function to verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    # Wait for services to start
    sleep 30
    
    # Check if all containers are running
    if docker-compose -f $DEPLOYMENT_DIR/app/docker-compose.prod.yml ps | grep -q "Up"; then
        print_success "All containers are running"
    else
        print_error "Some containers failed to start"
        docker-compose -f $DEPLOYMENT_DIR/app/docker-compose.prod.yml ps
        return 1
    fi
    
    # Test API endpoint
    if curl -f -s http://localhost:8001/api/status > /dev/null; then
        print_success "API is responding"
    else
        print_warning "API not responding yet (this may be normal during startup)"
    fi
    
    print_success "Deployment verification completed"
}

# Function to display post-deployment information
show_post_deployment_info() {
    print_success "=== DEPLOYMENT COMPLETED SUCCESSFULLY ==="
    echo ""
    print_status "Your VATSIM Data Collection System is now running!"
    echo ""
    print_status "Access URLs:"
    print_status "- API: https://api.$DOMAIN_NAME"
    print_status "- Grafana: https://grafana.$DOMAIN_NAME"
    print_status "- Traefik Dashboard: https://traefik.$DOMAIN_NAME"
    echo ""
    print_status "Credentials (SAVE THESE SECURELY):"
    print_status "- Grafana Admin: admin / $GRAFANA_PASSWORD"
    print_status "- API Master Key: $API_MASTER_KEY"
    print_status "- Database Password: $POSTGRES_PASSWORD"
    echo ""
    print_warning "IMPORTANT NEXT STEPS:"
    print_status "1. Configure DNS A records for your domain to point to $SERVER_IP"
    print_status "2. Wait 5-10 minutes for SSL certificates to be generated"
    print_status "3. Test the API: curl https://api.$DOMAIN_NAME/api/status"
    print_status "4. Access Grafana to view dashboards"
    print_status "5. Set up monitoring alerts"
    print_status "6. Configure backup storage (S3) if needed"
    echo ""
    print_status "Logs location: $DEPLOYMENT_DIR/logs"
    print_status "Config location: $DEPLOYMENT_DIR/config"
    print_status "Backup location: $DEPLOYMENT_DIR/backups"
    echo ""
    print_status "To check container status: docker-compose -f $DEPLOYMENT_DIR/app/docker-compose.prod.yml ps"
    print_status "To view logs: docker-compose -f $DEPLOYMENT_DIR/app/docker-compose.prod.yml logs -f"
}

# Main deployment function
main() {
    print_status "Starting VATSIM Data Collection System Production Deployment"
    echo ""
    
    check_root
    check_prerequisites
    get_user_input
    
    echo ""
    print_warning "This will deploy the VATSIM system to production."
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Deployment cancelled"
        exit 0
    fi
    
    create_directories
    clone_repository
    generate_passwords
    create_env_file
    configure_firewall
    create_docker_override
    deploy_application
    verify_deployment
    show_post_deployment_info
    
    print_success "Deployment completed successfully!"
}

# Run main function
main "$@"
