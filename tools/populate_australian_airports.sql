-- ===========================================
-- POPULATE AUSTRALIAN AIRPORTS
-- ===========================================
-- This script populates the airport_config table with Australian airports
-- from the airport_coordinates.json file

-- Clear existing Australian airports to avoid duplicates
DELETE FROM airport_config WHERE airport_code LIKE 'Y%';

-- Insert Australian airports from airport_coordinates.json
INSERT INTO airport_config (airport_code, airport_name, latitude, longitude, country, region, facility_type) VALUES
('YBBN', 'Brisbane Airport', -27.3842, 153.1175, 'Australia', 'Queensland', 'airport'),
('YSSY', 'Sydney Kingsford Smith Airport', -33.9399, 151.1753, 'Australia', 'New South Wales', 'airport'),
('YMML', 'Melbourne Airport', -37.8136, 144.9631, 'Australia', 'Victoria', 'airport'),
('YPPH', 'Perth Airport', -31.9403, 115.9669, 'Australia', 'Western Australia', 'airport'),
('YSCL', 'Adelaide Airport', -34.9454, 138.5306, 'Australia', 'South Australia', 'airport'),
('YBCS', 'Cairns Airport', -16.8858, 145.7553, 'Australia', 'Queensland', 'airport'),
('YPDN', 'Darwin International Airport', -12.4083, 130.8725, 'Australia', 'Northern Territory', 'airport'),
('YBRM', 'Broome International Airport', -17.9447, 122.2325, 'Australia', 'Western Australia', 'airport'),
('YBAF', 'Brisbane West Wellcamp Airport', -27.4067, 151.4772, 'Australia', 'Queensland', 'airport'),
('YMAV', 'Avalon Airport', -38.0394, 144.4694, 'Australia', 'Victoria', 'airport'),
('YBRK', 'Rockhampton Airport', -23.3819, 150.4753, 'Australia', 'Queensland', 'airport'),
('YBCG', 'Gold Coast Airport', -28.1644, 153.5047, 'Australia', 'Queensland', 'airport'),
('YBTL', 'Townsville Airport', -19.2525, 146.7656, 'Australia', 'Queensland', 'airport'),
('YBRN', 'Burnie Airport', -41.0578, 145.9039, 'Australia', 'Tasmania', 'airport'),
('YBAS', 'Alice Springs Airport', -23.8067, 133.9022, 'Australia', 'Northern Territory', 'airport'),
('YPDL', 'Devonport Airport', -41.1697, 146.4303, 'Australia', 'Tasmania', 'airport'),
('YPPN', 'Proserpine Airport', -20.4950, 148.5522, 'Australia', 'Queensland', 'airport');

-- Verify the data was inserted
SELECT 
    airport_code,
    airport_name,
    country,
    region
FROM airport_config 
WHERE airport_code LIKE 'Y%'
ORDER BY airport_code; 