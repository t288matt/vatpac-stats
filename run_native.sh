#!/bin/bash

echo "🚀 Starting VATSIM Data App (Native Mode)"
echo "=========================================="

# Function to check if service is running
service_running() {
    sudo systemctl is-active --quiet $1
}

# Function to start service if not running
start_service() {
    local service=$1
    local name=$2
    
    if ! service_running $service; then
        echo "❌ $name not running. Starting..."
        sudo systemctl start $service
        sleep 2
        if service_running $service; then
            echo "✅ $name started successfully"
        else
            echo "❌ Failed to start $name"
            exit 1
        fi
    else
        echo "✅ $name is running"
    fi
}

# Check and start PostgreSQL
start_service postgresql "PostgreSQL"

# Check and start Redis
start_service redis-server "Redis"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run setup_native.sh first"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Run setup_native.sh first"
    exit 1
fi

# Load environment variables
echo "📝 Loading environment variables..."
export $(cat .env | xargs)

# Set default values if not in .env
export PRODUCTION_MODE=${PRODUCTION_MODE:-false}
export DATABASE_URL=${DATABASE_URL:-postgresql://vatsim_user:vatsim_password@localhost:5432/vatsim_data}
export REDIS_URL=${REDIS_URL:-redis://localhost:6379}

# Test database connection
echo "🔍 Testing database connection..."
python -c "
import psycopg2
try:
    conn = psycopg2.connect('$DATABASE_URL')
    conn.close()
    print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"

# Test Redis connection
echo "🔍 Testing Redis connection..."
python -c "
import redis
try:
    r = redis.from_url('$REDIS_URL')
    r.ping()
    print('✅ Redis connection successful')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    exit(1)
"

echo "🚀 Starting application..."
echo "📊 API will be available at: http://localhost:8001"
echo "📚 Documentation at: http://localhost:8001/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the application
python run.py 