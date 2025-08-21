-- ICAO to State Mapping for Australian Airports
-- This table maps ICAO codes to Australian states/territories

CREATE TABLE IF NOT EXISTS icao_state_mapping (
    icao_code VARCHAR(4) PRIMARY KEY,
    airport_name VARCHAR(100),
    state VARCHAR(50),
    city VARCHAR(50)
);

-- Insert major Australian airports with their states
INSERT INTO icao_state_mapping (icao_code, airport_name, state, city) VALUES
-- New South Wales
('YSSY', 'Sydney Airport', 'NSW', 'Sydney'),
('YSBK', 'Bankstown Airport', 'NSW', 'Sydney'),
('YSCB', 'Canberra Airport', 'ACT', 'Canberra'),
('YSCN', 'Camden Airport', 'NSW', 'Sydney'),
('YSHL', 'Shellharbour Airport', 'NSW', 'Shellharbour'),
('YSTW', 'Tamworth Airport', 'NSW', 'Tamworth'),

-- Victoria
('YMML', 'Melbourne Airport', 'VIC', 'Melbourne'),
('YMAV', 'Avalon Airport', 'VIC', 'Geelong'),
('YMEN', 'Essendon Airport', 'VIC', 'Melbourne'),
('YMHB', 'Hobart Airport', 'TAS', 'Hobart'),
('YMLT', 'Launceston Airport', 'TAS', 'Launceston'),
('YMMB', 'Moorabbin Airport', 'VIC', 'Melbourne'),
('YTRE', 'Traralgon Airport', 'VIC', 'Traralgon'),

-- Queensland
('YBBN', 'Brisbane Airport', 'QLD', 'Brisbane'),
('YBAF', 'Archerfield Airport', 'QLD', 'Brisbane'),
('YBCG', 'Gold Coast Airport', 'QLD', 'Gold Coast'),
('YBCS', 'Cairns Airport', 'QLD', 'Cairns'),
('YBLN', 'Ballina Airport', 'QLD', 'Ballina'),
('YBMK', 'Mackay Airport', 'QLD', 'Mackay'),
('YBNA', 'Bundaberg Airport', 'QLD', 'Bundaberg'),
('YBRK', 'Rockhampton Airport', 'QLD', 'Rockhampton'),
('YBTL', 'Townsville Airport', 'QLD', 'Townsville'),
('YBUD', 'Bundaberg Airport', 'QLD', 'Bundaberg'),
('YBUN', 'Bundaberg Airport', 'QLD', 'Bundaberg'),

-- Western Australia
('YPAD', 'Adelaide Airport', 'SA', 'Adelaide'),
('YPPH', 'Port Hedland Airport', 'WA', 'Port Hedland'),
('YPJT', 'Perth Jandakot Airport', 'WA', 'Perth'),
('YPKA', 'Port Augusta Airport', 'SA', 'Port Augusta'),
('YPMQ', 'Port Macquarie Airport', 'NSW', 'Port Macquarie'),
('YPDN', 'Darwin Airport', 'NT', 'Darwin'),

-- South Australia
('YRED', 'Renmark Airport', 'SA', 'Renmark'),

-- Northern Territory
('YGYM', 'Gympie Airport', 'QLD', 'Gympie'),

-- Tasmania
('YHBA', 'Hobart Airport', 'TAS', 'Hobart'),
('YHML', 'Hamilton Airport', 'VIC', 'Hamilton'),

-- Other major airports
('YTWB', 'Toowoomba Airport', 'QLD', 'Toowoomba'),
('YTYA', 'Townsville Airport', 'QLD', 'Townsville'),
('YUAN', 'Newcastle Airport', 'NSW', 'Newcastle'),
('YCDR', 'Caloundra Airport', 'QLD', 'Caloundra'),
('YDPO', 'Devonport Airport', 'TAS', 'Devonport'),
('YGIG', 'Gladstone Airport', 'QLD', 'Gladstone'),
('YKTN', 'Katherine Airport', 'NT', 'Katherine'),
('YLIL', 'Lilydale Airport', 'VIC', 'Lilydale'),
('YMAY', 'Maryborough Airport', 'QLD', 'Maryborough'),
('YMND', 'Melbourne Airport', 'VIC', 'Melbourne'),
('YSCB', 'Canberra Airport', 'ACT', 'Canberra'),
('YSHL', 'Shellharbour Airport', 'NSW', 'Shellharbour'),
('YWLM', 'Williamtown Airport', 'NSW', 'Newcastle'),
('YWVA', 'Wagga Wagga Airport', 'NSW', 'Wagga Wagga');

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_icao_state_mapping_icao ON icao_state_mapping(icao_code);
CREATE INDEX IF NOT EXISTS idx_icao_state_mapping_state ON icao_state_mapping(state);
