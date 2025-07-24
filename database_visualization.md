# PostgreSQL Database Visualization

## 📊 Database Overview

The VATSIM Data Collection System uses a **PostgreSQL database** with the following characteristics:

- **Database Name**: `vatsim_data`
- **User**: `vatsim_user`
- **Tables**: 10 main tables + 2 system tables
- **Current Status**: Fresh database (no data yet)
- **Architecture**: Optimized for real-time VATSIM data collection

## 🗂️ Database Schema

### Core Tables

#### 1. **controllers** (0 records)
**Purpose**: Stores VATSIM ATC controller information
```
┌─────────────────┬─────────────────────┬─────────────┐
│ Column          │ Type                │ Description │
├─────────────────┼─────────────────────┼─────────────┤
│ id              │ INTEGER (PK)        │ Unique ID   │
│ callsign        │ VARCHAR(50) (UNIQUE)│ Controller  │
│ facility        │ VARCHAR(50)         │ Facility    │
│ position        │ VARCHAR(50)         │ Position    │
│ status          │ VARCHAR(20)         │ online/offline│
│ frequency       │ VARCHAR(20)         │ Radio freq  │
│ last_seen       │ TIMESTAMP           │ Last active │
│ workload_score  │ DOUBLE PRECISION    │ Workload    │
│ preferences     │ JSONB               │ Settings    │
│ created_at      │ TIMESTAMP           │ Created     │
│ updated_at      │ TIMESTAMP           │ Updated     │
└─────────────────┴─────────────────────┴─────────────┘
```

#### 2. **flights** (0 records)
**Purpose**: Stores active flight information
```
┌─────────────────┬─────────────────────┬─────────────┐
│ Column          │ Type                │ Description │
├─────────────────┼─────────────────────┼─────────────┤
│ id              │ INTEGER (PK)        │ Unique ID   │
│ callsign        │ VARCHAR(50)         │ Flight #    │
│ aircraft_type   │ VARCHAR(20)         │ Aircraft    │
│ position_lat    │ DOUBLE PRECISION    │ Latitude    │
│ position_lng    │ DOUBLE PRECISION    │ Longitude   │
│ altitude        │ INTEGER             │ Altitude    │
│ speed           │ INTEGER             │ Air speed   │
│ heading         │ INTEGER             │ Direction   │
│ ground_speed    │ INTEGER             │ Ground speed│
│ vertical_speed  │ INTEGER             │ Climb/desc  │
│ squawk          │ VARCHAR(10)         │ Transponder │
│ flight_plan     │ JSONB               │ Route data  │
│ last_updated    │ TIMESTAMP           │ Last update │
│ controller_id   │ INTEGER (FK)        │ Controller  │
│ created_at      │ TIMESTAMP           │ Created     │
│ departure       │ VARCHAR(10)         │ Origin      │
│ arrival         │ VARCHAR(10)         │ Destination │
│ route           │ TEXT                │ Flight plan │
│ status          │ VARCHAR(20)         │ Active/etc  │
└─────────────────┴─────────────────────┴─────────────┘
```

#### 3. **sectors** (0 records)
**Purpose**: Stores airspace sector information
```
┌─────────────────┬─────────────────────┬─────────────┐
│ Column          │ Type                │ Description │
├─────────────────┼─────────────────────┼─────────────┤
│ id              │ INTEGER (PK)        │ Unique ID   │
│ name            │ VARCHAR(100)        │ Sector name │
│ facility        │ VARCHAR(50)         │ Facility    │
│ controller_id   │ INTEGER (FK)        │ Controller  │
│ traffic_density │ INTEGER             │ Traffic     │
│ status          │ VARCHAR(20)         │ Active/etc  │
│ priority_level  │ INTEGER             │ Priority    │
│ boundaries      │ TEXT                │ Coordinates │
└─────────────────┴─────────────────────┴─────────────┘
```

### Analytics Tables

#### 4. **flight_summaries** (0 records)
**Purpose**: Aggregated flight statistics

#### 5. **traffic_movements** (0 records)
**Purpose**: Traffic flow analysis

#### 6. **movement_summaries** (0 records)
**Purpose**: Movement pattern analysis

### Configuration Tables

#### 7. **airport_config** (13 columns)
**Purpose**: Airport-specific configurations

#### 8. **movement_detection_config** (6 columns)
**Purpose**: Movement detection settings

#### 9. **system_config** (5 columns)
**Purpose**: System-wide settings

#### 10. **events** (5 columns)
**Purpose**: Scheduled events and activities

## 🔗 Relationships

```
controllers (1) ──── (N) flights
controllers (1) ──── (N) sectors
controllers (1) ──── (N) flight_summaries
```

## 📈 Database Features

### Indexes (Performance Optimization)
- **controllers**: callsign, facility, last_seen, status
- **flights**: callsign, aircraft_type, departure, arrival, position, last_updated
- **Composite indexes** for efficient queries

### Triggers
- **Automatic timestamps**: `created_at` and `updated_at` fields
- **Data integrity**: Foreign key constraints

### Data Types
- **JSONB**: For flexible flight plans and preferences
- **TIMESTAMP WITH TIME ZONE**: For accurate time tracking
- **DOUBLE PRECISION**: For precise coordinates

## 🚀 Current Status

**Database is fresh and ready for data collection:**
- ✅ All tables created
- ✅ Indexes optimized
- ✅ Triggers configured
- ✅ Foreign keys established
- ⏳ Waiting for VATSIM data ingestion

## 📊 Expected Data Volume

Based on the previous SQLite database:
- **Controllers**: ~400 active controllers
- **Flights**: ~3,500 active flights
- **Sectors**: ~5 airspace sectors
- **Real-time updates**: Every 30 seconds

## 🔧 Management Commands

```bash
# Connect to database
docker compose exec postgres psql -U vatsim_user -d vatsim_data

# View table structure
\d table_name

# Count records
SELECT COUNT(*) FROM table_name;

# View recent data
SELECT * FROM table_name ORDER BY created_at DESC LIMIT 10;
```

## 🎯 Next Steps

1. **Start data collection** to populate the database
2. **Monitor performance** with the built-in indexes
3. **Analyze traffic patterns** using the analytics tables
4. **Generate reports** from the summary tables 