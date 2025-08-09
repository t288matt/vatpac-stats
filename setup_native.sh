#!/bin/bash

echo "🚀 VATSIM Data App - Native Setup Script"
echo "=========================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ This script should not be run as root"
   exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install package if not exists
install_if_missing() {
    local package=$1
    local install_cmd=$2
    
    if ! command_exists $package; then
        echo "📦 Installing $package..."
        eval $install_cmd
    else
        echo "✅ $package already installed"
    fi
}

echo "🔍 Checking system dependencies..."

# Check/Install PostgreSQL
if ! command_exists psql; then
    echo "📦 Installing PostgreSQL..."
    sudo apt update
    sudo apt install -y postgresql postgresql-contrib
else
    echo "✅ PostgreSQL already installed"
fi

# Check/Install Redis
if ! command_exists redis-cli; then
    echo "📦 Installing Redis..."
    sudo apt install -y redis-server
else
    echo "✅ Redis already installed"
fi

# Check Python version
if ! command_exists python3.11; then
    echo "📦 Installing Python 3.11..."
    sudo apt install -y python3.11 python3.11-venv python3.11-dev
else
    echo "✅ Python 3.11 already installed"
fi

echo "🔧 Setting up database..."

# Start PostgreSQL if not running
if ! sudo systemctl is-active --quiet postgresql; then
    echo "🚀 Starting PostgreSQL..."
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
fi

# Create database and user
echo "🗄️  Setting up database..."
sudo -u postgres psql -c "CREATE USER vatsim_user WITH PASSWORD 'vatsim_password';" 2>/dev/null || echo "User already exists"
sudo -u postgres createdb vatsim_data 2>/dev/null || echo "Database already exists"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE vatsim_data TO vatsim_user;" 2>/dev/null || echo "Privileges already granted"

echo "🔧 Setting up Redis..."

# Start Redis if not running
if ! sudo systemctl is-active --quiet redis-server; then
    echo "🚀 Starting Redis..."
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
fi

# Configure Redis memory settings
echo "⚙️  Configuring Redis..."
sudo sed -i 's/# maxmemory <bytes>/maxmemory 512mb/' /etc/redis/redis.conf
sudo sed -i 's/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf
sudo systemctl restart redis-server

echo "🐍 Setting up Python environment..."

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3.11 -m venv venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "📝 Creating environment file..."

# Create .env file
cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://vatsim_user:vatsim_password@localhost:5432/vatsim_data
REDIS_URL=redis://localhost:6379

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001
PRODUCTION_MODE=false

# Performance Settings
MEMORY_LIMIT_MB=2048
BATCH_SIZE_THRESHOLD=10000

# Error Handling
LOG_LEVEL=info
ERROR_MONITORING_ENABLED=true

# VATSIM API Settings
VATSIM_API_URL=https://data.vatsim.net/v3/
VATSIM_POLLING_INTERVAL=30
VATSIM_WRITE_INTERVAL=300

EOF

echo "🗄️  Initializing database..."

# Initialize database
python -c "from app.database import init_db; init_db()" 2>/dev/null || echo "Database initialization failed or already done"

echo "✅ Native setup completed!"
echo ""
echo "🚀 To start the application:"
echo "   source venv/bin/activate"
echo "   python run.py"
echo ""
echo "🔧 Or use the quick start script:"
echo "   chmod +x run_native.sh"
echo "   ./run_native.sh"
echo ""
echo "📊 The app will be available at: http://localhost:8001" 