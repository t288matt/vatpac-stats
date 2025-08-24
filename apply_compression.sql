-- ============================================================================
-- APPLY LZ4 COMPRESSION TO EXISTING TABLES
-- ============================================================================
-- This script applies LZ4 compression to large TEXT fields that benefit from compression
-- LZ4 provides fastest compression/decompression - perfect for VATSIM 60-second polling
-- Run this on your existing database to enable compression immediately

-- High-priority TEXT fields (constantly written, frequently exceed 2KB)
ALTER TABLE flights ALTER COLUMN route SET COMPRESSION lz4;
ALTER TABLE flights ALTER COLUMN remarks SET COMPRESSION lz4;
ALTER TABLE controllers ALTER COLUMN text_atis SET COMPRESSION lz4;

-- Archive and summary TEXT fields (historical data, can be very long)
ALTER TABLE flights_archive ALTER COLUMN route SET COMPRESSION lz4;
ALTER TABLE flight_summaries ALTER COLUMN route SET COMPRESSION lz4;
ALTER TABLE controllers_archive ALTER COLUMN text_atis SET COMPRESSION lz4;

-- ============================================================================
-- COMPRESSION APPLIED SUCCESSFULLY
-- ============================================================================
-- Note: Existing data will be compressed when next updated
-- Future writes will use LZ4 compression automatically
-- No downtime required - tables remain accessible during compression
-- LZ4 provides excellent performance for your VATSIM use case
