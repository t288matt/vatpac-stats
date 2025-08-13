#!/bin/bash

# =============================================================================
# VATSIM Data System - Complete Cleanup Script
# =============================================================================
# This script completely removes the entire VATSIM data application,
# including all Docker containers, images, volumes, and project files.
# 
# WARNING: This will permanently delete ALL data and configurations!
# Use only when you want a completely fresh start.
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running or not accessible"
        print_error "Please start Docker and try again"
        exit 1
    fi
    print_success "Docker is running"
}

# Function to confirm user wants to proceed
confirm_cleanup() {
    echo
    echo "=================================================="
    echo "🚨 COMPLETE SYSTEM CLEANUP CONFIRMATION 🚨"
    echo "=================================================="
    echo
    echo "This script will PERMANENTLY DELETE:"
    echo "  • All Docker containers"
    echo "  • All Docker images" 
    echo "  • All Docker volumes (including database data)"
    echo "  • All Docker networks"
    echo "  • All project files and configurations"
    echo
    echo "⚠️  WARNING: This action is IRREVERSIBLE! ⚠️"
    echo
    read -p "Are you absolutely sure you want to continue? (yes/no): " confirm
    
    if [[ $confirm != "yes" ]]; then
        print_warning "Cleanup cancelled by user"
        exit 0
    fi
    
    echo
    read -p "Type 'DELETE EVERYTHING' to confirm: " final_confirm
    
    if [[ $final_confirm != "DELETE EVERYTHING" ]]; then
        print_warning "Final confirmation failed. Cleanup cancelled."
        exit 0
    fi
    
    print_status "Proceeding with complete system cleanup..."
}

# Function to stop and remove Docker services
cleanup_docker_services() {
    print_status "Stopping and removing Docker services..."
    
    # Check if we're in the project directory
    if [[ -f "docker-compose.yml" ]]; then
        print_status "Found docker-compose.yml, stopping services..."
        docker-compose down --remove-orphans --volumes 2>/dev/null || true
        print_success "Docker services stopped"
    else
        print_warning "No docker-compose.yml found, skipping service stop"
    fi
}

# Function to remove all Docker containers
cleanup_containers() {
    print_status "Removing all Docker containers..."
    
    # Get list of all containers (running and stopped)
    containers=$(docker ps -aq 2>/dev/null || true)
    
    if [[ -n "$containers" ]]; then
        print_status "Found $(echo "$containers" | wc -l) containers to remove..."
        echo "$containers" | xargs -r docker rm -f
        print_success "All containers removed"
    else
        print_success "No containers found to remove"
    fi
}

# Function to remove all Docker images
cleanup_images() {
    print_status "Removing all Docker images..."
    
    # Get list of all images
    images=$(docker images -aq 2>/dev/null || true)
    
    if [[ -n "$images" ]]; then
        print_status "Found $(echo "$images" | wc -l) images to remove..."
        echo "$images" | xargs -r docker rmi -f
        print_success "All images removed"
    else
        print_success "No images found to remove"
    fi
}

# Function to remove all Docker volumes
cleanup_volumes() {
    print_status "Removing all Docker volumes..."
    
    # Get list of all volumes
    volumes=$(docker volume ls -q 2>/dev/null || true)
    
    if [[ -n "$volumes" ]]; then
        print_status "Found $(echo "$volumes" | wc -l) volumes to remove..."
        echo "$volumes" | xargs -r docker volume rm -f
        print_success "All volumes removed"
    else
        print_success "No volumes found to remove"
    fi
}

# Function to remove all Docker networks
cleanup_networks() {
    print_status "Removing all Docker networks..."
    
    # Get list of custom networks (exclude default ones)
    networks=$(docker network ls --filter "type=custom" -q 2>/dev/null || true)
    
    if [[ -n "$networks" ]]; then
        print_status "Found $(echo "$networks" | wc -l) custom networks to remove..."
        echo "$networks" | xargs -r docker network rm
        print_success "All custom networks removed"
    else
        print_success "No custom networks found to remove"
    fi
}

