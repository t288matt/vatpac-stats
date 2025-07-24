# Remote Machine Installation Guide

## 🚀 Quick Installation Steps

### **Prerequisites**
- **macOS** (or Linux/Windows)
- **Python 3.8+** installed
- **Git** for cloning the repository
- **Internet connection** for downloading dependencies

### **Step 1: Clone the Repository**
```bash
git clone <your-repository-url>
cd vatsim-data-collection
```

### **Step 2: Install Python Dependencies**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

### **Step 3: Configure Environment**
```bash
# Create environment file
cat > .env << EOF
DATABASE_URL=sqlite:///./atc_optimization.db
REDIS_URL=redis://localhost:6379
API_HOST=0.0.0.0
API_PORT=8001
MEMORY_LIMIT_MB=2048
BATCH_SIZE_THRESHOLD=10000
LOG_LEVEL=INFO
EOF
```

### **Step 4: Test the Application**
```bash
# Run the application
python run.py
```

### **Step 5: Verify Installation**
- **API Status**: http://localhost:8001/api/status
- **Dashboard**: http://localhost:8001/frontend/index.html
- **API Docs**: http://localhost:8001/docs

## 📋 Detailed Installation Steps

### **1. System Requirements**

#### **Minimum Requirements**
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 10GB free space
- **Network**: Stable internet connection

#### **Recommended Requirements**
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 50GB+ SSD
- **Network**: High-speed internet

### **2. Python Installation**

#### **macOS**
```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11

# Verify installation
python3 --version
```

#### **Linux (Ubuntu/Debian)**
```bash
# Update package list
sudo apt update

# Install Python and pip
sudo apt install python3 python3-pip python3-venv

# Verify installation
python3 --version
```

#### **Windows**
1. Download Python from https://www.python.org/downloads/
2. Install with "Add to PATH" option
3. Verify installation: `python --version`

### **3. Project Setup**

#### **Clone Repository**
```bash
# Clone the repository
git clone <your-repository-url>
cd vatsim-data-collection

# Verify files are present
ls -la
```

#### **Create Virtual Environment**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Verify activation
which python  # Should point to venv/bin/python
```

#### **Install Dependencies**
```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Verify installation
python -c "import fastapi, sqlalchemy, redis; print('✅ Dependencies installed successfully')"
```

### **4. Configuration**

#### **Environment Variables**
```bash
# Create .env file
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
```

#### **Directory Structure**
```bash
# Create necessary directories
mkdir -p data logs backups

# Set permissions
chmod 755 data logs backups
```

### **5. Testing the Installation**

#### **Start the Application**
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Start the application
python run.py
```

#### **Verify Services**
```bash
# Check if application is running
curl http://localhost:8001/api/status

# Check database
ls -la atc_optimization.db

# Check logs
ls -la logs/
```

### **6. Production Setup**

#### **Systemd Service (Linux)**
```bash
# Create service file
sudo tee /etc/systemd/system/vatsim-data.service << EOF
[Unit]
Description=VATSIM Data Collection System
After=network.target

[Service]
Type=simple
User=vatsim
WorkingDirectory=/opt/vatsim-data-collection
Environment=PATH=/opt/vatsim-data-collection/venv/bin
ExecStart=/opt/vatsim-data-collection/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable vatsim-data.service
sudo systemctl start vatsim-data.service
```

#### **LaunchAgent (macOS)**
```bash
# Create LaunchAgent plist
cat > ~/Library/LaunchAgents/com.vatsim.data.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.vatsim.data</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/vatsim-data-collection/venv/bin/python</string>
        <string>/opt/vatsim-data-collection/run.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/opt/vatsim-data-collection</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

# Load the service
launchctl load ~/Library/LaunchAgents/com.vatsim.data.plist
```

## 🔧 Troubleshooting

### **Common Issues**

#### **Python Version Issues**
```bash
# Check Python version
python3 --version

# If version is too old, install newer version
brew install python@3.11  # macOS
sudo apt install python3.11  # Ubuntu
```

#### **Dependency Installation Issues**
```bash
# Clear pip cache
pip cache purge

# Upgrade pip
pip install --upgrade pip

# Install with verbose output
pip install -r requirements.txt -v
```

#### **Permission Issues**
```bash
# Fix directory permissions
chmod 755 data logs backups

# Fix file permissions
chmod 644 .env
```

#### **Port Already in Use**
```bash
# Check what's using port 8001
lsof -i :8001

# Kill the process
kill -9 <PID>

# Or change port in .env
echo "API_PORT=8002" >> .env
```

### **Logs and Debugging**
```bash
# Check application logs
tail -f logs/app.log

# Check system logs
journalctl -u vatsim-data.service -f  # Linux
log show --predicate 'process == "vatsim"' --last 1h  # macOS
```

## 📊 Performance Monitoring

### **Resource Usage**
```bash
# Monitor CPU and memory
top -p $(pgrep -f "python run.py")

# Monitor disk usage
df -h
du -sh data/ logs/ backups/
```

### **Network Monitoring**
```bash
# Check network connections
netstat -an | grep 8001

# Monitor network traffic
iftop -i eth0  # Linux
nettop -m tcp   # macOS
```

## 🔄 Next Steps After Installation

1. **Test Data Collection**: Verify VATSIM data is being collected
2. **Monitor Performance**: Check resource usage and optimize
3. **Set Up Backups**: Configure automated database backups
4. **Security**: Configure firewall and access controls
5. **Dockerization**: Prepare for container deployment

## 📞 Support

If you encounter issues:

1. **Check logs**: `tail -f logs/app.log`
2. **Verify dependencies**: `pip list`
3. **Test connectivity**: `curl http://localhost:8001/api/status`
4. **Check system resources**: `top`, `df`, `free`

---

**Installation completed successfully! 🎉**

Your VATSIM data collection system is now running on the remote machine and ready for dockerization. 