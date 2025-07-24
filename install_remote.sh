#!/bin/bash

# VATSIM Data Collection System - Remote Installation Script
# This script installs the application on a remote machine

set -e

echo "🚁 Installing VATSIM Data Collection System on Remote Machine..."
echo "================================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    print_error "requirements.txt not found. Please run this script from the project root directory."
    exit 1
fi

# Check Python version
echo "🔍 Checking Python version..."
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    print_status "Python $python_version is compatible"
else
    print_error "Python $python_version is too old. Please install Python 3.8 or higher."
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ -d "venv" ]; then
    print_warning "Virtual environment already exists. Removing..."
    rm -rf venv
fi

python3 -m venv venv
print_status "Virtual environment created"

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate
print_status "Virtual environment activated"

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip
print_status "Pip upgraded"

# Install dependencies
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt
print_status "Dependencies installed"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data logs backups
chmod 755 data logs backups
print_status "Directories created"

# Create .env file
echo "⚙️  Creating environment configuration..."
cat > .env << EOF
# Database Configuration
DATABASE_URL=sqlite:///./atc_optimization.db

# Redis Configuration (optional for local testing)
REDIS_URL=redis://localhost:6379

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001

# Performance Settings
MEMORY_LIMIT_MB=2048
BATCH_SIZE_THRESHOLD=10000

# Logging
LOG_LEVEL=INFO
EOF
print_status "Environment configuration created"

# Test the installation
echo "🧪 Testing installation..."
python -c "import fastapi, sqlalchemy, redis; print('✅ All dependencies imported successfully')"
print_status "Installation test passed"

# Create startup script
echo "🚀 Creating startup script..."
cat > start.sh << 'EOF'
#!/bin/bash
# VATSIM Data Collection System - Startup Script

# Activate virtual environment
source venv/bin/activate

# Start the application
python run.py
EOF

chmod +x start.sh
print_status "Startup script created"

# Create systemd service (Linux)
if command -v systemctl &> /dev/null; then
    echo "🔧 Creating systemd service..."
    sudo tee /etc/systemd/system/vatsim-data.service << EOF
[Unit]
Description=VATSIM Data Collection System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    print_status "Systemd service created"
    print_warning "To enable the service, run: sudo systemctl enable vatsim-data.service"
fi

# Create LaunchAgent (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🔧 Creating LaunchAgent for macOS..."
    cat > ~/Library/LaunchAgents/com.vatsim.data.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.vatsim.data</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(pwd)/venv/bin/python</string>
        <string>$(pwd)/run.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$(pwd)</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF
    print_status "LaunchAgent created"
    print_warning "To load the service, run: launchctl load ~/Library/LaunchAgents/com.vatsim.data.plist"
fi

echo ""
echo "🎉 Installation completed successfully!"
echo "======================================"
echo ""
echo "📋 Next steps:"
echo "1. Start the application: ./start.sh"
echo "2. Access the dashboard: http://localhost:8001/frontend/index.html"
echo "3. Check API status: http://localhost:8001/api/status"
echo "4. View API docs: http://localhost:8001/docs"
echo ""
echo "🔧 For production deployment:"
if command -v systemctl &> /dev/null; then
    echo "   sudo systemctl enable vatsim-data.service"
    echo "   sudo systemctl start vatsim-data.service"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "   launchctl load ~/Library/LaunchAgents/com.vatsim.data.plist"
fi
echo ""
echo "📚 For more information, see: REMOTE_INSTALLATION_GUIDE.md"
echo "" 