# Function to clean up Docker system
cleanup_docker_system() {
    print_status "Performing final Docker system cleanup..."
    
    # Remove all unused containers, networks, images
    docker system prune -a --volumes -f 2>/dev/null || true
    
    # Remove any remaining unused volumes
    docker volume prune -f 2>/dev/null || true
    
    # Remove any remaining unused networks
    docker network prune -f 2>/dev/null || true
    
    print_success "Docker system cleanup completed"
}

# Function to remove project files
cleanup_project_files() {
    print_status "Removing project files..."
    
    # Get current directory
    current_dir=$(pwd)
    
    # Check if we're in a project directory
    if [[ -f "docker-compose.yml" ]] || [[ -f "requirements.txt" ]] || [[ -d "app" ]]; then
        print_status "Detected project directory: $current_dir"
        
        # Ask user if they want to remove the entire directory
        echo
        read -p "Remove entire project directory '$current_dir'? (yes/no): " remove_dir
        
        if [[ $remove_dir == "yes" ]]; then
            print_status "Removing project directory..."
            
            # Go to parent directory
            cd ..
            
            # Remove the project directory
            rm -rf "$(basename "$current_dir")"
            
            print_success "Project directory removed"
            print_status "You are now in: $(pwd)"
        else
            print_warning "Project directory preserved"
        fi
    else
        print_warning "No project directory detected, skipping file removal"
    fi
}

# Function to verify cleanup
verify_cleanup() {
    print_status "Verifying cleanup..."
    
    echo
    echo "=================================================="
    echo "🧹 CLEANUP VERIFICATION 🧹"
    echo "=================================================="
    
    # Check containers
    container_count=$(docker ps -aq 2>/dev/null | wc -l)
    echo "Containers remaining: $container_count"
    
    # Check images
    image_count=$(docker images -q 2>/dev/null | wc -l)
    echo "Images remaining: $image_count"
    
    # Check volumes
    volume_count=$(docker volume ls -q 2>/dev/null | wc -l)
    echo "Volumes remaining: $volume_count"
    
    # Check custom networks
    network_count=$(docker network ls --filter "type=custom" -q 2>/dev/null | wc -l)
    echo "Custom networks remaining: $network_count"
    
    echo "=================================================="
    
    if [[ $container_count -eq 0 ]] && [[ $image_count -eq 0 ]] && [[ $volume_count -eq 0 ]] && [[ $network_count -eq 0 ]]; then
        print_success "✅ Complete cleanup successful! System is clean."
    else
        print_warning "⚠️  Some items remain. Manual cleanup may be needed."
    fi
}

# Function to show next steps
show_next_steps() {
    echo
    echo "=================================================="
    echo "🚀 NEXT STEPS FOR FRESH INSTALL 🚀"
    echo "=================================================="
    echo
    echo "To reinstall the VATSIM Data System:"
    echo
    echo "1. Clone the repository:"
    echo "   git clone <your-repo-url>"
    echo "   cd <project-directory>"
    echo
    echo "2. Build and start the system:"
    echo "   docker-compose up --build"
    echo
    echo "3. Verify the installation:"
    echo "   docker-compose ps"
    echo "   curl http://localhost:8000/"
    echo
    echo "=================================================="
}

# Main execution
main() {
    echo
    echo "=================================================="
    echo "🧹 VATSIM Data System - Complete Cleanup Script 🧹"
    echo "=================================================="
    echo
    
    # Check if Docker is running
    check_docker
    
    # Confirm user wants to proceed
    confirm_cleanup
    
    # Perform cleanup steps
    cleanup_docker_services
    cleanup_containers
    cleanup_images
    cleanup_volumes
    cleanup_networks
    cleanup_docker_system
    cleanup_project_files
    
    # Verify cleanup
    verify_cleanup
    
    # Show next steps
    show_next_steps
    
    echo
    print_success "🎉 Cleanup script completed successfully!"
    echo
}

# Run main function
main "$@"
