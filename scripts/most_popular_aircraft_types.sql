-- Most Popular Aircraft Types by Flights Flown
-- 
-- This query finds which aircraft types are most popular based on
-- the number of flights flown, including detailed statistics.
--
-- Usage:
--   docker exec vatsim_postgres psql -U vatsim_user -d vatsim_data -f scripts/most_popular_aircraft_types.sql
--

-- Aircraft category summary only (detailed rankings removed)

-- ============================================================================
-- SUMMARY STATISTICS BY AIRCRAFT CATEGORY
-- ============================================================================
-- This section provides summary statistics grouped by aircraft categories

WITH aircraft_categories AS (
    SELECT 
        aircraft_type,
        name,
        cid,
        total_enroute_time_minutes,
        time_online_minutes,
        controller_callsigns,
        controller_time_percentage,
        -- Categorize aircraft by type with more specific groupings
        CASE 
            -- Airbus Family (Check first to avoid conflicts)
            WHEN aircraft_type LIKE '%A320%' OR aircraft_type LIKE '%A321%' OR aircraft_type LIKE '%A319%' OR aircraft_type LIKE '%A20N%' OR aircraft_type = 'A20N' THEN 'Airbus A320 Family'
            WHEN aircraft_type LIKE '%A350%' OR aircraft_type LIKE '%A35%' THEN 'Airbus A350 Family'
            WHEN aircraft_type LIKE '%A330%' OR aircraft_type LIKE '%A33%' THEN 'Airbus A330 Family'
            WHEN aircraft_type LIKE '%A380%' OR aircraft_type LIKE '%A38%' THEN 'Airbus A380 Family'
            WHEN aircraft_type LIKE '%A21%' AND aircraft_type NOT LIKE '%A20N%' THEN 'Airbus A220 Family'
            
            -- Boeing Family
            WHEN aircraft_type LIKE '%B738%' OR aircraft_type LIKE '%B737%' OR aircraft_type LIKE '%B38%' THEN 'Boeing 737 Family'
            WHEN aircraft_type LIKE '%B788%' OR aircraft_type LIKE '%B789%' THEN 'Boeing 787 Family'
            WHEN aircraft_type LIKE '%B77%' THEN 'Boeing 777 Family'
            WHEN aircraft_type LIKE '%B74%' THEN 'Boeing 747 Family'
            WHEN aircraft_type LIKE '%B76%' THEN 'Boeing 767 Family'
            
            -- Regional Jets
            WHEN aircraft_type LIKE '%RJ%' OR aircraft_type LIKE '%CRJ%' OR aircraft_type LIKE '%ERJ%' THEN 'Regional Jets'
            WHEN aircraft_type LIKE '%AT7%' OR aircraft_type LIKE '%ATR%' THEN 'ATR Turboprops'
            WHEN aircraft_type LIKE '%DH8%' OR aircraft_type LIKE '%DHC%' THEN 'De Havilland Canada'
            WHEN aircraft_type LIKE '%SF3%' OR aircraft_type LIKE '%SAAB%' THEN 'Saab Turboprops'
            
            -- Business Jets (Comprehensive Category)
            WHEN aircraft_type LIKE '%C750%' OR aircraft_type LIKE '%C700%' OR aircraft_type LIKE '%C680%' OR aircraft_type LIKE '%CIT%' OR aircraft_type LIKE '%C%' THEN 'Business Jets'
            WHEN aircraft_type LIKE '%PC12%' OR aircraft_type LIKE '%PC24%' OR aircraft_type LIKE '%PC21%' THEN 'Business Jets'
            WHEN aircraft_type LIKE '%GULF%' OR aircraft_type LIKE '%G550%' OR aircraft_type LIKE '%G650%' OR aircraft_type LIKE '%GLF%' THEN 'Business Jets'
            WHEN aircraft_type LIKE '%FALC%' OR aircraft_type LIKE '%FA50%' OR aircraft_type LIKE '%FA900%' THEN 'Business Jets'
            WHEN aircraft_type LIKE '%LEAR%' OR aircraft_type LIKE '%LJ%' THEN 'Business Jets'
            WHEN aircraft_type LIKE '%HAWK%' OR aircraft_type LIKE '%HS%' THEN 'Business Jets'
            WHEN aircraft_type LIKE '%CHALL%' OR aircraft_type LIKE '%CL%' OR aircraft_type LIKE '%CL60%' THEN 'Business Jets'
            WHEN aircraft_type LIKE '%TBM%' OR aircraft_type LIKE '%TBM9%' THEN 'Business Jets'
            
            -- General Aviation
            WHEN aircraft_type LIKE '%C172%' OR aircraft_type LIKE '%C152%' OR aircraft_type LIKE '%C182%' OR aircraft_type LIKE '%C208%' OR aircraft_type LIKE '%C310%' OR aircraft_type LIKE '%C337%' OR aircraft_type LIKE '%C404%' THEN 'Cessna Props'
            WHEN aircraft_type LIKE '%PA28%' OR aircraft_type LIKE '%PA32%' OR aircraft_type LIKE '%PA44%' THEN 'Piper Aircraft'
            WHEN aircraft_type LIKE '%DA40%' OR aircraft_type LIKE '%DA42%' OR aircraft_type LIKE '%DA62%' THEN 'Diamond Aircraft'
            WHEN aircraft_type LIKE '%BEECH%' OR aircraft_type LIKE '%BE%' OR aircraft_type LIKE '%BARON%' THEN 'Beechcraft Aircraft'
            WHEN aircraft_type LIKE '%MOONEY%' OR aircraft_type LIKE '%M20%' THEN 'Mooney Aircraft'
            
            -- Military Aircraft (Comprehensive Category)
            WHEN aircraft_type LIKE '%F%' AND aircraft_type ~ '^[A-Z][0-9]' THEN 'Military Aircraft'
            WHEN aircraft_type LIKE '%F16%' OR aircraft_type LIKE '%F18%' OR aircraft_type LIKE '%F15%' THEN 'Military Aircraft'
            WHEN aircraft_type LIKE '%F35%' OR aircraft_type LIKE '%F22%' THEN 'Military Aircraft'
            WHEN aircraft_type LIKE '%F111%' OR aircraft_type LIKE '%F18S%' THEN 'Military Aircraft'
            WHEN aircraft_type LIKE '%C130%' OR aircraft_type LIKE '%C17%' OR aircraft_type LIKE '%C5%' THEN 'Military Aircraft'
            WHEN aircraft_type LIKE '%KC%' OR aircraft_type LIKE '%TANKER%' THEN 'Military Aircraft'
            WHEN aircraft_type LIKE '%P3%' OR aircraft_type LIKE '%P8%' THEN 'Military Aircraft'
            WHEN aircraft_type LIKE '%MIG%' OR aircraft_type LIKE '%SU%' THEN 'Military Aircraft'
            WHEN aircraft_type LIKE '%MIR%' OR aircraft_type LIKE '%MIRAGE%' THEN 'Military Aircraft'
            WHEN aircraft_type LIKE '%TOR%' OR aircraft_type LIKE '%TORNADO%' THEN 'Military Aircraft'
            WHEN aircraft_type LIKE '%HAR%' OR aircraft_type LIKE '%HARRIER%' THEN 'Military Aircraft'
            WHEN aircraft_type LIKE '%CH%' OR aircraft_type LIKE '%UH%' OR aircraft_type LIKE '%AH%' THEN 'Military Aircraft'
            WHEN aircraft_type LIKE '%H60%' OR aircraft_type LIKE '%UH60%' THEN 'Military Aircraft'
            WHEN aircraft_type LIKE '%PTS%' OR aircraft_type LIKE '%PARATROOPER%' THEN 'Military Aircraft'
            
            -- Helicopters (Comprehensive Category)
            WHEN aircraft_type LIKE '%H%' OR aircraft_type LIKE '%HELI%' OR aircraft_type LIKE '%ROTOR%' OR aircraft_type LIKE '%R%' OR aircraft_type LIKE '%ROBIN%' OR aircraft_type LIKE '%ROBINSON%' OR aircraft_type LIKE '%GYRO%' OR aircraft_type LIKE '%AUTO%' THEN 'Helicopters'
            
            -- Vintage/Classic Aircraft
            WHEN aircraft_type LIKE '%DC3%' OR aircraft_type LIKE '%DC6%' OR aircraft_type LIKE '%DC9%' THEN 'Douglas Classic Aircraft'
            WHEN aircraft_type LIKE '%CONC%' OR aircraft_type LIKE '%CONCORDE%' THEN 'Concorde'
            WHEN aircraft_type LIKE '%SPIT%' OR aircraft_type LIKE '%MUSTANG%' OR aircraft_type LIKE '%WARBIRD%' THEN 'Warbirds'
            
            -- Special Purpose
            WHEN aircraft_type LIKE '%GLID%' OR aircraft_type LIKE '%SAILPLANE%' THEN 'Gliders'
            WHEN aircraft_type LIKE '%BALLOON%' OR aircraft_type LIKE '%AIRSHIP%' THEN 'Lighter Than Air'
            
            -- Additional Boeing Models (Already covered in main Boeing families)
            -- All Boeing 737 variants now consolidated into Boeing 737 Family above
            WHEN aircraft_type LIKE '%B58%' THEN 'Beechcraft Baron'
            WHEN aircraft_type LIKE '%B350%' THEN 'Beechcraft King Air'
            
            -- Additional Airbus Models
            WHEN aircraft_type LIKE '%A30%' AND aircraft_type NOT LIKE '%A20N%' THEN 'Airbus A300/A310'
            WHEN aircraft_type LIKE '%A31%' THEN 'Airbus A310'
            WHEN aircraft_type LIKE '%A32%' THEN 'Airbus A320 Variants'
            WHEN aircraft_type LIKE '%A33%' THEN 'Airbus A330 Variants'
            WHEN aircraft_type LIKE '%A34%' THEN 'Airbus A340 Variants'
            WHEN aircraft_type LIKE '%A35%' THEN 'Airbus A350 Variants'
            WHEN aircraft_type LIKE '%A38%' THEN 'Airbus A380 Variants'
            WHEN aircraft_type LIKE '%A225%' THEN 'Antonov An-225'
            
            -- Embraer Aircraft
            WHEN aircraft_type LIKE '%E1%' OR aircraft_type LIKE '%E2%' OR aircraft_type LIKE '%EMB%' THEN 'Embraer Regional Jets'
            WHEN aircraft_type LIKE '%ERJ%' OR aircraft_type LIKE '%E17%' OR aircraft_type LIKE '%E19%' THEN 'Embraer ERJ Series'
            
            -- Bombardier Aircraft
            WHEN aircraft_type LIKE '%CRJ%' OR aircraft_type LIKE '%CL%' THEN 'Bombardier Regional Jets'
            WHEN aircraft_type LIKE '%Q%' OR aircraft_type LIKE '%DASH%' THEN 'Bombardier Q Series'
            
            -- Additional Regional Aircraft
            WHEN aircraft_type LIKE '%ATR%' OR aircraft_type LIKE '%AT%' THEN 'ATR Turboprops'
            WHEN aircraft_type LIKE '%FOKKER%' OR aircraft_type LIKE '%FK%' THEN 'Fokker Aircraft'
            WHEN aircraft_type LIKE '%BAE%' OR aircraft_type LIKE '%AVRO%' THEN 'BAE Systems Aircraft'
            
            -- Additional Business Jets (Already covered in main Business Jets category)
            
            -- Additional General Aviation
            WHEN aircraft_type LIKE '%CESS%' OR aircraft_type LIKE '%C%' THEN 'Cessna Aircraft'
            WHEN aircraft_type LIKE '%PIPER%' OR aircraft_type LIKE '%PA%' THEN 'Piper Aircraft'
            WHEN aircraft_type LIKE '%DIAM%' OR aircraft_type LIKE '%DA%' THEN 'Diamond Aircraft'
            WHEN aircraft_type LIKE '%BEECH%' OR aircraft_type LIKE '%BE%' THEN 'Beechcraft Aircraft'
            WHEN aircraft_type LIKE '%MOON%' OR aircraft_type LIKE '%M%' THEN 'Mooney Aircraft'
            WHEN aircraft_type LIKE '%GRUMM%' OR (aircraft_type LIKE '%AA%' AND aircraft_type NOT LIKE '%A2%' AND aircraft_type NOT LIKE '%A3%' AND aircraft_type NOT LIKE '%A4%' AND aircraft_type NOT LIKE '%A5%' AND aircraft_type NOT LIKE '%A6%' AND aircraft_type NOT LIKE '%A7%' AND aircraft_type NOT LIKE '%A8%') THEN 'Grumman Aircraft'
            WHEN aircraft_type LIKE '%BELL%' OR aircraft_type LIKE '%BL%' THEN 'Bell Aircraft'
            
            -- Additional Military Aircraft (Already covered in main Military Aircraft category)
            
            -- Vintage/Classic Aircraft
            WHEN aircraft_type LIKE '%DC%' THEN 'Douglas Classic Aircraft'
            WHEN aircraft_type LIKE '%CONC%' OR aircraft_type LIKE '%CONCORDE%' THEN 'Concorde'
            WHEN aircraft_type LIKE '%SPIT%' OR aircraft_type LIKE '%MUSTANG%' OR aircraft_type LIKE '%WARBIRD%' THEN 'Warbirds'
            WHEN aircraft_type LIKE '%LOCK%' OR aircraft_type LIKE '%L%' THEN 'Lockheed Classic Aircraft'
            WHEN aircraft_type LIKE '%BOE%' THEN 'Boeing Classic Aircraft'
            
            -- Experimental and Homebuilt
            WHEN aircraft_type LIKE '%EXP%' OR aircraft_type LIKE '%HOME%' OR aircraft_type LIKE '%BUILT%' THEN 'Experimental Aircraft'
            WHEN aircraft_type LIKE '%ULTR%' OR aircraft_type LIKE '%LIGHT%' THEN 'Ultralight Aircraft'
            
            -- Agricultural and Utility
            WHEN aircraft_type LIKE '%AG%' OR aircraft_type LIKE '%CROP%' OR aircraft_type LIKE '%DUST%' THEN 'Agricultural Aircraft'
            WHEN aircraft_type LIKE '%UTIL%' OR aircraft_type LIKE '%UTILITY%' THEN 'Utility Aircraft'
            WHEN aircraft_type LIKE '%CARGO%' OR aircraft_type LIKE '%FREIGHT%' THEN 'Cargo Aircraft'
            
            -- Seaplanes and Amphibious
            WHEN aircraft_type LIKE '%SEA%' OR aircraft_type LIKE '%FLOAT%' OR aircraft_type LIKE '%AMPH%' THEN 'Seaplanes'
            
            -- Gliders and Sailplanes
            WHEN aircraft_type LIKE '%GLID%' OR aircraft_type LIKE '%SAIL%' OR aircraft_type LIKE '%SOAR%' THEN 'Gliders'
            
            -- Lighter Than Air
            WHEN aircraft_type LIKE '%BALLOON%' OR aircraft_type LIKE '%AIRSHIP%' OR aircraft_type LIKE '%BLIMP%' THEN 'Lighter Than Air'
            
            -- Specific Aircraft Models (Exact Matches)
            WHEN aircraft_type = '172' OR aircraft_type = 'C172' THEN 'Cessna 172'
            WHEN aircraft_type = 'C152' THEN 'Cessna 152'
            WHEN aircraft_type = 'C182' THEN 'Cessna 182'
            WHEN aircraft_type = 'C208' THEN 'Cessna Caravan'
            WHEN aircraft_type = 'C25C' THEN 'Cessna Citation'
            WHEN aircraft_type = 'C310' THEN 'Cessna 310'
            WHEN aircraft_type = 'C337' THEN 'Cessna Skymaster'
            WHEN aircraft_type = 'C404' THEN 'Cessna 404'
            WHEN aircraft_type = 'C510' THEN 'Cessna Citation Mustang'
            WHEN aircraft_type = 'C56X' THEN 'Cessna Citation Excel'
            WHEN aircraft_type = 'C700' THEN 'Cessna Citation Longitude'
            WHEN aircraft_type = 'C750' THEN 'Cessna Citation X'
            WHEN aircraft_type = 'CL60' THEN 'Bombardier Challenger'
            WHEN aircraft_type = 'P28A' THEN 'Piper PA-28'
            WHEN aircraft_type = 'PA24' THEN 'Piper PA-24'
            WHEN aircraft_type = 'PA44' THEN 'Piper PA-44'
            WHEN aircraft_type = 'DA40' THEN 'Diamond DA40'
            WHEN aircraft_type = 'DA42' THEN 'Diamond DA42'
            WHEN aircraft_type = 'DA50' THEN 'Diamond DA50'
            WHEN aircraft_type = 'DA62' THEN 'Diamond DA62'
            WHEN aircraft_type = 'BE10' THEN 'Beechcraft King Air'
            WHEN aircraft_type = 'BE36' THEN 'Beechcraft Bonanza'
            WHEN aircraft_type = 'BE58' THEN 'Beechcraft Baron'
            WHEN aircraft_type = 'BE9L' THEN 'Beechcraft King Air'
            WHEN aircraft_type = 'PC12' THEN 'Pilatus PC-12'
            WHEN aircraft_type = 'PC21' THEN 'Pilatus PC-21'
            WHEN aircraft_type = 'PC24' THEN 'Pilatus PC-24'
            WHEN aircraft_type = 'TBM9' THEN 'TBM TBM-900'
            WHEN aircraft_type = 'SR22' THEN 'Cirrus SR22'
            WHEN aircraft_type = 'MXS' THEN 'MX Aircraft MXS'
            WHEN aircraft_type = 'S22T' THEN 'Cirrus SR22T'
            WHEN aircraft_type = 'SW4' THEN 'Fairchild Swearingen'
            WHEN aircraft_type = 'L410' THEN 'Let L-410'
            WHEN aircraft_type = 'SF34' THEN 'Saab 340'
            WHEN aircraft_type = 'SF50' THEN 'Cirrus Vision SF50'
            WHEN aircraft_type = 'E190' THEN 'Embraer E190'
            WHEN aircraft_type = 'E300' THEN 'Embraer E300'
            WHEN aircraft_type = 'E50P' THEN 'Embraer Phenom'
            WHEN aircraft_type = 'EC45' THEN 'Eurocopter EC145'
            WHEN aircraft_type = 'AS50' THEN 'Eurocopter AS350'
            WHEN aircraft_type = 'H60' THEN 'Sikorsky H-60'
            WHEN aircraft_type = 'UH60' THEN 'Sikorsky UH-60'
            WHEN aircraft_type = 'F111' THEN 'General Dynamics F-111'
            WHEN aircraft_type = 'F18S' THEN 'McDonnell Douglas F-18'
            WHEN aircraft_type = 'F35' THEN 'Lockheed Martin F-35'
            WHEN aircraft_type = 'GLF6' THEN 'Gulfstream G650'
            WHEN aircraft_type = 'CONC' THEN 'Concorde'
            WHEN aircraft_type = 'PTS1' THEN 'Paratrooper Aircraft'
            WHEN aircraft_type = 'RJ70' THEN 'Avro RJ70'
            WHEN aircraft_type = 'P8' THEN 'Boeing P-8 Poseidon'
            WHEN aircraft_type = 'A225' THEN 'Antonov An-225'
            
            ELSE 'Other Aircraft'
        END as aircraft_category
    FROM flight_summaries
    WHERE aircraft_type IS NOT NULL 
        AND aircraft_type != ''
        AND total_enroute_time_minutes > 0
        AND completion_time >= NOW() - INTERVAL '6 months'
),
category_stats AS (
    SELECT 
        aircraft_category,
        COUNT(*) as total_flights,
        COUNT(DISTINCT aircraft_type) as unique_aircraft_types,
        ROUND(AVG(total_enroute_time_minutes), 1) as avg_flight_duration_minutes,
        ROUND(AVG(time_online_minutes), 1) as avg_time_online_minutes,
        ROUND(
            (COUNT(CASE WHEN controller_callsigns IS NOT NULL AND jsonb_typeof(controller_callsigns) = 'object' AND controller_callsigns != '{}' THEN 1 END)::numeric / COUNT(*)) * 100, 1
        ) as percent_with_controllers,
        ROUND(AVG(total_enroute_time_minutes::numeric / NULLIF(time_online_minutes, 0)), 2) as avg_efficiency_ratio
    FROM aircraft_categories
    GROUP BY aircraft_category
)
SELECT 
    aircraft_category as type,
    COUNT(*) as total_flights,
    COUNT(DISTINCT cid) as unique_pilots,
    ROUND(AVG(controller_time_percentage), 1) || '%' as avg_time_with_atc
FROM aircraft_categories
GROUP BY aircraft_category
ORDER BY COUNT(*) DESC;
