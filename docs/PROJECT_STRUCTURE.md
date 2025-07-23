# Project Structure

## 📁 Directory Overview

```
VATSIM data/
├── app/                          # Main application code
│   ├── __init__.py
│   ├── main.py                   # FastAPI application & routes
│   ├── config.py                 # Configuration management
│   ├── database.py               # Database connection & setup
│   ├── models.py                 # SQLAlchemy models
│   ├── data_ingestion.py         # Data ingestion service
│   ├── vatsim_client.py         # VATSIM API client
│   ├── services/                 # Business logic services
│   │   ├── data_service.py       # Data processing service
│   │   ├── traffic_analysis_service.py  # Traffic analysis
│   │   ├── vatsim_service.py    # VATSIM data service
│   │   └── ml_service.py        # Machine learning service
│   └── utils/                    # Utility functions
│       └── logging.py           # Logging configuration
├── frontend/                     # Frontend assets
│   ├── index.html               # Main dashboard
│   ├── sprint3.html             # Sprint 3 dashboard
│   └── unattended_dashboard.html # Unattended sessions
├── data/                        # Data storage
├── docs/                        # Documentation
├── logs/                        # Application logs
├── atc_optimization.db          # SQLite database
├── airport_coordinates.json     # Airport data
├── requirements.txt             # Python dependencies
├── run.py                      # Application entry point
└── README.md                   # Project documentation
```

## 🔧 Core Components

### Backend (app/)
- **main.py**: FastAPI application with all endpoints
- **config.py**: Environment configuration and settings
- **database.py**: Database connection and initialization
- **models.py**: SQLAlchemy ORM models
- **services/**: Business logic layer
  - **data_service.py**: Handles data ingestion and processing
  - **traffic_analysis_service.py**: Traffic movement detection
  - **vatsim_service.py**: VATSIM API integration
  - **ml_service.py**: Machine learning capabilities

### Frontend (frontend/)
- **index.html**: Main dashboard interface
- **sprint3.html**: Enhanced dashboard features
- **unattended_dashboard.html**: Unattended session monitoring

### Data Storage
- **atc_optimization.db**: SQLite database with all collected data
- **airport_coordinates.json**: Airport location data
- **data/**: Directory for additional data files
- **logs/**: Application log files

## 🚀 Key Features

### Real-time Data Collection
- VATSIM network integration
- Automatic data ingestion every 30 seconds
- Traffic movement detection
- Database persistence

### Dashboards
- **Main Dashboard**: System overview and status
- **Traffic Dashboard**: Airport activity monitoring
- **Graph Dashboard**: Interactive charts and analytics

### API Endpoints
- RESTful API for data access
- Real-time status updates
- Traffic movement queries
- Regional summaries

## 📊 Data Models

### Core Entities
- **Flight**: Aircraft position and status
- **Controller**: ATC controller information
- **TrafficMovement**: Detected arrivals/departures
- **AirportConfig**: Airport configuration data

### Relationships
- Flights → TrafficMovements (one-to-many)
- Airports → TrafficMovements (one-to-many)
- Controllers → Sectors (one-to-many)

## 🔄 Data Flow

1. **VATSIM API** → **vatsim_service.py**
2. **Data Processing** → **data_service.py**
3. **Traffic Analysis** → **traffic_analysis_service.py**
4. **Database Storage** → **SQLite**
5. **Dashboard Display** → **Frontend**

## 🛠️ Configuration

### Environment Variables
- Database connection settings
- VATSIM API configuration
- Logging levels
- Detection parameters

### Detection Parameters
- Movement detection radius
- Altitude thresholds
- Speed thresholds
- Confidence scoring

## 📈 Monitoring

### Logs
- Application logs in `logs/` directory
- Error tracking and debugging
- Performance monitoring

### Database
- SQLite database with optimized queries
- Data retention policies
- Backup and recovery procedures

---

*Last updated: July 2025* 