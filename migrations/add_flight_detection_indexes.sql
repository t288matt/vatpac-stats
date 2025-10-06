-- Flight Detection Performance Optimization Indexes
-- Added to improve flight detection query performance and reduce timeouts

-- Flight transceivers frequency + time optimization
-- This index helps with frequency-based filtering for flight transceivers
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_flight_frequency_time_optimized 
ON transceivers (frequency, timestamp) 
WHERE entity_type = 'flight';

-- General frequency index for transceivers
-- This index helps with general frequency-based queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transceivers_frequency_concurrent 
ON transceivers (frequency);
