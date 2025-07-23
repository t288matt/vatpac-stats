
        -- Enable required extensions
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
        
        -- Controllers table with optimized indexes
        CREATE TABLE IF NOT EXISTS controllers (
            id SERIAL PRIMARY KEY,
            callsign VARCHAR(50) UNIQUE NOT NULL,
            facility VARCHAR(50) NOT NULL,
            position VARCHAR(50),
            status VARCHAR(20) DEFAULT 'offline',
            frequency VARCHAR(20),
            last_seen TIMESTAMPTZ DEFAULT NOW(),
            workload_score FLOAT DEFAULT 0.0,
            preferences JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Optimized indexes for controllers
        CREATE INDEX IF NOT EXISTS idx_controllers_callsign ON controllers(callsign);
        CREATE INDEX IF NOT EXISTS idx_controllers_facility ON controllers(facility);
        CREATE INDEX IF NOT EXISTS idx_controllers_status ON controllers(status);
        CREATE INDEX IF NOT EXISTS idx_controllers_last_seen ON controllers(last_seen);
        
        -- Flights table with partitioning for time-based data
        CREATE TABLE IF NOT EXISTS flights (
            id SERIAL PRIMARY KEY,
            callsign VARCHAR(50) NOT NULL,
            aircraft_type VARCHAR(20),
            position_lat FLOAT,
            position_lng FLOAT,
            altitude INTEGER,
            speed INTEGER,
            heading INTEGER,
            ground_speed INTEGER,
            vertical_speed INTEGER,
            squawk VARCHAR(10),
            flight_plan JSONB,
            last_updated TIMESTAMPTZ DEFAULT NOW(),
            controller_id INTEGER REFERENCES controllers(id),
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Optimized indexes for flights
        CREATE INDEX IF NOT EXISTS idx_flights_callsign ON flights(callsign);
        CREATE INDEX IF NOT EXISTS idx_flights_aircraft_type ON flights(aircraft_type);
        CREATE INDEX IF NOT EXISTS idx_flights_position ON flights(position_lat, position_lng);
        CREATE INDEX IF NOT EXISTS idx_flights_last_updated ON flights(last_updated);
        CREATE INDEX IF NOT EXISTS idx_flights_controller_id ON flights(controller_id);
        
        -- Traffic movements table
        CREATE TABLE IF NOT EXISTS traffic_movements (
            id SERIAL PRIMARY KEY,
            airport_code VARCHAR(10) NOT NULL,
            movement_type VARCHAR(20) NOT NULL,
            aircraft_callsign VARCHAR(50),
            aircraft_type VARCHAR(20),
            timestamp TIMESTAMPTZ DEFAULT NOW(),
            runway VARCHAR(10),
            altitude INTEGER,
            speed INTEGER,
            heading INTEGER,
            metadata JSONB
        );
        
        -- Optimized indexes for traffic movements
        CREATE INDEX IF NOT EXISTS idx_traffic_movements_airport ON traffic_movements(airport_code);
        CREATE INDEX IF NOT EXISTS idx_traffic_movements_type ON traffic_movements(movement_type);
        CREATE INDEX IF NOT EXISTS idx_traffic_movements_timestamp ON traffic_movements(timestamp);
        
        -- System configuration table
        CREATE TABLE IF NOT EXISTS system_config (
            id SERIAL PRIMARY KEY,
            key VARCHAR(100) UNIQUE NOT NULL,
            value TEXT,
            description TEXT,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Events table for system events
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            event_type VARCHAR(50) NOT NULL,
            event_data JSONB,
            timestamp TIMESTAMPTZ DEFAULT NOW(),
            severity VARCHAR(20) DEFAULT 'info'
        );
        
        -- Optimized indexes for events
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_events_severity ON events(severity);
        
        -- Create materialized views for performance
        CREATE MATERIALIZED VIEW IF NOT EXISTS flight_summary AS
        SELECT 
            DATE_TRUNC('hour', last_updated) as hour,
            COUNT(*) as total_flights,
            COUNT(DISTINCT aircraft_type) as unique_aircraft_types,
            AVG(altitude) as avg_altitude,
            AVG(speed) as avg_speed
        FROM flights
        WHERE last_updated > NOW() - INTERVAL '24 hours'
        GROUP BY DATE_TRUNC('hour', last_updated)
        ORDER BY hour;
        
        -- Create indexes on materialized view
        CREATE INDEX IF NOT EXISTS idx_flight_summary_hour ON flight_summary(hour);
        
        -- Create function to refresh materialized view
        CREATE OR REPLACE FUNCTION refresh_flight_summary()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW flight_summary;
        END;
        $$ LANGUAGE plpgsql;
        
        -- Create function to update updated_at timestamp
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        -- Create triggers for updated_at
        CREATE TRIGGER update_controllers_updated_at 
            BEFORE UPDATE ON controllers 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        
        CREATE TRIGGER update_flights_updated_at 
            BEFORE UPDATE ON flights 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        