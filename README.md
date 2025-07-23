# VATSIM Data Collection & Traffic Analysis System

## 🛩️ Overview

A real-time VATSIM (Virtual Air Traffic Simulation Network) data collection and traffic analysis system focused on Australian airspace. The system provides comprehensive dashboards and analytics for air traffic movements.

## 🚀 Features

### Real-time Data Collection
- **VATSIM Network Integration**: Collects live data from VATSIM network every 30 seconds
- **Australian Airports**: Monitors 9 major Australian airports
- **Traffic Movement Detection**: Automatic detection of arrivals and departures
- **Data Persistence**: SQLite database with optimized storage

### Dashboards & Analytics
- **📊 Traffic Dashboard**: User-friendly interface showing airport activity
- **📈 Graph Dashboard**: Interactive charts for Australia's 5 largest airports
- **🔄 Real-time Updates**: Auto-refresh every 30 seconds
- **📱 Mobile Responsive**: Works on all devices

### API Endpoints
- `/api/status` - System status and statistics
- `/api/controllers` - Active controllers
- `/api/flights` - Current flights
- `/api/traffic/movements/{airport}` - Airport movements
- `/api/traffic/summary/{region}` - Regional summary
- `/api/traffic/trends/{airport}` - Traffic trends

## 🏗️ Architecture

### Core Components
- **FastAPI Backend**: Modern async web framework
- **SQLAlchemy ORM**: Database management
- **Background Tasks**: Continuous data ingestion
- **Service Layer**: Modular architecture for maintainability

### Data Flow
1. **VATSIM API** → **Data Service** → **Database**
2. **Traffic Analysis** → **Movement Detection** → **Dashboard**
3. **Real-time Updates** → **User Interface**

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- pip

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd vatsim-data

# Install dependencies
pip install -r requirements.txt

# Initialize database with Australian airports
python init_australian_airports.py

# Start the server
python run.py
```

### Access URLs
- **Main Dashboard**: http://localhost:8000/
- **Traffic Dashboard**: http://localhost:8000/traffic-dashboard
- **Graph Dashboard**: http://localhost:8000/graph-dashboard
- **API Documentation**: http://localhost:8000/docs

## 📊 Monitored Airports

### Australia's 5 Largest Airports
1. **YSSY** - Sydney Airport
2. **YMML** - Melbourne Airport
3. **YBBN** - Brisbane Airport
4. **YPPH** - Perth Airport
5. **YBCG** - Gold Coast Airport

### Additional Airports
- **YBCS** - Cairns Airport
- **YPDN** - Darwin Airport
- **YSCB** - Canberra Airport
- **YBAF** - Archerfield Airport

## 🔧 Configuration

### Movement Detection Parameters
- **Detection Radius**: 10 nautical miles
- **Altitude Thresholds**: 1000ft (departure), 3000ft (arrival)
- **Speed Thresholds**: 50 knots (departure), 150 knots (arrival)
- **Confidence Threshold**: 0.7

### Data Collection
- **Update Interval**: 30 seconds
- **Data Retention**: Configurable
- **Database**: SQLite (optimized for performance)

## 📈 Current Status

The system is actively collecting VATSIM data and monitoring Australian airports. Traffic movements are detected when flights come within the configured detection radius of monitored airports.

## 🛡️ Error Handling

- **Graceful Degradation**: System continues operating even if VATSIM API is unavailable
- **Logging**: Comprehensive logging for debugging and monitoring
- **Data Validation**: Input validation and error recovery
- **Connection Retry**: Automatic retry for network issues

## 🔮 Future Enhancements

- **Historical Analytics**: Long-term trend analysis
- **Predictive Modeling**: Traffic pattern prediction
- **Multi-region Support**: Expand beyond Australia
- **Advanced Visualizations**: 3D maps and real-time tracking
- **Alert System**: Custom notifications for specific events

## 📝 License

This project is for educational and research purposes related to air traffic simulation.

## 🤝 Contributing

Contributions are welcome! Please ensure all code follows the project's architecture principles and includes appropriate tests.

---

*Last updated: July 2025*
