-- Query to find most popular routes by military aircraft from last week
-- Using flight_summaries table for completed flights with route information

SELECT 
    fs.departure,
    fs.arrival,
    fs.aircraft_type,
    COUNT(*) as total_flights,
    COUNT(DISTINCT fs.cid) as unique_pilots,
    ROUND(
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 
        2
    ) as percentage_of_total_military_flights,
    ROUND(
        COUNT(DISTINCT fs.cid) * 100.0 / SUM(COUNT(DISTINCT fs.cid)) OVER (), 
        2
    ) as percentage_of_total_military_pilots
FROM flight_summaries fs
WHERE 
    fs.aircraft_type IN (
        -- Russian/Soviet Fighters & Interceptors
        'MIG21', 'MIG23', 'MIG25', 'MIG29', 'MIG31', 'MIG35', 'MIG41',
        'SU27', 'SU30', 'SU33', 'SU34', 'SU35', 'SU37', 'SU57', 'SU75',
        'TU22', 'TU95', 'TU160', 'TU22M', 'TU95MS', 'TU160M',
        
        -- US Fighters & Attack Aircraft
        'F14', 'F15', 'F16', 'F18', 'F18S', 'F22', 'F35', 'F4', 'F5',
        'F111', 'F117', 'A4', 'A6', 'A7', 'A10', 'A12', 'AV8', 'F15E',
        'F16C', 'F16D', 'F18C', 'F18D', 'F18E', 'F18F', 'F22A', 'F35A',
        'F35B', 'F35C', 'F4E', 'F5E', 'F5F', 'F111F', 'F117A',
        
        -- European Fighters
        'TYPH', 'RAF', 'GRIP', 'MIR2', 'MIR4', 'HAR', 'JAG', 'TORN',
        'VIGG', 'M2K', 'RAPH', 'EF2K', 'GR4', 'FGR4', 'TORN', 'VIGG',
        'MIR2', 'MIR4', 'HAR', 'JAG', 'TORN', 'VIGG', 'M2K', 'RAPH',
        'EF2K', 'GR4', 'FGR4', 'TYPH', 'RAF', 'GRIP', 'MIR2', 'MIR4',
        
        -- Bombers & Strategic Aircraft
        'B1', 'B2', 'B21', 'B52', 'B1B', 'B2A', 'B21A', 'B52H',
        'SR71', 'U2', 'TR1', 'SR72', 'U2S', 'TR1A', 'SR71A', 'U2R',
        
        -- Military Transport Aircraft
        'C130', 'C17', 'C5', 'C141', 'C160', 'C27', 'C295', 'C130J',
        'C17A', 'C5M', 'C141B', 'C160R', 'C27J', 'C295M', 'HERC',
        'A400', 'IL76', 'AN124', 'AN225', 'C17A', 'C5M', 'C141B',
        
        -- Military Helicopters
        'H60', 'H64', 'H47', 'H53', 'H1', 'H2', 'H3', 'H6', 'H8',
        'AH64', 'AH1', 'AH6', 'AH1Z', 'AH64E', 'CH47', 'CH53', 'CH60',
        'MH60', 'MH47', 'MH53', 'MH6', 'MH8', 'UH60', 'UH1', 'UH72',
        
        -- Military Patrol & Reconnaissance
        'P3', 'P8', 'P1', 'P3C', 'P8A', 'P1A', 'E2', 'E3', 'E4', 'E6',
        'E8', 'E2C', 'E3A', 'E4B', 'E6B', 'E8C', 'RC135', 'U2S', 'TR1A',
        
        -- Military Trainers
        'T38', 'T45', 'T6', 'T1', 'T38A', 'T45A', 'T6A', 'T1A',
        'T50', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12', 'T13', 'T14',
        
        -- Military Drones & UAVs
        'MQ1', 'MQ9', 'MQ1C', 'MQ9A', 'MQ1B', 'MQ9B', 'MQ1D', 'MQ9C',
        'RQ4', 'RQ7', 'RQ11', 'RQ170', 'RQ180', 'RQ4A', 'RQ7B', 'RQ11B',
        
        -- Additional Military Aircraft
        'F18S', 'F18T', 'F18U', 'F18V', 'F18W', 'F18X', 'F18Y', 'F18Z',
        'MIG21B', 'MIG21F', 'MIG21M', 'MIG21S', 'MIG21U', 'MIG21UM',
        'SU27M', 'SU27S', 'SU27UB', 'SU27SM', 'SU27SM3', 'SU27UBM',
        'F15C', 'F15D', 'F15E', 'F15EX', 'F15I', 'F15K', 'F15S', 'F15SG',
        'F16A', 'F16B', 'F16C', 'F16D', 'F16E', 'F16F', 'F16I', 'F16V',
        
        -- Experimental & Prototype Military Aircraft
        'X35', 'X47', 'YF23', 'YF22', 'X35A', 'X35B', 'X35C', 'X47A',
        'X47B', 'YF23A', 'YF22A', 'X35D', 'X47C', 'YF23B', 'YF22B',
        
        -- Military Aircraft with Pattern Matching
        'F-%', 'MIG%', 'SU-%', 'TU-%', 'MIR%', 'A-%', 'B-%', 'C-%',
        'E-%', 'H-%', 'P-%', 'T-%', 'V-%', 'X-%', 'Y-%', 'Z-%',
        'MQ%', 'RQ%', 'AH%', 'CH%', 'MH%', 'UH%', 'RC%', 'TR%'
    )
    -- Only include completed flights from last week
    AND fs.completion_time >= NOW() - INTERVAL '1 week'
    -- Ensure we have valid departure and arrival data
    AND fs.departure IS NOT NULL 
    AND fs.arrival IS NOT NULL
    AND fs.departure != ''
    AND fs.arrival != ''
GROUP BY fs.departure, fs.arrival, fs.aircraft_type
ORDER BY total_flights DESC, unique_pilots DESC, fs.aircraft_type;

